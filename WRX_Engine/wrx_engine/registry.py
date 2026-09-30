"""Registro dos inputs da EA e o quanto de cada um o motor ja porta.

Fonte da verdade da LISTA DE REVISAO (`review.py`). Mantido em sincronia com o CSV publico de
inputs por um teste (`tests/test_registry.py`); na sua maquina, `python -m wrx_engine.review
sync --ea "caminho/White Rabbit X (Global Multi-Indicator).mq5"` compara com os `input` do .mq5.

Status:
  PORTED   portado e coberto por teste (a fidelidade ao MT5 ainda depende da paridade -- ver README)
  PARTIAL  portado em parte; a nota diz o que falta
  DEFERRED nao portado ainda; o motor RECUSA o set se o input estiver ligado
  UI       so interface/log/identidade -- sem efeito nas ordens
  INERT    tem efeito no MT5 real, mas nao no Tester ideal (nada a simular)
"""
from __future__ import annotations

from dataclasses import dataclass

PORTED, PARTIAL, DEFERRED, UI, INERT = "PORTED", "PARTIAL", "DEFERRED", "UI", "INERT"


@dataclass(frozen=True)
class InputInfo:
    status: str
    note: str = ""


def _t(rows: str) -> dict[str, InputInfo]:
    out = {}
    for line in rows.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        names, status, *note = [x.strip() for x in line.split("|")]
        for n in names.split(","):
            out[n.strip()] = InputInfo(status, note[0] if note else "")
    return out


REGISTRY: dict[str, InputInfo] = _t("""
# ---- Geral / interface
NomedaEstrategia | UI
InterfaceLanguage,EnableChartDashboard,PlotIndicatorsOnChart,DashboardCorner,DashboardOffsetX,DashboardOffsetY | UI
ShowClosedDealLabels,MaxVisibleDealLabels,ClosedDealLabelFontSize,ApplyEmbeddedChartTheme | UI
ChartTheme,DASH_C_DEAL_BG,DASH_C_PANEL_BG,DashboardPanelOpacityPct | UI
MagicNumber | INERT | so identifica ordens; o motor simula um unico magic
MaxSlippage | INERT | Tester ideal executa sem desvio; slippage nao e modelado (so entra na validacao do OnInit)
# ---- Entradas
TimeFrame | PORTED | M1..W1; sinal 1x por barra deste TF (exige >= 50 barras do TF)
EntryIndicator | PORTED | os 12 (MACD, EMA, Momentum, Stochastic, TRIX, RSI, CCI, WPR, DeMarker, MFI, OsMA, Ichimoku)
InpAppliedPrice | PORTED | vale para MACD/EMA/Momentum/TRIX/RSI/CCI/OsMA
Fast_EMA,Slow_EMA,MACD_SMA | PORTED | significado depende do indicador (ver signals.build_entry_series)
EntryMethod | PORTED | 7 metodos
StochasticSlowing,StochasticMethod,StochasticPriceField | PORTED | HIPOTESE: slowing por soma/soma; metodo aplica ao %D
IchimokuUseKumo,IchimokuChikouFilter | PORTED | nuvem calculada Kijun barras atras (como o comentario do .mq5)
ATR_TimeFrame,PeriodoATR | PORTED | iATR = SMA do True Range (hipotese); ATR[0] parcial no 1o tick
AtivarStop,VelaStop,Stop | PORTED | SL por perna; o trailing cria SL em posicao sem SL
AtivarTake,VelaTake,Take | PORTED |
TakeOrganico | PORTED | fecha a mercado quando bid > abertura da posicao mais recente + ATR*Take (LastTradePrice = posicao ABERTA)
# ---- Filtros
AtivarFiltroMTF,MTF_RequererAmbos | PORTED | TFs superiores = GetHigherTimeframes(TimeFrame) (confirmado no OnInit)
AtivarFiltroMA,MA_TimeFrame,MA_Period,MA_Method,MA_AppliedPrice,MetodoMA,SentidoMA,MA_SlopeLookback | PORTED |
AtivarFiltroADX,ADX_TimeFrame,ADX_Period,ADX_Limiar,MetodoADX | PORTED | HIPOTESE: iADX com EMA (alpha 2/(n+1)) em +DI/-DI/DX
EntradaATR,VolatilityFilter,MultiplicadorATR,PeriodoBaselineATR | PORTED | baseline inclui o ATR[0] parcial
AtivarFiltroNoticias,NewsSomenteAltoImpacto,NewsMinutosAntes,NewsMinutosDepois,NewsMoedasManual,NewsCSVFile | PORTED | eventos vem de load_news_csv (mesmo CSV do exportador); moedas manuais ou base+cotacao de simbolo de 6 letras
# ---- Saidas
AtivarBreakeven,BreakevenDistancia | PORTED | reavaliado so nas decisoes (1x/minuto)
AtivarTrailATR,MetodoDeCalculo,TrailVela,Trail,TrailSoLucro | PORTED | TrailingStopSet 1x por barra do TF de entrada; na piramide tambem ha o trailing da cesta
ReversalExitMode | PORTED | 0, 1 (ordem oposta, exige hedging) e 2 (sinal contrario)
ReversalExitUseEntryFilters | PORTED |
# ---- Risco e lote
TradeCapitalPercentage,CapitalBaseR,MaxRiscoTradeR,MaxRiscoRelativoAoLoteMinimo | PORTED | Fixed-R
PositionSizeMode,PositionSizeValue | PORTED | Percentage (saldo ao vivo), Monetary (capital inicial), FixedLot, FixedR
DailyLossLimitPercent | PORTED | pior caso do dia = fechado desde a ancora + perda no SL das abertas (bloqueia ENTRADA nova)
MaxEquityDrawdownPercent | PORTED | trava de equity da estrategia, a cada tick; liquida e para o teste
MinFreeMarginPercent | PARTIAL | depende da margem da corretora: preencha margin_a/margin_b no SymbolSpec (sem isso nao e modelada)
Trava_Diaria_Percent,Trava_Total_Percent,Protecao_Fecha_Posicoes | PORTED | equity da conta (aqui = 1 simbolo); estado do GlobalVariable assumido limpo a cada teste
# ---- Recovery / Grid
RecoveryMode,Multiplicador,MaxMartingaleSteps,MaxMartingaleLot,DAlembertStep | PORTED | historico de ciclos por lado (ApplyRecoveryOperation)
GridMode,UsarsomenteATRGRID,DistanciaMinima | PORTED | 1 = grid classico (alvo monetario congelado na semente); 3 = piramide; 2 e invalido (o EA recusa)
PyramidTrailSoLucro,PyramidLevelOnlyInProfit | PORTED |
# ---- Entradas pendentes
EntryOrderType,PendingReferencia,PendingDistanciaATR,PendingExpiracaoBarras,PendingGatilho,PendingHoraSessao,PendingFaixaBarras | PORTED | Stop/Limit/OCO/sessao; preenchimento: stop no tick, limit no preco (calibrar: pending_fill)
# ---- Agenda
Fecharordensforadohorario | PORTED | roda antes de checar se ha dados prontos
TOD_From_Hour,TOD_From_Min,TOD_To_Hour,TOD_To_Min | PORTED |
TradeMonday,TradeTuesday,TradeWednesday,TradeThursday,TradeFriday,TradeSaturday,TradeSunday | PORTED |
# ---- Execucao / exposicao
MaxSpread | PORTED | spread em pontos inteiros do tick
MaxLongTrades,MaxShortTrades,Hedging | PORTED |
ModificationSafetyPoints | PORTED |
# ---- EA Bollinger (familia de entrada alternativa)
BandsPeriod,BandsDeviation,InpAppliedPrice_BB | PORTED | iBands: base SMA, desvio padrao populacional
BandsShift | PARTIAL | so 0 (deslocamento horizontal nao portado; o motor recusa != 0)
BollingerEntryMode,SqueezeLookback,SqueezeTolerancePct | PORTED | 0 reversao, 1 rompimento, 2 squeeze (largura na barra 2 vs minimo de N barras)
StopBolinger,TakeBolinger,BreakevenBolinger | PORTED | saidas alternativas por banda (Take/BE so no modo Reversal)
# ---- EA Candles Entry (familia de entrada alternativa)
CandleTF1,CandleIndex1,CandleTF2,CandleIndex2,CandleTF3,CandleIndex3 | PORTED | 3 slots: applied price x open; indice 0 = candle em formacao (parcial)
# ---- WFO / otimizacao
AtivarWFO,MetodoDeEntradawfo | PORTED | janelas IS/OOS, bloqueio de entrada, carencia de grid, retirada do lucro; inicio = 1a barra M1 do teste (hipotese)
input_end_date,wfo_windowSize,wfo_customWindowSizeDays,wfo_stepSize,wfo_customStepSizePercent,WFO_CarenciaPercentil | PORTED |
selectedFormula | DEFERRED | formulas de fitness do OnTester ainda nao portadas
""")


def is_separator(name: str) -> bool:
    return name.startswith("myBlankSpace")


def lookup(name: str) -> InputInfo:
    if is_separator(name):
        return InputInfo(UI, "separador visual")
    return REGISTRY.get(name, InputInfo("UNKNOWN", "input ausente do registro -- classifique"))
