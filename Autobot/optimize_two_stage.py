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
  ESTAGIO 3.5 (tick real, grid/Pyramid/trail)  GEOMETRIA DE SAIDA: reabre so
                    os eixos de saida de cada sistema (grid classico: Take,
                    DistanciaMinima, VelaTake, UsarsomenteATRGRID; Grid
                    Inverso: Trail, TrailVela, MetodoDeCalculo,
                    DistanciaMinima, Multiplicador, UsarsomenteATRGRID;
                    trail puro/breakeven: Trail, TrailVela, MetodoDeCalculo,
                    +BreakevenDistancia so no 05_BE_TRAIL) sobre o resto ja
                    travado, e busca DIRETO em tick real (grid: dono,
                    2026-08-03, apos medir 45%+ de divergencia; Grid Inverso:
                    dono, 2026-08-17, 73.1%; trail puro: dono, 2026-08-22,
                    36-70% em EURJPY). Pequeno o bastante pra ser viavel
                    (~10-25 min); ataca a causa raiz -- geometria de saida e
                    a parte que realmente diverge OHLC vs tick real nesses
                    sistemas sem TP fixo -- em vez de so reprovar depois de
                    pronta.
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
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import campeoes_arquivo
import custo_nativo
import monte_carlo_wrx
import optimize_sets as base
import ready_library
from generate_system_sets import FORMULA_POR_SISTEMA
from mt5_runner import garantir_terminal_livre, lancar_terminal

AQUI = Path(__file__).resolve().parent
RELATORIOS_DIR = AQUI / "campanha_relatorios"
RELATORIO_SUFIXOS = (".htm", ".png", "-hst.png", "-mfemae.png", "-holding.png")
CHECKPOINTS_DIR = AQUI / "campanha_checkpoints"


def _checkpoint_estagio1(symbol: str, sistema: str, variante: str) -> Path:
    return CHECKPOINTS_DIR / f"{symbol}__{sistema}__{variante}.json"


def salvar_checkpoint_estagio1(symbol: str, sistema: str, variante: str,
                               cab: list[str], linhas: list[list[str]],
                               rodada: int) -> None:
    """Persiste o progresso do Estagio 1 apos cada rodada, combo a combo.

    Achado do dono, 2026-08-06: reiniciar a campanha (pra aplicar um fix)
    jogava fora o `linhas` acumulado das rodadas ja rodadas -- o cache do
    tester (.opt) preserva o resultado BRUTO de cada passe individual e
    acelera re-simular, mas isso e coisa diferente de reaproveitar o que o
    Estagio 1 ja tinha DECIDIDO (quantas rodadas, quais linhas passaram o
    piso). Sem isto, um restart sempre recomeca a contagem do zero mesmo
    com o MT5 respondendo rapido pelo cache.
    """
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    _checkpoint_estagio1(symbol, sistema, variante).write_text(
        json.dumps({"symbol": symbol, "sistema": sistema, "variante": variante,
                    "cab": cab, "linhas": linhas, "rodada_concluida": rodada},
                   ensure_ascii=False),
        encoding="utf-8")


def carregar_checkpoint_estagio1(symbol: str, sistema: str,
                                 variante: str) -> dict | None:
    """Devolve o checkpoint SO se bater com este combo exato. `None` em
    qualquer outra situacao (ausente, corrompido, de outro combo) -- upgrade
    opcional, nunca uma dependencia dura: sem checkpoint valido, o Estagio 1
    comeca do zero normalmente, como sempre fez.
    """
    caminho = _checkpoint_estagio1(symbol, sistema, variante)
    if not caminho.exists():
        return None
    try:
        dado = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if (dado.get("symbol") != symbol or dado.get("sistema") != sistema
            or dado.get("variante") != variante
            or not isinstance(dado.get("linhas"), list)
            or not isinstance(dado.get("cab"), list)
            or not isinstance(dado.get("rodada_concluida"), int)):
        return None
    return dado


def limpar_checkpoint_estagio1(symbol: str, sistema: str, variante: str) -> None:
    _checkpoint_estagio1(symbol, sistema, variante).unlink(missing_ok=True)


PROGRESSO_PATH = AQUI / "campanha_progresso.json"


def salvar_progresso(symbol: str, sistema: str, variante: str, **campos) -> None:
    """Grava o progresso atual do combo (achado do dono, 2026-08-07): sem
    isso, ninguem de fora consegue ver o combo avancando sem abrir o log
    bruto do Tester -- um combo lento (grid pode passar de 2h so no
    Estagio 1) fica indistinguivel de um combo travado. Best-effort: falha
    de escrita aqui (disco cheio, permissao) nunca deve derrubar a
    campanha, so perde a visibilidade.
    """
    try:
        PROGRESSO_PATH.write_text(
            json.dumps({"symbol": symbol, "sistema": sistema,
                       "variante": variante,
                       "atualizado_em": datetime.now().isoformat(timespec="seconds"),
                       **campos}, ensure_ascii=False),
            encoding="utf-8")
    except OSError:
        pass


def limpar_progresso() -> None:
    PROGRESSO_PATH.unlink(missing_ok=True)

# FILE_COMMON (2026-08-04): a EA grava TODAS as 14 formulas aqui a cada
# passe do genetico -- Print/PrintFormat dentro de OnTester() nao aparece
# em log nenhum durante otimizacao (so em passe unico), confirmado com
# teste de canario; FileWrite com FILE_COMMON sim, validado ao vivo (17
# passes -> 17 linhas, sem colisao entre os 4 agentes em paralelo).
ARQUIVO_TODAS_FORMULAS = (Path(os.environ["APPDATA"])
                          / "MetaQuotes" / "Terminal" / "Common" / "Files"
                          / "levain_wrx_all_formulas.txt")

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

# O proprio MT5 escreve essa linha -- NAO o EA -- e a grafia muda de build
# pra build sem aviso: achado do dono, 2026-08-07, o terminal se auto-
# atualizou NO MEIO desta sessao (terminal64.exe trocou de mtime as 15:13:59)
# e a mensagem virou de "automatical testing finished" (com "-al", builds
# ate entao) para "automatic testing finished" (grafia padrao, builds
# depois) -- confirmado nos dois lados no mesmo log bruto do dia. Fixar
# qualquer uma das duas grafias quebra assim que o MT5 atualizar de novo;
# aceitar as duas e a unica versao que sobrevive a uma atualizacao do
# terminal sem virar bug de novo.
TESTE_CONCLUIDO = re.compile(r"automatic(al)? testing finished")

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
           "EntradaATR", "Hedging"}

# FASE 2 = SO NUMEROS: com a escrita travada, refinam-se os eixos numericos na
# faixa fina da biblioteca -- periodos, multiplicadores, distancias, limiares.
# O ajuste dos filtros entra aqui e SO se a flag sobreviveu (GATES corta o
# ajuste de quem morreu cravada em false).
NUMEROS = ["Fast_EMA", "Slow_EMA", "MACD_SMA", "StochasticSlowing",
           "PeriodoATR", "VelaStop", "VelaTake", "TrailVela",
           "Stop", "Take", "Trail", "BreakevenDistancia",
           "Multiplicador", "DistanciaMinima", "MaxMartingaleSteps",
           "DAlembertStep",
           "MA_TimeFrame", "MA_Period", "MA_SlopeLookback",
           "ADX_TimeFrame", "ADX_Period", "ADX_Limiar",
           "MA_Method", "MetodoMA", "SentidoMA", "MA_AppliedPrice",
           "MetodoADX", "MTF_RequererAmbos", "VolatilityFilter"]

# Geometria de saida da familia grid (dono, 2026-08-03, estendido
# 2026-08-17): medido que grid classico diverge OHLC->tick real em ate 45%+
# (23x subestimado, ver docstring do modulo) -- e SO na geometria de saida,
# porque a entrada (indicador/metodo/timeframe) da o MESMO instante nos
# dois modelos por construcao (anti-repaint no fechamento da barra).
# Buscar o circuito inteiro em tick real e inviavel (medido: ~7-8x mais
# lento por passe que OHLC, semanas por simbolo em escala) -- mas reabrir
# SO os eixos de saida, ja travados pelas fases 1/2 em OHLC, e um genetico
# pequeno e barato o bastante pra rodar direto em tick real.
#
# 12_GRID_INVERSO entrou aqui em 2026-08-17 (achado do dono): tinha o MESMO
# buraco que motivou este mecanismo pro grid classico em 2026-08-03, so que
# nunca tinha sido estendido pra ele -- medido 73.1% de divergencia OHLC vs
# tick real numa corrida de teste (EURUSD, 3 meses), reprovado por causa
# disso sem nenhuma correcao disponivel. Eixos diferentes do grid classico
# porque a saida e diferente (trailing ATR sobre a cesta, nao meta de
# lucro): GATES confirma que Trail/TrailVela/MetodoDeCalculo sao os eixos
# de geometria REALMENTE ativos pra ele (o oposto do grid classico, onde
# ficam mortos porque AtivarTrailATR e cravado false) -- e Stop/VelaStop
# ficam de fora aqui mesmo sendo ativos (AtivarStop=true pro Pyramid,
# diferente do grid classico): e risco por perna, nao timing de saida da
# cesta, o tipo de divergencia que este mecanismo ataca.
# 08_GRID_UNIFIED removido (2026-08-16) -- ver generate_system_sets.py:SYSTEMS.
#
# 03_TRAIL_ONLY/05_BE_TRAIL entraram aqui em 2026-08-22 (achado do dono, campanha
# de conta pequena em USDJPY/EURJPY): mesmo buraco de novo, dessa vez em trail
# puro -- 3 combos de EURJPY reprovados por divergencia de 36.5%/50.8%/69.6%,
# maior ainda que o do Pyramid. Mesma causa raiz: sem TP, a posicao so sai no
# trailing (ou breakeven), entao pode ficar aberta dias/semanas -- quanto mais
# tempo aberta, mais a aproximacao por barra M1 (em vez do caminho real do tick)
# acumula erro. Eixos: Trail/TrailVela/MetodoDeCalculo pros dois (mesmos 3 do
# Pyramid, mesmo motivo -- GATES confirma que sao os unicos de geometria
# realmente ativos aqui, AtivarTrailATR cravado true nesses dois sistemas);
# BreakevenDistancia so no 05_BE_TRAIL, que tambem sai fora no breakeven (gated
# por AtivarBreakeven, cravado true so nesse). Sem DistanciaMinima/
# UsarsomenteATRGRID/Multiplicador: sao conceito de cesta multi-perna (grid),
# 03/05 sao posicao unica, esses eixos nem existem de verdade pra eles.
# 11_SIGNAL_ONLY NAO entra aqui apesar de tambem nao ter TP: fecha so no sinal
# contrario, sem trail/breakeven nenhum -- nao ha geometria de saida pra
# rebuscar, a divergencia dele (se houver) e de outra natureza.
SISTEMAS_GEOMETRIA_TICK_REAL = {"07_GRID_SEPARATE", "12_GRID_INVERSO",
                                "03_TRAIL_ONLY", "05_BE_TRAIL",
                                "04_SLTP_TRAIL"}
EIXOS_GEOMETRIA_TICK_REAL = {
    "07_GRID_SEPARATE": ["Take", "DistanciaMinima", "VelaTake",
                         "UsarsomenteATRGRID"],
    "12_GRID_INVERSO": ["Trail", "TrailVela", "MetodoDeCalculo",
                        "DistanciaMinima", "Multiplicador",
                        "UsarsomenteATRGRID"],
    "03_TRAIL_ONLY": ["Trail", "TrailVela", "MetodoDeCalculo"],
    "05_BE_TRAIL": ["Trail", "TrailVela", "MetodoDeCalculo",
                    "BreakevenDistancia"],
    # 04_SLTP_TRAIL entrou em 2026-08-27 (achado do dono): unico irmao da
    # familia trend fora desta protecao -- zerou 4/4 na confirmacao de 1
    # ano, sempre por divergencia, nunca por retencao (163%-368%, bem acima
    # do piso). AtivarTrailATR/AtivarTake/AtivarStop cravados true (N) no
    # .set origem -- geometria mais completa da familia (SL+TP fixos +
    # trailing + breakeven opcional), o cenario de maior ambiguidade
    # O->H->L->C. BreakevenDistancia entra mesmo com AtivarBreakeven
    # otimizavel (Y): GATES ja filtra dinamicamente por candidato, entao
    # incluir aqui e seguro mesmo quando o vencedor especifico tiver
    # breakeven desligado.
    "04_SLTP_TRAIL": ["Stop", "VelaStop", "Take", "VelaTake",
                      "Trail", "TrailVela", "MetodoDeCalculo",
                      "BreakevenDistancia"],
}

# Gate de sobrevivencia de periodo completo (dono, 2026-08-08): DESACOPLADO
# de SISTEMAS_GEOMETRIA_TICK_REAL de proposito (achado 2026-08-22: nao dava
# mais pra derivar um do outro por uniao -- 03_TRAIL_ONLY/05_BE_TRAIL
# entraram no Estagio 3.5 mas NAO tem o risco que motiva este gate). Este
# conjunto e sobre QUEM roda o Estagio 4.5 (verificar_sobrevivencia_completa,
# ver docstring): todo sistema sem SL nativo POR POSICAO que limite o dano de
# uma sequencia ruim, onde a exposicao (cesta, escalonamento de lote) so
# quebra no periodo continuo de verdade -- 03_TRAIL_ONLY/05_BE_TRAIL tem SL
# real por posicao (sao Fixed-R capazes por causa disso, ver r_capable em
# generate_system_sets.py) e ficam de fora por isso, mesmo estando em
# SISTEMAS_GEOMETRIA_TICK_REAL agora.
SISTEMAS_GATE_SOBREVIVENCIA = {
    "07_GRID_SEPARATE", "09_MARTINGALE", "10_DALEMBERT", "11_SIGNAL_ONLY",
    # 12_GRID_INVERSO (achado do dono, 2026-08-16): unica excecao aqui que
    # TEM SL nativo por perna (AtivarStop=true, ao contrario do resto deste
    # conjunto) -- entra mesmo assim porque e cesta multi-perna com
    # mecanismo de saida NOVO (trailing ATR sobre a cesta, nunca testado
    # ao vivo) e Multiplicador geometrico podendo crescer exposicao numa
    # sequencia que ainda pode reverter. Mesma familia de risco "cesta que
    # so quebra no periodo continuo de verdade" que motivou este gate.
    "12_GRID_INVERSO"}

# Camada de recuperacao buscada em ETAPA SEPARADA, depois da entrada/saida ja
# estarem travadas no vencedor SEM recuperacao (achado do dono, 2026-08-16):
# antes, MaxMartingaleSteps/DAlembertStep eram so mais um eixo dentro do
# mesmo genetico do Estagio 1/2 -- o otimizador podia usar lote crescendo
# depois de perda pra disfarcar um sinal de entrada mediocre dentro da
# amostra, e isso so aparecia quebrado no gate de sobrevivencia (periodo
# completo), nunca na janela curta de busca. Separar em duas etapas valida o
# sinal honesto primeiro (RecoveryMode=0 travado, lote fixo puro, igual
# 01_SLTP mede) e so DEPOIS liga a recuperacao e busca os eixos dela sozinhos,
# em cima do vencedor ja validado. Ver Estagio 2.5 em main().
#
# MaxMartingaleSteps entra nos DOIS -- confirmado no .mq5 (RefreshDAlembertState,
# g_dalembert_buy/sell = MathMin(..., MaxMartingaleSteps)): nao e exclusivo do
# martingale classico, tambem tampa quantos passos o D'Alembert acumula antes
# de resetar. Achado do dono, 2026-08-16, revisando o primeiro smoke test do
# D'Alembert: o JSON de saida trazia MaxMartingaleSteps sem DAlembertStep ter
# saido junto do Estagio 2.5 -- a lista tinha so 1 eixo, faltava o segundo.
SISTEMAS_RECUPERACAO_DUAS_ETAPAS = {"09_MARTINGALE", "10_DALEMBERT"}
EIXOS_RECUPERACAO = {"09_MARTINGALE": ["MaxMartingaleSteps"],
                     "10_DALEMBERT": ["DAlembertStep", "MaxMartingaleSteps"]}
RECOVERY_MODE_LIGADO = {"09_MARTINGALE": "1", "10_DALEMBERT": "2"}

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
    "MA_TimeFrame": "AtivarFiltroMA",
    "MA_Period": "AtivarFiltroMA",
    "MetodoMA": "AtivarFiltroMA",
    "MA_Method": "AtivarFiltroMA",
    "SentidoMA": "AtivarFiltroMA",
    "MA_AppliedPrice": "AtivarFiltroMA",
    "MA_SlopeLookback": "AtivarFiltroMA",
    "ADX_TimeFrame": "AtivarFiltroADX",
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


def piso_trades_da_janela(inicio: str, fim: str, taxa_anual: float,
                          piso_minimo: int = 30) -> int:
    """Deriva o piso de trades do Estagio 2+ a partir da duracao REAL
    testada, no lugar do piso absoluto --min-trades (default 100,
    calibrado pra corridas multi-ano). Achado do dono, 2026-08-27:
    sweep_formulas.py roda esse piso em janelas de 92 dias -- 100 trades
    em 92 dias e uma barra muito mais dura que 100 trades em 3+ anos, e e
    a causa mais provavel de "nenhum candidato" em sistemas de reversao a
    media (09_MARTINGALE/10_DALEMBERT, AUDNZD).

    piso_minimo=30 espelha o piso1 ja aceito no Estagio 1 (linha ~1451,
    max(30, min_trades//3)) -- uma janela curtissima nao deriva pra um
    numero absurdo.
    """
    d0 = datetime.strptime(inicio, "%Y.%m.%d")
    d1 = datetime.strptime(fim, "%Y.%m.%d")
    dias = max(1, (d1 - d0).days)
    return max(piso_minimo, round(taxa_anual * dias / 365))


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
            cand, lucro_is, trades_is = {}, 0.0, None
        else:
            cand = {c: v for c, v in zip(cab, linha) if c not in metricas}
            lucro_is = base.num(linha[cab.index("Profit")])
            # Trades OOS (R METRICS) so existe pra sistemas Fixed-R -- grid e
            # recovery usam lote fixo/monetario e o bloco nunca aparece no
            # log da EA, deixando `r['trades']` sempre None (achado real,
            # 2026-08-03: candidato aprovado sem NENHUMA visao de quantos
            # trades geraram o lucro). A coluna "Trades" do proprio relatorio
            # genetico existe pra qualquer sizing e nao depende de idioma do
            # terminal -- serve de contagem IN-SAMPLE quando o R METRICS falha.
            trades_is = (int(base.num(linha[cab.index("Trades")]))
                        if "Trades" in cab else None)
        passo = dict(travados, **cand, MetodoDeEntradawfo="1")
        reescrever(origem, trabalho, [], passo)
        faltando = conferir_set(trabalho, passo)
        if faltando:
            print(f"      {i:2}. pulado: nao chegou ao set {faltando}", flush=True)
            continue
        try:
            r = passe_unico(trabalho, args.symbol, args.period, args.inicio,
                            args.fim, args.deposit, modelo)
        except subprocess.TimeoutExpired:
            # Achado do dono, 2026-08-06: um UNICO passe travado (o mesmo
            # bug de processo que nao fecha a tempo, ja visto no gate de
            # sobrevivencia) derrubava o main() inteiro com traceback --
            # jogando fora HORAS de Estagio 1 ja completo (3 rodadas, todos
            # os indicadores medidos) so porque o 2o candidato do torneio
            # nao respondeu. O combo virava "sem JSON final" no ledger, sem
            # veredito nenhum sobre a estrategia -- so um crash disfarcado
            # de reprovacao. Pulado como qualquer outro candidato sem
            # medida (linha 458 acima) em vez de propagar.
            print(f"      {i:2}. pulado: timeout no passe unico", flush=True)
            continue
        ret, exp = r["retencao"], r["expectancy"]
        # trades_is viaja com `r` (nao so no print) pra chegar ate o ledger --
        # sem isso o "trades" do combo vencedor (conf[0], usado no JSON final)
        # ficava None pra sempre em grid/martingale/d'Alembert, e a coluna
        # Trades do dashboard nunca mostrava nada pra exatamente os sistemas
        # que motivaram o achado (2026-08-03).
        r["trades_is"] = trades_is
        trades_txt = (f"{r['trades']} trades" if r["trades"] is not None
                     else (f"~{trades_is} trades (IS, R METRICS indisponivel "
                           "neste sizing)" if trades_is is not None
                           else "trades n/d"))
        print(f"      {i:2}. lucro IS {lucro_is:>8.2f} | retencao "
              f"{'    n/d' if ret is None else f'{ret:>7.1f}%'} | "
              f"{trades_txt} | expectancy "
              f"{'n/d' if exp is None else f'{exp:+.3f}R'}", flush=True)
        salvar_progresso(args.symbol, args.sistema, args.variante,
                         estagio=f"torneio ({rotulo})",
                         finalista_atual=f"{i}/{len(candidatos)}")
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


def carregar_campeao_atual(sistema: str, simbolo: str, variante: str) -> dict | None:
    """Metricas do candidato JA IMPLANTADO (VALIDADO_*.set) para o mesmo
    combo. Reusa a MESMA convencao de nome e o MESMO ledger que
    ready_library.py ja usa pra responder "existe algo pronto?" -- gate
    relativo (inspirado no should_promote() do Zeus) nao inventa um segundo
    lugar pra essa resposta morar, so LE o que ja existe.

    Devolve None so quando nao ha campeao NENHUM (combo nunca aprovado).
    Quando o arquivo existe mas o ledger nao tem registro dele, devolve {}
    (nao None) -- distincao que importa na pratica: a recalibracao de
    24-28/08 rodou por scripts diretos (_continuar_calibracao.py e
    variantes), nao por campanha.py, entao a maioria dos campeoes atuais
    (ex. 12_GRID_INVERSO/XAUUSD) tem arquivo VALIDADO_ real mas ZERO
    registro no ledger (so 11 entradas, todas de antes de 19/08) -- achado
    ao testar este gate pela primeira vez, nao suposicao. Sem a distincao,
    o log ficaria mudo sobre por que um campeao real nao esta gateando
    nada, em vez de avisar que falta dado.
    """
    simbolo_norm = simbolo.replace(".", "_")
    candidato = ready_library.TESTER / f"VALIDADO_{simbolo_norm}_{sistema}_{variante}.set"
    if not candidato.exists():
        return None
    registros = ready_library.metricas_do_ledger(ready_library.LEDGER)
    return registros.get((simbolo_norm, sistema, variante), {})


# Ponto de partida do gate.py/config.py do Zeus (should_promote(),
# 2026-08-30) -- mesmos valores, nao numero calibrado pros NOSSOS sistemas
# ainda. Tolerancias relativas (nao 100%): um desafiante pode ser um pouco
# pior num eixo isolado desde que o composite_score final vença, mesma
# filosofia do Zeus (nenhum eixo isolado veta sozinho, exceto trades/score).
GATE_MIN_TRADES_RELATIVO = 30
GATE_MIN_PF = 1.15
GATE_PF_RELATIVE = 0.95
GATE_MAX_DD_PCT = 25.0
GATE_DD_RELATIVE = 1.15
GATE_SHARPE_RELATIVE = 0.90


def composite_score(profit: float, deposit: float, profit_factor: float,
                    max_dd_pct: float, trades: int,
                    min_trades: int = GATE_MIN_TRADES_RELATIVO) -> float:
    """Espelha composite_score() do gate.py do Zeus (2026-08-30): retorno %
    (nao so profit_factor*log(trades) -- versao antiga do Zeus degenerava
    pra sizing quase zero, porque encolher posicao encolhe max_dd_pct de
    graca) vezes profit factor, amortecido pelo drawdown.
    """
    if trades < min_trades:
        return -1e9
    if deposit <= 0:
        return -1e9
    return_pct = profit / deposit * 100.0
    dd_guard = 1.0 + max_dd_pct / 20.0
    return return_pct * profit_factor / dd_guard


def avaliar_gate_relativo(campeao: dict, desafiante: dict) -> tuple[bool, list[str]]:
    """Espelha should_promote() do gate.py do Zeus: 5 checks SIMULTANEOS,
    todos precisam passar (sem credito parcial) -- trades, profit_factor
    relativo, max_dd_pct relativo, Sharpe relativo, composite_score
    estritamente maior. Ausencia de dado do campeao em qualquer eixo pula
    SO aquele check (mesma logica de "sem baseline, sem regressao" que
    carregar_campeao_atual() ja segue) -- nao derruba o desafiante por um
    campo que o campeao nunca teve medido (ex.: ledger antigo, sem
    profit_factor).
    """
    checks: list[tuple[bool, str]] = []
    trades = desafiante.get("trades")
    if trades is not None:
        checks.append((
            trades >= GATE_MIN_TRADES_RELATIVO,
            f"trades {trades} >= {GATE_MIN_TRADES_RELATIVO}"))

    pf_campeao = campeao.get("profit_factor")
    pf_desafiante = desafiante.get("profit_factor")
    if pf_campeao is not None and pf_desafiante is not None:
        min_pf = max(GATE_MIN_PF, pf_campeao * GATE_PF_RELATIVE)
        checks.append((
            pf_desafiante >= min_pf,
            f"profit_factor {pf_desafiante:.4f} >= {min_pf:.4f} (max de "
            f"piso={GATE_MIN_PF} e {GATE_PF_RELATIVE}*campeao={pf_campeao:.4f})"))

    dd_campeao = campeao.get("max_dd_pct")
    dd_desafiante = desafiante.get("max_dd_pct")
    if dd_campeao is not None and dd_desafiante is not None:
        max_dd = min(GATE_MAX_DD_PCT, dd_campeao * GATE_DD_RELATIVE)
        checks.append((
            dd_desafiante <= max_dd,
            f"max_dd_pct {dd_desafiante:.4f} <= {max_dd:.4f} (min de "
            f"teto={GATE_MAX_DD_PCT} e {GATE_DD_RELATIVE}*campeao={dd_campeao:.4f})"))

    sharpe_campeao = campeao.get("sharpe")
    sharpe_desafiante = desafiante.get("sharpe")
    if sharpe_campeao is not None and sharpe_desafiante is not None:
        min_sharpe = sharpe_campeao * GATE_SHARPE_RELATIVE
        checks.append((
            sharpe_desafiante > 0 and sharpe_desafiante >= min_sharpe,
            f"sharpe {sharpe_desafiante:.4f} > 0 e >= "
            f"{GATE_SHARPE_RELATIVE}*campeao={min_sharpe:.4f}"))

    score_campeao = campeao.get("composite_score")
    score_desafiante = desafiante.get("composite_score")
    if score_campeao is not None and score_desafiante is not None:
        checks.append((
            score_desafiante > score_campeao,
            f"composite_score {score_desafiante:.4f} > campeao "
            f"{score_campeao:.4f}"))

    aprovado = all(ok for ok, _ in checks)
    motivos = [f"{'OK' if ok else 'REPROVADO'}: {msg}" for ok, msg in checks]
    return aprovado, motivos


def remedir_campeao_na_janela(sistema: str, simbolo: str, variante: str,
                              inicio: str, fim: str, deposito: int,
                              periodo: str) -> dict:
    """Re-mede o campeao ATUAL (parametros travados do ledger) na MESMA
    janela do desafiante desta corrida -- achado real, 2026-08-30: o gate
    comparava o campeao com as metricas ESTATICAS do ledger (medidas
    sabe-se-la quando, numa janela qualquer) contra o desafiante medido na
    janela DESTE run, sem garantir que sao a mesma. Mesmo erro que o
    proprio Zeus documenta ja ter cometido e corrigido (gate.py: "based on
    two backtest.BacktestResult objects measured on the IDENTICAL out-of-
    sample window... comparing KPIs from different date ranges is a
    meaningless apples-to-oranges comparison, not a smaller version of the
    same bug").

    Custa um passe de MT5 a mais (~30-90s) toda vez que o gate roda --
    aceito pelo mesmo motivo que o Zeus aceita: e o preco de uma decisao
    de promocao que nao pode dar errado por comparar coisas diferentes.

    Devolve {} se nao ha campeao, sem parametros no ledger, ou sem
    template de origem -- mesmo contrato de ausencia de
    carregar_campeao_atual()/avaliar_gate_relativo() (gate so pula,
    nunca quebra).
    """
    campeao = carregar_campeao_atual(sistema, simbolo, variante)
    if not campeao or "parametros" not in campeao:
        return {}
    origem = base.achar_set(simbolo, sistema, variante)
    if origem is None:
        return {}

    trabalho = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_REMEDIR_CAMPEAO.set"
    wfo = janelas_wfo(inicio, fim)
    passo = dict(wfo, **campeao["parametros"], MetodoDeEntradawfo="1",
                InterfaceLanguage="1")
    reescrever(origem, trabalho, [], passo)
    limpar_todas_formulas()
    r = passe_unico(trabalho, simbolo, periodo, inicio, fim, deposito, 4)
    stats_list = carregar_todas_formulas()
    stats = stats_list[-1] if stats_list else None
    if stats is None:
        return {}

    gp, gl = stats.get("gross_profit"), stats.get("gross_loss")
    pf = gp / abs(gl) if gp is not None and gl not in (None, 0) else None
    dd = stats.get("equity_dd_rel_pct")
    sharpe = stats.get("sharpe")
    trades = stats.get("trades")
    profit = stats.get("profit")
    score = (composite_score(profit, deposito, pf, dd, trades)
            if None not in (pf, dd, trades, profit) else None)
    return {"profit_factor": pf, "max_dd_pct": dd, "sharpe": sharpe,
           "composite_score": score, "trades": trades,
           "expectancy_r": r["expectancy"]}


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


_PADRAO_ALL_FORMULAS = re.compile(
    r"ALL_FORMULAS Profit=([-\d.]+) Trades=(\d+) GrossProfit=([-\d.]+) "
    r"GrossLoss=([-\d.]+) EquityDDPercent=([-\d.]+) Sharpe=([-\d.]+) "
    r"InitialDeposit=([-\d.]+) \| GridSurvival=([-\d.]+) "
    r"ProfitFormula=([-\d.]+) ProfitWinTradeDD=([-\d.]+) "
    r"EffRelDeposit=([-\d.]+) AdjEffGrid=([-\d.]+) "
    r"ProfitRelDDDeposit=([-\d.]+) PPTDD=([-\d.]+) SharpeAdjDD=([-\d.]+) "
    r"PessimisticProfit=([-\d.]+) ResilienceDD=([-\d.]+) "
    r"ReturnUniformity=([-\d.]+) SystemRobustness=([-\d.]+) "
    r"LevainComposite=([-\d.]+) SomaR=([-\d.]+) "
    r"EquityDDRelPercent=([-\d.]+) ZeusScore=([-\d.]+)")

_CAMPOS_ALL_FORMULAS = [
    "profit", "trades", "gross_profit", "gross_loss", "equity_dd_pct",
    "sharpe", "initial_deposit", "grid_survival", "profit_formula",
    "profit_win_trade_dd", "eff_rel_deposit", "adj_eff_grid",
    "profit_rel_dd_deposit", "pptdd", "sharpe_adj_dd", "pessimistic_profit",
    "resilience_dd", "return_uniformity", "system_robustness",
    "levain_composite", "soma_r",
    # Acrescentado 2026-08-30, no FIM da lista de proposito: mantem os
    # indices 7-20 usados por _CAMPO_POR_INDICE_FORMULA intactos.
    # STAT_EQUITY_DDREL_PERCENT (drawdown vs PICO de capital, nao vs
    # deposito inicial como equity_dd_pct acima) -- o max_dd_pct que o
    # gate relativo (avaliar_gate_relativo(), espelha o should_promote()
    # do Zeus) precisa pra comparar de verdade contra o mesmo campo do
    # Zeus.
    "equity_dd_rel_pct",
    # Formula_ZeusCompositeScore (2026-08-30, indice 15 no enum
    # CustomFormulaType) -- PORTE LITERAL do composite_score() do Zeus,
    # ver ZeusCompositeScore() no .mq5. Vem DEPOIS de equity_dd_rel_pct
    # na lista porque foi gravado depois dele na mesma linha do
    # FileWrite (append no fim de proposito, mesma disciplina de nao
    # remexer indices anteriores) -- por isso o mapeamento formula->campo
    # logo abaixo nao e um slice continuo unico.
    "zeus_score",
]

# indice de formula (mesmo enum CustomFormulaType do .mq5, mesmo valor
# gravado em selectedFormula no .set por FORMULA_POR_SISTEMA) -> campo de
# _CAMPOS_ALL_FORMULAS. As 14 formulas originais (posicoes 7-20) vem de um
# slice continuo, derivado da propria lista -- nunca desalinha se
# _CAMPOS_ALL_FORMULAS mudar nesse trecho. zeus_score (indice 15) e
# adicionado a parte porque nao esta na posicao contigua seguinte
# (equity_dd_rel_pct, que nao e formula, ficou no meio).
_CAMPO_POR_INDICE_FORMULA: dict[int, str] = dict(
    enumerate(_CAMPOS_ALL_FORMULAS[7:21], start=1))
_CAMPO_POR_INDICE_FORMULA[15] = "zeus_score"


def campo_da_formula(sistema: str) -> str:
    """Campo de _CAMPOS_ALL_FORMULAS que corresponde a formula que
    REALMENTE guia a busca genetica de `sistema` (FORMULA_POR_SISTEMA em
    generate_system_sets.py, mesmo indice gravado em selectedFormula no
    .set).

    Existe porque priorizar_lucro_no_topo()/reordenar_por_formula()
    decidiam ELEGIBILIDADE sempre por GridSurvivalScore (default antigo,
    nunca trocado) mesmo em sistemas guiados por outra formula -- achado do
    dono, 2026-08-24: 03_TRAIL_ONLY usa ReturnUniformity, 05_BE_TRAIL usa
    ProfitRelativeToDDAndDeposit, 07_GRID_SEPARATE/12_GRID_INVERSO usam
    ResilienceToDrawdown, mas o corte de elegibilidade que antecede a
    repriorizacao por lucro continuava ordenando pela formula ERRADA --
    podia descartar candidatos que a formula real preferia antes deles
    chegarem a ser considerados pelo torneio de retencao.
    """
    indice = FORMULA_POR_SISTEMA[sistema]
    if indice not in _CAMPO_POR_INDICE_FORMULA:
        raise KeyError(
            f"sistema {sistema!r} usa indice de formula {indice}, sem "
            "campo mapeado em _CAMPO_POR_INDICE_FORMULA.")
    return _CAMPO_POR_INDICE_FORMULA[indice]


_PADRAO_SELECTED_FORMULA = re.compile(r"selectedFormula=(\d+)\|\|")


def indice_formula_do_set(caminho: Path) -> int | None:
    """Le o indice REAL gravado em selectedFormula no .set de origem --
    mesmo padrao que sweep_formulas.py escreve ao reescrever o .set pra
    testar uma formula especifica. None se o arquivo nao existir ou o
    padrao nao for encontrado (set antigo sem esse input, etc.).
    """
    try:
        texto = caminho.read_text(encoding="utf-16")
    except OSError:
        return None
    m = _PADRAO_SELECTED_FORMULA.search(texto)
    return int(m.group(1)) if m else None


def campo_da_formula_ativa(sistema: str, origem: Path) -> str:
    """Como campo_da_formula(), mas prefere o indice REALMENTE escrito no
    .set de origem sobre FORMULA_POR_SISTEMA -- fonte de verdade do que o
    genetico esta evoluindo NESTE combo especifico.

    Existe porque sweep_formulas.py reescreve selectedFormula no .set pra
    testar cada uma das 14 formulas SEM regenerar os sets (sem atualizar
    FORMULA_POR_SISTEMA) -- achado do dono, 2026-08-24, testando Profit x
    ReturnUniformity em GBPUSD: sem isso, o corte de elegibilidade
    continuaria filtrando por ReturnUniformity (o valor de producao) mesmo
    testando Profit, contaminando a comparacao com a MESMA classe de bug
    que campo_da_formula() corrigiu pra producao.
    """
    indice = indice_formula_do_set(origem)
    if indice is None:
        indice = FORMULA_POR_SISTEMA[sistema]
    if indice not in _CAMPO_POR_INDICE_FORMULA:
        raise KeyError(
            f"sistema {sistema!r} usa indice de formula {indice}, sem "
            "campo mapeado em _CAMPO_POR_INDICE_FORMULA.")
    return _CAMPO_POR_INDICE_FORMULA[indice]


def ler_todas_formulas(log: str) -> list[dict]:
    """Le TODAS as linhas ALL_FORMULAS de um log, uma por passe (ordem de
    execucao, nao a ordem do relatorio).

    Cada formula e calculada pela PROPRIA EA (OnTester, 2026-08-04) --
    GridSurvivalScore e PessimisticProfit usam desvio-padrao/contagem de
    trades individuais via g_closedOperations[], dado que nao sobrevive no
    relatorio resumido do genetico. Reimplementar essas duas em Python a
    partir das colunas do relatorio teria dado numero aproximado, nao real
    -- por isso a EA imprime, em vez do Python recalcular.

    Funcao separada de proposito, mesmo padrao de ler_metricas: testa em
    milissegundos contra um log gravado, sem precisar do MT5.

    Linha malformada e pulada, nunca propagada (achado do dono, 2026-08-22:
    ValueError 'could not convert string to float: -' derrubou o combo
    inteiro). O regex de _PADRAO_ALL_FORMULAS aceita um "-" sozinho como campo -- sintoma
    de colisao de escrita entre os ate 14 agentes locais gravando no MESMO
    arquivo compartilhado (FILE_COMMON, ver limpar_todas_formulas()): rara,
    mas nao impossivel, mesma ressalva que magic_estavel() ja faz sobre
    colisao de hash. Um passe sem leitura valida de formula so perde a nota
    externa DESSE passe (cai pro `if f is None` em priorizar_lucro_no_topo/
    reordenar_por_formula) -- nao motivo pra derrubar o combo inteiro que
    ja levou dezenas de minutos de busca genetica de verdade.
    """
    saida = []
    for m in _PADRAO_ALL_FORMULAS.finditer(log):
        valores = m.groups()
        try:
            d = {campo: (int(v) if campo == "trades" else float(v))
                for campo, v in zip(_CAMPOS_ALL_FORMULAS, valores)}
        except ValueError:
            continue
        saida.append(d)
    return saida


def casar_formula_com_relatorio(cab: list[str], linhas: list[list[str]],
                                todas_formulas: list[dict],
                                tolerancia_pct: float = 0.001) -> dict[int, dict]:
    """Casa cada linha do relatorio .xml do genetico (por indice) com o
    dict de formulas do MESMO passe, lido do log.

    O relatorio do genetico reordena as linhas por resultado -- a ordem em
    que elas aparecem NAO e a ordem de execucao dos passes, entao nao da
    pra casar por posicao. O casamento usa Profit+Trades (+Equity DD % se
    disponivel) como impressao digital: os dois lados vem da MESMA chamada
    de TesterStatistics() no mesmo passe, entao devem bater quase exato.
    """
    if "Profit" not in cab or "Trades" not in cab:
        return {}
    i_profit = cab.index("Profit")
    i_trades = cab.index("Trades")
    i_dd = cab.index("Equity DD %") if "Equity DD %" in cab else None
    casados: dict[int, dict] = {}
    usados: set[int] = set()
    for idx_linha, linha in enumerate(linhas):
        profit_rel = base.num(linha[i_profit])
        trades_rel = int(base.num(linha[i_trades]))
        dd_rel = base.num(linha[i_dd]) if i_dd is not None else None
        for idx_f, f in enumerate(todas_formulas):
            if idx_f in usados or f["trades"] != trades_rel:
                continue
            if abs(f["profit"] - profit_rel) > max(0.01, abs(profit_rel) * tolerancia_pct):
                continue
            if dd_rel is not None and abs(f["equity_dd_pct"] - dd_rel) > 0.5:
                continue
            casados[idx_linha] = f
            usados.add(idx_f)
            break
    return casados


def limpar_todas_formulas() -> None:
    """Apaga o arquivo compartilhado antes de uma rodada genetica.

    Os 4 agentes gravam no MESMO arquivo (FILE_COMMON); sem limpar antes,
    a proxima rodada leria linhas de uma rodada anterior junto com as suas.
    """
    ARQUIVO_TODAS_FORMULAS.unlink(missing_ok=True)


def carregar_todas_formulas() -> list[dict]:
    """Le o arquivo compartilhado (UTF-16, escrito pela EA via FileWrite)
    da ULTIMA rodada genetica. Lista vazia se a EA nao escreveu nada --
    versao antiga do .ex5 sem o FileWrite, ou nenhum passe rodou.
    """
    if not ARQUIVO_TODAS_FORMULAS.exists():
        return []
    texto = ARQUIVO_TODAS_FORMULAS.read_text(encoding="utf-16", errors="replace")
    return ler_todas_formulas(texto)


def reordenar_por_formula(cab: list[str], linhas: list[list[str]],
                          campo: str) -> list[list[str]]:
    """Reordena as linhas do relatorio pela formula EXTERNA (arquivo que a
    EA grava via FileWrite), em vez da ordem nativa do genetico.

    A busca do grid evolui pela formula pura (GridSurvivalScore, via
    selectedFormula do .set -- OptimizationCriterion=6/Custom faz o genetico
    do MT5 evoluir SO em cima do que OnTester() devolve, mais nenhuma outra
    coluna do relatorio). Esta funcao reconstroi essa mesma nota fora do
    MT5, batendo por fingerprint (Profit+Trades+Equity DD%) com o que a EA
    gravou via FileWrite -- o relatorio nativo do genetico nao tem os dados
    por-trade que GridSurvivalScore precisa (CalculateStandardDeviation em
    cima de g_closedOperations[].net).

    Sem casamento (arquivo vazio, ou .ex5 antigo sem o FileWrite): devolve
    `linhas` na ordem original -- upgrade opcional, nunca uma dependencia
    dura que aborta o combo se faltar.
    """
    formulas = carregar_todas_formulas()
    if not formulas:
        return linhas
    casados = casar_formula_com_relatorio(cab, linhas, formulas)
    if not casados:
        return linhas
    indexadas = sorted(enumerate(linhas),
                       key=lambda item: (casados[item[0]][campo]
                                         if item[0] in casados else float("-inf")),
                       reverse=True)
    return [linha for _, linha in indexadas]


def priorizar_lucro_no_topo(cab: list[str], linhas: list[list[str]],
                            campo: str,
                            corte_pct: float = 0.20,
                            minimo: int = 10) -> list[list[str]]:
    """Formula pura decide quem E ELEGIVEL; lucro decide quem VENCE entre os
    elegiveis -- achado do dono, 2026-08-05: a formula sozinha as vezes
    elegia um passe de score alto e lucro baixo (600 de GridSurvivalScore,
    60 de lucro) na frente de outro so um pouco atras em score mas com
    lucro bem maior. O genetico do MT5 continua evoluindo 100% pela formula
    (isso nao muda, e nao da pra mudar -- OptimizationCriterion=6 so ve
    OnTester()); esta funcao so reordena o relatorio JA FINALIZADO.

    Corta o topo por formula (piso de risco -- e aqui que o teste A/B de
    2026-08-04 comparou "so formula" x "so lucro" e formula ganhou em
    sobrevivencia real), depois reordena SO essa fatia por lucro. O resto
    da lista (fora do topo) fica na ordem de formula original, sem uso
    imediato mas preservado por seguranca.
    """
    por_formula = reordenar_por_formula(cab, linhas, campo)
    return _priorizar_lucro_na_fatia(cab, por_formula, corte_pct, minimo)


def _priorizar_lucro_na_fatia(cab: list[str], linhas_por_formula: list[list[str]],
                              corte_pct: float = 0.20,
                              minimo: int = 10) -> list[list[str]]:
    """So a fatia de cima (`linhas_por_formula` ja vem ordenada por formula):
    pura reordenacao por lucro, sem tocar arquivo nenhum -- testavel em
    milissegundos, mesmo motivo do resto do modulo (ver reordenar_por_formula).
    """
    if not linhas_por_formula or "Profit" not in cab:
        return linhas_por_formula
    corte = max(minimo, round(len(linhas_por_formula) * corte_pct))
    topo, resto = linhas_por_formula[:corte], linhas_por_formula[corte:]
    i_lucro = cab.index("Profit")
    i_dd = cab.index("Equity DD %") if "Equity DD %" in cab else None
    topo = sorted(topo, key=lambda r: (base.num(r[i_lucro]),
                                       -base.num(r[i_dd]) if i_dd is not None else 0),
                 reverse=True)
    return topo + resto


def passe_unico(caminho_set: Path, symbol: str, periodo: str, inicio: str,
                fim: str, deposito: int, modelo: int,
                timeout: int | None = None) -> dict:
    """Roda UM backtest e devolve saldo final, trades e abortos.

    E assim que os ticks reais entram: como CONFERENCIA dos parametros que a
    otimizacao em OHLC ja escolheu, nao como busca. Otimizar em tick real sao
    milhares de passes a ~35s cada; conferir e um passe.

    E o passe unico responde a mesma pergunta que a otimizacao cara responderia:
    o resultado do OHLC se sustenta em dado real? Se sustenta, acabou. Se nao,
    ele EXPOE a divergencia -- enquanto otimizar em tick real teria escondido o
    problema, entregando um resultado bonito ajustado ao modelo caro.

    Sem teto proprio (dono, 2026-08-06): o antigo timeout=3600 fixo matava
    passes legitimos em ativo pesado (muito tick/history data pra carregar)
    -- e como lancar_terminal() nunca deixa o TimeoutExpired escapar, nao
    ha mais risco de crash em esperar. O teto real que ainda existe e o de
    fora, campanha.py --timeout (12h por combo).
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
        lancar_terminal(base.TERMINAL, ini, timeout)
    limite = time.monotonic() + 90
    log = ""
    while time.monotonic() < limite:
        log = base.texto_novo(antes)
        if TESTE_CONCLUIDO.search(log):
            break
        time.sleep(1)

    return ler_metricas(log)


def avaliar_sobrevivencia(log: str, deposito: int) -> dict:
    """Le o trecho de log de UM passe de sobrevivencia e decide se o set
    ENTREGUE (WFO desligado, periodo completo) sobrevive ou estoura margem.

    Funcao separada de proposito, mesma razao do ler_metricas: testa em
    milissegundos contra um log gravado, sem precisar do MT5.
    """
    # retcode=10019 ("No money"): o broker recusa abrir posicao NOVA por
    # falta de margem -- achado do dono, 2026-08-04, testando manualmente
    # o EURUSD/BUY_MULTI que o gate tinha aprovado (saldo final saudavel,
    # sem stop out). Diferente de estouro: a conta nao QUEBRA, ela FICA
    # PRESA, incapaz de operar por tempo indeterminado -- o saldo final
    # bonito escondia isso porque nenhuma posicao nova reduziu o saldo
    # parado. Sem SL nativo por posicao (grid usa cesta manual), qualquer
    # ocorrencia e sinal de que a cesta cresceu alem do que a conta aguenta.
    sem_margem = len(re.findall(r"retcode=10019", log))
    # CheckStopTradingCondition() no EA: stop de emergencia por drawdown de
    # equity, PERMANENTE (tradingStopped=true trava entrada pra sempre).
    # Achado do dono, 2026-08-15, revisando aprovados apos o fix do swap:
    # EURUSD/08_GRID_UNIFIED/BOTH_MULTI se autodesligou em 2025.04.03 (uma
    # cesta cresceu perna de 25x/13x o FixedLot perseguindo o alvo, o preco
    # nao voltou, o stop liquidou tudo com -1020 num tiro so) e ficou parado
    # ~16 meses ate o fim do periodo -- saldo final congelado passou pelo
    # piso de 50% porque nada mais mexeu nele depois. "stop out occurred" e
    # mensagem da CORRETORA (margin call de verdade); esta e o EA se
    # autodesligando por conta propria, saldo saudavel ou nao.
    autodesligou = "Trading stopped: strategy equity=" in log
    # Liquidacao forcada no CORTE do calendario do teste (achado do dono,
    # 2026-08-16, revisando o grafico de saldo de um aprovado -- queda de
    # ~1494 pra ~1220 no ultimo ponto). Nao e a estrategia quebrando: cesta
    # de recuperacao sem prazo fixo (grid/martingale/d'alembert) nao tem
    # garantia de terminar exatamente na borda de uma data de corte fixa --
    # o MT5 forca fechar tudo que ainda esta aberto, na hora que for, seja
    # a cesta fundo no vermelho ou perto do lucro (pura sorte de onde a
    # borda cai). Por isso NAO entra no calculo de `sobreviveu`/`motivo`
    # (nao e culpa da estrategia) -- so fica visivel pra quem for avaliar o
    # resultado, em vez de exigir abrir o log de deals na mao pra descobrir
    # que o final estava contaminado por fechamento forcado.
    fechados_fim_teste = len(re.findall(
        r"position closed due end of test", log))
    m = re.search(r"final balance ([\d.]+)", log)
    saldo_final = float(m.group(1)) if m else None
    # Ver TESTE_CONCLUIDO no topo do arquivo -- o MT5 muda a grafia dessa
    # linha entre builds (auto-update no meio de UMA sessao ja fez isso,
    # 2026-08-07), entao nunca comparar contra uma string fixa aqui.
    # saldo_final continua tambem aceito como prova de conclusao (nao so a
    # linha do Tester) -- defesa extra pro caso raro de ShutdownTerminal=1
    # cortar a ultima linha de bookkeeping antes dela ser gravada.
    completou = bool(TESTE_CONCLUIDO.search(log)) or saldo_final is not None
    estourou = "stop out occurred" in log
    # Piso de 50%: nao e so o stop out literal que denuncia ruina -- uma conta
    # que termina o periodo perto de zero sem tecnicamente estourar margem
    # (ex.: liquidacao forcada no fim do teste) e o mesmo problema.
    sobreviveu = (completou and not estourou and not autodesligou
                 and sem_margem == 0
                 and saldo_final is not None and saldo_final >= 0.5 * deposito)
    if not completou:
        motivo = ("teste nao completou -- nem a linha de bookkeeping do "
                  "Tester nem saldo final apareceram no log (timeout de verdade, "
                  "crash, ou log vazio)")
    elif estourou:
        motivo = "stop out (estouro de margem) durante o periodo completo"
    elif autodesligou:
        motivo = ("Trading stopped: a propria EA acionou o stop de "
                  "emergencia por drawdown de equity e travou entrada pra "
                  "sempre (tradingStopped permanente) -- saldo final pode "
                  "parecer saudavel so porque nada mais mexeu nele depois")
    elif sem_margem > 0:
        motivo = (f"sem margem pra abrir posicao {sem_margem}x durante o "
                  "periodo completo (retcode=10019, No money) -- conta "
                  "ficou presa, mesmo sem estourar")
    elif saldo_final is None:
        motivo = "saldo final nao encontrado no log"
    elif saldo_final < 0.5 * deposito:
        motivo = f"saldo final {saldo_final:.2f} < 50% do deposito ({deposito})"
    else:
        motivo = None
    return {"sobreviveu": sobreviveu, "saldo_final": saldo_final,
            "motivo": motivo, "fechados_fim_teste": fechados_fim_teste}


def verificar_sobrevivencia_completa(caminho_set: Path, symbol: str,
                                     periodo: str, inicio: str, fim: str,
                                     deposito: int,
                                     timeout: int = 1800) -> dict:
    """Roda o set ENTREGUE (WFO desligado) no periodo INTEIRO e continuo, em
    tick real -- a mesma coisa que um comprador faz ao carregar o set e
    apertar Start. NENHUMA etapa anterior do circuito testa isso.

    Achado do dono, 2026-08-03: AUDCHF/07_GRID_SEPARATE foi aprovado com 0%
    de divergencia numa janela OOS de ~45 dias (retencao 85.78%) -- e o set
    ENTREGUE, rodado no periodo completo (~3 anos, como um comprador roda),
    estourou margem em 33% do periodo, saldo 500 -> 273.98. A janela curta
    nunca da tempo da cesta do grid (sem SL nativo por posicao, cesta manual
    via ManageGridBasket) crescer o bastante pra quebrar; so o periodo
    completo expoe isso. Monte Carlo nao cobre essa lacuna: e estruturalmente
    isento pra grid/martingale/d'alembert/signal-only (precisa de trades em
    R, esses sistemas usam lote fixo/monetario) -- esta funcao e o gate de
    ruina que faltava para eles.

    Extensao pra martingale/d'alembert/signal-only (dono, 2026-08-08): o
    mesmo buraco existe fora do grid -- nenhum dos tres tem SL nativo
    (martingale/d'alembert dobram/somam lote apos perda; signal-only sai
    so por sinal), entao o mesmo "ficou preso sem margem" ou "estourou no
    periodo completo" pode passar despercebido pela mesma razao: a janela
    WFO (curta, rolante) nunca da tempo da sequencia de perdas crescer o
    bastante pra quebrar. FORMULA_POR_SISTEMA ja guia a BUSCA destes dois
    por ResilienceToDrawdown (drawdown real, via OnTester) -- isso reduz o
    risco mas mede em janelas WFO, nao no periodo continuo; este gate
    continua sendo a unica prova em cima do periodo inteiro de verdade.
    """
    rel = str(caminho_set.relative_to(base.DADOS / "MQL5" / "Profiles" / "Tester"))
    antes = base.marcar_logs()
    with tempfile.TemporaryDirectory() as tmp:
        ini = Path(tmp) / "conf.ini"
        base.escrever_ini(ini, symbol, periodo, rel.replace("/", "\\"),
                          inicio, fim, deposito, 4, 6, "conf_sobrevivencia")
        texto_ini = ini.read_text(encoding="utf-16")
        ini.write_text(texto_ini.replace("Optimization=2", "Optimization=0"),
                       encoding="utf-16")
        lancar_terminal(base.TERMINAL, ini, timeout)
    limite = time.monotonic() + 90
    log = ""
    while time.monotonic() < limite:
        log = base.texto_novo(antes)
        if TESTE_CONCLUIDO.search(log):
            break
        time.sleep(1)

    return avaliar_sobrevivencia(log, deposito)


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
        lancar_terminal(base.TERMINAL, ini, timeout)
    log = base.texto_novo(antes)
    m = re.search(r"local (\d+) tasks", log)
    print(f"    passes executados: {m.group(1) if m else '?'}", flush=True)
    candidatos = sorted(base.DADOS.glob(f"{nome_rel}*"),
                        key=lambda p: (p.suffix.lower() != ".xml", p.name))
    if not candidatos:
        return [], []
    return base.ler_relatorio(candidatos[0])


def arquivar_relatorio(symbol: str, sistema: str, variante: str,
                       nome_origem: str = "conf_wrx",
                       nome_destino: str | None = None) -> str | None:
    """Copia <nome_origem>.* pra fora de DADOS antes do proximo passe
    sobrescrever -- mesmo relatorio que o Monte Carlo (ou o gate de
    sobrevivencia) acabou de ler. Roda pra TODO combo, aprovado ou nao: e
    a base do "certificado de qualidade" (dono, 2026-08-03) e do que
    faltava no dashboard -- "um monte de relatorio, e nao temos nada la".

    `nome_destino` renomeia na copia -- usado pra distinguir o relatorio da
    janela OOS ("conf_wrx" -> fica "conf_wrx") do relatorio do periodo
    completo do gate de sobrevivencia ("conf_sobrevivencia" -> vira
    "sobrevivencia", achado do dono 2026-08-04: sem esse segundo relatorio
    arquivado nao dava pra CONFERIR visualmente o motivo de um veredito de
    sobrevivencia, so confiar no numero final).

    Chave SEM timestamp: uma recorrida do mesmo combo substitui o relatorio
    anterior, mesma convencao do `VALIDADO_*.set` de entrega. Nunca aborta o
    combo -- e um extra pro dashboard, nao faz parte do veredito.
    """
    nome_destino = nome_destino or nome_origem
    pasta_rel = f"{symbol.replace('.', '_')}__{sistema}__{variante}"
    destino = RELATORIOS_DIR / pasta_rel
    try:
        destino.mkdir(parents=True, exist_ok=True)
        copiados = 0
        for sufixo in RELATORIO_SUFIXOS:
            origem_arq = base.DADOS / f"{nome_origem}{sufixo}"
            if origem_arq.exists():
                shutil.copy2(origem_arq, destino / f"{nome_destino}{sufixo}")
                copiados += 1
        return pasta_rel if copiados else None
    except OSError as exc:
        print(f"    AVISO: nao arquivou o relatorio ({exc})", flush=True)
        return None


def emitir_reprovado_cedo(symbol: str, sistema: str, variante: str,
                          motivo: str) -> None:
    """Imprime o JSON final para uma reprovacao decidida ANTES do circuito
    completo (nenhum candidato passou um piso, torneio sem medida, etc.).

    Achado do dono, 2026-08-07: sem isso, `campanha.py` nao acha nenhuma
    linha comecando com '{' na saida e registra a reprovacao como
    "erro: sem JSON final" -- tecnicamente inofensivo (o combo nao repete a
    toa, `aprovado` fica False do mesmo jeito), mas a razao real da
    reprovacao se perde do ledger, e um combo interrompido de verdade fica
    indistinguivel de uma reprovacao limpa. As chaves batem com o JSON
    completo (linha ~1700) pra qualquer leitor do ledger (dashboard,
    resumo) nao precisar de um caminho separado so pra este caso.
    """
    print(json.dumps({"simbolo": symbol, "sistema": sistema,
                      "variante": variante, "lucro_ohlc": None,
                      "lucro_tick_real": None,
                      "lucro_ajustado_custo_nativo": None,
                      "retencao_oos": None, "retencao_pct": None,
                      "sizing_entrega": None, "expectancy_r": None,
                      "trades_oos": None, "trades_is": None,
                      "mc_dd_p95": None, "mc_dd_observado": None,
                      "mc_prob_ruina": None, "mc_aprovado": True,
                      "mc_medido": False, "sobrevivencia_medida": False,
                      "sobrevivencia_saldo_final": None,
                      "sobrevivencia_motivo_reprovacao": None,
                      "sobrevivencia_fechados_fim_teste": None,
                      "sobrevivencia_relatorio_dir": None,
                      "relatorio_dir": None, "parametros": {},
                      "motivo_reprovacao_precoce": motivo},
                     ensure_ascii=False))


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
    ap.add_argument("--to", dest="fim", default=datetime.now().strftime("%Y.%m.%d"))
    ap.add_argument("--deposit", type=int, default=500)
    ap.add_argument("--min-trades", type=int, default=100)
    ap.add_argument("--min-pf", type=float, default=1.2)
    # Opt-in (dono, 2026-08-27): ver piso_trades_da_janela(). Quando passado,
    # SUBSTITUI --min-trades por um piso derivado de --from/--to; --min-pf
    # fica intocado de proposito -- PF e razao, nao contagem, e afrouxar PF
    # numa janela curta so aumenta risco de curve-fit.
    ap.add_argument("--min-trades-per-year", type=float, default=None)
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

    if args.min_trades_per_year is not None:
        piso_antigo = args.min_trades
        args.min_trades = piso_trades_da_janela(args.inicio, args.fim,
                                                args.min_trades_per_year)
        dias = (datetime.strptime(args.fim, "%Y.%m.%d")
                - datetime.strptime(args.inicio, "%Y.%m.%d")).days
        print(f"    --min-trades-per-year={args.min_trades_per_year:g} | janela "
              f"{args.inicio}..{args.fim} ({dias}d) -> piso de {args.min_trades} "
              f"trades (era --min-trades={piso_antigo})", flush=True)

    garantir_terminal_livre(fechar=args.fechar_terminal)

    origem = base.achar_set(args.symbol, args.sistema, args.variante)
    if origem is None:
        print(f"Set nao encontrado: {args.symbol}/{args.sistema}/{args.variante}")
        return 1
    trabalho = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_ETAPA.set"
    rotulo = f"{args.symbol} {args.sistema} {args.variante}"
    print(f"=== {rotulo} | {args.inicio} a {args.fim} ===", flush=True)
    # Marca o inicio ja aqui -- sobrescreve qualquer progresso do combo
    # anterior na hora, em vez de deixar dado velho parado ate a primeira
    # rodada do Estagio 1 terminar (pode ser 45min+ em grid).
    salvar_progresso(args.symbol, args.sistema, args.variante,
                     estagio="iniciando")

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
    duas_etapas = args.sistema in SISTEMAS_RECUPERACAO_DUAS_ETAPAS
    eixos_recuperacao = EIXOS_RECUPERACAO.get(args.sistema, []) if duas_etapas else []
    if duas_etapas:
        # RecoveryMode=0 (Recovery_None) pelos Estagios 1-2: o vencedor de
        # entrada/saida precisa nascer medido em lote fixo puro, sem a
        # recuperacao amplificando (ou escondendo) o sinal. Volta a ligar no
        # Estagio 2.5, depois do vencedor ja travado. Ver constante no topo.
        travados["RecoveryMode"] = "0"
    eixos_fase1 = eixos_da_fase1(origem)
    if eixos_recuperacao:
        eixos_fase1 = [e for e in eixos_fase1 if e not in eixos_recuperacao]
    n = reescrever(origem, trabalho, eixos_fase1, travados)
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
    rodada_inicial = 1
    checkpoint = carregar_checkpoint_estagio1(args.symbol, args.sistema,
                                              args.variante)
    if checkpoint:
        cab, linhas = checkpoint["cab"], checkpoint["linhas"]
        rodada_inicial = checkpoint["rodada_concluida"] + 1
        print(f"    checkpoint do estagio 1 encontrado: retomando da rodada "
              f"{rodada_inicial} ({len(linhas)} linhas ja acumuladas de "
              "corridas anteriores)", flush=True)
    # Grid busca por GridSurvivalScore puro (FORMULA_POR_SISTEMA); limpa o
    # arquivo ANTES do loop, nao a cada rodada, porque `linhas` ACUMULA entre
    # rodadas (append, nao substitui) -- o arquivo de formulas precisa
    # acumular do mesmo jeito pra continuar casando linha a linha. So limpa
    # em inicio de verdade: com checkpoint, o arquivo pode ter formulas de
    # rodadas anteriores (processo antigo) que `linhas` ainda referencia --
    # limpar aqui perderia o casamento por fingerprint dessas linhas.
    if args.sistema in SISTEMAS_GEOMETRIA_TICK_REAL and not checkpoint:
        limpar_todas_formulas()
    for rodada in range(rodada_inicial, 4):
        t0 = time.time()
        cab_r, linhas_r = rodar(trabalho, args.symbol, args.period, args.inicio,
                                args.fim, args.deposit, 1, args.timeout)
        if not linhas_r:
            if not linhas:
                print("    relatorio vazio -- nenhum passe sobreviveu aos filtros")
                emitir_reprovado_cedo(args.symbol, args.sistema, args.variante,
                                      "estagio 1: relatorio vazio, nenhum "
                                      "passe sobreviveu aos filtros")
                limpar_checkpoint_estagio1(args.symbol, args.sistema, args.variante)
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
            # So informativo agora -- pedido do dono, 2026-08-05: "no minimo
            # 3 testes de exploracao inicial". O corte antecipado aqui
            # economizava uma rodada quando a 2a nao melhorava sobre a 1a,
            # mas isso deixava de garantir a exploracao minima pedida; as 3
            # rodadas do range() acima sempre rodam agora, sem early-exit.
            melhorou = (aptos > aptos_ant
                        or melhor > melhor_ant + max(abs(melhor_ant) * 0.05, 1e-9))
            if not melhorou:
                print("    rodada sem melhora (seguindo mesmo assim, "
                      "minimo de 3 rodadas e obrigatorio).", flush=True)
        melhor_ant = max(melhor_ant, melhor)
        aptos_ant = max(aptos_ant, aptos)
        salvar_checkpoint_estagio1(args.symbol, args.sistema, args.variante,
                                   cab, linhas, rodada)
        salvar_progresso(args.symbol, args.sistema, args.variante,
                         estagio="1/5 (regioes)", rodada=f"{rodada}/3",
                         melhor_lucro=melhor, indicadores_aptos=aptos)
        # Ponto seguro pra pausa (dono, 2026-08-09): o checkpoint desta
        # rodada acabou de ser gravado, entao parar AQUI nunca perde
        # trabalho -- retomar rele o mesmo checkpoint e segue da proxima
        # rodada. Nao ha ponto seguro equivalente dentro dos Estagios 2-5
        # (sem checkpoint proprio ainda), entao uma pausa pedida depois
        # deste ponto so vale no fim do combo inteiro -- ver
        # campanha.registrar_ou_pausar().
        if base.pausa_solicitada():
            print("    pausa solicitada -- parando apos esta rodada "
                  "(checkpoint ja salvo, retoma daqui).", flush=True)
            salvar_progresso(args.symbol, args.sistema, args.variante,
                             estagio="pausado")
            return base.CODIGO_PAUSA

    melhores = base.escolher_candidatos(cab, linhas, piso1, 1.0)
    if not melhores:
        print("    nenhum passe passou o piso no estagio 1")
        emitir_reprovado_cedo(args.symbol, args.sistema, args.variante,
                              "estagio 1: nenhum passe passou o piso apos "
                              "as 3 rodadas")
        limpar_checkpoint_estagio1(args.symbol, args.sistema, args.variante)
        return 1
    # NAO limpa o checkpoint aqui (achado do dono, 2026-08-06): as 3 rodadas
    # do Estagio 1 sao a parte cara (pode passar de 2h num grid); o torneio
    # de retencao e os estagios seguintes, logo depois, tambem levam tempo e
    # podem ser interrompidos -- limpar o checkpoint assim que o Estagio 1
    # termina joga fora exatamente o trabalho que ele existe pra proteger se
    # a interrupcao cair um passo depois. So limpa no fim de verdade (sucesso
    # no fim da funcao, ou reprovacao decidida em algum return abaixo).
    relatar_cobertura(cab, linhas, melhores)
    if args.sistema in SISTEMAS_GEOMETRIA_TICK_REAL:
        # Os pisos (trades/PF) ja filtraram; a formula de risco decide QUEM
        # E ELEGIVEL (piso), o lucro decide quem VENCE dentro do topo --
        # "campeao por indicador" abaixo pega o primeiro de cada grupo,
        # entao a ordem aqui decide quem representa cada indicador.
        melhores = priorizar_lucro_no_topo(cab, melhores, campo=campo_da_formula_ativa(args.sistema, origem))

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
    if eixos_recuperacao:
        # Fora do Estagio 2 pelo mesmo motivo do Estagio 1: RecoveryMode
        # ainda esta em "0" aqui, os eixos nao tem efeito nenhum enquanto isso
        # -- reabrem sozinhos no Estagio 2.5, com a entrada/saida ja travada.
        numeros = [e for e in numeros if e not in eixos_recuperacao]
    cortados = [c for c in NUMEROS if c not in numeros]
    n = reescrever(origem, trabalho, numeros, travados)
    print(f"  [2/5] numeros em OHLC ({n} parametros, escrita travada)",
          flush=True)
    if cortados:
        print(f"    fora por nao pertencerem ao {nome_ind}: {cortados}",
              flush=True)
    if args.sistema in SISTEMAS_GEOMETRIA_TICK_REAL:
        limpar_todas_formulas()
    t0 = time.time()
    cab, linhas = rodar(trabalho, args.symbol, args.period, args.inicio,
                        args.fim, args.deposit, 1, args.timeout)
    if not linhas:
        print("    relatorio vazio no estagio 2")
        emitir_reprovado_cedo(args.symbol, args.sistema, args.variante,
                              "estagio 2: relatorio vazio")
        limpar_checkpoint_estagio1(args.symbol, args.sistema, args.variante)
        return 1
    finais = base.escolher_candidatos(cab, linhas, args.min_trades, args.min_pf)
    if args.sistema in SISTEMAS_GEOMETRIA_TICK_REAL:
        # Formula de risco decide o piso de elegibilidade pro torneio de
        # retencao; lucro decide o vencedor dentro do topo elegivel.
        finais = priorizar_lucro_no_topo(cab, finais, campo=campo_da_formula_ativa(args.sistema, origem))
    print(f"    {(time.time()-t0)/60:.0f} min | aptos: {len(finais)} de {len(linhas)} "
          f"(piso: >= {args.min_trades} trades, PF >= {args.min_pf})", flush=True)
    if not finais:
        print("    nenhum candidato passou os pisos.")
        emitir_reprovado_cedo(args.symbol, args.sistema, args.variante,
                              "estagio 2: nenhum candidato passou os pisos "
                              "de trades/profit factor")
        limpar_checkpoint_estagio1(args.symbol, args.sistema, args.variante)
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
        emitir_reprovado_cedo(args.symbol, args.sistema, args.variante,
                              "estagio 2: nenhum finalista do torneio de "
                              "numeros produziu medida de retencao")
        limpar_checkpoint_estagio1(args.symbol, args.sistema, args.variante)
        return 1
    travados.update(ordenados[0][2])
    otimizados.update(ordenados[0][2])

    # ---- Estagio 2.5: CAMADA DE RECUPERACAO (so Martingale/D'Alembert) ------
    # Entrada/saida ja travadas no vencedor medido SEM recuperacao (Estagios
    # 1-2, RecoveryMode="0"). Liga a recuperacao de verdade e busca SO o eixo
    # dela em cima disso -- ver SISTEMAS_RECUPERACAO_DUAS_ETAPAS no topo do
    # arquivo pro raciocinio completo. Falha aqui (relatorio vazio, ninguem
    # passou o piso, ou torneio sem medida) NAO aborta o combo: o sinal base
    # ja foi validado sozinho, entao mantem o valor padrao do eixo no set
    # (RecoveryMode ja fica travado ligado de qualquer jeito) em vez de
    # jogar fora um vencedor de entrada/saida bom por causa so da calibracao
    # da recuperacao.
    if duas_etapas:
        assert eixos_recuperacao  # SISTEMAS_RECUPERACAO_DUAS_ETAPAS <= EIXOS_RECUPERACAO.keys()
        nomes_rec = ", ".join(eixos_recuperacao)
        travados["RecoveryMode"] = RECOVERY_MODE_LIGADO[args.sistema]
        n = reescrever(origem, trabalho, eixos_recuperacao, travados)
        print(f"\n  [2.5/5] camada de recuperacao em OHLC ({n} parametros: "
              f"{nomes_rec}, entrada/saida ja travada no vencedor "
              "sem recuperacao)", flush=True)
        t0 = time.time()
        cab_rec, linhas_rec = rodar(trabalho, args.symbol, args.period,
                                    args.inicio, args.fim, args.deposit, 1,
                                    args.timeout)
        if not linhas_rec:
            print("    relatorio vazio no estagio 2.5; mantendo o valor "
                  f"padrao de {nomes_rec} no set.", flush=True)
        else:
            finais_rec = base.escolher_candidatos(
                cab_rec, linhas_rec, args.min_trades, args.min_pf)
            print(f"    {(time.time()-t0)/60:.0f} min | aptos: "
                  f"{len(finais_rec)} de {len(linhas_rec)}", flush=True)
            if not finais_rec:
                print("    nenhum candidato de recuperacao passou os pisos; "
                      f"mantendo o valor padrao de {nomes_rec} no "
                      "set.", flush=True)
            else:
                ordenados_rec = torneio_retencao(
                    finais_rec[:args.finalistas], cab_rec, metricas, origem,
                    trabalho, travados, args, 1,
                    "camada de recuperacao (OHLC, ~2s cada)")
                if not ordenados_rec:
                    print("    nenhum finalista da recuperacao produziu "
                          f"medida de retencao; mantendo o valor padrao de "
                          f"{nomes_rec} no set.", flush=True)
                else:
                    travados.update(ordenados_rec[0][2])
                    otimizados.update(ordenados_rec[0][2])

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

    # ---- Estagio 3.5: GEOMETRIA DE SAIDA em TICKS REAIS -----------------------
    # Grid, Pyramid e trail puro (ver comentario em SISTEMAS_GEOMETRIA_TICK_REAL).
    # Reabre so os eixos de saida DESTE sistema sobre o resto ja travado
    # (indicador, regiao, filtros) e busca DIRETO em tick real -- pequeno o
    # bastante pra ser viavel, e ataca a causa raiz da divergencia em vez de so
    # medi-la depois de pronta.
    lucro_ohlc_pre_geometria = ordenados[0][1] if ordenados else None
    geometria_refeita_tick_real = False
    if args.sistema in SISTEMAS_GEOMETRIA_TICK_REAL:
        eixos_geometria = EIXOS_GEOMETRIA_TICK_REAL[args.sistema]
        # reescrever() trava (nome in travar) ANTES de checar `otimizar` --
        # esses eixos ja estao em `travados` desde a fase 2 (NUMEROS), entao
        # precisam sair do dict passado aqui pra virarem Y de verdade. Achado
        # ao ver "0 parametros" no primeiro combo real (AUDCAD): a fase nunca
        # rodou, so revalidou o mesmo ponto que a fase 2 ja tinha achado.
        travados_sem_geo = {k: v for k, v in travados.items()
                           if k not in eixos_geometria}
        n = reescrever(origem, trabalho, eixos_geometria,
                      travados_sem_geo)
        print(f"\n  [3.5/5] geometria de saida em TICKS REAIS ({n} parametros: "
              f"{eixos_geometria})", flush=True)
        limpar_todas_formulas()
        t0 = time.time()
        cab_g, linhas_g = rodar(trabalho, args.symbol, args.period,
                                args.inicio, args.fim, args.deposit, 4,
                                args.timeout)
        geo_ok = (base.escolher_candidatos(cab_g, linhas_g, args.min_trades,
                                           args.min_pf) if linhas_g else [])
        geo_ok = (priorizar_lucro_no_topo(cab_g, geo_ok, campo=campo_da_formula_ativa(args.sistema, origem))
                 if geo_ok else geo_ok)
        print(f"    {(time.time()-t0)/60:.1f} min | aptos: {len(geo_ok)} de "
              f"{len(linhas_g)}", flush=True)
        if geo_ok:
            ord_g = torneio_retencao(geo_ok[:args.finalistas], cab_g,
                                     metricas, origem, trabalho, travados,
                                     args, 4, "geometria de saida (tick "
                                     "real, ~35s cada)")
            if ord_g and ord_g[0][0] is not None:
                geometria_refeita_tick_real = True
                print(f"    geometria refeita em tick real: retencao "
                      f"{ordenados[0][0]} -> {ord_g[0][0]}", flush=True)
                travados.update(ord_g[0][2])
                otimizados.update(ord_g[0][2])
                ordenados = ord_g
            else:
                print("    torneio da geometria sem medida; mantida a "
                      "geometria de OHLC.", flush=True)
        else:
            print("    nenhum candidato de geometria passou os pisos; "
                  "mantida a geometria de OHLC.", flush=True)

    # ---- Estagio 4: confirmacao em TICKS REAIS ------------------------------
    print("\n  [4/5] confirmacao em TICKS REAIS", flush=True)
    t0 = time.time()
    # limpar/carregar ao redor do UNICO passe que torneio_retencao([None], ...)
    # roda aqui (ver docstring: candidato None = so mede travados) -- pega o
    # ALL_FORMULAS (Profit/GrossProfit/GrossLoss/EquityDDPercent/Sharpe/
    # EquityDDRelPercent) do MESMO passe IS+OOS combinado que produz `oos`
    # logo abaixo, pro gate relativo (avaliar_gate_relativo()) medir
    # profit_factor/max_dd_pct/sharpe sem rodar passe a mais.
    limpar_todas_formulas()
    conf = torneio_retencao([None], cab, metricas, origem, trabalho, travados,
                            args, 4, "vencedor (tick real)")
    stats_confirmacao = carregar_todas_formulas()
    stats_confirmacao = stats_confirmacao[-1] if stats_confirmacao else None
    if not conf:
        print("    a confirmacao em tick real nao produziu retencao.")
        emitir_reprovado_cedo(args.symbol, args.sistema, args.variante,
                              "estagio 4: a confirmacao em tick real nao "
                              "produziu retencao")
        limpar_checkpoint_estagio1(args.symbol, args.sistema, args.variante)
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

    relatorio_dir = arquivar_relatorio(args.symbol, args.sistema, args.variante)

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
        rotulo_base = ("lucro na busca (tick real):"
                       if geometria_refeita_tick_real else "lucro em OHLC:")
        print(f"\n    {rotulo_base:<21}{lucro_ohlc:>10.2f}")
        print(f"    lucro em tick real:  {lucro_real:>10.2f}")
        print(f"    divergencia:         {div:>9.1f}%")
        if geometria_refeita_tick_real and lucro_ohlc_pre_geometria is not None:
            print(f"    (memo: geometria OHLC prometia {lucro_ohlc_pre_geometria:.2f} "
                  f"na mesma busca -- comparavel ao lucro em tick real acima)")

    # Custo nativo (dono, 2026-08-02): simbolo .HT sai com comissao/swap ZERO
    # por construcao (CustomSymbolCreate nao herda isso do broker -- e config
    # de GRUPO no servidor, nao propriedade de simbolo). So informativo por
    # enquanto -- nao entra no veredito ate decidirmos exigir isso no gate.
    lucro_ajustado = None
    simbolo_nativo = args.symbol.split(".")[0] if "." in args.symbol else None
    custo = custo_nativo.custo_cacheado(simbolo_nativo) if simbolo_nativo else None
    if custo and lucro_real is not None:
        volume = custo_nativo.volume_negociado(base.DADOS / "conf_wrx.htm")
        if volume:
            lucro_ajustado = custo_nativo.ajustar_lucro(lucro_real, volume, custo)
            print(f"    lucro ajustado ao custo nativo de {simbolo_nativo}: "
                  f"{lucro_ajustado:>10.2f} (comissao+swap medidos: "
                  f"{volume * (custo['comissao_por_lote'] + custo['swap_por_lote']):+.2f} "
                  f"em {volume:.2f} lotes)", flush=True)

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

    # Stats do passe combinado (ALL_FORMULAS, capturado antes do Estagio 4
    # acima) -- calculado sempre que r_capavel, independente do veredito ate
    # aqui: entra no registro final pra QUALQUER candidato Fixed-R, aprovado
    # ou nao, pro ledger acumular baseline mesmo de tentativas reprovadas.
    desafiante_stats: dict = {}
    if r_capavel and stats_confirmacao is not None:
        gp = stats_confirmacao.get("gross_profit")
        gl = stats_confirmacao.get("gross_loss")
        pf = gp / abs(gl) if gp is not None and gl not in (None, 0) else None
        dd = stats_confirmacao.get("equity_dd_rel_pct")
        sharpe = stats_confirmacao.get("sharpe")
        trades_conf = stats_confirmacao.get("trades")
        profit_conf = stats_confirmacao.get("profit")
        score = (composite_score(profit_conf, args.deposit, pf, dd, trades_conf)
                 if None not in (pf, dd, trades_conf, profit_conf) else None)
        desafiante_stats = {"profit_factor": pf, "max_dd_pct": dd,
                           "sharpe": sharpe, "composite_score": score,
                           "trades": trades_conf}

    # Gate relativo ao campeao (transplante do should_promote() do Zeus,
    # gate.py: um desafiante so promove se for melhor que quem ja esta
    # IMPLANTADO, nunca so melhor que um piso absoluto). Full port 2026-08-30
    # (v1 era so expectancy_r): profit_factor/max_dd_pct/sharpe saem do MESMO
    # passe combinado que produziu `oos` -- ver avaliar_gate_relativo() pro
    # porque de 5 checks simultaneos em vez de 1 so.
    #
    # O campeao e RE-MEDIDO na MESMA janela do desafiante (remedir_campeao_
    # na_janela), nao lido do ledger estatico -- achado 2026-08-30: sem
    # isso o gate comparava metricas de janelas DIFERENTES, mesmo erro que
    # o Zeus documenta ja ter cometido (ver docstring da funcao).
    if aprovado and r_capavel:
        if stats_confirmacao is None:
            print("    gate relativo ao campeao: sem ALL_FORMULAS deste "
                  "passe (.ex5 antigo sem o FileWrite, ou escrita perdida) "
                  "-- pulando, upgrade opcional nunca dependencia dura.",
                  flush=True)
        else:
            campeao = remedir_campeao_na_janela(
                args.sistema, args.symbol, args.variante,
                args.inicio, args.fim, args.deposit, args.period)
            gate_aprovado, motivos_gate = avaliar_gate_relativo(campeao, desafiante_stats)
            if not motivos_gate:
                print("    gate relativo ao campeao: sem campeao ou sem "
                      "baseline em nenhum eixo -- nada a comparar.", flush=True)
            else:
                for m in motivos_gate:
                    print(f"    gate relativo: {m}", flush=True)
                if not gate_aprovado:
                    aprovado = False

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
                limpar_checkpoint_estagio1(args.symbol, args.sistema, args.variante)
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

    # ---- Gate de sobrevivencia: periodo completo, como o comprador roda de
    # verdade -- achado do dono, 2026-08-03 (grid), estendido 2026-08-08 pra
    # martingale/d'alembert/signal-only (ver docstring da funcao).
    sobrevivencia = None
    sobrevivencia_relatorio_dir = None
    if aprovado and args.sistema in SISTEMAS_GATE_SOBREVIVENCIA:
        print("\n    gate de sobrevivencia: rodando o set ENTREGUE no "
              "periodo completo (continuo, tick real)...", flush=True)
        reescrever(origem, trabalho, [], entrega)
        faltando = conferir_set(trabalho, entrega)
        if faltando:
            print(f"    ABORTADO: o set de entrega saiu incompleto antes do "
                  f"gate de sobrevivencia: {faltando}")
            limpar_checkpoint_estagio1(args.symbol, args.sistema, args.variante)
            return 1
        t0 = time.time()
        sobrevivencia = verificar_sobrevivencia_completa(
            trabalho, args.symbol, args.period, args.inicio, args.fim,
            args.deposit, max(args.timeout, 1800))
        # Arquiva o relatorio do PROPRIO gate (curva de equity do periodo
        # completo, nao so o numero final) -- achado do dono, 2026-08-04:
        # sem isso nao dava pra CONFERIR visualmente um veredito de
        # sobrevivencia, so confiar no saldo final relatado.
        sobrevivencia_relatorio_dir = arquivar_relatorio(
            args.symbol, args.sistema, args.variante,
            nome_origem="conf_sobrevivencia", nome_destino="sobrevivencia")
        print(f"    {(time.time()-t0)/60:.1f} min | saldo final "
              f"{sobrevivencia['saldo_final']}", flush=True)
        if not sobrevivencia["sobreviveu"]:
            aprovado = False
            print(f"    REPROVADO no gate de sobrevivencia: "
                  f"{sobrevivencia['motivo']}.", flush=True)
        else:
            print("    OK: sobreviveu ao periodo completo sem estourar "
                  "margem.", flush=True)

    print("\n    " + ("APROVADO: candidato pronto para a entrega."
                      if aprovado else
                      "REPROVADO: nao promova este candidato."), flush=True)

    # O prefixo carrega o veredito. Um reprovado gravado como "VALIDADO_" entra
    # na biblioteca pelo nome e ninguem reabre o log para descobrir que a
    # retencao era negativa -- o arquivo passa a afirmar o que ele nao provou.
    prefixo = "VALIDADO" if aprovado else "REPROVADO"
    outro_prefixo = "REPROVADO" if aprovado else "VALIDADO"
    destino = (base.DADOS / "MQL5" / "Profiles" / "Tester" /
               f"{prefixo}_{args.symbol.replace('.', '_')}_"
               f"{args.sistema}_{args.variante}.set")
    # Um combo re-testado pode mudar de veredito (aprovado -> reprovado ou o
    # contrario) -- sem apagar o arquivo do prefixo anterior, os dois convivem
    # no disco e o dashboard (_sets_certificados em dashboard_campanha.py, que
    # so faz glob de VALIDADO_*) pode achar o VALIDADO_ antigo e mostrar
    # "certificado" um candidato que acabou de ser reprovado agora (achado do
    # dono, 2026-08-17: EURUSD/07_GRID_SEPARATE/BUY_MULTI reprovado hoje no
    # gate de sobrevivencia, mas o painel ainda mostrava um VALIDADO_ de uma
    # aprovacao anterior do mesmo combo).
    outro_destino = (base.DADOS / "MQL5" / "Profiles" / "Tester" /
                     f"{outro_prefixo}_{args.symbol.replace('.', '_')}_"
                     f"{args.sistema}_{args.variante}.set")
    outro_destino.unlink(missing_ok=True)
    # Arquiva o campeao ATUAL antes de sobrescrever -- so quando `aprovado`
    # (destino e o caminho VALIDADO_, entao ha um campeao de verdade em
    # risco de ser perdido). Ver campeoes_arquivo.py: mesmo principio do
    # deploy.py do Zeus, achado direto na pele hoje com o backup manual do
    # piloto de ML.
    if aprovado:
        campeoes_arquivo.arquivar_campeao_anterior(
            args.sistema, args.symbol, args.variante, destino)
    reescrever(origem, destino, [], entrega)
    faltando = conferir_set(destino, entrega)
    if faltando:
        print(f"\n  ABORTADO: o set de entrega saiu incompleto: {faltando}")
        limpar_checkpoint_estagio1(args.symbol, args.sistema, args.variante)
        return 1

    print(f"\n    set gravado (WFO desligado): {destino.name}")
    print(json.dumps({"simbolo": args.symbol, "sistema": args.sistema,
                      "variante": args.variante, "lucro_ohlc": lucro_ohlc,
                      "lucro_tick_real": lucro_real,
                      "lucro_ajustado_custo_nativo": lucro_ajustado,
                      "retencao_oos": oos["retencao"],
                      "retencao_pct": retencao_pct,
                      "sizing_entrega": sizing_entrega,
                      "expectancy_r": oos["expectancy"],
                      "trades_oos": oos["trades"],
                      "trades_is": oos.get("trades_is"),
                      # Gate relativo completo (2026-08-30, espelha
                      # should_promote()/composite_score() do Zeus): do MESMO
                      # passe combinado IS+OOS acima, nao um passe OOS-puro
                      # dedicado -- ver avaliar_gate_relativo().
                      "profit_factor": desafiante_stats.get("profit_factor"),
                      "max_dd_pct": desafiante_stats.get("max_dd_pct"),
                      "sharpe": desafiante_stats.get("sharpe"),
                      "composite_score": desafiante_stats.get("composite_score"),
                      "mc_dd_p95": mc["mc_dd_p95"] if mc else None,
                      "mc_dd_observado": mc["mc_dd_observado"] if mc else None,
                      "mc_prob_ruina": mc["mc_prob_ruina"] if mc else None,
                      "mc_aprovado": mc_aprovado,
                      # So-informativo, nunca usado no veredito: mc_aprovado
                      # comeca True de proposito (grid/martingale/d'Alembert
                      # sao estruturalmente isentos de MC) -- sem isso o
                      # dashboard nao distingue "MC passou" de "MC nem rodou".
                      "mc_medido": mc is not None and mc.get("mc_dd_p95") is not None,
                      # Gate de sobrevivencia (2026-08-03, estendido
                      # 2026-08-08): so roda pra SISTEMAS_GATE_SOBREVIVENCIA
                      # (grid + martingale + d'alembert + signal-only). None
                      # = nao se aplica a este sistema, nao "passou sem
                      # medir" -- nao confundir com o mesmo problema que
                      # mc_medido resolveu pro MC.
                      "sobrevivencia_medida": sobrevivencia is not None,
                      "sobrevivencia_saldo_final": (
                          sobrevivencia["saldo_final"] if sobrevivencia else None),
                      "sobrevivencia_motivo_reprovacao": (
                          sobrevivencia["motivo"] if sobrevivencia else None),
                      # So-informativo, igual mc_medido acima: quantas
                      # posicoes o MT5 liquidou a forca no CORTE do periodo
                      # (nao a estrategia quebrando -- ver comentario em
                      # avaliar_sobrevivencia). Nao entra no veredito de
                      # sobreviveu/motivo, so fica visivel pra quem avaliar.
                      "sobrevivencia_fechados_fim_teste": (
                          sobrevivencia["fechados_fim_teste"]
                          if sobrevivencia else None),
                      "sobrevivencia_relatorio_dir": sobrevivencia_relatorio_dir,
                      "relatorio_dir": relatorio_dir,
                      "parametros": {**otimizados, **vencedor}},
                     ensure_ascii=False))
    limpar_checkpoint_estagio1(args.symbol, args.sistema, args.variante)
    return 0


if __name__ == "__main__":
    sys.exit(main())
