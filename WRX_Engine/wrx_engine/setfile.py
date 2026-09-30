"""Leitura de .set do White Rabbit X + a GUARDA de escopo do motor.

`load_set` devolve o valor ATUAL de cada input (o token antes do primeiro `||`).
Inputs ausentes assumem o DEFAULT DO EA (copiados do .mq5) -- nao um default nosso.

`unsupported()` lista tudo que esta LIGADO e o motor ainda nao implementa. Quem chama
`run_backtest` recebe `UnsupportedConfig` em vez de um resultado que ignora o eixo em
silencio (uma varredura em que o eixo e ignorado sai com todas as celulas iguais e
parece que mediu algo).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .bars import TF_MINUTES

# Defaults do EA (White Rabbit X (Global Multi-Indicator).mq5, EA 1.12)
_DEFAULTS: dict[str, object] = {
    "TimeFrame": 0, "ATR_TimeFrame": 0, "EntryIndicator": 0, "InpAppliedPrice": 1,
    "Fast_EMA": 12, "Slow_EMA": 26, "MACD_SMA": 9, "EntryMethod": 6,
    "PeriodoATR": 14, "PeriodoBaselineATR": 100,
    "StochasticSlowing": 3, "StochasticMethod": 0, "StochasticPriceField": 0,
    "IchimokuUseKumo": True, "IchimokuChikouFilter": False,
    "MTF_RequererAmbos": False, "MA_TimeFrame": 0, "MA_Period": 200, "MA_Method": 1, "MA_AppliedPrice": 1,
    "MetodoMA": 2, "SentidoMA": 0, "MA_SlopeLookback": 3,
    "ADX_TimeFrame": 0, "ADX_Period": 14, "ADX_Limiar": 25.0, "MetodoADX": 0,
    "VolatilityFilter": 1, "MultiplicadorATR": 1.5,
    "AtivarStop": True, "VelaStop": 0, "Stop": 3.0,
    "TakeOrganico": False, "AtivarTake": True, "VelaTake": 0, "Take": 3.0,
    "AtivarBreakeven": True, "BreakevenDistancia": 0.5,
    "AtivarTrailATR": False, "ReversalExitMode": 2, "ReversalExitUseEntryFilters": False,
    "PositionSizeMode": 2, "PositionSizeValue": 0.01, "TradeCapitalPercentage": 100.0,
    "CapitalBaseR": 0.0, "MaxRiscoTradeR": 0.0, "MaxRiscoRelativoAoLoteMinimo": 1.5,
    "DailyLossLimitPercent": 0.0, "MaxEquityDrawdownPercent": 30.0, "MinFreeMarginPercent": 50.0,
    "Trava_Diaria_Percent": 0.0, "Trava_Total_Percent": 0.0,
    "RecoveryMode": 0, "GridMode": 0,
    "AtivarFiltroMTF": False, "AtivarFiltroMA": False, "AtivarFiltroADX": False,
    "EntradaATR": False, "AtivarFiltroNoticias": False,
    "EntryOrderType": 0, "PendingGatilho": 0,
    "Fecharordensforadohorario": False,
    "TOD_From_Hour": 0, "TOD_From_Min": 0, "TOD_To_Hour": 23, "TOD_To_Min": 55,
    "TradeMonday": True, "TradeTuesday": True, "TradeWednesday": True,
    "TradeThursday": True, "TradeFriday": True, "TradeSaturday": False, "TradeSunday": False,
    "MaxSpread": 0.0, "MaxLongTrades": 1, "MaxShortTrades": 1, "Hedging": False,
    "ModificationSafetyPoints": 0, "AtivarWFO": False, "MetodoDeEntradawfo": 0,
    # --- adicionados no porte completo (valores = defaults do .mq5 v1.24)
    "MetodoDeCalculo": 1, "TrailVela": 0, "Trail": 3.0, "TrailSoLucro": False,
    "Multiplicador": 1.0, "MaxMartingaleSteps": 0, "MaxMartingaleLot": 0.0, "DAlembertStep": 0.01,
    "UsarsomenteATRGRID": False, "DistanciaMinima": 2.0, "PyramidTrailSoLucro": False,
    "PyramidLevelOnlyInProfit": False,
    "PendingReferencia": 0, "PendingDistanciaATR": 0.5, "PendingExpiracaoBarras": 3,
    "PendingHoraSessao": 8, "PendingFaixaBarras": 4,
    "NewsSomenteAltoImpacto": False, "NewsMinutosAntes": 15, "NewsMinutosDepois": 15,
    "NewsMoedasManual": "", "NewsCSVFile": "WhiteRabbit_News.csv",
    "Protecao_Fecha_Posicoes": True, "MaxSlippage": 10,
    "wfo_windowSize": 360, "wfo_customWindowSizeDays": 0, "wfo_stepSize": 180, "wfo_customStepSizePercent": 0,
    "input_end_date": "2026.07.21", "WFO_CarenciaPercentil": 75,
}

# Nomes dos enums, so para mensagens de erro legiveis.
_ENTRY_INDICATOR = ["MACD", "EMA_Cross", "Momentum", "Stochastic", "TRIX", "RSI", "CCI",
                    "WPR", "DeMarker", "MFI", "OsMA", "Ichimoku"]
_SIZE_MODE = ["Percentage", "Monetary", "FixedLot", "FixedR"]


class UnsupportedConfig(ValueError):
    """O set liga algo que o motor ainda nao porta."""

    def __init__(self, motivos: list[str]):
        self.motivos = motivos
        super().__init__("configuracao fora do escopo do motor:\n  - " + "\n  - ".join(motivos))


def _coerce(default: object, text: str) -> object:
    text = text.strip()
    if isinstance(default, bool):
        return text.lower() in ("true", "1", "yes")
    if isinstance(default, int):
        return int(float(text))
    if isinstance(default, float):
        return float(text)
    return text


def read_set_text(path: str | Path) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-16", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeError:
            continue
    raise ValueError(f"nao consegui decodificar {path}")


def parse_set_text(text: str) -> dict[str, str]:
    """chave -> valor atual (antes do primeiro '||'). Linhas ';' sao comentario."""
    out: dict[str, str] = {}
    for line in text.replace("\r", "\n").split("\n"):
        line = line.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.split("||", 1)[0].strip()
    return out


@dataclass
class WrxParams:
    raw: dict = field(default_factory=dict, repr=False)
    v: dict = field(default_factory=dict, repr=False)      # TODOS os inputs conhecidos, ja tipados
    # sinal
    timeframe_idx: int = 0
    atr_timeframe_idx: int = 0
    entry_indicator: int = 0
    applied_price: int = 1
    fast: int = 12
    slow: int = 26
    signal: int = 9
    entry_method: int = 6
    period_atr: int = 14
    period_baseline_atr: int = 100
    stoch_slowing: int = 3
    stoch_method: int = 0
    stoch_price_field: int = 0          # 0 = Low/High, 1 = Close/Close
    ichimoku_use_kumo: bool = True
    ichimoku_chikou: bool = False
    # filtros
    use_mtf: bool = False
    mtf_both: bool = False
    use_ma: bool = False
    ma_tf_idx: int = 0
    ma_period: int = 200
    ma_method: int = 1
    ma_applied_price: int = 1
    ma_rule: int = 2
    ma_reversal: bool = False
    ma_slope_lookback: int = 3
    use_adx: bool = False
    adx_tf_idx: int = 0
    adx_period: int = 14
    adx_limit: float = 25.0
    adx_with_di: bool = False
    use_vol: bool = False
    vol_high: bool = True
    vol_mult: float = 1.5
    # saidas
    use_stop: bool = True
    vela_stop: int = 0
    stop: float = 3.0
    use_take: bool = True
    vela_take: int = 0
    take: float = 3.0
    use_breakeven: bool = True
    breakeven_dist: float = 0.5
    # lote
    size_mode: int = 2
    size_value: float = 0.01
    trade_capital_pct: float = 100.0
    capital_base_r: float = 0.0
    max_risco_r: float = 0.0
    max_risco_rel_min: float = 1.5
    # agenda / exposicao
    tod_from: int = 0          # minutos desde 00:00
    tod_to: int = 23 * 60 + 55
    days: tuple = (False, True, True, True, True, True, False)   # indexado por day_of_week (0=dom)
    max_spread: float = 0.0
    max_long: int = 1
    max_short: int = 1
    hedging: bool = False
    safety_points: int = 0
    reversal_exit_mode: int = 0        # 0 = off, 2 = fecha no sinal contrario completo
    reversal_use_filters: bool = False
    close_outside_hours: bool = False

    @property
    def tf_min(self) -> int:
        return TF_MINUTES[self.timeframe_idx]

    @property
    def atr_tf_min(self) -> int:
        return TF_MINUTES[self.atr_timeframe_idx]


def params_from_dict(d: dict[str, str]) -> WrxParams:
    v = {k: (_coerce(dflt, d[k]) if k in d else dflt) for k, dflt in _DEFAULTS.items()}
    days = (v["TradeSunday"], v["TradeMonday"], v["TradeTuesday"], v["TradeWednesday"],
            v["TradeThursday"], v["TradeFriday"], v["TradeSaturday"])
    return WrxParams(
        raw=dict(d) | {k: v[k] for k in _DEFAULTS}, v=v,
        timeframe_idx=v["TimeFrame"], atr_timeframe_idx=v["ATR_TimeFrame"],
        entry_indicator=v["EntryIndicator"], applied_price=v["InpAppliedPrice"],
        fast=v["Fast_EMA"], slow=v["Slow_EMA"], signal=v["MACD_SMA"],
        entry_method=v["EntryMethod"], period_atr=v["PeriodoATR"],
        period_baseline_atr=v["PeriodoBaselineATR"],
        stoch_slowing=v["StochasticSlowing"], stoch_method=v["StochasticMethod"],
        stoch_price_field=v["StochasticPriceField"], ichimoku_use_kumo=v["IchimokuUseKumo"],
        ichimoku_chikou=v["IchimokuChikouFilter"],
        use_mtf=v["AtivarFiltroMTF"], mtf_both=v["MTF_RequererAmbos"], use_ma=v["AtivarFiltroMA"],
        ma_tf_idx=v["MA_TimeFrame"], ma_period=v["MA_Period"], ma_method=v["MA_Method"],
        ma_applied_price=v["MA_AppliedPrice"], ma_rule=v["MetodoMA"], ma_reversal=v["SentidoMA"] == 1,
        ma_slope_lookback=v["MA_SlopeLookback"], use_adx=v["AtivarFiltroADX"], adx_tf_idx=v["ADX_TimeFrame"],
        adx_period=v["ADX_Period"], adx_limit=v["ADX_Limiar"], adx_with_di=v["MetodoADX"] == 1,
        use_vol=v["EntradaATR"], vol_high=v["VolatilityFilter"] == 1, vol_mult=v["MultiplicadorATR"],
        use_stop=v["AtivarStop"], vela_stop=v["VelaStop"], stop=v["Stop"],
        use_take=v["AtivarTake"], vela_take=v["VelaTake"], take=v["Take"],
        use_breakeven=v["AtivarBreakeven"], breakeven_dist=v["BreakevenDistancia"],
        size_mode=v["PositionSizeMode"], size_value=v["PositionSizeValue"],
        trade_capital_pct=v["TradeCapitalPercentage"], capital_base_r=v["CapitalBaseR"],
        max_risco_r=v["MaxRiscoTradeR"], max_risco_rel_min=v["MaxRiscoRelativoAoLoteMinimo"],
        tod_from=v["TOD_From_Hour"] * 60 + v["TOD_From_Min"],
        tod_to=v["TOD_To_Hour"] * 60 + v["TOD_To_Min"], days=days,
        max_spread=v["MaxSpread"], max_long=v["MaxLongTrades"], max_short=v["MaxShortTrades"],
        hedging=v["Hedging"], safety_points=v["ModificationSafetyPoints"],
        reversal_exit_mode=v["ReversalExitMode"], reversal_use_filters=v["ReversalExitUseEntryFilters"],
        close_outside_hours=v["Fecharordensforadohorario"],
    )


class InvalidConfig(ValueError):
    """Combinacao que o EA recusa no OnInit (INIT_PARAMETERS_INCORRECT): o Tester nem abriria."""


def oninit_errors(v: dict, *, hedging_account: bool = True) -> list[str]:
    """Espelho das validacoes do OnInit(). `hedging_account`: conta do Tester e hedging?"""
    e: list[str] = []
    mode = v["PositionSizeMode"]
    pct, mon, fixo, rfix = mode == 0, mode == 1, mode == 2, mode == 3
    mart, dal = v["RecoveryMode"] == 1, v["RecoveryMode"] == 2
    grid = v["GridMode"] != 0
    pyr = v["GridMode"] == 3
    if v["GridMode"] not in (0, 1, 3):
        e.append("GridMode=2 foi aposentado (Unified removido): o EA falha de proposito")
    if not 0 < v["TradeCapitalPercentage"] <= 100:
        e.append("TradeCapitalPercentage fora de (0,100]")
    if not 0 <= v["DailyLossLimitPercent"] < 100:
        e.append("DailyLossLimitPercent fora de [0,100)")
    if v["NewsMinutosAntes"] < 0 or v["NewsMinutosDepois"] < 0:
        e.append("janela de noticias negativa")
    if v["MaxMartingaleSteps"] < 0 or v["MaxMartingaleLot"] < 0:
        e.append("limites de recovery negativos")
    if mart and (v["MaxLongTrades"] > 1 or v["MaxShortTrades"] > 1):
        e.append("Martingale exige no maximo 1 posicao por lado")
    if not (0 <= v["MaxEquityDrawdownPercent"] < 100 and 0 <= v["MinFreeMarginPercent"] < 100):
        e.append("MaxEquityDrawdownPercent/MinFreeMarginPercent fora de [0,100)")
    if not (0 <= v["Trava_Diaria_Percent"] < 100 and 0 <= v["Trava_Total_Percent"] < 100):
        e.append("Trava_*_Percent fora de [0,100)")
    fast, slow, sig = v["Fast_EMA"], v["Slow_EMA"], v["MACD_SMA"]
    ind = v["EntryIndicator"]
    if fast <= 0 or sig <= 0:
        e.append("periodos do indicador <= 0")
    if ind in (0, 1, 10) and (slow <= 0 or fast >= slow):
        e.append("exige Fast < Slow")
    if v["AtivarFiltroMTF"] and (slow <= 0 or fast >= slow):
        e.append("filtro MTF exige Fast < Slow")
    if ind == 11 and (slow <= fast or sig <= slow):
        e.append("Ichimoku exige Tenkan < Kijun < SenkouB")
    if ind == 3 and v["StochasticSlowing"] <= 0:
        e.append("Stochastic slowing <= 0")
    if v["PeriodoATR"] <= 0:
        e.append("PeriodoATR <= 0")
    if v["EntradaATR"] and (v["PeriodoBaselineATR"] <= 0 or v["MultiplicadorATR"] <= 0):
        e.append("filtro de volatilidade invalido")
    if v["AtivarStop"] and v["Stop"] <= 0:
        e.append("Stop <= 0 com AtivarStop")
    if v["AtivarTake"] and v["Take"] <= 0:
        e.append("Take <= 0 com AtivarTake")
    if v["AtivarTrailATR"] and v["Trail"] <= 0:
        e.append("Trail <= 0 com AtivarTrailATR")
    if fixo and v["PositionSizeValue"] <= 0:
        e.append("lote fixo <= 0")
    if pct and v["PositionSizeValue"] <= 0:
        e.append("Percentage <= 0")
    if pct and not v["AtivarStop"]:
        e.append("Percentage exige Stop Loss")
    if mon and v["PositionSizeValue"] <= 0:
        e.append("Monetary <= 0")
    if rfix and (pct or mon or fixo or (grid and not pyr)):
        e.append("FixedR nao combina com outros modos nem com Grid classico")
    if rfix and dal:
        e.append("FixedR nao permite D'Alembert")
    if rfix and not v["AtivarStop"]:
        e.append("FixedR exige AtivarStop")
    if rfix and (v["PositionSizeValue"] <= 0 or v["CapitalBaseR"] < 0 or v["MaxRiscoTradeR"] < 0):
        e.append("inputs Fixed-R invalidos")
    if (mart or grid) and v["Multiplicador"] <= 0:
        e.append("Multiplicador <= 0 com Martingale/Grid")
    if dal and (not fixo or grid or v["DAlembertStep"] <= 0):
        e.append("D'Alembert exige Fixed Lot, Grid desligado e passo > 0")
    if grid:
        if not pyr and (pct or rfix or (not mon and not fixo)):
            e.append("Grid classico so aceita Monetary ou Fixed Lot")
        if v["RecoveryMode"] != 0:
            e.append("Grid e recovery nao combinam")
        if not hedging_account:
            e.append("Grid exige conta hedging")
        if v["DistanciaMinima"] <= 0:
            e.append("Grid exige DistanciaMinima > 0")
        if pyr:
            if not v["AtivarTrailATR"]:
                e.append("Pirâmide exige trailing ATR ligado")
        elif not v["AtivarTake"]:
            e.append("Grid exige Take Profit")
        if v["MaxLongTrades"] == 1 or v["MaxShortTrades"] == 1:
            e.append("Com Grid cada limite de lado deve ser 0 ou >= 2")
    if v["Hedging"] and not hedging_account:
        e.append("Hedging=true exige conta hedging")
    if v["ReversalExitMode"] == 1 and (not v["Hedging"] or not hedging_account or v["MaxLongTrades"] == 0
                                       or v["MaxShortTrades"] == 0 or grid):
        e.append("saida por ordem oposta exige bilateral, hedging e grid desligado")
    if v["MaxLongTrades"] < 0 or v["MaxShortTrades"] < 0 or v["MaxSlippage"] < 0:
        e.append("limites negativos")
    if not (0 <= v["TOD_From_Hour"] <= 23 and 0 <= v["TOD_To_Hour"] <= 23
            and 0 <= v["TOD_From_Min"] <= 59 and 0 <= v["TOD_To_Min"] <= 59):
        e.append("filtro de horario invalido")
    if v["AtivarBreakeven"] and v["BreakevenDistancia"] <= 0:
        e.append("BreakevenDistancia <= 0")
    if v["PendingGatilho"] == 1 and (v["EntryOrderType"] == 0 or not 0 <= v["PendingHoraSessao"] <= 23
                                     or v["PendingFaixaBarras"] < 1):
        e.append("gatilho de sessao invalido")
    if v["EntryOrderType"] != 0 and (v["PendingExpiracaoBarras"] < 1 or v["PendingDistanciaATR"] < 0):
        e.append("entrada pendente invalida")
    return e


def unsupported(d: dict[str, str]) -> list[str]:
    """O que esta LIGADO no set e o motor ainda nao porta (a lista vai encolhendo a cada fase)."""
    v = {k: (_coerce(dflt, d[k]) if k in d else dflt) for k, dflt in _DEFAULTS.items()}
    m: list[str] = []
    if not 0 <= v["EntryIndicator"] <= 11:
        m.append(f"EntryIndicator={v['EntryIndicator']} invalido")
    if v["ReversalExitMode"] not in (0, 1, 2):
        m.append(f"ReversalExitMode={v['ReversalExitMode']} invalido")
    if v["AtivarWFO"] and v["MetodoDeEntradawfo"] == 0:
        m.append("AtivarWFO=true com 'In Sample' (janelas IS/OOS ainda nao portadas)")
    return m


def load_set(path: str | Path, *, strict: bool = True) -> WrxParams:
    d = parse_set_text(read_set_text(path))
    if strict:
        motivos = unsupported(d)
        if motivos:
            raise UnsupportedConfig(motivos)
    return params_from_dict(d)


def params_from_text(text: str, *, strict: bool = True) -> WrxParams:
    d = parse_set_text(text)
    if strict:
        motivos = unsupported(d)
        if motivos:
            raise UnsupportedConfig(motivos)
    return params_from_dict(d)


__all__ = ["WrxParams", "UnsupportedConfig", "InvalidConfig", "oninit_errors", "load_set", "params_from_text",
           "parse_set_text", "read_set_text", "unsupported"]
