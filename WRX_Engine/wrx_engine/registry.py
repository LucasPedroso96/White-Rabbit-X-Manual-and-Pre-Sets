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
MaxSlippage | INERT | Tester ideal executa sem desvio; slippage nao e modelado
# ---- Entradas
TimeFrame | PORTED | M1..W1; sinal 1x por barra deste TF
EntryIndicator | PORTED | os 12 (MACD, EMA, Momentum, Stochastic, TRIX, RSI, CCI, WPR, DeMarker, MFI, OsMA, Ichimoku)
InpAppliedPrice | PORTED | vale para MACD/EMA/Momentum/TRIX/RSI/CCI/OsMA
Fast_EMA,Slow_EMA,MACD_SMA | PORTED | significado depende do indicador (ver signals.build_entry_series)
EntryMethod | PORTED | 7 metodos
StochasticSlowing,StochasticMethod,StochasticPriceField | PORTED | HIPOTESE: slowing por soma/soma; metodo aplica ao %D
IchimokuUseKumo,IchimokuChikouFilter | PORTED | nuvem calculada Kijun barras atras (como o comentario do .mq5)
ATR_TimeFrame,PeriodoATR | PORTED | iATR = SMA do True Range (hipotese); ATR[0] parcial no 1o tick
AtivarStop,VelaStop,Stop | PORTED | so com FixedR por enquanto
AtivarTake,VelaTake,Take | PORTED |
TakeOrganico | DEFERRED | depende de LastTradePrice() (nao lido): pode ancorar no trade ANTERIOR
# ---- Filtros
AtivarFiltroMTF,MTF_RequererAmbos | PORTED | HIPOTESE: TFs superiores = GetHigherTimeframes(TimeFrame) (OnInit nao lido)
AtivarFiltroMA,MA_TimeFrame,MA_Period,MA_Method,MA_AppliedPrice,MetodoMA,SentidoMA,MA_SlopeLookback | PORTED |
AtivarFiltroADX,ADX_TimeFrame,ADX_Period,ADX_Limiar,MetodoADX | PORTED | HIPOTESE: iADX com EMA (alpha 2/(n+1)) em +DI/-DI/DX
EntradaATR,VolatilityFilter,MultiplicadorATR,PeriodoBaselineATR | PORTED | baseline inclui o ATR[0] parcial
AtivarFiltroNoticias,NewsSomenteAltoImpacto,NewsMinutosAntes,NewsMinutosDepois,NewsMoedasManual,NewsCSVFile | DEFERRED | WhiteRabbitNewsFilter.mqh nao lido
# ---- Saidas
AtivarBreakeven,BreakevenDistancia | PORTED | reavaliado so nas decisoes (1x/minuto)
AtivarTrailATR,MetodoDeCalculo,TrailVela,Trail,TrailSoLucro | DEFERRED | TrailingStopSet() nao lido
ReversalExitMode | PARTIAL | 0 e 2 portados; 1 (OnOppositeOrder) recusado
ReversalExitUseEntryFilters | PORTED |
# ---- Risco e lote
TradeCapitalPercentage,CapitalBaseR,MaxRiscoTradeR,MaxRiscoRelativoAoLoteMinimo | PORTED | Fixed-R
PositionSizeMode,PositionSizeValue | PARTIAL | so FixedR; Percentage/Monetary/FixedLot adiados
DailyLossLimitPercent,MaxEquityDrawdownPercent,MinFreeMarginPercent | DEFERRED | zere no set (os defaults do EA sao 0/30/50!)
Trava_Diaria_Percent,Trava_Total_Percent,Protecao_Fecha_Posicoes | DEFERRED | WhiteRabbitGlobalProtection.mqh nao lido
# ---- Recovery / Grid
RecoveryMode,Multiplicador,MaxMartingaleSteps,MaxMartingaleLot,DAlembertStep | DEFERRED | historico de ciclos lido; sizing de Percentage/Monetary/Fixed nao
GridMode,UsarsomenteATRGRID,DistanciaMinima,PyramidTrailSoLucro,PyramidLevelOnlyInProfit | DEFERRED | grid/piramide nao lidos
# ---- Entradas pendentes
EntryOrderType,PendingReferencia,PendingDistanciaATR,PendingExpiracaoBarras,PendingGatilho,PendingHoraSessao,PendingFaixaBarras | DEFERRED |
# ---- Agenda
Fecharordensforadohorario | PORTED | roda antes de checar se ha dados prontos
TOD_From_Hour,TOD_From_Min,TOD_To_Hour,TOD_To_Min | PORTED |
TradeMonday,TradeTuesday,TradeWednesday,TradeThursday,TradeFriday,TradeSaturday,TradeSunday | PORTED |
# ---- Execucao / exposicao
MaxSpread | PORTED | spread em pontos inteiros do tick
MaxLongTrades,MaxShortTrades,Hedging | PORTED |
ModificationSafetyPoints | PORTED |
# ---- WFO / otimizacao
AtivarWFO | PARTIAL | so false, ou true com 'In Sample + Out Sample' (nao bloqueia entradas)
MetodoDeEntradawfo | PARTIAL | 0 (In Sample) com AtivarWFO=true e recusado
input_end_date,wfo_windowSize,wfo_customWindowSizeDays,wfo_stepSize,wfo_customStepSizePercent,WFO_CarenciaPercentil | DEFERRED | janelas IS/OOS
selectedFormula | DEFERRED | formulas de OnTester (fitness) ainda nao portadas
""")


def is_separator(name: str) -> bool:
    return name.startswith("myBlankSpace")


def lookup(name: str) -> InputInfo:
    if is_separator(name):
        return InputInfo(UI, "separador visual")
    return REGISTRY.get(name, InputInfo("UNKNOWN", "input ausente do registro -- classifique"))
