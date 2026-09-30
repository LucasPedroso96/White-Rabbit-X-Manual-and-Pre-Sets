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
        raw=dict(d) | {k: v[k] for k in _DEFAULTS},
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


def unsupported(d: dict[str, str]) -> list[str]:
    """Tudo que esta LIGADO no set e o motor (passo 1: 01_SLTP + MACD, Fixed-R) nao porta."""
    v = {k: (_coerce(dflt, d[k]) if k in d else dflt) for k, dflt in _DEFAULTS.items()}
    m: list[str] = []
    if not 0 <= v["EntryIndicator"] <= 11:
        m.append(f"EntryIndicator={v['EntryIndicator']} invalido")
    if v["PositionSizeMode"] != 3:
        m.append(f"PositionSizeMode={_SIZE_MODE[v['PositionSizeMode']]} (so FixedR)")
    if v["PositionSizeMode"] == 3 and not v["AtivarStop"]:
        m.append("FixedR exige AtivarStop=true (o EA recusa no OnInit)")
    if v["RecoveryMode"] != 0:
        m.append("RecoveryMode != None (Martingale/D'Alembert)")
    if v["GridMode"] != 0:
        m.append("GridMode != Disabled")
    if v["AtivarTrailATR"]:
        m.append("AtivarTrailATR (trailing)")
    if v["TakeOrganico"]:
        m.append("TakeOrganico")
    if v["ReversalExitMode"] == 1:
        m.append("ReversalExitMode=OnOppositeOrder (fecha ao abrir posicao oposta; exige conta hedge)")
    elif v["ReversalExitMode"] not in (0, 2):
        m.append(f"ReversalExitMode={v['ReversalExitMode']} invalido")
    for k in ("AtivarFiltroNoticias",):
        if v[k]:
            m.append(f"{k}=true")
    for k in ("DailyLossLimitPercent", "MaxEquityDrawdownPercent", "MinFreeMarginPercent",
              "Trava_Diaria_Percent", "Trava_Total_Percent"):
        if v[k]:
            m.append(f"{k}={v[k]} (travas de conta/margem nao portadas; zere no set)")
    if v["EntryOrderType"] != 0 or v["PendingGatilho"] != 0:
        m.append("entrada pendente (Stop/Limit/OCO/sessao)")
    if v["AtivarWFO"] and v["MetodoDeEntradawfo"] == 0:
        m.append("AtivarWFO=true com 'In Sample' (bloqueia entrada fora da janela IS)")
    if v["MaxRiscoTradeR"] < 0 or v["CapitalBaseR"] < 0:
        m.append("inputs Fixed-R invalidos")
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


__all__ = ["WrxParams", "UnsupportedConfig", "load_set", "params_from_text",
           "parse_set_text", "read_set_text", "unsupported"]
