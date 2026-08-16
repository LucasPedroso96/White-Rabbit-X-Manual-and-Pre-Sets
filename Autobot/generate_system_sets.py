# -*- coding: utf-8 -*-
"""Gera a biblioteca de sets de otimizacao do White Rabbit X por TIPO DE SISTEMA.

Filosofia (definida pelo dono do projeto):
- Um .set por (classe, ativo, SISTEMA, lado). O SISTEMA e o esqueleto de
  gestao: SL/TP, trailing puro, SL+TP+trail, saida por reversao, grid separado,
  grid unificado, martingale, d'alembert, signal-only.
- Cada set otimiza do INICIO AO FIM: indicador de entrada, metodo de entrada,
  timeframe, precos, periodos, ATR, filtros e a geometria de saida do proprio
  sistema. Nada de estagios: o operador desliga na mao (Y->N) o que ja resolveu.
- Passos finos. Acima de 100 milhoes de combinacoes o MT5 chaveia para genetico
  automaticamente, entao densidade alta e desejavel, nao um problema.

Invariantes que o gerador garante (senao o tester devolve
"incorrect input parameters" = INIT_PARAMETERS_INCORRECT no OnInit do EA):
- Fast < Slow em TODA combinacao (Fast maximo < Slow minimo).
- Ichimoku exige Tenkan < Kijun < SenkouB -> vive em sets proprios.
- Percentage/Fixed-R exigem SL: os sistemas sem SL usam Fixed Lot.
- Grid: so Monetary/FixedLot, TP ligado, distancia > 0, lado 0 ou >= 2,
  recovery desligado, conta hedging.
- Martingale: no maximo uma posicao por lado.
- D'Alembert: Fixed Lot, grid desligado, passo > 0.
"""
from __future__ import annotations

import csv
import hashlib
import sys
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import wrx_paths

TERMINAL = wrx_paths.data_dir() / "MQL5"
EA_SOURCE = TERMINAL / "Experts" / "White Rabbit X (Global Multi-Indicator).mq5"
TEMPLATE = TERMINAL / "Profiles" / "Tester" / "exemplo arquivo set.set"
OUTPUT = TERMINAL / "Profiles" / "Tester" / "White_Rabbit_X_Sets_templates"

MAGIC_BASE = 610_000_000
MAGIC_SPAN = 89_999_999   # magics ficam entre 610.000.000 e 699.999.999


def magic_estavel(chave: str, usados: dict[int, str]) -> int:
    """MagicNumber derivado do NOME do set, nao da ordem de geracao.

    Antes vinha de um contador (magic += 1 por arquivo). O efeito colateral so
    aparece quando a biblioteca muda de tamanho: ao remover 178 arquivos de um
    sistema, a identidade de todos os sets seguintes deslocou junto. Como a EA
    reconhece as proprias posicoes pelo magic, um set regenerado deixava de
    enxergar o que ele mesmo tinha aberto.

    Aqui a identidade sai da chave: enquanto o caminho do arquivo nao mudar, o
    numero nao muda -- acrescentar ou remover sistemas nao mexe nos outros.

    Colisao e improvavel (3,7 mil chaves em 90 milhoes de slots) mas nao
    impossivel, e dois sets com o mesmo magic disputariam as mesmas posicoes.
    Quando acontece, anda para o proximo slot livre.
    """
    bruto = hashlib.blake2s(chave.encode("utf-8"), digest_size=8).digest()
    magic = MAGIC_BASE + int.from_bytes(bruto, "big") % MAGIC_SPAN
    while magic in usados and usados[magic] != chave:
        magic = MAGIC_BASE + (magic - MAGIC_BASE + 1) % MAGIC_SPAN
    usados[magic] = chave
    return magic

# ---------------------------------------------------------------- utilidades


def fmt(value: float | int | str) -> str:
    """Formata numero no estilo do .set (sem zeros sobrando, ponto decimal)."""
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer() and abs(value) < 1e15:
        return str(int(value))
    return f"{value:g}"


def steps(start: float, step: float, stop: float) -> int:
    return int(round((stop - start) / step)) + 1


# Criterio de busca POR TIPO DE SISTEMA. Cada esqueleto de saida falha de um
# jeito diferente, e o criterio precisa perguntar o que aquele esqueleto tem
# de provar. Todos passam por AdditionalFilters() no EA, entao o piso de
# qualidade (trades, PF, DD) e o mesmo -- muda so o que e premiado acima dele.
#
# Revisado 2026-08-10 (dono), em duas passadas:
#
# Passada 1 -- fulltest: as atribuicoes antigas (9/8/10 por raciocinio de
# design, nunca comparadas contra alternativa -- so o grid tinha A/B de
# verdade, 2026-08-04) foram trocadas pelo vencedor de lucro bruto de um
# fulltest -- as 14 formulas, nos 11 sistemas, mesmo periodo curto
# (2026.06.10-08.10), SEM WFO (amostra_noite.py, resultados em
# amostra_noite_resultados.jsonl).
#
# Passada 2 -- peso estrutural do profit (dono: "MT5 evolui pelo OnTester",
# entao o que importa nao e so quem ganhou UMA corrida curta, e sim o quanto
# CADA formula pesa profit na propria conta -- isso e o que guia a evolucao
# geracao apos geracao no circuito completo). Cada formula da passada 1 foi
# reclassificada por peso de profit (forte: multiplica direto, sem dividir
# por trades/deposito/stdev; moderado: pesa mas normaliza por deposito ou
# balance; fraco/diluido: divide por trades E deposito antes de qualquer
# peso) cruzado com risco (tem termo de DD/margem, ou e cega a risco). Dois
# vencedores da passada 1 reprovaram nesse crivo e foram corrigidos:
#
#   02_SLTP_ORGANIC: vencedor era ProfitPerTradeAdjustedByDD (7) -- a MESMA
#   formula que ja era o default antigo da EA, ja documentada noutro lugar
#   deste arquivo como a mais diluida do catalogo (divide por trades E por
#   deposito antes de pesar). Ganhou a corrida curta por 1.6% sobre o #2
#   (EfficiencyRelativeToDeposit, 207.41 vs 210.87) -- dentro do ruido de um
#   teste de amostra 1. Trocado pro #2: peso forte/moderado, sem a mesma
#   diluicao.
#
#   09_MARTINGALE: vencedor era Profit puro (2) -- o MESMO padrao que ja
#   quebrou margem quando testado assim pro grid em 2026-08-04 (lucro curto
#   melhor, periodo completo estourou), agora aplicado a outro sistema sem
#   SL nativo e sem teto de lote (MaxMartingaleLot ainda fixo em 0). Os TOP 5
#   da corrida curta pra martingale sao todos formulas cegas a risco (Profit,
#   SystemRobustness, ProfitWinTradeDD...) -- nenhuma delas tem termo de DD.
#   Revertido pra ResilienceToDrawdown (10), a mesma formula que ja guiava
#   martingale antes e que tem DD explicito na conta.
#
# AVISO que continua valendo pros outros 8 (o motivo do teste de 2026-08-04
# existir): isto e lucro bruto, SEM WFO e SEM o gate de sobrevivencia do
# periodo completo -- mede se o dinheiro esta na mesa, nao se perseguir ele
# e seguro. Passaram no crivo de peso/risco desta revisao, mas nenhum tem
# ainda o tipo de validacao que o grid tem (A/B no circuito completo) --
# proximo passo, nao circulo fechado.
#
#  1 GridSurvivalScore    grid: cesta tem dinamica propria (sem SL, alvo
#                         comum) -- unico com A/B real, mantido.
# 10 ResilienceToDrawdown (lucro liquido / DD maximo) * 0,7 + bruto * 0,3 --
#                         peso forte, DD explicito. 01_SLTP, 08_GRID_UNIFIED,
#                         09_MARTINGALE (revertido, ver acima).
#  4 EfficiencyRelativeToDeposit peso moderado-forte, DD-penalty. 02_SLTP_
#                         ORGANIC (trocado, ver acima), 11_SIGNAL_ONLY.
#  5 AdjustedEfficiencyForGrid  peso moderado, DD-penalty. Venceu em
#                         03_TRAIL_ONLY, 04_SLTP_TRAIL, 06_REVERSAL_EXIT e
#                         10_DALEMBERT -- apesar do nome, generalizou bem
#                         fora do grid no teste.
#  6 ProfitRelativeToDDAndDeposit peso moderado, DD no denominador.
#                         05_BE_TRAIL.
#
# Nao usados de proposito: 13 LevainComposite satura (todo passe bom devolve
# 1.0 e o genetico perde gradiente no topo), 11 ReturnUniformity ignora
# tamanho (um sistema minusculo e suave venceria um bom), e agora tambem
# 7 ProfitPerTradeAdjustedByDD e 2 Profit puro -- ver correcoes acima.
FORMULA_POR_SISTEMA = {
    "01_SLTP": 10, "02_SLTP_ORGANIC": 4,
    "03_TRAIL_ONLY": 5, "04_SLTP_TRAIL": 5, "05_BE_TRAIL": 6,
    "06_REVERSAL_EXIT": 5,
    # 2026-08-04: testado Profit puro (2) guiando a busca do grid, com
    # GridSurvivalScore (1) so como filtro externo pos-busca -- comparado
    # ao vivo contra o metodo antigo no MESMO combo (EURUSD/
    # 07_GRID_SEPARATE/BUY_MULTI): GridSurvivalScore-guiado achou lucro
    # OOS 7x maior E sobreviveu ao periodo completo (saldo 3335.25);
    # Profit-guiado achou lucro OOS baixo E estourou margem (saldo 408.68,
    # REPROVADO). Amostra de 1 combo, mas a direcao foi clara -- revertido
    # pro padrao, e confirmado de novo no fulltest de 2026-08-10 (venceu a
    # comparacao com as outras 13 formulas tambem). GridSurvivalScore
    # continua guiando a busca; o filtro externo (ler_todas_formulas em
    # optimize_two_stage.py) segue ligado, so vira redundante/confirmatorio
    # nesse modo em vez de decisivo.
    "07_GRID_SEPARATE": 1, "08_GRID_UNIFIED": 10,
    # 09_MARTINGALE: o fulltest de 2026-08-10 elegeu Profit puro (2), mas
    # revertido pra ResilienceToDrawdown (10) na revisao de peso/risco --
    # ver o bloco de comentario no topo deste dict. Profit puro e
    # exatamente o padrao que ja estourou margem quando testado assim pro
    # grid (2026-08-04); martingale tem o mesmo buraco estrutural (sem SL
    # nativo, MaxMartingaleLot ainda 0/sem teto), entao herda o mesmo risco.
    "09_MARTINGALE": 10, "10_DALEMBERT": 5,
    "11_SIGNAL_ONLY": 4,
}

# Dependente -> chave que o liga, conforme o EA. Espelha os GATES do circuito
# (optimize_two_stage.py); mexeu aqui, mexa la. Trailing: `AtivarTrailATR`
# governa MetodoDeCalculo ("Trailing Price Source"), TrailVela e Trail.
GATES_DEPENDENCIAS = {
    "MetodoDeCalculo": "AtivarTrailATR",
    "TrailVela": "AtivarTrailATR",
    "Trail": "AtivarTrailATR",
    "VelaTake": "AtivarTake",
    "VelaStop": "AtivarStop",
    "BreakevenDistancia": "AtivarBreakeven",
    "MTF_RequererAmbos": "AtivarFiltroMTF",
    "MA_TimeFrame": "AtivarFiltroMA",
    "MA_Period": "AtivarFiltroMA",
    "MA_Method": "AtivarFiltroMA",
    "MetodoMA": "AtivarFiltroMA",
    "SentidoMA": "AtivarFiltroMA",
    "MA_AppliedPrice": "AtivarFiltroMA",
    "MA_SlopeLookback": "AtivarFiltroMA",
    "ADX_TimeFrame": "AtivarFiltroADX",
    "ADX_Period": "AtivarFiltroADX",
    "ADX_Limiar": "AtivarFiltroADX",
    "MetodoADX": "AtivarFiltroADX",
    "VolatilityFilter": "EntradaATR",
    "NewsMinutosAntes": "AtivarFiltroNoticias",
    "NewsMinutosDepois": "AtivarFiltroNoticias",
}


@dataclass
class Profile:
    """Mapa nome->tupla do .set, com contagem de combinacoes."""

    values: dict[str, str] = field(default_factory=dict)

    def fix(self, name: str, value) -> None:
        v = fmt(value)
        step = "0" if v in ("true", "false") else "1"
        self.values[name] = f"{v}||{v}||{step}||{v}||N"

    def raw(self, name: str, value: str) -> None:
        self.values[name] = value

    def opt(self, name: str, current, start, step, stop,
            ativo: bool = True) -> None:
        """Eixo de otimizacao. Com ativo=False grava a FAIXA mas deixa em N.

        Serve aos parametros que pertencem a uma fase seguinte: o operador so
        troca o N por Y e ja tem inicio, passo e fim calibrados, em vez de ter
        de inventar a faixa na hora. Guardar a faixa desligada e melhor do que
        fixar um valor unico, que apagaria a calibracao por classe de ativo.
        """
        self.values[name] = (f"{fmt(current)}||{fmt(start)}||{fmt(step)}||"
                             f"{fmt(stop)}||{'Y' if ativo else 'N'}")

    def opt_bool(self, name: str, current: str = "false",
                 ativo: bool = True) -> None:
        """Eixo booleano. Mesmo contrato de `opt`: ativo=False grava e deixa N."""
        self.values[name] = f"{current}||false||0||true||{'Y' if ativo else 'N'}"

    def desativar_inertes(self) -> list[str]:
        """Rebaixa para N todo eixo Y atras de chave efetivamente cravada em
        false NESTE sistema.

        O esqueleto de cada sistema crava chaves (trailing off no 01_SLTP, TP
        off no 03_TRAIL_ONLY, SL off no grid...), e um eixo dependente aberto
        atras de chave morta nao e so desperdicio, e diluicao: TrailVela(4) x
        MetodoDeCalculo(5) num sistema sem trailing faz o genetico avaliar 20
        copias identicas de cada combinacao real. Este passe roda no fim da
        montagem, entao vale para qualquer combinacao de blocos -- em vez de
        depender de cada bloco lembrar o que o outro cravou.

        Chave "efetivamente cravada" = fixa OU marcada N (o otimizador nao vai
        move-la desta fase); chave em Y e viva, e seus dependentes importam no
        ramo true.
        """
        rebaixados = []
        for nome, flag in GATES_DEPENDENCIAS.items():
            alvo = self.values.get(nome)
            chave = self.values.get(flag)
            if not alvo or not chave:
                continue
            c = chave.split("||")
            viva = len(c) == 5 and c[4] == "Y"
            if viva or c[0].strip().lower() != "false":
                continue
            a = alvo.split("||")
            if len(a) == 5 and a[4] == "Y":
                self.values[nome] = "||".join(a[:4] + ["N"])
                rebaixados.append(nome)
        return rebaixados

    def passes(self) -> int:
        total = 1
        for value in self.values.values():
            parts = value.split("||")
            if len(parts) != 5 or parts[4] != "Y":
                continue
            if parts[1] in ("true", "false"):
                total *= 1 if parts[1] == parts[3] else 2
                continue
            total *= steps(float(parts[1]), float(parts[2]), float(parts[3]))
        return total

    def flags(self) -> list[str]:
        return [n for n, v in self.values.items()
                if v.split("||")[-1] == "Y"]


@dataclass(frozen=True)
class AssetClass:
    code: str
    timeframe: int          # ENUM_ALLOWED_TIMEFRAMES: 0=M1 .. 7=W1
    tf_lo: int
    tf_hi: int
    sl_lo: float
    sl_hi: float
    tp_hi: float
    slippage: int
    weekend: bool
    news: str
    capital_base: float   # capital sobre o qual 1R e calculado (Fixed-R)


CLASSES = {
    "01_Forex": AssetClass("01_Forex", 2, 1, 5, 1.0, 6.0, 9.0, 5, False, "", 1000),
    "02_Cryptocurrencies": AssetClass("02_Cryptocurrencies", 4, 2, 6, 2.0, 9.0, 14.0, 20, True, "USD", 2500),
    "03_Indices_Energies": AssetClass("03_Indices_Energies", 3, 1, 5, 1.5, 8.0, 12.0, 15, False, "USD,EUR,JPY", 2500),
    "04_US_Stocks_CFD": AssetClass("04_US_Stocks_CFD", 4, 2, 6, 1.5, 8.0, 12.0, 10, False, "USD", 5000),
    "05_Metals": AssetClass("05_Metals", 2, 1, 5, 1.5, 7.0, 10.0, 10, False, "USD,EUR", 10000),
}

ASSETS: dict[str, list[str]] = {
    "01_Forex": [
        "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY",
        "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD",
        "EURUSD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD",
        "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"],
    "02_Cryptocurrencies": ["ADAUSD", "BTCUSD", "DOGEUSD", "ETHUSD", "SOLUSD", "XRPUSD"],
    "03_Indices_Energies": ["BRENT", "WTI"],
    "04_US_Stocks_CFD": [
        "AAPL", "ADBE", "AMZN", "BA", "BAC", "BRK.B", "C", "CAT", "CMCSA",
        "CSCO", "CVX", "DAL", "DIS", "EA", "EBAY", "FOXA", "GE", "GM", "GOOGL",
        "GS", "HPE", "IBM", "INTC", "JNJ", "JPM", "KO", "LLY", "MCD", "META",
        "MMM", "MSFT", "NEM", "NFLX", "NKE", "NVDA", "ORCL", "PEP", "PFE",
        "PG", "PM", "PRU", "PYPL", "SBUX", "TSLA", "UPS", "V", "VZ", "WFC",
        "WMT", "XOM"],
    "05_Metals": ["XAGUSD", "XAUEUR", "XAUUSD"],
}

# --------------------------------------------------------------- nucleo comum


def apply_core(p: Profile, ac: AssetClass, ichimoku: bool,
               grid: bool = False) -> None:
    """Entrada + filtros: identico em todos os sistemas (exceto ATR de entrada,
    que so existe em grid -- ver bloco do EntradaATR)."""
    if ichimoku:
        # Tenkan < Kijun < SenkouB e exigido pelo OnInit em toda combinacao.
        p.fix("EntryIndicator", 11)
        p.opt("Fast_EMA", 9, 6, 4, 14)
        p.opt("Slow_EMA", 26, 18, 4, 34)
        # Senkou B agora TEM efeito (a nuvem passou a ser lida), mas somar um
        # terceiro eixo aos dois modos novos triplicaria o espaco de saida.
        # Fica no valor classico; ligue depois de escolher o modo.
        p.fix("MACD_SMA", 52)
        # As duas decisoes que definem como o Ichimoku opera, e que ate agora
        # nao existiam: referencia pela nuvem ou pelo Kijun, e confirmacao do
        # Chikou.
        p.opt_bool("IchimokuUseKumo", "true")
        p.opt_bool("IchimokuChikouFilter")
    else:
        # MACD/EMA/Momentum/Stochastic/TRIX/RSI compartilham a mesma geometria
        # de periodos. Fast maximo (18) < Slow minimo (21) mantem fast<slow em
        # todo passe, inclusive com o filtro MTF ligado, que tambem exige.
        p.opt("EntryIndicator", 0, 0, 1, 10)
        p.opt("Fast_EMA", 12, 6, 3, 18)   # periodo principal: TODOS usam
        # PERIODOS QUE SO ALGUNS INDICADORES USAM ficam em N na fase 1 e sao
        # abertos na fase 2 pelo circuito, SE o indicador vencedor os usar --
        # verificado na criacao dos handles do EA (linhas ~1234-1290):
        #   EntrySlowPeriod   -> MACD, EMA_Cross, OsMA (e Kijun no Ichimoku)
        #   EntrySignalPeriod -> MACD, Stochastic (%D), OsMA, Ichimoku
        # Num set MULTI o indicador varia de 0 a 10; deixa-los abertos aqui faz
        # o genetico avaliar 5x (slow) e 5x (signal) COPIAS IDENTICAS para cada
        # um dos 8 indicadores que os ignoram -- passe queimado a toa.
        # Com Slow cravado em 27 e Fast indo ate 18, fast<slow vale sempre,
        # inclusive com o filtro MTF ligado (exigencia do OnInit).
        p.opt("Slow_EMA", 27, 21, 6, 45)
        p.opt("MACD_SMA", 9, 3, 3, 15)
        p.fix("IchimokuUseKumo", "true")
        p.fix("IchimokuChikouFilter", "false")
        # Mesmo motivo: os tres do Stochastic so tem efeito com EntryIndicator
        # = Stochastic (1 de 11). Abertos, multiplicariam a fase 1 por 32 para
        # servir a um unico ramo.
        p.opt("StochasticPriceField", 0, 0, 1, 1)

    # FASE 1 = DESCOBERTA DE REGIOES (pedido do dono, 2026-07-31): o grupo de
    # Entradas entra COMPLETO ja na primeira busca -- applied price, Stochastic
    # inteiro, ATR e as saidas do sistema. "Estamos descobrindo regioes nesse
    # primeiro setor"; as fases seguintes vao TIRANDO os inputs de escrita
    # (enums, bools) e deixando so os numericos para refinar.
    #
    # Nota sobre o InpAppliedPrice: o anti-repaint nao vem dele -- os sinais
    # leem os indices [1] e [2], sempre barra FECHADA, entao todo applied price
    # ja esta congelado quando o sinal nasce. O rompimento de EMA_Cross e
    # Ichimoku continua medido no close (`Close[1] > MACD_Signal[1]`), o que e
    # variante deliberada, nao incoerencia.
    p.opt("InpAppliedPrice", 1, 1, 1, 7)

    p.opt("EntryMethod", 1, 0, 1, 6)
    p.opt("TimeFrame", ac.timeframe, ac.tf_lo, 1, ac.tf_hi)

    p.opt("StochasticSlowing", 3, 1, 2, 7)
    p.opt("StochasticMethod", 0, 0, 1, 3)   # MODE_SMA..LWMA
    if ichimoku:
        p.fix("StochasticPriceField", 0)  # STO_LOWHIGH

    # ATR alimenta stop, alvo e trailing. Prende-lo ao timeframe da classe de
    # ativo assume que a volatilidade de referencia mora no mesmo prazo da
    # entrada, o que e palpite, nao medida -- por isso tambem e eixo da fase 1.
    p.opt("ATR_TimeFrame", ac.timeframe, max(0, ac.tf_lo - 1), 1, ac.tf_hi)
    p.opt("PeriodoATR", 14, 7, 7, 28)

    # Filtros em FUNIL (pedido do dono, 2026-07-31): a FLAG de cada filtro e
    # OPCIONAL desde a primeira etapa -- eixo true/false, o genetico decide SE
    # o filtro existe junto com o sinal. O ajuste do filtro (periodo, metodo,
    # applied price...) fica gravado em N para as etapas seguintes, que so o
    # abrem se a flag sobreviveu -- e assim que os passos DIMINUEM etapa a
    # etapa, em vez de a primeira busca pagar por dezenas de copias identicas
    # de cada combinacao com filtro desligado (818 de 3.435 resultados ja
    # vieram duplicados por eixo atras de chave morta, medido).
    p.opt_bool("AtivarFiltroMTF")
    p.opt_bool("MTF_RequererAmbos", "false")
    p.opt_bool("AtivarFiltroMA")
    p.opt("MA_TimeFrame", ac.timeframe, ac.tf_lo, 1, ac.tf_hi)
    p.opt("MA_Period", 200, 100, 100, 300)
    p.opt("MA_Method", 1, 0, 1, 3)          # SMA..LWMA
    p.opt("MetodoMA", 2, 0, 1, 3)
    p.opt("SentidoMA", 0, 0, 1, 1)          # tendencia / reversao
    p.opt("MA_AppliedPrice", 1, 1, 1, 7)
    p.opt("MA_SlopeLookback", 3, 1, 1, 5)
    p.opt_bool("AtivarFiltroADX")
    p.opt("ADX_TimeFrame", ac.timeframe, ac.tf_lo, 1, ac.tf_hi)
    p.opt("ADX_Period", 14, 7, 7, 28)
    p.opt("ADX_Limiar", 25, 15, 5, 30)
    p.opt("MetodoADX", 0, 0, 1, 1)          # forca / forca+DI
    # "ATR entrada e somente para Grid" (dono, 2026-07-31): o filtro de
    # volatilidade por ATR (`(!EntradaATR || CheckBuyVolatility())`) so e eixo
    # nos sistemas de grid, onde a cadencia das entradas governa a cesta; nos
    # demais fica cravado em false. O ATR como referencia de DISTANCIA da
    # cesta e outro parametro (UsarsomenteATRGRID), tambem exclusivo do grid.
    if grid:
        p.opt_bool("EntradaATR")
        p.opt("VolatilityFilter", 1, 0, 1, 1)   # baixa / alta
    else:
        p.fix("EntradaATR", "false")
        p.fix("VolatilityFilter", 1)

    # Noticias exigem CSV em Common\Files: fica desligado por padrao. Sub-flag
    # bate com o default da propria EA (false) -- com o filtro mestre desligado
    # ela e inerte (CheckNewsFilter retorna cedo), mas nao ha motivo pra deixar
    # gravado um valor que ninguem escolheu deliberadamente (dono, 2026-07-31).
    p.fix("AtivarFiltroNoticias", "false")
    p.fix("NewsSomenteAltoImpacto", "false")
    p.fix("NewsMinutosAntes", 15)
    p.fix("NewsMinutosDepois", 15)
    p.raw("NewsMoedasManual", ac.news)
    p.raw("NewsCSVFile", "WhiteRabbit_News.csv")


def apply_defaults(p: Profile, ac: AssetClass, side: str, magic: int,
                   name: str) -> None:
    """Tudo que nao pertence a estrategia: fixo e neutro."""
    p.raw("NomedaEstrategia", name)
    for blank in BLANKS:
        p.raw(blank, "")

    # Sizing: definido por sistema em apply_sizing(). O default aqui e Fixed Lot,
    # que e o unico compativel com grid / d-alembert / sem-SL.
    p.fix("TradeCapitalPercentage", 100)
    p.fix("PositionSizeMode", 2)
    p.fix("PositionSizeValue", 0.01)
    p.fix("CapitalBaseR", 0)
    p.fix("MaxRiscoTradeR", 0)
    p.fix("DailyLossLimitPercent", 0)
    p.fix("MaxEquityDrawdownPercent", 0)
    p.fix("MinFreeMarginPercent", 0)

    # Global Risk Protection (dono, 2026-08-14): soma a conta INTEIRA (todo
    # simbolo, todo magic number) -- e uma trava de nivel de conta/prop firm,
    # nao faz sentido por combo de otimizacao/backtest isolado. Desligado de
    # proposito (0 = desativado), nunca otimizavel: e pra uso manual/ao vivo,
    # nao pra a busca genetica mexer.
    p.fix("Trava_Diaria_Percent", 0)
    p.fix("Trava_Total_Percent", 0)
    p.fix("Protecao_Fecha_Posicoes", "true")

    p.fix("ReversalExitUseEntryFilters", "false")
    p.fix("RecoveryMode", 0)
    p.fix("Multiplicador", 1)
    p.fix("MaxMartingaleSteps", 0)
    p.fix("MaxMartingaleLot", 0)
    p.fix("DAlembertStep", 0.01)
    p.fix("GridMode", 0)
    p.fix("UsarsomenteATRGRID", "false")
    p.fix("DistanciaMinima", 2)

    # FILTROS DE EXECUCAO (hora, dia, spread): faixas gravadas em N -- sao os
    # ULTIMOS a rodar no circuito (dono, 2026-07-31), em IS+OOS. O EA aceita
    # janela invertida (From>To = sessao noturna) e from==to = 24h, entao toda
    # combinacao 0..23 e valida (inTimeInterval + guarda do OnInit).
    p.opt_bool("Fecharordensforadohorario", "false", ativo=False)
    p.opt("TOD_From_Hour", 0, 0, 1, 23, ativo=False)
    p.fix("TOD_From_Min", 0)
    p.opt("TOD_To_Hour", 23, 0, 1, 23, ativo=False)
    p.fix("TOD_To_Min", 55)
    for day in ("TradeMonday", "TradeTuesday", "TradeWednesday",
                "TradeThursday", "TradeFriday"):
        p.opt_bool(day, "true", ativo=False)
    weekend = "true" if ac.weekend else "false"
    if ac.weekend:
        # So o mercado 24/7 tem fim de semana para filtrar.
        p.opt_bool("TradeSaturday", weekend, ativo=False)
        p.opt_bool("TradeSunday", weekend, ativo=False)
    else:
        p.fix("TradeSaturday", weekend)
        p.fix("TradeSunday", weekend)

    # MaxSpread em pontos, ancorado no custo tipico da classe (slippage e a
    # referencia de grandeza que ja temos por classe). 0 = sem filtro, sempre
    # dentro do espaco -- o corte so vence se PAGAR em retencao.
    p.opt("MaxSpread", 0, 0, ac.slippage, ac.slippage * 10, ativo=False)
    p.fix("MaxSlippage", ac.slippage)
    p.fix("MagicNumber", magic)
    p.fix("ModificationSafetyPoints", 0)
    # English fixo nos sets de trabalho: com Auto (0), GetInterfaceLanguage()
    # detecta o idioma do terminal (TerminalInfoString(TERMINAL_LANGUAGE)) e
    # aqui isso vira Portugues -- o set de entrega volta para Auto (0) em
    # optimize_two_stage.py, entao cada comprador ve o proprio idioma dele.
    p.fix("InterfaceLanguage", 1)

    # Painel LIGADO: em otimizacao o EA nao desenha nada de qualquer forma --
    # CanRenderChartInterface() ja retorna false quando MQL_VISUAL_MODE e 0.
    # Desligar aqui so tirava o painel do backtest visual, que e onde se olha.
    p.fix("EnableChartDashboard", "true")
    p.fix("PlotIndicatorsOnChart", "true")
    p.fix("DashboardCorner", 0)
    p.fix("DashboardOffsetX", 12)
    p.fix("DashboardOffsetY", 24)
    p.fix("ShowClosedDealLabels", "true")
    p.fix("MaxVisibleDealLabels", 120)
    p.fix("ClosedDealLabelFontSize", 10)
    p.fix("ApplyEmbeddedChartTheme", "true")
    p.fix("ChartTheme", 0)          # Theme_Dark -- default do EA
    p.fix("DASH_C_DEAL_BG", 3328)   # C'0,13,0' em BGR (R+G*256+B*65536)
    p.fix("DASH_C_PANEL_BG", 0)     # clrBlack
    p.fix("DashboardPanelOpacityPct", 100)

    # Walk-forward LIGADO por padrao, em In-Sample (dono, 2026-07-31: "todos
    # sets tao com wfo desligados no insample! isso e errado!"). O template e
    # ferramenta de OTIMIZACAO: com WFO off, qualquer genetico manual enxerga
    # o periodo inteiro e a retencao nao prova nada. Em modo In-Sample (0) o
    # algoritmo so ve as janelas IS -- e o modo de otimizar; validar e trocar
    # MetodoDeEntradawfo para 1 (IS+OOS).
    #
    # ⚠ input_end_date precisa BATER com o fim do teste (tolerancia 80h),
    # senao o OnTester devolve 0 em todo passe, em silencio. Cravar uma data
    # literal aqui e o mesmo erro que o "From" do dashboard tinha (2026-08-06,
    # ~3 anos de defasagem) -- calculado sempre relativo a hoje, igual
    # hojeMT5()/anosAtrasMT5() em app.js, entao toda regeneracao da biblioteca
    # (mesmo dias/semanas depois) sai com a data certa sem ninguem lembrar de
    # atualizar na mao. Regenerar sem rodar de novo e ficar defasado de novo;
    # se so quer atualizar a data sem reconstruir tudo, configure_wfo.py
    # (tambem calculado por padrao) e mais barato.
    # Em Custom, passo NEGATIVO = dias fixos; positivo = % do In-Sample.
    # (O set de ENTREGA continua saindo com WFO desligado -- andaime de
    # validacao nao vai para o comprador; ver optimize_two_stage.py.)
    p.fix("AtivarWFO", "true")
    p.fix("MetodoDeEntradawfo", 0)
    p.raw("input_end_date", datetime.now().strftime("%Y.%m.%d"))
    p.fix("wfo_windowSize", -1)              # Custom
    p.fix("wfo_customWindowSizeDays", 122)   # In-Sample: 122 dias
    p.fix("wfo_stepSize", -1)                # Custom
    p.fix("wfo_customStepSizePercent", -61)  # Out-of-Sample: 61 dias
    p.fix("selectedFormula", 13)  # Levain Composite Score

    set_exposure(p, side, 1, hedging=False)


def set_exposure(p: Profile, side: str, per_side: int, hedging: bool) -> None:
    """Lado "BOTH" abre compra E venda ao mesmo tempo.

    So faz sentido em sistema cuja gestao atravessa os dois lados -- hoje, a
    cesta unificada. Exige conta hedging: em netting os dois lados se anulam.
    """
    p.fix("MaxLongTrades", per_side if side in ("BUY", "BOTH") else 0)
    p.fix("MaxShortTrades", per_side if side in ("SELL", "BOTH") else 0)
    if side == "BOTH":
        # Compra e venda ao mesmo tempo: permitir ou nao posicoes opostas
        # simultaneas e decisao de ESTRATEGIA, nao de infraestrutura (dono,
        # 2026-07-31: "sistemas buy e sell juntos obrigatorio otimizar o
        # hedge"). Com Hedging=false a EA nao mantem os dois lados abertos e a
        # cesta unificada opera outra dinamica -- e um regime diferente, que o
        # genetico deve poder escolher.
        # O OnInit so rejeita Hedging=true em conta NETTING; o terminal de
        # teste e hedging, entao os dois ramos rodam.
        p.opt_bool("Hedging", "true" if hedging else "false")
    else:
        p.fix("Hedging", "true" if hedging else "false")


# --------------------------------------------------------------- os sistemas

@dataclass(frozen=True)
class System:
    code: str
    label: str
    status: str
    notes: str


SYSTEMS: list[System] = [
    System("01_SLTP", "Stop Loss + Take Profit ATR", "RESEARCH",
           "Saida classica: SL e TP como multiplos de ATR, breakeven opcional."),
    System("02_SLTP_ORGANIC", "Stop Loss + Take Profit organico", "RESEARCH",
           "TP organico ancorado no ultimo trade + multiplo de ATR."),
    System("03_TRAIL_ONLY", "Trailing puro (trend follow)", "RESEARCH",
           "Sem TP: a posicao morre no trailing. Captura tendencia longa."),
    System("04_SLTP_TRAIL", "SL + TP + Trailing", "RESEARCH",
           "TP fixo com trailing atras: trava lucro antes do alvo."),
    System("05_BE_TRAIL", "Breakeven + Trailing", "RESEARCH",
           "Breakeven cedo e trailing depois; sem TP fixo."),
    System("06_REVERSAL_EXIT", "Saida por sinal contrario", "RESEARCH",
           "A posicao fecha quando o indicador vira. SL como rede de seguranca."),
    System("07_GRID_SEPARATE", "Grid com lucro separado por lado", "HEDGE_ACCOUNT_REQUIRED",
           "Cada lado tem alvo proprio. Exige conta hedging real."),
    System("08_GRID_UNIFIED", "Grid com cesta unificada", "HEDGE_ACCOUNT_REQUIRED",
           "Compra e venda abertas juntas sob UM alvo unico. Conta hedging "
           "obrigatoria: em netting os lados se anulam."),
    System("09_MARTINGALE", "Martingale em lote fixo", "HIGH_RISK",
           "Uma posicao por lado; lote cresce apos perda. Curva de risco severa."),
    System("10_DALEMBERT", "D'Alembert em lote fixo", "HIGH_RISK",
           "Incremento aritmetico de lote apos perda; menos agressivo."),
    System("11_SIGNAL_ONLY", "Signal only (sem SL/TP)", "HIGH_RISK_RESEARCH",
           "Cobertura negativa: mede o sinal cru, sem rede de protecao."),
]

# Sistemas cuja gestao atravessa compra e venda, entao o set liga os dois lados
# num arquivo unico ("BOTH") em vez de um por lado. So a cesta unificada se
# encaixa: o alvo dela e a soma dos dois lados. Um lado so a tornaria identica
# ao 07_GRID_SEPARATE.
BILATERAL = {"08_GRID_UNIFIED"}


def apply_sizing_and_formula(p: Profile, system: str, ac: AssetClass) -> None:
    """Escolhe o modo de sizing e o criterio de otimizacao de cada sistema.

    R (multiplo de risco) so existe no EA quando PositionSizeMode e Fixed-R (3)
    ou Percentage (0): ComputeRMetrics devolve false em qualquer outro modo, e
    a formula SomaR viraria 0 em todo passe. Fixed-R tambem exige Stop Loss
    ativo, e o EA proibe combina-lo com grid e com D'Alembert.

    Onde da para usar Fixed-R, usamos: 1R = 1% do capital base, o que torna o
    resultado comparavel entre ativos e sistemas e faz o OnTester imprimir as
    metricas em R (Total R, R medio/expectancia, payoff, DD em R) em cada passe.
    O criterio de OTIMIZACAO continua sendo o Levain Composite Score, que pesa
    PF, lucro por trade ajustado por DD, Sharpe e recovery factor -- SomaR
    sozinho maximiza edge bruto e ignora drawdown.
    """
    r_capable = system in ("01_SLTP", "02_SLTP_ORGANIC", "03_TRAIL_ONLY",
                           "04_SLTP_TRAIL", "05_BE_TRAIL", "06_REVERSAL_EXIT")
    if r_capable:
        p.fix("PositionSizeMode", 3)     # Fixed-R
        p.fix("PositionSizeValue", 1.0)  # 1R = 1% do capital base
        # Capital base FIXO por classe, medido no broker: e o menor valor em
        # que o lote minimo ainda cabe em 1% de risco com stop de 3x ATR.
        # Com zero aqui, o EA usaria o saldo do OnInit e a otimizacao passaria
        # a depender de quanto havia na conta naquele dia -- o mesmo set daria
        # resultados diferentes em contas diferentes.
        p.fix("CapitalBaseR", ac.capital_base)
        p.fix("MaxRiscoTradeR", 0)       # sem teto artificial na pesquisa
    else:
        p.fix("PositionSizeMode", 2)     # Fixed Lot
        p.fix("PositionSizeValue", 0.01)

    # CRITERIO DA FASE 1: Pessimistic Average Profit (9).
    #
    # A fase 1 responde uma pergunta so: este sinal tem vantagem, ou os ganhos
    # vieram de poucas operacoes felizes? O Pessimistic Profit e feito para
    # isso -- desconta a dependencia de ganhos extremos, entao a sorte
    # concentrada nao sobe no ranking.
    #
    # O Levain Composite (13) saiu daqui e continua util como PORTAO de
    # qualidade, mas nao serve para ordenar: os quatro componentes tem teto e os
    # pesos somam 1, entao todo passe que atinge os benchmarks devolve
    # exatamente 1.0 e o genetico perde o gradiente no topo -- justamente onde o
    # campeao e escolhido. Medido: 6 passes empatados em 1.0, e passes com lucro
    # 42 ficando abaixo de passes com lucro 23.
    #
    # As fases seguintes pedem criterios diferentes, e usar o mesmo nas quatro
    # atrapalha: filtro REDUZ numero de trades, entao otimizar a fase 2 por
    # lucro total pune o filtro que corta operacao ruim. Ver configure_wfo.py
    # --fase, que troca criterio e modo de uma vez.
    p.fix("selectedFormula", FORMULA_POR_SISTEMA[system])


def apply_system(p: Profile, system: str, ac: AssetClass, side: str) -> None:
    """Aplica o esqueleto de gestao e otimiza a geometria de saida dele."""
    sl_mid = round((ac.sl_lo + ac.sl_hi) / 2, 2)

    if system == "01_SLTP":
        p.fix("AtivarStop", "true")
        p.fix("AtivarTake", "true")
        p.fix("TakeOrganico", "false")
        p.fix("AtivarTrailATR", "false")
        p.fix("ReversalExitMode", 0)
        p.opt("VelaStop", 0, 0, 1, 3)
        p.opt("Stop", sl_mid, ac.sl_lo, 0.5, ac.sl_hi)
        p.opt("VelaTake", 0, 0, 1, 3)
        p.opt("Take", sl_mid, ac.sl_lo, 0.5, ac.tp_hi)
        p.opt_bool("AtivarBreakeven", "true")
        # Teto descido de 3.0 para 0.7 (achado do dono, 2026-08-16): o gatilho
        # do breakeven e Stop*BreakevenDistancia (nao Take), entao nada aqui impede
        # ele de cair ALEM do Take -- so reduz a chance. Sistema com Take real
        # (este bloco): teto baixo o suficiente pra, no caso tipico (Stop~Take, os
        # dois nascem do mesmo sl_mid), o gatilho ficar bem antes do alvo em vez
        # de emparelhar com ele. Nao mexido em 05_BE_TRAIL/06_REVERSAL_EXIT: nenhum
        # dos dois tem Take ativo, entao nao ha TP pra correr contra.
        p.opt("BreakevenDistancia", 0.35, 0.2, 0.15, 0.7)
        p.opt("MetodoDeCalculo", 1, 0, 1, 4)
        p.opt("TrailVela", 0, 0, 1, 3)
        p.fix("Trail", sl_mid)

    elif system == "02_SLTP_ORGANIC":
        p.fix("AtivarStop", "true")
        p.fix("AtivarTake", "true")
        p.fix("TakeOrganico", "true")
        p.fix("AtivarTrailATR", "false")
        p.fix("ReversalExitMode", 0)
        p.opt("VelaStop", 0, 0, 1, 3)
        p.opt("Stop", sl_mid, ac.sl_lo, 0.5, ac.sl_hi)
        p.opt("VelaTake", 0, 0, 1, 3)
        p.opt("Take", sl_mid, ac.sl_lo, 0.5, ac.tp_hi)
        p.opt_bool("AtivarBreakeven", "true")
        # Teto descido de 3.0 para 0.7 (achado do dono, 2026-08-16): o gatilho
        # do breakeven e Stop*BreakevenDistancia (nao Take), entao nada aqui impede
        # ele de cair ALEM do Take -- so reduz a chance. Sistema com Take real
        # (este bloco): teto baixo o suficiente pra, no caso tipico (Stop~Take, os
        # dois nascem do mesmo sl_mid), o gatilho ficar bem antes do alvo em vez
        # de emparelhar com ele. Nao mexido em 05_BE_TRAIL/06_REVERSAL_EXIT: nenhum
        # dos dois tem Take ativo, entao nao ha TP pra correr contra.
        p.opt("BreakevenDistancia", 0.35, 0.2, 0.15, 0.7)
        p.opt("MetodoDeCalculo", 1, 0, 1, 4)
        p.opt("TrailVela", 0, 0, 1, 3)
        p.fix("Trail", sl_mid)

    elif system == "03_TRAIL_ONLY":
        p.fix("AtivarStop", "true")
        p.fix("AtivarTake", "false")
        p.fix("TakeOrganico", "false")
        p.fix("Take", sl_mid)
        p.opt("VelaTake", 0, 0, 1, 3)
        p.fix("AtivarTrailATR", "true")
        p.fix("ReversalExitMode", 0)
        p.opt("VelaStop", 0, 0, 1, 3)
        p.opt("Stop", sl_mid, ac.sl_lo, 0.5, ac.sl_hi)
        p.opt("MetodoDeCalculo", 1, 0, 1, 4)
        p.opt("TrailVela", 0, 0, 1, 3)
        p.opt("Trail", sl_mid, ac.sl_lo, 0.5, ac.sl_hi)
        # Breakeven CRAVADO OFF: "trail only" e trailing puro. Com o BE como
        # eixo aqui, este sistema alcancava as duas configuracoes do
        # 05_BE_TRAIL e o 05 virava subconjunto seu -- duas corridas de ~2h
        # para medir o mesmo esqueleto, e um vencedor de "TRAIL_ONLY" que
        # podia sair com breakeven ligado, contrariando o proprio nome.
        # Agora 03 e 05 sao disjuntos: um mede o trailing sozinho, o outro
        # mede o que o breakeven ACRESCENTA a ele.
        p.fix("AtivarBreakeven", "false")
        p.opt("BreakevenDistancia", 1.0, 0.5, 0.5, 3.0)

    elif system == "04_SLTP_TRAIL":
        p.fix("AtivarStop", "true")
        p.fix("AtivarTake", "true")
        p.fix("TakeOrganico", "false")
        p.fix("AtivarTrailATR", "true")
        p.fix("ReversalExitMode", 0)
        p.opt("VelaStop", 0, 0, 1, 3)
        p.opt("Stop", sl_mid, ac.sl_lo, 0.5, ac.sl_hi)
        p.opt("VelaTake", 0, 0, 1, 3)
        p.opt("Take", sl_mid, ac.sl_lo, 0.5, ac.tp_hi)
        # Aberto na fase 1, como em 03_TRAIL_ONLY e 05_BE_TRAIL: e o MESMO
        # trailing nos tres, e a fonte de preco e decisao central dele. Ficar
        # cravado so aqui era inconsistencia acumulada, nao desenho.
        p.opt("MetodoDeCalculo", 1, 0, 1, 4)
        p.opt("TrailVela", 0, 0, 1, 3)
        p.opt("Trail", sl_mid, ac.sl_lo, 0.5, ac.sl_hi)
        p.opt_bool("AtivarBreakeven", "true")
        # Teto descido de 3.0 para 0.7 (achado do dono, 2026-08-16): o gatilho
        # do breakeven e Stop*BreakevenDistancia (nao Take), entao nada aqui impede
        # ele de cair ALEM do Take -- so reduz a chance. Sistema com Take real
        # (este bloco): teto baixo o suficiente pra, no caso tipico (Stop~Take, os
        # dois nascem do mesmo sl_mid), o gatilho ficar bem antes do alvo em vez
        # de emparelhar com ele. Nao mexido em 05_BE_TRAIL/06_REVERSAL_EXIT: nenhum
        # dos dois tem Take ativo, entao nao ha TP pra correr contra.
        p.opt("BreakevenDistancia", 0.35, 0.2, 0.15, 0.7)

    elif system == "05_BE_TRAIL":
        p.fix("AtivarStop", "true")
        p.fix("AtivarTake", "false")
        p.fix("TakeOrganico", "false")
        p.fix("Take", sl_mid)
        p.opt("VelaTake", 0, 0, 1, 3)
        p.fix("AtivarTrailATR", "true")
        p.fix("AtivarBreakeven", "true")
        p.fix("ReversalExitMode", 0)
        p.opt("VelaStop", 0, 0, 1, 3)
        p.opt("Stop", sl_mid, ac.sl_lo, 0.5, ac.sl_hi)
        p.opt("BreakevenDistancia", 1.0, 0.5, 0.5, 3.0)
        p.opt("MetodoDeCalculo", 1, 0, 1, 4)
        p.opt("TrailVela", 0, 0, 1, 3)
        p.opt("Trail", sl_mid, ac.sl_lo, 0.5, ac.sl_hi)

    elif system == "06_REVERSAL_EXIT":
        # Modo 2 (OnIndicatorSignal) nao exige hedging; modo 1 exigiria.
        p.fix("AtivarStop", "true")
        p.fix("AtivarTake", "false")
        p.fix("TakeOrganico", "false")
        p.fix("Take", sl_mid)
        p.opt("VelaTake", 0, 0, 1, 3)
        p.fix("ReversalExitMode", 2)
        p.opt_bool("ReversalExitUseEntryFilters")
        p.opt("VelaStop", 0, 0, 1, 3)
        p.opt("Stop", sl_mid, ac.sl_lo, 0.5, ac.sl_hi)
        p.opt_bool("AtivarTrailATR")
        p.opt("MetodoDeCalculo", 1, 0, 1, 4)
        p.opt("Trail", sl_mid, ac.sl_lo, 0.5, ac.sl_hi)
        p.opt("TrailVela", 0, 0, 1, 3)
        p.opt_bool("AtivarBreakeven", "true")
        p.opt("BreakevenDistancia", 1.0, 0.5, 0.5, 3.0)

    elif system in ("07_GRID_SEPARATE", "08_GRID_UNIFIED"):
        # Grid: SL desligado (a cesta e a gestao), TP obrigatorio,
        # recovery off, lado >= 2, conta hedging.
        if system == "07_GRID_SEPARATE":
            p.fix("GridMode", 1)
        else:
            # 08_GRID_UNIFIED: quem decide separado (1) vs unificado (2) e
            # o proprio algoritmo por combo, nao um travamento de arquivo --
            # "unificado" no nome e so o ponto de partida (current=2), nao
            # a unica opcao. Nunca inclui 0 (Grid_Disabled): desligar o
            # grid tornaria o arquivo incoerente com o proprio sistema que
            # ele representa. Pedido explicito do dono, 2026-08-08.
            p.opt("GridMode", 2, 1, 1, 2)
        p.fix("AtivarStop", "false")
        # Grid nao tem SL nativo (a cesta e a gestao), mas Stop continua
        # tendo efeito real: e a base que o breakeven do EA usa quando nao
        # ha SL na posicao (ApplyBreakevenForSide, .mq5: slDistance =
        # ATR[VelaStop] * Stop, multiplicado por BreakevenDistancia). Achado
        # do dono, 2026-08-08: Stop estava fixo aqui enquanto os outros 6
        # sistemas com breakeven o deixam otimizavel -- travado, o
        # otimizador so podia variar a distancia do breakeven pelo
        # multiplicador (BreakevenDistancia), nunca pela base.
        #
        # Faixa mais grossa que os outros 6 sistemas de proposito (3 passos
        # -- lo/mid/hi -- em vez do passo 0.5 deles): la Stop e o SL de
        # verdade, o eixo principal de risco, precisa de granularidade fina.
        # Aqui e so a base do breakeven, papel secundario, e ja e
        # multiplicativamente redundante com BreakevenDistancia (mesma
        # distancia final sai de varios pares Stop/BreakevenDistancia
        # diferentes) -- passo fino so inflaria o espaco de busca sem
        # sinal novo. Pedido do dono, 2026-08-08.
        p.opt("Stop", sl_mid, ac.sl_lo, (ac.sl_hi - ac.sl_lo) / 2, ac.sl_hi)
        p.opt("VelaStop", 0, 0, 1, 3)
        p.fix("AtivarTake", "true")
        p.fix("TakeOrganico", "false")
        p.opt("VelaTake", 0, 0, 1, 3)
        # Achado do dono, 2026-08-05: mesmo esquema dos outros 6 sistemas
        # que oferecem BE (opt_bool + range), nao inventado pra grid.
        # Achado do dono, 2026-08-05: mesmo esquema dos outros 6 sistemas
        # que oferecem BE (opt_bool + range), nao inventado pra grid.
        p.opt_bool("AtivarBreakeven", "true")
        # Teto descido de 3.0 para 0.7 (achado do dono, 2026-08-16): o gatilho
        # do breakeven e Stop*BreakevenDistancia (nao Take), entao nada aqui impede
        # ele de cair ALEM do Take -- so reduz a chance. Sistema com Take real
        # (este bloco): teto baixo o suficiente pra, no caso tipico (Stop~Take, os
        # dois nascem do mesmo sl_mid), o gatilho ficar bem antes do alvo em vez
        # de emparelhar com ele. Nao mexido em 05_BE_TRAIL/06_REVERSAL_EXIT: nenhum
        # dos dois tem Take ativo, entao nao ha TP pra correr contra.
        p.opt("BreakevenDistancia", 0.35, 0.2, 0.15, 0.7)
        p.fix("AtivarTrailATR", "false")
        p.opt("MetodoDeCalculo", 1, 0, 1, 4)
        p.opt("TrailVela", 0, 0, 1, 3)
        p.fix("Trail", sl_mid)
        p.fix("ReversalExitMode", 0)
        p.fix("RecoveryMode", 0)
        p.opt("Take", sl_mid, ac.sl_lo, 0.5, ac.tp_hi)
        # Multiplicador = 1: alvo da cesta = lucro-por-lote x volume base, sem
        # premio embutido. O input e "Target Profit Multiplier", nao progressao
        # de lote -- acima de 1 a cesta passa a exigir MAIS do que ela mesma
        # produziria, e a matematica deixa de fechar. Fixo tambem tira um eixo
        # de 9 valores da busca.
        p.fix("Multiplicador", 1)
        # Piso subido de 1.0 para 2.5 (achado do dono, 2026-08-16): cesta
        # densa demais (pernas abrindo com pouco movimento contra) e o que
        # deixa o lote de recuperacao (CalculateGridVolume, sem teto) crescer
        # rapido demais numa tendencia forte e estourar o stop de emergencia
        # -- ja visto ao vivo (EURUSD 08_GRID_UNIFIED, saldo congelado apos
        # tradingStopped permanente). Espacar mais ataca a causa (cesta
        # cresce mais devagar) em vez de so limitar o sintoma (tamanho do
        # lote). Teto tambem subiu (5.0 -> 6.0) pra manter faixa de busca
        # comparavel.
        p.opt("DistanciaMinima", 3.5, 2.5, 0.5, 6.0)
        p.opt_bool("UsarsomenteATRGRID")
        # Sem teto de posicoes por lado: o dono confia na distancia ATR
        # (DistanciaMinima) e no proximo sinal como freio, nao numa contagem
        # fixa. 999 e o "sem limite" pratico do MaxLongTrades/MaxShortTrades --
        # travado (N), sem eixo de busca 2..10 por cima (a cesta unificada
        # ("BOTH") ja recebe os dois lados de set_exposure).
        set_exposure(p, side, 999, hedging=True)
        # MinFreeMarginPercent (dono, 2026-08-10): apply_defaults() zera isto
        # pra todo mundo, neutro pros 6 sistemas Fixed-R (CapitalBaseR ja e a
        # rede deles). Grid nao tem SL nativo e o dono decidiu deliberadamente
        # NAO travar por contagem (MaxLongTrades/MaxShortTrades continuam
        # 999, ver comentario acima) -- entao a margem livre real vira o
        # UNICO freio que sobra contra cesta grande demais. A EA ja tem o
        # guard (CanSendTradeRequest, .mq5: recusa ordem nova se a margem
        # livre projetada cair abaixo disto) -- so estava desligado bem onde
        # mais precisa dele. Fixo, nao otimizavel: um piso de seguranca nao
        # pode virar eixo de busca, senao o genetico so escolheria o valor
        # que rende mais no curto prazo, nao o que protege no periodo
        # inteiro (a mesma lacuna que o gate de sobrevivencia existe pra
        # cobrir).
        p.fix("MinFreeMarginPercent", 20)
        # (criterio vem de FORMULA_POR_SISTEMA, aplicado depois deste bloco)

    elif system == "09_MARTINGALE":
        p.fix("RecoveryMode", 1)
        p.fix("GridMode", 0)
        p.fix("AtivarStop", "true")
        p.fix("AtivarTake", "true")
        p.fix("TakeOrganico", "false")
        p.fix("AtivarTrailATR", "false")
        p.opt("MetodoDeCalculo", 1, 0, 1, 4)
        p.opt("TrailVela", 0, 0, 1, 3)
        p.fix("Trail", sl_mid)
        p.fix("ReversalExitMode", 0)
        p.opt("VelaStop", 0, 0, 1, 3)
        p.opt("VelaTake", 0, 0, 1, 3)
        p.fix("MaxMartingaleLot", 0)
        p.opt("Stop", sl_mid, ac.sl_lo, 0.5, ac.sl_hi)
        p.opt("Take", sl_mid, ac.sl_lo, 0.5, ac.tp_hi)
        # Multiplicador = 1: o lote de recuperacao e dimensionado para cobrir
        # EXATAMENTE o deficit acumulado (`|TotalLoss| * Multiplicador /
        # (stop x tickValue)`). A progressao ja nasce da perda -- acima de 1 ela
        # passa a perseguir a perda MAIS um premio, e o lote cresce
        # superlinearmente. A faixa anterior comecava em 1.2, entao nenhum
        # passe chegava a testar a recuperacao fechada.
        p.fix("Multiplicador", 1)
        p.opt("MaxMartingaleSteps", 3, 2, 2, 8)
        p.opt_bool("AtivarBreakeven", "true")
        # Teto descido de 3.0 para 0.7 (achado do dono, 2026-08-16): o gatilho
        # do breakeven e Stop*BreakevenDistancia (nao Take), entao nada aqui impede
        # ele de cair ALEM do Take -- so reduz a chance. Sistema com Take real
        # (este bloco): teto baixo o suficiente pra, no caso tipico (Stop~Take, os
        # dois nascem do mesmo sl_mid), o gatilho ficar bem antes do alvo em vez
        # de emparelhar com ele. Nao mexido em 05_BE_TRAIL/06_REVERSAL_EXIT: nenhum
        # dos dois tem Take ativo, entao nao ha TP pra correr contra.
        p.opt("BreakevenDistancia", 0.35, 0.2, 0.15, 0.7)
        set_exposure(p, side, 1, hedging=False)  # martingale: 1 por lado
        # MinFreeMarginPercent (dono, 2026-08-10): mesmo raciocinio do grid
        # -- o lote de recuperacao cresce pra cobrir o deficit acumulado, sem
        # teto absoluto (MaxMartingaleLot continua 0), entao a margem livre
        # real e o freio que falta durante a busca. Ver comentario completo
        # no bloco do grid.
        p.fix("MinFreeMarginPercent", 20)

    elif system == "10_DALEMBERT":
        p.fix("RecoveryMode", 2)
        p.fix("GridMode", 0)
        p.fix("AtivarStop", "true")
        p.fix("AtivarTake", "true")
        p.fix("TakeOrganico", "false")
        p.fix("AtivarTrailATR", "false")
        p.opt("MetodoDeCalculo", 1, 0, 1, 4)
        p.opt("TrailVela", 0, 0, 1, 3)
        p.fix("Trail", sl_mid)
        p.fix("ReversalExitMode", 0)
        p.opt("VelaStop", 0, 0, 1, 3)
        p.opt("VelaTake", 0, 0, 1, 3)
        p.fix("MaxMartingaleLot", 0)
        p.opt("Stop", sl_mid, ac.sl_lo, 0.5, ac.sl_hi)
        p.opt("Take", sl_mid, ac.sl_lo, 0.5, ac.tp_hi)
        p.opt("DAlembertStep", 0.02, 0.01, 0.02, 0.09)
        p.opt("MaxMartingaleSteps", 3, 2, 2, 8)
        p.opt_bool("AtivarBreakeven", "true")
        # Teto descido de 3.0 para 0.7 (achado do dono, 2026-08-16): o gatilho
        # do breakeven e Stop*BreakevenDistancia (nao Take), entao nada aqui impede
        # ele de cair ALEM do Take -- so reduz a chance. Sistema com Take real
        # (este bloco): teto baixo o suficiente pra, no caso tipico (Stop~Take, os
        # dois nascem do mesmo sl_mid), o gatilho ficar bem antes do alvo em vez
        # de emparelhar com ele. Nao mexido em 05_BE_TRAIL/06_REVERSAL_EXIT: nenhum
        # dos dois tem Take ativo, entao nao ha TP pra correr contra.
        p.opt("BreakevenDistancia", 0.35, 0.2, 0.15, 0.7)
        set_exposure(p, side, 1, hedging=False)
        # MinFreeMarginPercent (dono, 2026-08-10): ver comentario completo no
        # bloco do grid -- mesma lacuna, mesmo remedio.
        p.fix("MinFreeMarginPercent", 20)

    elif system == "11_SIGNAL_ONLY":
        p.fix("AtivarStop", "false")
        p.fix("Stop", sl_mid)
        p.opt("VelaStop", 0, 0, 1, 3)
        p.fix("AtivarTake", "false")
        p.fix("Take", sl_mid)
        p.opt("VelaTake", 0, 0, 1, 3)
        p.fix("TakeOrganico", "false")
        p.fix("AtivarBreakeven", "false")
        p.fix("BreakevenDistancia", 1.0)
        p.fix("AtivarTrailATR", "false")
        p.opt("MetodoDeCalculo", 1, 0, 1, 4)
        p.opt("TrailVela", 0, 0, 1, 3)
        p.fix("Trail", sl_mid)
        p.fix("ReversalExitMode", 2)
        p.opt_bool("ReversalExitUseEntryFilters")

    else:
        raise ValueError(f"sistema desconhecido: {system}")


# ------------------------------------------------------------------- escrita

def load_schema() -> tuple[list[str], list[str]]:
    """Le a ordem dos inputs e as secoes direto do fonte da EA.

    O .set precisa listar os inputs na mesma ordem em que a EA os declara. Ler
    o .mq5 mantem os dois em sincronia sozinho: acrescentar um input na EA e
    regerar basta, sem reabrir o Strategy Tester para salvar um template novo.
    """
    src = EA_SOURCE.read_text(encoding="utf-8", errors="replace")
    order: list[str] = []
    structure: list[str] = []
    for line in src.splitlines():
        group = re.match(r'^\s*input\s+group\s+"([^"]*)"', line)
        if group:
            structure.append(f"; {group.group(1)}")
            continue
        found = re.match(
            r"^\s*input\s+(?!group\b)[A-Za-z_][A-Za-z0-9_]*\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if found:
            order.append(found.group(1))
            structure.append(found.group(1))
    if not order:
        raise SystemExit("Nenhum input encontrado no fonte da EA.")
    return order, structure


SCHEMA, STRUCTURE = load_schema()
BLANKS = [n for n in SCHEMA if n.startswith("myBlankSpace")]


def render(p: Profile, header: list[str]) -> str:
    lines = list(header)
    lines.append("; this file contains input parameters for testing/optimizing")
    lines.append("; to use it, click Load in the context menu of the Inputs tab")
    lines.append(";")
    for item in STRUCTURE:
        if item.startswith(";"):
            lines.append(item)
        else:
            lines.append(f"{item}={p.values[item]}")
    return "\r\n".join(lines) + "\r\n"


def main() -> None:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)

    manifest: list[dict] = []
    magics_usados: dict[int, str] = {}
    total_passes_max = 0

    for class_code, assets in ASSETS.items():
        ac = CLASSES[class_code]
        for asset in assets:
            for system in SYSTEMS:
                # Sistema bilateral gera UM arquivo em vez de BUY e SELL: com os
                # dois lados ligados, os dois arquivos seriam identicos.
                for side in (("BOTH",) if system.code in BILATERAL
                             else ("BUY", "SELL")):
                    for ichimoku in (False, True):
                        variant = "ICHIMOKU" if ichimoku else "MULTI"
                        name = f"WRX {system.code} {asset} {side} {variant}"
                        magic = magic_estavel(
                            f"{class_code}/{asset}/{system.code}/"
                            f"{side}_{variant}", magics_usados)
                        p = Profile()
                        apply_defaults(p, ac, side, magic, name)
                        apply_core(p, ac, ichimoku,
                                   grid=system.code in ("07_GRID_SEPARATE",
                                                        "08_GRID_UNIFIED"))
                        apply_system(p, system.code, ac, side)
                        apply_sizing_and_formula(p, system.code, ac)
                        p.desativar_inertes()

                        missing = [n for n in SCHEMA if n not in p.values]
                        if missing:
                            raise SystemExit(f"{name}: sem valor -> {missing}")

                        passes = p.passes()
                        total_passes_max = max(total_passes_max, passes)
                        algorithm = ("COMPLETE_SEARCH" if passes <= 20_000
                                     else "FAST_GENETIC")
                        header = [
                            "; White Rabbit X - set de otimizacao por sistema",
                            f"; Sistema={system.code} ({system.label})",
                            f"; Ativo={asset} | Classe={class_code} | Lado={side}",
                            f"; Indicadores={'Ichimoku' if ichimoku else 'MACD/EMA/Momentum/Stochastic/TRIX'}",
                            f"; ParametrosOtimizados={len(p.flags())}",
                            f"; Combinacoes={passes:,}".replace(",", "."),
                            f"; Algoritmo={algorithm}",
                            f"; Status={system.status}",
                            f"; Nota={system.notes}",
                            "; Desligue (Y->N) o que ja tiver resolvido antes da proxima rodada.",
                        ]
                        content = render(p, header)
                        rel = (Path(class_code) / asset / system.code /
                               f"{side}_{variant}.set")
                        target = OUTPUT / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(content, encoding="utf-16")

                        # Cabecalhos em ingles: o manifesto e publico e vai
                        # junto com a biblioteca, que tem leitor fora do Brasil.
                        manifest.append({
                            "Class": class_code, "Symbol": asset,
                            "System": system.code, "Side": side,
                            "Variant": variant,
                            "OptimizedParams": len(p.flags()),
                            "Combinations": passes,
                            "Algorithm": algorithm,
                            "MagicNumber": magic,
                            "Status": system.status,
                            "Path": rel.as_posix(),
                            "SHA256": hashlib.sha256(
                                target.read_bytes()).hexdigest().upper(),
                        })

    with (OUTPUT / "MANIFESTO_SISTEMAS.csv").open(
            "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(manifest[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(manifest)

    # O README morre junto com a pasta a cada regeracao; reescreve sempre.
    import subprocess
    subprocess.run([sys.executable,
                    str(Path(__file__).with_name("write_library_docs.py"))],
                   check=True, capture_output=True)

    print(f"Sets gerados: {len(manifest)}")
    print(f"Ativos: {sum(len(v) for v in ASSETS.values())} | "
          f"Sistemas: {len(SYSTEMS)} | Variantes: 2 | "
          f"Lados: 2, menos {len(BILATERAL)} bilateral(is) com arquivo unico")
    print(f"Maior espaco de busca: {total_passes_max:,}".replace(",", "."))
    print(f"Saida: {OUTPUT}")


if __name__ == "__main__":
    main()
