# -*- coding: utf-8 -*-
"""Circuito de otimizacao: busca em OHLC, conferencia em ticks reais.

O PORQUE, medido nesta EA:

A divergencia entre o modo OHLC e ticks reais nao e uniforme. Os sinais sao
avaliados no FECHAMENTO da barra (anti-repaint, "each selected entry timeframe
is evaluated exactly once when a new bar"), entao escolher indicador, metodo ou
timeframe da o mesmo instante de entrada nos dois modos. Ja stop, alvo e
trailing dependem de QUANDO o preco tocou cada nivel dentro da barra -- e ali o
OHLC subestimou a perda em 3,3x no trailing e 23x no grid, sempre otimista.

A tentacao e otimizar a gestao direto em tick real para fugir disso. Nao vale:
sao milhares de passes a ~35s cada, 11 horas por set -- e, pior, o resultado
ESCONDERIA a divergencia em vez de expo-la, entregando um numero ajustado ao
modelo caro sem nunca revelar que o barato mentia.

Um passe de conferencia custa 35 segundos e responde a mesma pergunta: o
resultado do OHLC se sustenta? Se sim, acabou. Se nao, voce descobre AGORA que
aquele sistema nao aceita busca em OHLC -- que e exatamente a informacao que a
otimizacao cara teria enterrado.

  ESTAGIO 1 (OHLC)  REGIOES: o grupo de Entradas COMPLETO (indicador, metodo,
                    timeframe, applied price, periodos, Stochastic, Ichimoku,
                    ATR), as SAIDAS do sistema (trail/tp/sl conforme o tipo) e
                    as flags de filtro, tudo de uma vez. O genetico roda ATE 3
                    RODADAS (dono: "essa fase pode repetir ate umas 3 vezes")
                    -- relancar continua a mesma busca -- e para cedo se a
                    rodada nao melhorar o retrato. Um TORNEIO de retencao
                    decide entre UM CAMPEAO POR INDICADOR; do vencedor
                    travam-se os inputs DE ESCRITA (enums e bools).
  ESTAGIO 2 (OHLC)  NUMEROS: com a escrita travada, refina os eixos numericos
                    e o ajuste dos filtros que sobreviveram. Bool que morreu
                    na fase 1 leva o setor inteiro junto (GATES) -- "se uma
                    bool nao foi escolhida, nao preciso otimizar aquele setor
                    nas seguintes". Torneio de retencao escolhe.
  ESTAGIO 3 (IS+OOS)  FILTROS DE EXECUCAO: hora, dia e spread -- os ultimos a
                    rodar, otimizando em In-Sample + Out-Sample por decisao
                    do dono. So sao adotados se MELHORAREM a retencao.
  ESTAGIO 4 (ticks reais)  CONFIRMACAO do vencedor unico (~35s por passe):
                    retencao em IS+OOS e divergencia OHLC vs tick real.
                    Reprovou em qualquer uma, nao promove.
  ESTAGIO 5 (ticks reais)  PROVA EM PERCENTUAL: o circuito mediu em Fixed-R
                    com capital base fixo -- scale-invariant, sem juros
                    compostos. A conta real opera em % do saldo. Troca
                    PositionSizeMode para Percentage, repete o passe em tick
                    real e SO ENTAO salva -- a entrega sai no modo provado.

Por que o torneio, e nao "pegar o melhor do estagio 2": o genetico ja procura o
maximo in-sample, entao o primeiro colocado e, por construcao, o ponto que
melhor se ajustou ao trecho que a busca enxergou. Medimos 4 sistemas assim e os
4 reprovaram fora da amostra (retencoes -37%, -84%, -32%, e um +39% que caiu na
divergencia). Reservar as janelas OOS e nunca usa-las para DECIDIR so servia
para constatar o estrago depois que ele estava feito.

Uso:
    python optimize_two_stage.py --symbol EURUSD.HT --sistema 01_SLTP \\
        --variante SELL_MULTI --from 2023.08.01 --to 2026.07.21 --deposit 500
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import monte_carlo_wrx
import optimize_sets as base
from mt5_runner import garantir_terminal_livre

# FASE 1 = DESCOBERTA DE REGIOES (pedido do dono, 2026-07-31): o grupo de
# Entradas COMPLETO -- indicador, metodo, timeframe, applied price, periodos,
# Stochastic inteiro, Ichimoku, ATR -- MAIS as saidas do sistema (respeitando
# o tipo: trail, tp/sl, grid...) e as flags de filtro como liga/desliga.
# "Estamos descobrindo regioes nesse primeiro setor." reescrever() so marca o
# que tem faixa no set daquele sistema, entao a lista pode ser superconjunto:
# eixo que nao existe ali e ignorado.
REGIOES = ["TimeFrame", "EntryIndicator", "InpAppliedPrice", "Fast_EMA",
           "Slow_EMA", "MACD_SMA", "EntryMethod",
           "StochasticSlowing", "StochasticMethod", "StochasticPriceField",
           "IchimokuUseKumo", "IchimokuChikouFilter",
           "ATR_TimeFrame", "PeriodoATR",
           "VelaStop", "Stop", "VelaTake", "Take", "TakeOrganico",
           "Trail", "TrailVela", "MetodoDeCalculo",
           "AtivarBreakeven", "BreakevenDistancia", "AtivarTrailATR",
           "Multiplicador", "DistanciaMinima", "MaxMartingaleSteps",
           "DAlembertStep", "UsarsomenteATRGRID",
           "ReversalExitUseEntryFilters",
           "AtivarFiltroMA", "AtivarFiltroADX", "AtivarFiltroMTF",
           "EntradaATR"]           # EntradaATR so tem faixa nos sets de grid

# Enum do EA (ENUM_ENTRY_INDICATOR). Ichimoku (11) vive em set proprio porque o
# OnInit exige Tenkan<Kijun<SenkouB; os MULTI disputam 0..10 num eixo so.
INDICADORES = {0: "MACD", 1: "EMA", 2: "Momentum", 3: "Stochastic", 4: "TRIX",
               5: "RSI", 6: "CCI", 7: "WPR", 8: "DeMarker", 9: "MFI",
               10: "OsMA", 11: "Ichimoku"}

# Inputs "de escrita" (enums e bools): a fase 1 os decide e daqui em diante
# eles ficam TRAVADOS -- "vamos tirando inputs de escrita e deixando somente
# de numeros". E o que estreita o funil sem reabrir decisao estrutural.
ESCRITA = {"EntryIndicator", "EntryMethod", "TimeFrame", "InpAppliedPrice",
           "StochasticMethod", "StochasticPriceField",
           "IchimokuUseKumo", "IchimokuChikouFilter", "ATR_TimeFrame",
           "TakeOrganico", "MetodoDeCalculo", "AtivarBreakeven",
           "AtivarTrailATR", "UsarsomenteATRGRID",
           "ReversalExitUseEntryFilters",
           "AtivarFiltroMA", "AtivarFiltroADX", "AtivarFiltroMTF",
           "EntradaATR"}

# FASE 2 = SO NUMEROS: com a escrita travada, refinam-se os eixos numericos na
# faixa fina da biblioteca -- periodos, multiplicadores, distancias, limiares.
# O ajuste dos filtros entra aqui e SO se a flag sobreviveu (GATES corta o
# ajuste de quem morreu cravada em false).
NUMEROS = ["Fast_EMA", "Slow_EMA", "MACD_SMA", "StochasticSlowing",
           "PeriodoATR", "VelaStop", "VelaTake", "TrailVela",
           "Stop", "Take", "Trail", "BreakevenDistancia",
           "Multiplicador", "DistanciaMinima", "MaxMartingaleSteps",
           "DAlembertStep",
           "MA_Period", "MA_SlopeLookback", "ADX_Period", "ADX_Limiar",
           "MA_Method", "MetodoMA", "SentidoMA", "MA_AppliedPrice",
           "MetodoADX", "MTF_RequererAmbos", "VolatilityFilter"]

# Parametro -> indicadores que REALMENTE o usam, lido na criacao dos handles
# do EA (~1234-1290). Fora dessa lista o parametro nao entra no calculo, entao
# otimiza-lo produz passes identicos -- o mesmo desperdicio de um eixo atras de
# chave desligada, so que condicionado ao indicador em vez de a um bool.
# A fase 1 os mantem cravados; a fase 2 abre SO os do vencedor.
INDICADOR_USA = {
    "Slow_EMA": {0, 1, 10, 11},        # MACD, EMA_Cross, OsMA, Ichimoku(Kijun)
    "MACD_SMA": {0, 3, 10, 11},        # MACD, Stochastic(%D), OsMA, Ichimoku
    "StochasticSlowing": {3},
    "StochasticMethod": {3},
    "StochasticPriceField": {3},
    # Nos MULTI o EntryIndicator so varia 0..10 -- Ichimoku (11) vive em set
    # proprio -- entao estes dois nunca tem efeito num vencedor MULTI.
    "IchimokuUseKumo": {11},
    "IchimokuChikouFilter": {11},
}


def eixos_da_fase1(origem: Path) -> list[str]:
    """TUDO que tem faixa no set, menos os filtros de execucao.

    Dono (2026-07-31): "todos indicadores e inputs devem estar aptos na
    primeira rodada! aqui tudo de acordo com o sistema". Uma lista fixa no
    codigo erraria justamente por ser fixa -- eixo novo no gerador nasceria
    apagado pelo circuito, que e o defeito que os valores de filtro sofreram.
    Lendo do PROPRIO set, "de acordo com o sistema" sai de graca: o arquivo do
    grid nao tem faixa de trailing, o do 03 nao tem faixa de take, e o que nao
    existe ali simplesmente nao aparece aqui.

    Fora ficam so os filtros de EXECUCAO (hora, dia, spread), que por ordem
    dele sao os ultimos a rodar, no estagio 3.
    """
    fora = set(EXEC_FILTROS)
    nomes = []
    for linha in origem.read_text(encoding="utf-16").replace("\r", "").split("\n"):
        m = re.match(r"^([A-Za-z_0-9]+)=(.*)$", linha)
        if not m:
            continue
        partes = m.group(2).split("||")
        if len(partes) == 5 and partes[1] != partes[3] and m.group(1) not in fora:
            nomes.append(m.group(1))
    return nomes


def eixos_do_indicador(nomes: list[str], indicador: str | None) -> list[str]:
    """Remove os eixos que o indicador vencedor nao usa.

    Sem indicador conhecido (set ICHIMOKU, onde ele e cravado no arquivo) a
    lista passa inteira: o proprio .set ja limita o que tem faixa.
    """
    if indicador is None:
        return nomes
    try:
        i = int(float(indicador))
    except (TypeError, ValueError):
        return nomes
    return [n for n in nomes
            if n not in INDICADOR_USA or i in INDICADOR_USA[n]]


# FASE 3 = FILTROS DE EXECUCAO, os ULTIMOS a rodar (dono, 2026-07-31):
# hora, dia da semana e spread maximo. Higiene de execucao, nao tese de
# mercado -- por isso so entram depois de sinal e numeros resolvidos, e por
# decisao explicita do dono OTIMIZAM em IS+OOS ("pode rodar no insample +
# ousample"). TradeSaturday/Sunday so tem faixa nos sets de cripto.
EXEC_FILTROS = ["TOD_From_Hour", "TOD_To_Hour", "Fecharordensforadohorario",
                "TradeMonday", "TradeTuesday", "TradeWednesday",
                "TradeThursday", "TradeFriday", "TradeSaturday",
                "TradeSunday", "MaxSpread"]

# Parametro -> flag que o liga. Com a flag cravada em false o parametro nao
# muda NADA no resultado: `CheckMAFilter` abre com `if (!AtivarFiltroMA) return
# true;`, e o mesmo vale para o ADX. Otimiza-los assim nao e so desperdicio, e
# diluicao: MA_Period(3) x MetodoMA(4) x ADX_Limiar(4) faz o genetico avaliar
# 48 copias identicas de cada combinacao real, e o relatorio sai com cinco
# primeiras linhas de lucro identico -- que foi como isso apareceu.
#
# So vale para flag CRAVADA. Se a flag estiver ela mesma em otimizacao (como
# AtivarBreakeven), o parametro importa no ramo em que ela e true.
GATES = {
    # Esqueleto do sistema: trailing, TP e SL cravados definem o tipo (01..11).
    # Espelha GATES_DEPENDENCIAS do gerador; mexeu la, mexa aqui.
    "MetodoDeCalculo": "AtivarTrailATR",
    "TrailVela": "AtivarTrailATR",
    "Trail": "AtivarTrailATR",
    "VelaTake": "AtivarTake",
    "VelaStop": "AtivarStop",
    "MA_Period": "AtivarFiltroMA",
    "MetodoMA": "AtivarFiltroMA",
    "MA_Method": "AtivarFiltroMA",
    "SentidoMA": "AtivarFiltroMA",
    "MA_AppliedPrice": "AtivarFiltroMA",
    "MA_SlopeLookback": "AtivarFiltroMA",
    "ADX_Period": "AtivarFiltroADX",
    "ADX_Limiar": "AtivarFiltroADX",
    "MetodoADX": "AtivarFiltroADX",
    "BreakevenDistancia": "AtivarBreakeven",
    "MTF_RequererAmbos": "AtivarFiltroMTF",
    "VolatilityFilter": "EntradaATR",
    "NewsMinutosAntes": "AtivarFiltroNoticias",
    "NewsMinutosDepois": "AtivarFiltroNoticias",
}


def reescrever(origem: Path, destino: Path, otimizar: list[str],
               travar: dict[str, str]) -> int:
    """Grava um .set marcando `otimizar` com Y e fixando `travar` com N.

    Preserva inicio/passo/fim de quem fica em Y -- sao as faixas que o gerador
    calibrou por classe de ativo. Devolve quantos parametros ficaram em Y.

    Parametros cuja flag de ativacao esta cravada em false NAO entram, mesmo
    pedidos em `otimizar` -- ver GATES.
    """
    linhas, marcados = [], 0
    # newline="" nos dois lados. Sem isso o modo texto do Windows traduz \n para
    # \r\n na ESCRITA, e o \r que ja colocamos vira \r\r\n -- cada reescrita
    # dobra o numero de linhas do arquivo. O MT5 tolera (a biblioteca inteira
    # nasceu assim e sempre funcionou), mas o efeito e cumulativo.
    with origem.open("r", encoding="utf-16", newline="") as fh:
        cru = fh.read()

    # Valores JA RESOLVIDOS (origem + o que travamos), para consultar os gates
    # antes de decidir quem entra. Precisa vir de uma varredura propria: o laco
    # de escrita percorre o arquivo em ordem, e a flag de um parametro pode
    # aparecer DEPOIS dele.
    resolvido = {}
    for linha in cru.replace("\r", "").split("\n"):
        m = re.match(r"^([^;=]+)=(.*)$", linha)
        if m:
            resolvido[m.group(1)] = m.group(2).split("||")
    for k, v in travar.items():
        resolvido[k] = [str(v), str(v), "0", str(v)]

    def gate_cravado_off(nome: str) -> bool:
        flag = GATES.get(nome)
        if flag is None:
            return False
        p = resolvido.get(flag)
        if p is None:
            return False
        cravada = len(p) < 5 or p[1] == p[3]      # sem faixa = valor unico
        return cravada and p[0].strip().lower() == "false"

    # Os sets da biblioteca vem com \r\r\n (o gerador junta com \r\n e o modo
    # texto do Windows traduz o \n de novo). Dividir por \r\n deixa um \r solto
    # no fim de cada linha, que voltaria na juncao -- dai a limpeza.
    for linha in (bruta.rstrip("\r") for bruta in cru.split("\r\n")):
        m = re.match(r"^([^;=]+)=(.*)$", linha)
        if m:
            nome, resto = m.group(1), m.group(2)
            partes = resto.split("||")
            if nome in travar:
                v = str(travar[nome])
                passo = "0" if v in ("true", "false") else "1"
                linha = (f"{nome}={v}||{v}||{passo}||{v}||N" if len(partes) == 5
                         else f"{nome}={v}")
            elif len(partes) == 5:
                # Marcar Y so faz sentido com faixa real: com inicio == fim o
                # MT5 recusa a otimizacao inteira ("no optimized parameter
                # selected"), mesmo havendo outros parametros validos.
                tem_faixa = partes[1] != partes[3]
                util = not gate_cravado_off(nome)
                alvo = "Y" if (nome in otimizar and tem_faixa and util) else "N"
                if alvo == "Y":
                    marcados += 1
                # O "nome=" precisa voltar: reconstruir so a partir das partes
                # do VALOR gera um arquivo sem nomes, que o MT5 le como se nao
                # houvesse parametro nenhum a otimizar.
                linha = f"{nome}=" + "||".join(partes[:4] + [alvo])
        linhas.append(linha)
    with destino.open("w", encoding="utf-16", newline="") as fh:
        fh.write("\r\n".join(linhas) + "\r\n")
    return marcados


def janelas_wfo(inicio: str, fim: str, ciclos_alvo: int = 6) -> dict[str, str]:
    """Configura o walk-forward interno A PARTIR do periodo da corrida.

    O holdout interno da EA entrega o mesmo que o Forward nativo do MT5 e sai
    mais barato: em modo In-Sample a EA nao opera fora das janelas IS, entao
    basta UM passe -- o nativo precisa reexecutar os melhores num segundo
    periodo. E as janelas aqui sao INTERCALADAS, enquanto o nativo valida
    sempre no trecho final; se aquele trecho tiver um regime proprio, e ele que
    decide tudo.

    O preco disso e a configuracao: sem AtivarWFO ligado o algoritmo ve o
    periodo inteiro e a retencao nao prova nada, e se input_end_date nao bater
    com a data final do teste (tolerancia de 80h) o OnTester devolve 0 em TODO
    passe, em silencio. Sao duas condicoes faceis de errar a mao -- por isso
    elas sao DERIVADAS aqui, da mesma data que vai para o .ini. Configuracao
    que nasce da corrida nao tem como desalinhar.

    Divide o periodo em `ciclos_alvo` blocos, cada um com 3/4 de In-Sample e
    1/4 de Out-of-Sample -- a proporcao usual fica entre 2:1 e 4:1.
    """
    d0 = datetime.strptime(inicio, "%Y.%m.%d")
    d1 = datetime.strptime(fim, "%Y.%m.%d")
    dias = (d1 - d0).days
    bloco = max(60, dias // max(1, ciclos_alvo))
    is_dias = max(30, int(bloco * 0.75))
    oos_dias = max(15, bloco - is_dias)
    return {
        "AtivarWFO": "true",
        "MetodoDeEntradawfo": "0",          # In-Sample: o genetico so ve IS
        "input_end_date": fim,              # casado com o ToDate do .ini
        "wfo_windowSize": "-1",             # Custom
        "wfo_customWindowSizeDays": str(is_dias),
        "wfo_stepSize": "-1",
        "wfo_customStepSizePercent": str(-oos_dias),   # negativo = dias fixos
    }


def conferir_set(caminho: Path, travados: dict[str, str]) -> list[str]:
    """Le o .set de volta e devolve os travados que NAO chegaram nele.

    Existe por causa de um erro que passou silencioso: o relatorio do tester so
    traz as colunas dos parametros marcados com Y, entao o vencedor do estagio 2
    nao carrega o sinal escolhido no estagio 1. Reconstruir o set final a partir
    do arquivo de origem devolvia o sinal ao DEFAULT da biblioteca, e a corrida
    de conferencia testava outra estrategia -- com um numero de divergencia de
    aparencia perfeitamente plausivel (96%).

    Conferir o que foi gravado e barato e transforma esse tipo de erro em falha
    ruidosa. O sinal que denunciou na epoca foi a contagem de trades (175 -> 935);
    como a entrada nasce no fechamento da barra, trocar de modelo nao pode mudar
    quantas entradas existem -- e um invariante entre os dois modelos.
    """
    lido = {}
    for linha in caminho.read_text(encoding="utf-16").replace("\r", "").split("\n"):
        if "=" in linha and not linha.startswith(";"):
            nome, valor = linha.split("=", 1)
            lido[nome] = valor.split("||")[0]
    return [k for k, v in travados.items() if lido.get(k) != str(v)]


def modo_de_sizing(caminho: Path) -> str | None:
    """PositionSizeMode do set de origem (primeiro campo).

    Decide se a prova em % existe para este sistema: o EA so aceita Percentage
    com stop ativo, e proibe Fixed-R em grid/martingale/d'alembert -- nesses, o
    set de origem ja vem em Fixed Lot/Monetary e nao ha modo % a provar.
    """
    for linha in caminho.read_text(encoding="utf-16").replace("\r", "").split("\n"):
        if linha.startswith("PositionSizeMode="):
            return linha.split("=", 1)[1].split("||")[0].strip()
    return None


def torneio_retencao(candidatos, cab, metricas, origem: Path, trabalho: Path,
                     travados: dict, args, modelo: int, rotulo: str) -> list:
    """Mede a retencao OUT-OF-SAMPLE de cada candidato e ordena por ela.

    O criterio de escolha do circuito inteiro. Ordenar por lucro in-sample
    escolheria justamente o ponto onde o genetico mais se ajustou ao trecho que
    enxergou -- medimos 4 sistemas assim e os 4 reprovaram fora da amostra.

    `modelo` decide o custo: 1 (OHLC, ~2s) serve para RANQUEAR entre estagios,
    4 (tick real, ~35s) para CONFIRMAR o vencedor. E o mesmo funil do circuito:
    barato para separar, caro so no fim.

    Todo passe roda em MetodoDeEntradawfo=1 (In Sample + Out Sample), porque e o
    unico modo em que as janelas OOS realmente operam. Em modo In-Sample a EA
    nao abre fora delas e a retencao vira vazamento da liquidacao forcada.

    Um candidato `None` significa "sem sobreposicao": mede o que ja esta em
    `travados`.
    """
    print(f"    torneio: {rotulo}", flush=True)
    saida = []
    for i, linha in enumerate(candidatos, 1):
        if linha is None:
            cand, lucro_is = {}, 0.0
        else:
            cand = {c: v for c, v in zip(cab, linha) if c not in metricas}
            lucro_is = base.num(linha[cab.index("Profit")])
        passo = dict(travados, **cand, MetodoDeEntradawfo="1")
        reescrever(origem, trabalho, [], passo)
        faltando = conferir_set(trabalho, passo)
        if faltando:
            print(f"      {i:2}. pulado: nao chegou ao set {faltando}", flush=True)
            continue
        r = passe_unico(trabalho, args.symbol, args.period, args.inicio,
                        args.fim, args.deposit, modelo)
        ret, exp = r["retencao"], r["expectancy"]
        print(f"      {i:2}. lucro IS {lucro_is:>8.2f} | retencao "
              f"{'    n/d' if ret is None else f'{ret:>7.1f}%'} | "
              f"{r['trades']} trades | expectancy "
              f"{'n/d' if exp is None else f'{exp:+.3f}R'}", flush=True)
        saida.append((ret, lucro_is, cand, r))
    # Sem retencao medida vai para o fim: ausencia de medida nao e boa medida.
    saida.sort(key=lambda t: (t[0] is not None, t[0] or -9e9, t[1]), reverse=True)
    return saida


def melhor_por_indicador(cab: list[str], linhas: list[list[str]]) -> list[list[str]]:
    """Um campeao por EntryIndicator, na ordem em que as linhas ja chegaram.

    "Todos os indicadores testados" se cumpre aqui, nao dentro do genetico: o
    genetico converge e enterra dez indicadores sob o que lucrou primeiro.
    Promover so `linhas[0]` decidia a entrada inteira sem que nenhum outro
    indicador tivesse sido MEDIDO. Um campeao por indicador segue para o
    torneio de retencao -- no maximo 12 passes de ~2s, e a escolha do sinal
    passa a usar o MESMO criterio do resto do circuito.

    Sem coluna EntryIndicator (variante ICHIMOKU, indicador cravado no set) ha
    um grupo so, e o campeao e a primeira linha.
    """
    if "EntryIndicator" not in cab:
        return linhas[:1]
    i = cab.index("EntryIndicator")
    vistos: set[str] = set()
    saida = []
    for linha in linhas:
        chave = linha[i]
        if chave in vistos:
            continue
        vistos.add(chave)
        saida.append(linha)
    return saida


def relatar_cobertura(cab: list[str], todas: list[list[str]],
                      aptas: list[list[str]]) -> None:
    """Imprime que fatia dos 11 indicadores MULTI o estagio 1 realmente viu.

    Dois numeros diferentes de proposito: "visitado" diz que o genetico gastou
    passes ali; "apto" diz que algum desses passes venceu os pisos. Indicador
    visitado e sem apto reprovou de verdade; indicador NUNCA visitado nao foi
    julgado -- relancar o genetico continua a mesma busca e pode alcanca-lo.
    """
    if "EntryIndicator" not in cab:
        print("    cobertura: indicador cravado no set (variante ICHIMOKU).",
              flush=True)
        return
    i = cab.index("EntryIndicator")

    def nomes(linhas: list[list[str]]) -> set[str]:
        achados = set()
        for linha in linhas:
            v = base.num(linha[i])
            if v != float("-inf"):
                achados.add(INDICADORES.get(int(v), str(linha[i])))
        return achados

    visitados, aptos = nomes(todas), nomes(aptas)
    universo = [n for v, n in sorted(INDICADORES.items()) if v <= 10]
    print(f"    cobertura de entradas: {len(visitados)}/{len(universo)} "
          f"visitados | aptos: {sorted(aptos)}", flush=True)
    reprovados = sorted(visitados - aptos)
    ausentes = [n for n in universo if n not in visitados]
    if reprovados:
        print(f"    visitados sem passe apto: {reprovados}", flush=True)
    if ausentes:
        print(f"    NUNCA visitados: {ausentes} -- relancar o genetico "
              "continua a busca.", flush=True)


def veredito(div: float | None, retencao: float | None,
             min_retencao: float) -> tuple[bool, list[str]]:
    """Aprova o candidato so quando as DUAS conferencias passam.

    Elas respondem perguntas diferentes e uma nao substitui a outra:

      divergencia  o numero do OHLC e real? Compara o MESMO conjunto de
                   parametros nos dois modelos de tick. Passar aqui diz que a
                   busca nao viveu de suavizacao intrabar -- nada alem disso.
      retencao     esse numero se repete em dado que a busca nao viu? Compara
                   janelas In-Sample e Out-of-Sample do mesmo passe.

    Separar os dois importa porque um candidato real passou na primeira com
    3,8% e reprovou na segunda com -37,1%: o lucro do OHLC era autentico e mesmo
    assim nao generalizava. Um veredito olhando so a divergencia teria escrito
    "confirmado" logo abaixo de uma retencao negativa.
    """
    motivos, aprovado = [], True
    if div is None:
        motivos.append("SEM VEREDITO: a conferencia em tick real nao produziu numero.")
        return False, motivos
    if div > 30:
        aprovado = False
        motivos.append("REPROVADO na divergencia: o resultado do OHLC nao se")
        motivos.append("sustentou em tick real. Neste sistema a gestao depende do")
        motivos.append("caminho intrabar -- medido antes: 3,3x em trailing, 23x em")
        motivos.append("grid. Trate o numero do OHLC como invalido, nao aproximado.")
    else:
        motivos.append(f"OK divergencia ({div:.1f}%): o lucro do OHLC e real.")

    if retencao is None:
        aprovado = False
        motivos.append("SEM RETENCAO: o passe IS+OOS nao reportou. Sem ela nao ha")
        motivos.append("prova de que o resultado sobrevive fora da amostra.")
    elif retencao < min_retencao:
        aprovado = False
        motivos.append(f"REPROVADO na retencao ({retencao:.1f}% < {min_retencao:.0f}%): "
                       "o desempenho")
        motivos.append("nao se repetiu nas janelas que a otimizacao nao enxergou.")
        if retencao < 0:
            motivos.append("Retencao negativa: fora da amostra a estrategia PERDEU.")
    else:
        motivos.append(f"OK retencao ({retencao:.1f}%): o desempenho se repetiu fora")
        motivos.append("da amostra.")

    # O veredito FINAL nao sai daqui: depois destas duas conferencias ainda ha
    # a prova em percentual (estagio 5), e imprimir "APROVADO" antes dela
    # deixaria no log uma afirmacao que o passo seguinte pode desmentir.
    motivos.insert(0, "")
    return aprovado, motivos


def ler_metricas(log: str) -> dict:
    """Extrai saldo, trades, R e retencao do trecho de log de UMA corrida.

    Funcao separada de proposito: ela nao precisa do MT5 para rodar, entao da
    para testa-la contra um log gravado em segundos. Enquanto morava dentro de
    passe_unico, um erro de uma linha so aparecia depois dos ~25 min de
    otimizacao que a precedem -- e foi exatamente o que aconteceu duas vezes.

    Os numeros vem do bloco R METRICS que a PROPRIA EA imprime, nao da contagem
    de linhas do log nem do relatorio .htm. Duas razoes:

    1. Base. Contar "deal #" da DEALS, e uma posicao fechada gera dois (entra e
       sai) -- por isso a conferencia mostrava 823 onde a otimizacao mostrava
       412, um 2x que parecia divergencia e era so unidade diferente.
    2. Idioma. O .htm sai no idioma do terminal ("Lucro Liquido Total" aqui),
       enquanto o log da EA sai sempre em ingles. Casar rotulo traduzido
       quebraria na maquina de qualquer comprador com outro idioma.
    """
    def ultimo(padrao: str):
        """Ultima ocorrencia, nunca a primeira.

        O log do tester e CUMULATIVO por dia: todas as corridas vao para o mesmo
        arquivo. O corte por offset de bytes ja isola o trecho desta corrida,
        mas se ele falhar a primeira ocorrencia vem de uma corrida ANTIGA -- e
        um numero de outra corrida e plausivel demais para levantar suspeita.
        Foi assim que uma contagem antiga virou escada crescente (904, 1040,
        1188) sem nunca parecer errada. Com a ultima, o pior caso e o resultado
        mais recente, nao um fantasma.
        """
        achados = re.findall(padrao, log)
        return achados[-1] if achados else None

    saldo = ultimo(r"final balance ([\d.]+)")
    r_met = ultimo(r"Trades: (\d+) \| Total R: ([+-]?[\d.]+) \| "
                   r"Average R \(expectancy\): ([+-]?[\d.]+)")
    ret = ultimo(r"Out-of-Sample Retention: (-?[\d.]+)%")
    win = ultimo(r"Win rate: ([\d.]+)%")
    return {
        "saldo": float(saldo) if saldo else None,
        "trades": int(r_met[0]) if r_met else None,
        "total_r": float(r_met[1]) if r_met else None,
        "expectancy": float(r_met[2]) if r_met else None,
        "win_rate": float(win) if win else None,
        # None distingue "nao medido" de 0.0 ("medido e nao reteve nada" ou
        # "In-Sample sem lucro, nada a reter") -- confundir os dois foi o que
        # fez a retencao parecer um resultado quando era so o modo In-Sample.
        "retencao": float(ret) if ret else None,
        "abortos": len(re.findall(r"aborted", log)),
    }


def passe_unico(caminho_set: Path, symbol: str, periodo: str, inicio: str,
                fim: str, deposito: int, modelo: int,
                timeout: int = 3600) -> dict:
    """Roda UM backtest e devolve saldo final, trades e abortos.

    E assim que os ticks reais entram: como CONFERENCIA dos parametros que a
    otimizacao em OHLC ja escolheu, nao como busca. Otimizar em tick real sao
    milhares de passes a ~35s cada; conferir e um passe.

    E o passe unico responde a mesma pergunta que a otimizacao cara responderia:
    o resultado do OHLC se sustenta em dado real? Se sustenta, acabou. Se nao,
    ele EXPOE a divergencia -- enquanto otimizar em tick real teria escondido o
    problema, entregando um resultado bonito ajustado ao modelo caro.
    """
    rel = str(caminho_set.relative_to(base.DADOS / "MQL5" / "Profiles" / "Tester"))
    antes = base.marcar_logs()
    with tempfile.TemporaryDirectory() as tmp:
        ini = Path(tmp) / "conf.ini"
        base.escrever_ini(ini, symbol, periodo, rel.replace("/", "\\"),
                          inicio, fim, deposito, modelo, 6, "conf_wrx")
        # escrever_ini monta otimizacao; aqui queremos um passe so.
        texto_ini = ini.read_text(encoding="utf-16")
        ini.write_text(texto_ini.replace("Optimization=2", "Optimization=0"),
                       encoding="utf-16")
        subprocess.run([str(base.TERMINAL), f"/config:{ini}"],  # noqa: S603
                       timeout=timeout, capture_output=True, check=False)
    limite = time.monotonic() + 90
    log = ""
    while time.monotonic() < limite:
        log = base.texto_novo(antes)
        if "automatic testing finished" in log:
            break
        time.sleep(1)

    return ler_metricas(log)


def rodar(caminho_set: Path, symbol: str, periodo: str, inicio: str, fim: str,
          deposito: int, modelo: int, timeout: int) -> tuple[list, list]:
    """Uma otimizacao genetica. Devolve (cabecalho, linhas) do relatorio."""
    rel = str(caminho_set.relative_to(base.DADOS / "MQL5" / "Profiles" / "Tester"))
    nome_rel = "otim_wrx"
    for velho in base.DADOS.glob(f"{nome_rel}*"):
        velho.unlink(missing_ok=True)
    antes = base.marcar_logs()
    with tempfile.TemporaryDirectory() as tmp:
        ini = Path(tmp) / "otim.ini"
        base.escrever_ini(ini, symbol, periodo, rel.replace("/", "\\"),
                          inicio, fim, deposito, modelo, 6, nome_rel)
        subprocess.run([str(base.TERMINAL), f"/config:{ini}"],  # noqa: S603
                       timeout=timeout, capture_output=True, check=False)
    log = base.texto_novo(antes)
    m = re.search(r"local (\d+) tasks", log)
    print(f"    passes executados: {m.group(1) if m else '?'}", flush=True)
    candidatos = sorted(base.DADOS.glob(f"{nome_rel}*"),
                        key=lambda p: (p.suffix.lower() != ".xml", p.name))
    if not candidatos:
        return [], []
    return base.ler_relatorio(candidatos[0])


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--sistema", default="01_SLTP")
    ap.add_argument("--variante", default="SELL_MULTI")
    # M1 e OBRIGATORIO em todos os estagios (dono, 2026-07-31): cada indicador
    # carrega o proprio TF via input (MTF_TF1/TF2, ATR_TimeFrame etc.) -- se o
    # chart period do tester nao for M1, qualquer input marcado "Current TF"
    # colapsa pro period do chart em vez do TF que o eixo pretende testar, e o
    # espaco de busca encolhe silenciosamente sem nenhum erro.
    ap.add_argument("--period", default="M1")
    ap.add_argument("--from", dest="inicio", default="2023.08.01")
    ap.add_argument("--to", dest="fim", default="2026.07.21")
    ap.add_argument("--deposit", type=int, default=500)
    ap.add_argument("--min-trades", type=int, default=100)
    ap.add_argument("--min-pf", type=float, default=1.2)
    # 30% e um piso de partida, nao um numero derivado: a literatura de walk-
    # forward costuma tratar 50%+ como bom e abaixo de 30% como fraco. Fica
    # exposto na linha de comando justamente para ser calibrado com a
    # distribuicao real dos nossos sistemas, quando ela existir.
    ap.add_argument("--min-retencao", type=float, default=30.0)
    # 8 finalistas ~= 5 min de passes. Poucos demais e o torneio vira o
    # mesmo "pega o maior lucro"; muitos demais e so custo, porque os
    # candidatos do fim da lista ja passaram longe dos pisos.
    ap.add_argument("--finalistas", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=21600)
    ap.add_argument("--fechar-terminal", action="store_true")
    args = ap.parse_args()

    garantir_terminal_livre(fechar=args.fechar_terminal)

    origem = base.achar_set(args.symbol, args.sistema, args.variante)
    if origem is None:
        print(f"Set nao encontrado: {args.symbol}/{args.sistema}/{args.variante}")
        return 1
    trabalho = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_ETAPA.set"
    rotulo = f"{args.symbol} {args.sistema} {args.variante}"
    print(f"=== {rotulo} | {args.inicio} a {args.fim} ===", flush=True)

    # ---- Estagio 1: REGIOES, no modelo rapido -------------------------------
    # O walk-forward interno entra JA na busca, nao so na conferencia depois:
    # em modo In-Sample o genetico nao enxerga as janelas OOS, entao o que ele
    # escolher ja nasce testado contra dado que nao viu. Configuracao derivada
    # do periodo, nunca digitada.
    # `travados` ACUMULA tudo o que ja foi decidido e viaja para os estagios
    # seguintes. Sem esse acumulo cada estagio so conhece o proprio vencedor, e
    # o que foi escolhido antes volta ao default -- ver conferir_set().
    travados = janelas_wfo(args.inicio, args.fim)
    wfo = dict(travados)
    # English fixo em todo o set de trabalho da campanha (fora de `wfo`, que
    # so guarda as janelas): com Auto, o EA detecta o idioma do terminal
    # (Portugues aqui) para o painel. A entrega (linha ~980) volta pra Auto --
    # so o nosso set de trabalho roda em EN.
    travados["InterfaceLanguage"] = "1"
    n = reescrever(origem, trabalho, eixos_da_fase1(origem), travados)
    print(f"  [1/5] regioes em OHLC ({n} parametros: entradas completas + "
          f"saidas + flags) | WFO In-Sample: "
          f"IS {wfo['wfo_customWindowSizeDays']}d / "
          f"OOS {abs(int(wfo['wfo_customStepSizePercent']))}d, "
          f"fim {wfo['input_end_date']}", flush=True)
    # Piso de trades mais baixo aqui: estamos descobrindo REGIOES, e uma
    # regiao boa com numeros ainda crus produz menos trades do que produzira.
    piso1 = max(30, args.min_trades // 3)
    metricas = {"Pass", "Result", "Profit", "Expected Payoff", "Profit Factor",
                "Recovery Factor", "Sharpe Ratio", "Custom", "Equity DD %", "Trades"}

    # Ate 3 rodadas do genetico (dono: "essa fase pode repetir ate umas 3
    # vezes"). Relancar continua a mesma busca -- o cache de otimizacao do
    # tester sobrevive entre lancamentos com a mesma configuracao. A
    # inteligencia da repeticao: so paga a proxima rodada se a atual MELHOROU
    # o retrato (lucro do topo subiu >5% ou um indicador novo virou apto).
    cab: list[str] = []
    linhas: list[list[str]] = []
    melhor_ant, aptos_ant = float("-inf"), -1
    for rodada in range(1, 4):
        t0 = time.time()
        cab_r, linhas_r = rodar(trabalho, args.symbol, args.period, args.inicio,
                                args.fim, args.deposit, 1, args.timeout)
        if not linhas_r:
            if not linhas:
                print("    relatorio vazio -- nenhum passe sobreviveu aos filtros")
                return 1
            print(f"    rodada {rodada}: relatorio vazio; sigo com as anteriores.",
                  flush=True)
            break
        cab = cab_r
        linhas += linhas_r
        melhores = base.escolher_candidatos(cab, linhas, piso1, 1.0)
        i_ind = cab.index("EntryIndicator") if "EntryIndicator" in cab else None
        aptos = (len({linha[i_ind] for linha in melhores}) if i_ind is not None
                 else (1 if melhores else 0))
        melhor = (base.num(melhores[0][cab.index("Profit")])
                  if melhores else float("-inf"))
        print(f"    rodada {rodada}: {(time.time()-t0)/60:.0f} min | melhor "
              f"lucro apto {melhor:.2f} | {aptos} indicadores aptos", flush=True)
        if rodada >= 2:
            melhorou = (aptos > aptos_ant
                        or melhor > melhor_ant + max(abs(melhor_ant) * 0.05, 1e-9))
            if not melhorou:
                print("    rodada sem melhora; encerrando o genetico das "
                      "regioes.", flush=True)
                break
        melhor_ant = max(melhor_ant, melhor)
        aptos_ant = max(aptos_ant, aptos)

    melhores = base.escolher_candidatos(cab, linhas, piso1, 1.0)
    if not melhores:
        print("    nenhum passe passou o piso no estagio 1")
        return 1
    relatar_cobertura(cab, linhas, melhores)

    # A regiao vencedora sai de um torneio de retencao, um campeao POR
    # INDICADOR: pegar melhores[0] escolheria por lucro in-sample -- o criterio
    # que os estagios seguintes existem para evitar -- e sem nenhum outro
    # indicador medido.
    campeoes = melhor_por_indicador(cab, melhores)
    ordenados_sinal = torneio_retencao(campeoes, cab, metricas, origem,
                                       trabalho, travados, args, 1,
                                       "regioes, um campeao por indicador "
                                       "(OHLC, ~2s cada)")
    if ordenados_sinal:
        ret_sinal, lucro_sinal, cand_sinal, _ = ordenados_sinal[0]
    else:
        # Torneio sem nenhuma medida (todos pulados): o maior lucro in-sample
        # segue como fallback EXPLICITO -- melhor uma regiao sem medida de
        # retencao agora do que abortar, porque os estagios seguintes ainda
        # vao medir e reprovar o combo se ele nao se sustentar.
        print("    torneio das regioes sem medidas; usando o maior lucro "
              "in-sample.", flush=True)
        ret_sinal = None
        lucro_sinal = base.num(melhores[0][cab.index("Profit")])
        cand_sinal = {c: v for c, v in zip(cab, melhores[0])
                      if c not in metricas}
    # Do vencedor trava-se SO a escrita (enums e bools): "vamos tirando inputs
    # de escrita e deixando somente de numeros". Os numericos do vencedor sao
    # regiao, nao resposta -- o estagio 2 os refina com a escrita cravada.
    escrita_vencedora = {c: v for c, v in cand_sinal.items() if c in ESCRITA}
    ind = escrita_vencedora.get("EntryIndicator")
    nome_ind = (INDICADORES.get(int(base.num(ind)), ind)
                if ind is not None else "cravado no set")
    print(f"    escrita travada ({nome_ind}, retencao "
          f"{'n/d' if ret_sinal is None else f'{ret_sinal:.1f}%'}, "
          f"lucro IS {lucro_sinal:.2f}): {escrita_vencedora}", flush=True)
    otimizados = dict(escrita_vencedora)

    # ---- Estagio 2: NUMEROS, ainda em OHLC ----------------------------------
    travados.update(escrita_vencedora)
    # Abre so os periodos que ESTE indicador usa: com o vencedor conhecido, os
    # eixos condicionais deixam de ser aposta e viram (ou nao) parte do ajuste.
    numeros = eixos_do_indicador(NUMEROS, ind)
    cortados = [c for c in NUMEROS if c not in numeros]
    n = reescrever(origem, trabalho, numeros, travados)
    print(f"  [2/5] numeros em OHLC ({n} parametros, escrita travada)",
          flush=True)
    if cortados:
        print(f"    fora por nao pertencerem ao {nome_ind}: {cortados}",
              flush=True)
    t0 = time.time()
    cab, linhas = rodar(trabalho, args.symbol, args.period, args.inicio,
                        args.fim, args.deposit, 1, args.timeout)
    if not linhas:
        print("    relatorio vazio no estagio 2")
        return 1
    finais = base.escolher_candidatos(cab, linhas, args.min_trades, args.min_pf)
    print(f"    {(time.time()-t0)/60:.0f} min | aptos: {len(finais)} de {len(linhas)}",
          flush=True)
    if not finais:
        print("    nenhum candidato passou os pisos.")
        return 0

    cols = [c for c in ("Profit", "Profit Factor", "Trades", "Equity DD %",
                        "Sharpe Ratio") if c in cab]
    idx = [cab.index(c) for c in cols]
    print("\n    " + "".join(f"{c:>16}" for c in cols))
    for linha in finais[:5]:
        print("    " + "".join(f"{base.num(linha[j]):>16.2f}" for j in idx))

    # O numero vencedor sai do torneio BARATO, em OHLC: o genetico ordenou por
    # lucro in-sample e pegar o primeiro escolheria, por construcao, o ponto que
    # melhor se ajustou ao trecho que a busca enxergou.
    ordenados = torneio_retencao(finais[:args.finalistas], cab, metricas,
                                 origem, trabalho, travados, args, 1,
                                 "numeros (OHLC, ~2s cada)")
    if not ordenados:
        print("    nenhum finalista dos numeros produziu medida de retencao.")
        return 1
    travados.update(ordenados[0][2])
    otimizados.update(ordenados[0][2])

    # ---- Estagio 3: FILTROS DE EXECUCAO (hora, dia, spread) -----------------
    # Ultimos a rodar, por ordem do dono. OTIMIZAM em IS+OOS
    # (MetodoDeEntradawfo=1) -- decisao explicita dele ("pode rodar no
    # insample + ousample"): a busca ve as janelas OOS operando, e o vazamento
    # de OOS para a selecao e aceito NESTES eixos de higiene. A protecao que
    # fica: os filtros so sao adotados se MELHORAREM a retencao ja medida.
    # Criterio PROPRIO desta fase: 7 = Drawdown-Adjusted Profit per Trade.
    # Filtro REDUZ o numero de trades por construcao -- julgar esta fase pelo
    # lucro total puniria justamente o filtro que corta operacao ruim, porque
    # cortar sempre encolhe o total. Lucro POR TRADE ajustado por drawdown faz
    # a pergunta certa: o que sobrou ficou melhor?
    n = reescrever(origem, trabalho, EXEC_FILTROS,
                   dict(travados, MetodoDeEntradawfo="1", selectedFormula="7"))
    print(f"\n  [3/5] filtros de execucao em IS+OOS ({n} parametros: "
          "hora, dia, spread)", flush=True)
    if n:
        t0 = time.time()
        cab_e, linhas_e = rodar(trabalho, args.symbol, args.period,
                                args.inicio, args.fim, args.deposit, 1,
                                args.timeout)
        exec_ok = (base.escolher_candidatos(cab_e, linhas_e, args.min_trades,
                                            args.min_pf) if linhas_e else [])
        print(f"    {(time.time()-t0)/60:.0f} min | aptos: {len(exec_ok)}",
              flush=True)
        if exec_ok:
            ord_e = torneio_retencao(exec_ok[:args.finalistas], cab_e,
                                     metricas, origem, trabalho, travados,
                                     args, 1, "execucao (OHLC, ~2s cada)")
            if ord_e and (ord_e[0][0] or -9e9) > (ordenados[0][0] or -9e9):
                print(f"    filtros de execucao melhoraram a retencao: "
                      f"{ordenados[0][0]} -> {ord_e[0][0]}", flush=True)
                travados.update(ord_e[0][2])
                otimizados.update(ord_e[0][2])
                ordenados = ord_e
            else:
                print("    filtros de execucao nao melhoraram a retencao; "
                      "mantidos os defaults (sem filtro).", flush=True)
    else:
        print("    nenhum eixo de execucao com faixa neste set.", flush=True)

    # ---- Estagio 4: confirmacao em TICKS REAIS ------------------------------
    print("\n  [4/5] confirmacao em TICKS REAIS", flush=True)
    t0 = time.time()
    conf = torneio_retencao([None], cab, metricas, origem, trabalho, travados,
                            args, 4, "vencedor (tick real)")
    if not conf:
        print("    a confirmacao em tick real nao produziu retencao.")
        return 1
    retencao_top, _, vencedor, oos = conf[0]
    lucro_ohlc = ordenados[0][1]
    print(f"\n    retencao confirmada em tick real: {retencao_top}%", flush=True)

    # Monte Carlo sobre os trades do passe IS+OOS que acabou de rodar -- tem
    # que ler o relatorio AGORA: o proximo passe (divergencia, logo abaixo)
    # reescreve o mesmo nome de relatorio ("conf_wrx") por cima.
    mc = monte_carlo_wrx.rodar_mc(
        monte_carlo_wrx.achar_relatorio("conf_wrx"), trabalho)
    mc_aprovado = True
    if mc is None:
        print("    Monte Carlo: nao aplicavel (sistema fora de Fixed-R ou "
              "relatorio sem trades legiveis).", flush=True)
    elif mc["mc_dd_p95"] is None:
        print(f"    Monte Carlo: poucos trades ({mc['mc_n_trades']}) para "
              "reamostrar com confianca.", flush=True)
    else:
        mc_aprovado = (mc["mc_dd_p95"] <= 2 * mc["mc_dd_observado"]
                       and mc["mc_prob_ruina"] <= 0.05)
        print(f"    Monte Carlo ({mc['mc_n_trades']} trades, 1000 reamostras): "
              f"DD p95 {mc['mc_dd_p95']:.2f}R (observado "
              f"{mc['mc_dd_observado']:.2f}R) | prob. ruina "
              f"{mc['mc_prob_ruina']*100:.1f}%"
              + ("" if mc_aprovado else " -- REPROVADO no Monte Carlo"),
              flush=True)

    # A divergencia exige um passe a mais, em modo In-Sample: ela compara o
    # MESMO conjunto de parametros nos dois modelos de tick, e o estagio 2 rodou
    # em In-Sample. Comparar contra o passe IS+OOS misturaria duas mudancas --
    # modelo de tick E periodo operado -- e nao mediria nenhuma das duas.
    travados.update(vencedor)
    reescrever(origem, trabalho, [], dict(travados, MetodoDeEntradawfo="0"))
    real = passe_unico(trabalho, args.symbol, args.period, args.inicio,
                       args.fim, args.deposit, 4)
    lucro_real = (real["saldo"] - args.deposit) if real["saldo"] is not None else None
    print(f"    conferencia In-Sample: {real['trades']} trades | "
          f"saldo {real['saldo']} | {real['abortos']} abortos", flush=True)
    if oos["expectancy"] is not None:
        print(f"    fora da amostra: expectancy {oos['expectancy']:+.3f}R | "
              f"total {oos['total_r']:+.1f}R | acerto {oos['win_rate']:.1f}%",
              flush=True)
    print(f"    {(time.time()-t0)/60:.1f} min nos estagios finais", flush=True)

    div = None
    if lucro_real is None:
        print("    a conferencia nao produziu resultado -- verifique o log.")
    elif abs(lucro_ohlc) > 1e-9:
        div = abs(lucro_real - lucro_ohlc) / abs(lucro_ohlc) * 100
        print(f"\n    lucro em OHLC:       {lucro_ohlc:>10.2f}")
        print(f"    lucro em tick real:  {lucro_real:>10.2f}")
        print(f"    divergencia:         {div:>9.1f}%")

    aprovado, motivos = veredito(div, oos["retencao"], args.min_retencao)
    for m in motivos:
        print(f"    {m}")
    if aprovado and not mc_aprovado:
        aprovado = False
        print("    REPROVADO no Monte Carlo: a sequencia de trades depende "
              "demais da ordem em que aconteceu (ver DD p95 acima).")

    # Sistemas com SL (Fixed-R) ja imprimem R METRICS a cada passe -- so
    # nunca tinham virado gate. Expectancy negativa em R e o mesmo problema
    # que retencao negativa: a "vantagem" nao sobrevive fora da amostra,
    # so que medida na unidade que o dono pediu para validar aqui (R, nao
    # dinheiro). Pedido do dono (2026-08-02): "algoritmos em Multiple R nas
    # ultimas etapas... a formula indicada foi somar R... para sistemas com SL".
    r_capavel = modo_de_sizing(origem) == "3"
    if aprovado and r_capavel and oos["expectancy"] is not None and oos["expectancy"] <= 0:
        aprovado = False
        print(f"    REPROVADO em R: expectancy fora da amostra "
              f"{oos['expectancy']:+.3f}R nao e positiva.")

    # ---- Estagio 5: prova em PERCENTUAL, e so entao salvar ------------------
    # O circuito inteiro mediu em Fixed-R com capital base fixo: 1R identico em
    # todo passe, sem juros compostos -- e o que torna as metricas comparaveis.
    # A conta real opera em % do saldo, onde cada perda encolhe o lote seguinte
    # e a SEQUENCIA das perdas passa a importar: um sistema pode reter em R e
    # degradar em % com a mesma expectancia, so pelo caminho. Regra do dono
    # (2026-07-31): validou em tick real, TROCA para Percentage, testa de novo,
    # e so salva se passar tambem -- a entrega sai no modo que foi provado.
    retencao_pct = None
    sizing_entrega = "origem"
    if aprovado:
        if modo_de_sizing(origem) == "3":
            print("\n  [5/5] prova em PERCENTUAL (tick real, juros compostos)",
                  flush=True)
            passo = dict(travados, PositionSizeMode="0", MetodoDeEntradawfo="1")
            reescrever(origem, trabalho, [], passo)
            faltando = conferir_set(trabalho, passo)
            if faltando:
                print(f"    ABORTADO: o set em % saiu incompleto: {faltando}")
                return 1
            pct = passe_unico(trabalho, args.symbol, args.period, args.inicio,
                              args.fim, args.deposit, 4)
            retencao_pct = pct["retencao"]
            print(f"    retencao em %: "
                  f"{'n/d' if retencao_pct is None else f'{retencao_pct:.1f}%'}"
                  f" | {pct['trades']} trades | saldo {pct['saldo']}",
                  flush=True)
            # Sizing nao decide entrada: o numero de trades e o MESMO invariante
            # usado entre modelos de tick. Se ele se mover aqui, a margem
            # bloqueou ordens (ou algo pior) -- e o resultado nao e comparavel.
            if (pct["trades"] is not None and oos["trades"] is not None
                    and pct["trades"] != oos["trades"]):
                print(f"    ATENCAO: trades mudaram no modo % "
                      f"({oos['trades']} -> {pct['trades']}); sizing nao muda "
                      "entrada -- verifique margem/abortos.", flush=True)
            if retencao_pct is None or retencao_pct < args.min_retencao:
                aprovado = False
                print("    REPROVADO na prova em %: o resultado do Fixed-R nao",
                      flush=True)
                print("    sobreviveu aos juros compostos do % do saldo.",
                      flush=True)
            else:
                sizing_entrega = "percentage"
                print("    OK em %: a entrega sai em Percentage, o modo "
                      "provado.", flush=True)
        else:
            print("\n  [5/5] prova em % nao se aplica: sistema sem Fixed-R "
                  "(lote fixo/monetary); entrega no modo de origem.",
                  flush=True)

    print("\n    " + ("APROVADO: candidato pronto para a entrega."
                      if aprovado else
                      "REPROVADO: nao promova este candidato."), flush=True)

    # O set entregue difere do set da biblioteca SO nos parametros otimizados:
    # toda a configuracao de WFO sai fora e volta ao default (AtivarWFO=false).
    #
    # O WFO e andaime de validacao, nao configuracao de uso. Ele age apenas em
    # backtest -- o gate e `isBacktest && AtivarWFO`, entao live nunca e
    # afetado --, mas um set entregue com ele ligado faria o comprador rodar um
    # backtest que ignora trechos do periodo, com janelas derivadas de uma
    # input_end_date que veio da NOSSA corrida. Ele veria menos trades do que
    # deveria e nao teria como saber por que.
    wfo_chaves = set(wfo) | {"AtivarWFO", "MetodoDeEntradawfo", "input_end_date"}
    entrega = {k: v for k, v in travados.items() if k not in wfo_chaves}
    entrega["AtivarWFO"] = "false"   # conferido contra o default da biblioteca
    # Set de trabalho roda fixado em English (evita paineis/erros em PT no
    # nosso terminal); o set entregue volta para Auto -- cada comprador ve
    # o dashboard no idioma do proprio terminal dele.
    entrega["InterfaceLanguage"] = "0"
    if r_capavel:
        # Formula_SomaR (14): pedido do dono ao implementar o Multiplo R --
        # sistemas com SL validam (e entregam) medidos em R, nao na formula
        # usada para MOLDAR a busca genetica (9/8, escolhidas para nao punir
        # sorte concentrada / filtro que reduz trades). SomaR sozinho nunca
        # decide quem vence aqui: so um candidato chega a entrega, ja aprovado
        # em retencao + divergencia + Monte Carlo + expectancy em R acima.
        entrega["selectedFormula"] = "14"
    if sizing_entrega == "percentage":
        # A prova do estagio 5 foi em %, entao e em % que o set sai: entregar
        # em Fixed-R seria entregar um modo que a ultima conferencia nao mediu.
        entrega["PositionSizeMode"] = "0"

    # O prefixo carrega o veredito. Um reprovado gravado como "VALIDADO_" entra
    # na biblioteca pelo nome e ninguem reabre o log para descobrir que a
    # retencao era negativa -- o arquivo passa a afirmar o que ele nao provou.
    prefixo = "VALIDADO" if aprovado else "REPROVADO"
    destino = (base.DADOS / "MQL5" / "Profiles" / "Tester" /
               f"{prefixo}_{args.symbol.replace('.', '_')}_"
               f"{args.sistema}_{args.variante}.set")
    reescrever(origem, destino, [], entrega)
    faltando = conferir_set(destino, entrega)
    if faltando:
        print(f"\n  ABORTADO: o set de entrega saiu incompleto: {faltando}")
        return 1

    print(f"\n    set gravado (WFO desligado): {destino.name}")
    print(json.dumps({"simbolo": args.symbol, "sistema": args.sistema,
                      "variante": args.variante, "lucro_ohlc": lucro_ohlc,
                      "lucro_tick_real": lucro_real,
                      "retencao_oos": oos["retencao"],
                      "retencao_pct": retencao_pct,
                      "sizing_entrega": sizing_entrega,
                      "expectancy_r": oos["expectancy"],
                      "trades_oos": oos["trades"],
                      "mc_dd_p95": mc["mc_dd_p95"] if mc else None,
                      "mc_dd_observado": mc["mc_dd_observado"] if mc else None,
                      "mc_prob_ruina": mc["mc_prob_ruina"] if mc else None,
                      "mc_aprovado": mc_aprovado,
                      "parametros": {**otimizados, **vencedor}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
