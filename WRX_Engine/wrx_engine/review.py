"""Lista de revisao guiada pelos inputs declarados da EA.

Tres comandos:

  python -m wrx_engine.review checklist [--out REVISAO_INPUTS.md]
      Tabela de TODOS os inputs: status no motor, nota e as sondas que os exercitam.

  python -m wrx_engine.review probes --baseline algum.set --out sondas/ [--ticks t.csv --spec s.json --warmup w.csv]
      Gera um .set por sonda (baseline seguro + UM recurso ligado) e `plano_de_teste.md`. Com --ticks/--spec,
      roda o motor e anota quantos trades/quanto R ele espera de cada sonda.

  python -m wrx_engine.review run --baseline algum.set --reports relatorios/ --ticks t.csv --spec s.json [--warmup w.csv]
      Para cada sonda com `relatorios/<id>.htm` (relatorio do Tester), roda o motor e compara trade a trade.
      Escreve REVISAO_INPUTS.md: PASS/FAIL por sonda e o veredito consolidado POR INPUT.

  python -m wrx_engine.review sync --ea "White Rabbit X (Global Multi-Indicator).mq5"
      Confere os `input` do .mq5 contra o registro (rode na sua maquina; acusa input novo sem status).

Roteiro no Tester: um relatorio por sonda, MESMO simbolo/periodo/deposito, "Every tick based on real ticks",
conta HEDGING se for usar a sonda com dois lados. Salve como `relatorios/<id>.htm`.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import registry as R
from .setfile import oninit_errors, params_from_dict, parse_set_text, read_set_text, unsupported

# ------------------------------------------------------------------ baseline seguro (tudo desligado que o motor nao porta)
BASE: dict[str, object] = {
    "AtivarWFO": "false", "MetodoDeEntradawfo": 1, "PositionSizeMode": 3, "PositionSizeValue": 1,
    "CapitalBaseR": 500, "TradeCapitalPercentage": 100, "MaxRiscoTradeR": 0, "MaxRiscoRelativoAoLoteMinimo": 1.5,
    "DailyLossLimitPercent": 0, "MaxEquityDrawdownPercent": 0, "MinFreeMarginPercent": 0,
    "Trava_Diaria_Percent": 0, "Trava_Total_Percent": 0, "RecoveryMode": 0, "GridMode": 0,
    "EntryOrderType": 0, "PendingGatilho": 0, "AtivarFiltroNoticias": "false", "AtivarTrailATR": "false",
    "TakeOrganico": "false", "ReversalExitMode": 0, "ReversalExitUseEntryFilters": "false",
    "Fecharordensforadohorario": "false", "AtivarFiltroMTF": "false", "AtivarFiltroMA": "false",
    "AtivarFiltroADX": "false", "EntradaATR": "false", "EntryIndicator": 0, "EntryMethod": 6,
    "Fast_EMA": 12, "Slow_EMA": 26, "MACD_SMA": 9, "TimeFrame": 0, "ATR_TimeFrame": 0, "PeriodoATR": 14,
    "InpAppliedPrice": 1, "AtivarStop": "true", "VelaStop": 0, "Stop": 3, "AtivarTake": "true", "VelaTake": 0,
    "Take": 3, "AtivarBreakeven": "false", "BreakevenDistancia": 0.5, "MaxLongTrades": 1, "MaxShortTrades": 0,
    "Hedging": "false", "MaxSpread": 0, "TOD_From_Hour": 0, "TOD_From_Min": 0, "TOD_To_Hour": 23, "TOD_To_Min": 55,
    "TradeMonday": "true", "TradeTuesday": "true", "TradeWednesday": "true", "TradeThursday": "true",
    "TradeFriday": "true", "TradeSaturday": "false", "TradeSunday": "false", "ModificationSafetyPoints": 0,
    "StochasticSlowing": 3, "StochasticMethod": 0, "StochasticPriceField": 0,
    "IchimokuUseKumo": "true", "IchimokuChikouFilter": "false",
    "TakeOrganico": "false", "AtivarTrailATR": "false", "MetodoDeCalculo": 1, "TrailVela": 0, "Trail": 3,
    "TrailSoLucro": "false", "Multiplicador": 1, "MaxMartingaleSteps": 0, "MaxMartingaleLot": 0,
    "DAlembertStep": 0.01, "UsarsomenteATRGRID": "false", "DistanciaMinima": 2, "PyramidTrailSoLucro": "false",
    "PyramidLevelOnlyInProfit": "false", "PendingReferencia": 0, "PendingDistanciaATR": 0.5,
    "PendingExpiracaoBarras": 3, "PendingHoraSessao": 8, "PendingFaixaBarras": 4, "Protecao_Fecha_Posicoes": "true",
    "NewsMinutosAntes": 15, "NewsMinutosDepois": 15, "NewsSomenteAltoImpacto": "false",
}


@dataclass(frozen=True)
class Probe:
    id: str
    title: str
    over: dict
    inputs: tuple[str, ...]
    needs_hedging: bool = False


def _p(id_, title, over, inputs=None, hedging=False) -> Probe:
    return Probe(id_, title, over, tuple(inputs if inputs is not None else over.keys()), hedging)


_IND = {1: ("EMA cruzamento", dict(Fast_EMA=9, Slow_EMA=21, MACD_SMA=5)),
        2: ("Momentum", dict(Fast_EMA=14, MACD_SMA=5)), 3: ("Stochastic", dict(Fast_EMA=5, MACD_SMA=3)),
        4: ("TRIX", dict(Fast_EMA=9, MACD_SMA=5)), 5: ("RSI", dict(Fast_EMA=14, MACD_SMA=5)),
        6: ("CCI", dict(Fast_EMA=14, MACD_SMA=5)), 7: ("Williams %R", dict(Fast_EMA=14, MACD_SMA=5)),
        8: ("DeMarker", dict(Fast_EMA=14, MACD_SMA=5)), 9: ("MFI", dict(Fast_EMA=14, MACD_SMA=5)),
        10: ("OsMA", dict(Fast_EMA=12, Slow_EMA=26, MACD_SMA=9)),
        11: ("Ichimoku (nuvem)", dict(Fast_EMA=9, Slow_EMA=26, MACD_SMA=52))}

PROBES: list[Probe] = [
    _p("P00_base", "Baseline: MACD, TF M1, Fixed-R, SL/TP 3xATR, so compra", {}, ["EntryIndicator", "PositionSizeMode",
       "PositionSizeValue", "CapitalBaseR", "TradeCapitalPercentage", "Stop", "Take", "AtivarStop", "AtivarTake",
       "PeriodoATR", "MaxRiscoRelativoAoLoteMinimo", "Fast_EMA", "Slow_EMA", "MACD_SMA", "EntryMethod", "InpAppliedPrice"]),
    _p("P01_sell", "So venda", dict(MaxLongTrades=0, MaxShortTrades=1)),
    _p("P02_both_hedge", "Compra e venda, conta hedging", dict(MaxLongTrades=1, MaxShortTrades=1, Hedging="true"), hedging=True),
    _p("P03_breakeven", "Breakeven", dict(AtivarBreakeven="true", BreakevenDistancia=1)),
    _p("P04_tf_m5", "Sinal em M5", dict(TimeFrame=1)), _p("P05_tf_m15", "Sinal em M15", dict(TimeFrame=2)),
    _p("P06_tf_h1", "Sinal em H1", dict(TimeFrame=4)),
    _p("P07_atr_m5", "ATR em M5", dict(ATR_TimeFrame=1)),
    _p("P08_velas", "Vela do ATR: SL=1, TP=2", dict(VelaStop=1, VelaTake=2)),
    _p("P09_atr_period", "Periodo do ATR 7", dict(PeriodoATR=7)),
    _p("P10_no_take", "Sem take profit", dict(AtivarTake="false")),
    _p("P11_maxrisk", "Teto de risco 0.5R", dict(MaxRiscoTradeR=0.5)),
    _p("P12_small_capital", "Capital pequeno (lote minimo / guarda 1.5x)", dict(CapitalBaseR=50)),
    _p("P13_no_guard", "Sem guarda anti-oversizing", dict(CapitalBaseR=50, MaxRiscoRelativoAoLoteMinimo=0)),
    _p("P14_price_low", "Applied price = Low", dict(InpAppliedPrice=4)),
    _p("P15_price_weighted", "Applied price = Weighted", dict(InpAppliedPrice=7)),
]
for i, (name, extra) in _IND.items():
    over = dict(EntryIndicator=i, **extra)
    PROBES.append(_p(f"P{20 + i:02d}_ind_{i:02d}", f"Indicador: {name}", over))
PROBES += [
    _p(f"P{40 + m}_method_{m}", f"EntryMethod={m}", dict(EntryMethod=m)) for m in range(6)
] + [
    _p("P47_ichi_no_kumo", "Ichimoku sem nuvem (preco x Kijun)", dict(EntryIndicator=11, Fast_EMA=9, Slow_EMA=26,
       MACD_SMA=52, IchimokuUseKumo="false")),
    _p("P48_ichi_chikou", "Ichimoku com filtro Chikou", dict(EntryIndicator=11, Fast_EMA=9, Slow_EMA=26, MACD_SMA=52,
       IchimokuChikouFilter="true")),
    _p("P49_stoch_close", "Stochastic Close/Close + %D EMA", dict(EntryIndicator=3, Fast_EMA=5, MACD_SMA=3,
       StochasticPriceField=1, StochasticMethod=1, StochasticSlowing=1)),
    _p("P50_mtf_any", "MTF: basta um TF superior alinhado", dict(AtivarFiltroMTF="true", MTF_RequererAmbos="false")),
    _p("P51_mtf_both", "MTF: os dois alinhados", dict(AtivarFiltroMTF="true", MTF_RequererAmbos="true")),
    _p("P52_ma_price_slope", "MA: preco E inclinacao", dict(AtivarFiltroMA="true", MA_Period=100, MetodoMA=2)),
    _p("P53_ma_price", "MA: so preco", dict(AtivarFiltroMA="true", MA_Period=100, MetodoMA=0)),
    _p("P54_ma_slope", "MA: so inclinacao", dict(AtivarFiltroMA="true", MA_Period=100, MetodoMA=1)),
    _p("P55_ma_or", "MA: preco OU inclinacao, reversao", dict(AtivarFiltroMA="true", MA_Period=100, MetodoMA=3, SentidoMA=1)),
    _p("P56_ma_sma_h1", "MA SMA em M15", dict(AtivarFiltroMA="true", MA_TimeFrame=2, MA_Period=50, MA_Method=0)),
    _p("P57_adx", "ADX so forca", dict(AtivarFiltroADX="true", ADX_Limiar=20, MetodoADX=0)),
    _p("P58_adx_di", "ADX + direcao DI", dict(AtivarFiltroADX="true", ADX_Limiar=20, MetodoADX=1)),
    _p("P59_vol_high", "Volatilidade alta", dict(EntradaATR="true", VolatilityFilter=1)),
    _p("P60_vol_low", "Volatilidade baixa", dict(EntradaATR="true", VolatilityFilter=0)),
    _p("P61_hours", "Janela 08:00-12:00", dict(TOD_From_Hour=8, TOD_To_Hour=12, TOD_To_Min=0)),
    _p("P62_hours_overnight", "Janela noturna 22:00-06:00", dict(TOD_From_Hour=22, TOD_To_Hour=6, TOD_To_Min=0)),
    _p("P63_no_friday", "Sem sexta", dict(TradeFriday="false")),
    _p("P64_spread", "MaxSpread=20", dict(MaxSpread=20)),
    _p("P65_reversal_exit", "Saida por sinal contrario (dois lados)", dict(ReversalExitMode=2, MaxLongTrades=1,
       MaxShortTrades=1, Hedging="true"), hedging=True),
    _p("P66_reversal_exit_filters", "Saida por sinal contrario respeitando filtros", dict(ReversalExitMode=2,
       ReversalExitUseEntryFilters="true", AtivarFiltroMA="true", MA_Period=100, MaxLongTrades=1, MaxShortTrades=1,
       Hedging="true"), hedging=True),
    _p("P67_close_outside", "Fecha posicoes fora do horario", dict(Fecharordensforadohorario="true", TOD_From_Hour=8,
       TOD_To_Hour=12, TOD_To_Min=0)),
    _p("P69_ma_price_lookback", "MA: applied price Low + lookback 10", dict(AtivarFiltroMA="true", MA_Period=100,
       MA_AppliedPrice=4, MA_SlopeLookback=10, MetodoMA=2)),
    _p("P70_adx_tf_period", "ADX em M15 periodo 7", dict(AtivarFiltroADX="true", ADX_TimeFrame=2, ADX_Period=7, ADX_Limiar=20)),
    _p("P71_vol_mult_baseline", "Volatilidade: mult 1.2, baseline 60", dict(EntradaATR="true", VolatilityFilter=1,
       MultiplicadorATR=1.2, PeriodoBaselineATR=60)),
    _p("P72_hours_minutes", "Janela 08:30-11:45", dict(TOD_From_Hour=8, TOD_From_Min=30, TOD_To_Hour=11, TOD_To_Min=45)),
    _p("P73_monday_only", "So segunda", dict(TradeMonday="true", TradeTuesday="false", TradeWednesday="false",
       TradeThursday="false", TradeFriday="false")),
    _p("P74_weekend_days", "Sabado e domingo liberados (mercado fechado: nao deve mudar nada)", dict(TradeSaturday="true",
       TradeSunday="true", TradeTuesday="false", TradeThursday="false")),
    _p("P75_wfo_in_plus_out", "WFO ligado em 'In Sample + Out Sample' (nao deve bloquear entradas)", dict(AtivarWFO="true",
       MetodoDeEntradawfo=1)),
    _p("P68_safety_points", "ModificationSafetyPoints=30 (com breakeven)", dict(AtivarBreakeven="true",
       ModificationSafetyPoints=30)),
]

_GRID = dict(GridMode=1, PositionSizeMode=2, PositionSizeValue=0.01, AtivarStop="false", AtivarTake="true",
             Hedging="true", MaxLongTrades=6, MaxShortTrades=0, AtivarBreakeven="true", DistanciaMinima=2)
_PYR = dict(GridMode=3, PositionSizeMode=2, PositionSizeValue=0.05, AtivarStop="true", Stop=4, AtivarTake="false",
            AtivarTrailATR="true", Trail=2, Hedging="true", MaxLongTrades=6, MaxShortTrades=0, Multiplicador=0.7,
            DistanciaMinima=2, AtivarBreakeven="false")
PROBES += [
    # ---- lote
    _p("P80_fixed_lot", "Lote fixo 0.05 com SL/TP", dict(PositionSizeMode=2, PositionSizeValue=0.05)),
    _p("P81_monetary", "Monetary: 1 lote por 10000 de capital inicial", dict(PositionSizeMode=1, PositionSizeValue=10000)),
    _p("P82_percentage", "Percentage: 1% do saldo ao vivo", dict(PositionSizeMode=0, PositionSizeValue=1)),
    _p("P83_signal_only", "Sinal puro: sem SL/TP, sai no sinal contrario (dois lados)", dict(PositionSizeMode=2,
       PositionSizeValue=0.05, AtivarStop="false", AtivarTake="false", AtivarBreakeven="false", ReversalExitMode=2,
       MaxLongTrades=1, MaxShortTrades=1, Hedging="true"), hedging=True),
    # ---- recovery
    _p("P84_martingale_fixed", "Martingale, lote fixo x2", dict(PositionSizeMode=2, PositionSizeValue=0.02,
       RecoveryMode=1, Multiplicador=2)),
    _p("P85_martingale_monetary", "Martingale monetario com take (recupera a divida no TP)", dict(PositionSizeMode=1,
       PositionSizeValue=10000, RecoveryMode=1, Multiplicador=1)),
    _p("P86_martingale_pct", "Martingale percentual", dict(PositionSizeMode=0, PositionSizeValue=1, RecoveryMode=1,
       Multiplicador=1)),
    _p("P87_martingale_fixedr", "Martingale em R com teto 3R", dict(PositionSizeMode=3, RecoveryMode=1, Multiplicador=1,
       MaxRiscoTradeR=3)),
    _p("P88_martingale_limits", "Martingale com MaxMartingaleSteps=3 e MaxMartingaleLot=0.08", dict(PositionSizeMode=2,
       PositionSizeValue=0.02, RecoveryMode=1, Multiplicador=2, MaxMartingaleSteps=3, MaxMartingaleLot=0.08)),
    _p("P89_dalembert", "D'Alembert passo 0.01, teto 0.06", dict(PositionSizeMode=2, PositionSizeValue=0.02,
       RecoveryMode=2, DAlembertStep=0.01, MaxMartingaleLot=0.06)),
    # ---- saidas
    _p("P90_trail_close", "Trailing ATR (preco de fechamento), sem TP", dict(AtivarTrailATR="true", AtivarTake="false")),
    _p("P91_trail_open", "Trailing sobre a abertura do candle", dict(AtivarTrailATR="true", AtivarTake="false", MetodoDeCalculo=0)),
    _p("P92_trail_high", "Trailing sobre a maxima", dict(AtivarTrailATR="true", AtivarTake="false", MetodoDeCalculo=2)),
    _p("P93_trail_low", "Trailing sobre a minima", dict(AtivarTrailATR="true", AtivarTake="false", MetodoDeCalculo=3)),
    _p("P94_trail_price", "Trailing sobre o preco (bid/ask)", dict(AtivarTrailATR="true", AtivarTake="false", MetodoDeCalculo=4)),
    _p("P95_trail_profit_only", "Trailing so no lucro", dict(AtivarTrailATR="true", AtivarTake="false", TrailSoLucro="true")),
    _p("P96_trail_vela", "Trailing com ATR da vela 2 e Trail=2", dict(AtivarTrailATR="true", AtivarTake="false", TrailVela=2, Trail=2)),
    _p("P97_sltp_trail", "SL + TP + trailing + breakeven", dict(AtivarTrailATR="true", AtivarTake="true", AtivarBreakeven="true")),
    _p("P98_organic_take", "Take organico junto com TP", dict(TakeOrganico="true", AtivarTake="true")),
    _p("P99_reversal_opposite", "Saida por ordem oposta (hedging, dois lados)", dict(ReversalExitMode=1, MaxLongTrades=1,
       MaxShortTrades=1, Hedging="true"), hedging=True),
    # ---- grid classico
    _p("P100_grid_fixed", "Grid classico, lote fixo", dict(_GRID), hedging=True),
    _p("P101_grid_monetary", "Grid classico, monetary", dict(_GRID, PositionSizeMode=1, PositionSizeValue=10000), hedging=True),
    _p("P102_grid_atr_only", "Grid: continua so pelo ATR (sem sinal)", dict(_GRID, UsarsomenteATRGRID="true"), hedging=True),
    _p("P103_grid_stop", "Grid com SL por perna", dict(_GRID, AtivarStop="true"), hedging=True),
    _p("P104_grid_mult", "Grid com Multiplicador 1.5 no alvo", dict(_GRID, Multiplicador=1.5), hedging=True),
    _p("P105_grid_distance", "Grid com DistanciaMinima=3", dict(_GRID, DistanciaMinima=3), hedging=True),
    _p("P106_grid_both", "Grid nos dois lados", dict(_GRID, MaxLongTrades=4, MaxShortTrades=4), hedging=True),
    # ---- piramide (12_GRID_INVERSO)
    _p("P107_pyr_fixed", "Piramide, lote fixo", dict(_PYR), hedging=True),
    _p("P108_pyr_fixedr", "Piramide em Fixed-R", dict(_PYR, PositionSizeMode=3, PositionSizeValue=1), hedging=True),
    _p("P109_pyr_pct", "Piramide percentual", dict(_PYR, PositionSizeMode=0, PositionSizeValue=1), hedging=True),
    _p("P110_pyr_level_profit", "Piramide: proximo nivel so com a ultima perna no empate", dict(_PYR,
       PyramidLevelOnlyInProfit="true"), hedging=True),
    _p("P111_pyr_trail_profit", "Piramide: trailing da cesta so no lucro", dict(_PYR, PyramidTrailSoLucro="true"), hedging=True),
    # ---- entradas pendentes
    _p("P112_pend_stop", "Entrada Stop", dict(EntryOrderType=1)),
    _p("P113_pend_limit", "Entrada Limit", dict(EntryOrderType=2)),
    _p("P114_pend_oco", "Entrada OCO (hedging, dois lados)", dict(EntryOrderType=3, MaxLongTrades=1, MaxShortTrades=1,
       Hedging="true"), hedging=True),
    _p("P115_pend_extreme", "Pendente ancorada na maxima/minima do candle, distancia 1 ATR", dict(EntryOrderType=1,
       PendingReferencia=1, PendingDistanciaATR=1.0)),
    _p("P116_pend_expiry", "Pendente expira em 1 barra", dict(EntryOrderType=1, PendingExpiracaoBarras=1)),
    _p("P117_pend_session", "Rompimento por sessao as 08h, faixa de 4 barras", dict(EntryOrderType=3, PendingGatilho=1,
       PendingHoraSessao=8, PendingFaixaBarras=4, MaxLongTrades=1, MaxShortTrades=1, Hedging="true"), hedging=True),
    # ---- travas
    _p("P118_daily_loss", "DailyLossLimitPercent=0.5", dict(DailyLossLimitPercent=0.5)),
    _p("P119_equity_dd", "MaxEquityDrawdownPercent=2", dict(MaxEquityDrawdownPercent=2)),
    _p("P120_gp_daily", "Protecao global diaria 1% (fecha tudo)", dict(Trava_Diaria_Percent=1)),
    _p("P121_gp_total_noclose", "Protecao global total 3% sem fechar (so bloqueia)", dict(Trava_Total_Percent=3,
       Protecao_Fecha_Posicoes="false")),
    _p("P122_news", "Filtro de noticias USD/EUR (precisa do CSV em Common\\Files)", dict(AtivarFiltroNoticias="true",
       NewsMoedasManual="USD,EUR")),
    _p("P125_news_window", "Noticias: so alto impacto, janela 30 antes / 5 depois", dict(AtivarFiltroNoticias="true",
       NewsMoedasManual="USD,EUR", NewsSomenteAltoImpacto="true", NewsMinutosAntes=30, NewsMinutosDepois=5,
       NewsCSVFile="WhiteRabbit_News.csv")),
    _p("P123_min_free_margin", "Reserva de margem livre 50% (precisa margin_a/margin_b no spec)", dict(MinFreeMarginPercent=50)),
    _p("P124_wfo_in_sample", "WFO 'In Sample': 122 dias IS + 61 OOS (ajuste input_end_date ao fim do teste)", dict(
       AtivarWFO="true", MetodoDeEntradawfo=0, wfo_windowSize=-1, wfo_customWindowSizeDays=122, wfo_stepSize=-1,
       wfo_customStepSizePercent=-61, WFO_CarenciaPercentil=0), ["AtivarWFO", "MetodoDeEntradawfo", "wfo_windowSize",
       "wfo_customWindowSizeDays", "wfo_stepSize", "wfo_customStepSizePercent", "WFO_CarenciaPercentil", "input_end_date"]),
]
_IDS = [p.id for p in PROBES]
assert len(_IDS) == len(set(_IDS)), "ids de sonda duplicados"


# ------------------------------------------------------------------ geracao dos .set
def merged(baseline: dict[str, str], probe: Probe) -> dict[str, str]:
    d = dict(baseline)
    d.update({k: str(v) for k, v in BASE.items()})
    d.update({k: str(v) for k, v in probe.over.items()})
    return d


def write_set(path: Path, values: dict[str, str], title: str) -> None:
    lines = [f"; WRX_Engine - sonda de revisao: {title}", "; carregue em Inputs -> Load. Valores fixos (sem otimizacao).",
             f"NomedaEstrategia=WRX probe {title}"]
    lines += [f"{k}={v}" for k, v in values.items() if k != "NomedaEstrategia"]
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-16"))


def make_probes(baseline_path: str | Path, out_dir: str | Path) -> list[Path]:
    base = parse_set_text(read_set_text(baseline_path))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for pr in PROBES:
        d = merged(base, pr)
        bad = unsupported(d)
        if bad:
            raise RuntimeError(f"sonda {pr.id} usa algo que o motor recusa: {bad}")
        oi = oninit_errors(params_from_dict(d).v, hedging_account=True)
        if oi:
            raise RuntimeError(f"sonda {pr.id} seria recusada pelo OnInit do EA: {oi}")
        p = out / f"{pr.id}.set"
        write_set(p, d, pr.title)
        paths.append(p)
    return paths


# ------------------------------------------------------------------ checklist
def probes_by_input() -> dict[str, list[str]]:
    m: dict[str, list[str]] = {}
    for pr in PROBES:
        for i in pr.inputs:
            m.setdefault(i, []).append(pr.id)
    return m


def checklist_markdown(verdicts: dict[str, str] | None = None) -> str:
    """verdicts: id_da_sonda -> PASS/FAIL. Sem ele, a coluna 'Veredito' mostra so o que falta rodar."""
    by_in = probes_by_input()
    names = list(R.REGISTRY)
    order = {R.PORTED: 0, R.PARTIAL: 1, R.DEFERRED: 2, R.INERT: 3, R.UI: 4}
    names.sort(key=lambda n: (order.get(R.REGISTRY[n].status, 9), n.lower()))
    rows = ["| Input | Status | Sondas | Veredito | Nota |", "|---|---|---|---|---|"]
    for n in names:
        info = R.REGISTRY[n]
        ps = by_in.get(n, [])
        if info.status in (R.PORTED, R.PARTIAL):
            if not ps:
                v = "SEM SONDA"
            elif verdicts is None:
                v = "a testar"
            else:
                got = [verdicts.get(p) for p in ps]
                v = "FAIL" if "FAIL" in got else ("PASS" if all(g == "PASS" for g in got) else
                                                   "PASS parcial" if "PASS" in got else "sem relatorio")
        elif info.status == R.DEFERRED:
            v = "nao portado"
        else:
            v = "-"
        rows.append(f"| `{n}` | {info.status} | {', '.join(ps) or '-'} | {v} | {info.note} |")
    return "\n".join(rows)


def _header(verdicts) -> str:
    n = len(R.REGISTRY)
    cnt = {s: sum(1 for i in R.REGISTRY.values() if i.status == s) for s in (R.PORTED, R.PARTIAL, R.DEFERRED, R.INERT, R.UI)}
    txt = (f"# Revisao de inputs - WRX Engine\n\n{n} inputs classificados: "
           + ", ".join(f"{k} {v}" for k, v in cnt.items()) + ".\n\n")
    if verdicts:
        p = sum(v == "PASS" for v in verdicts.values())
        txt += f"Sondas com relatorio: {len(verdicts)} ({p} PASS, {len(verdicts) - p} FAIL) de {len(PROBES)}.\n\n"
    txt += ("**PORTED nao quer dizer verificado**: so a paridade com o Tester (`Veredito`) verifica. "
            "`DEFERRED` = o motor recusa o set se o input estiver ligado.\n\n")
    return txt


# ------------------------------------------------------------------ execucao
def _load_frame(path):
    import pandas as pd
    return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path)


def run_probes(baseline, ticks_path, spec_path, warmup_path=None, reports=None, out_dir=None, deposit=10_000.0,
               news_csv=None):
    """Roda o motor em cada sonda; se houver relatorio, compara. Devolve dict id -> dict(resumo)."""
    from .bars import Bars, Ticks
    from .engine import load_news_csv, run_backtest
    from .parity import compare, deals_to_trades, parse_deals_html
    from .setfile import params_from_dict
    from .spec import SymbolSpec

    ticks = Ticks.from_frame(_load_frame(ticks_path))
    spec = SymbolSpec.from_json(spec_path)
    warm = Bars.from_frame(_load_frame(warmup_path)) if warmup_path else None
    base = parse_set_text(read_set_text(baseline))
    results = {}
    for pr in PROBES:
        params = params_from_dict(merged(base, pr))
        news = load_news_csv(news_csv, params.v["NewsSomenteAltoImpacto"]) if (news_csv and params.v["AtivarFiltroNoticias"]) else None
        try:
            res = run_backtest(params, spec, ticks, warmup_m1=warm, deposit=deposit, news_events=news)
        except Exception as e:                      # InvalidConfig etc: a sonda nao se aplica a este periodo/conta
            results[pr.id] = {"trades": 0, "net_r": 0.0, "skipped": {}, "verdict": "N/A", "detail": str(e)}
            continue
        row = {"trades": len(res.trades) + len(res.open_positions), "net_r": float(res.trades["r"].sum()) if len(res.trades) else 0.0,
               "skipped": dict(res.skipped)}
        if reports:
            rep = next((Path(reports) / f"{pr.id}{ext}" for ext in (".htm", ".html") if (Path(reports) / f"{pr.id}{ext}").exists()), None)
            if rep is not None:
                cmp_ = compare(res.trades, deals_to_trades(parse_deals_html(rep)))
                row.update(verdict="PASS" if cmp_.passed else "FAIL", detail=cmp_.text())
        results[pr.id] = row
    return results


def plan_markdown(results=None) -> str:
    out = ["# Plano de teste - sondas", "",
           "Para cada sonda: carregue o `.set`, rode o Tester (mesmo simbolo/periodo/deposito, Every tick based on real ticks), "
           "salve o relatorio como `relatorios/<id>.htm`. As marcadas **hedging** exigem conta hedging.", "",
           "| Sonda | O que muda | Hedging | Motor espera (trades / R) |", "|---|---|---|---|"]
    for pr in PROBES:
        exp = "-"
        if results and pr.id in results:
            r = results[pr.id]
            exp = f"{r['trades']} / {r['net_r']:+.1f}R"
        out.append(f"| `{pr.id}` | {pr.title} | {'sim' if pr.needs_hedging else ''} | {exp} |")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ sync com o .mq5
_INPUT_RE = re.compile(r"^\s*input\s+(?!group\b)[\w:<>\s]+?\s+(\w+)\s*(?:=|;)", re.M)


def ea_inputs(mq5_path: str | Path) -> list[str]:
    raw = Path(mq5_path).read_bytes()
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeError:
            continue
    return _INPUT_RE.findall(txt)


def sync_report(mq5_path) -> str:
    inp = ea_inputs(mq5_path)
    miss = [n for n in inp if R.lookup(n).status == "UNKNOWN"]
    extra = [n for n in R.REGISTRY if n not in set(inp)]
    lines = [f"{len(inp)} inputs no .mq5; {len(miss)} sem status no registro; {len(extra)} no registro ausentes do .mq5."]
    if miss:
        lines.append("SEM STATUS (classifique em registry.py): " + ", ".join(miss))
    if extra:
        lines.append("no registro mas NAO no .mq5 (renomeado/removido?): " + ", ".join(extra))
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("checklist"); c.add_argument("--out")
    pr = sub.add_parser("probes"); pr.add_argument("--baseline", required=True); pr.add_argument("--out", required=True)
    pr.add_argument("--ticks"); pr.add_argument("--spec"); pr.add_argument("--warmup")
    pr.add_argument("--deposit", type=float, default=10_000.0)
    rn = sub.add_parser("run"); rn.add_argument("--baseline", required=True); rn.add_argument("--reports", required=True)
    rn.add_argument("--ticks", required=True); rn.add_argument("--spec", required=True); rn.add_argument("--warmup")
    rn.add_argument("--out", default="REVISAO_INPUTS.md")
    rn.add_argument("--deposit", type=float, default=10_000.0, help="deposito do Tester")
    rn.add_argument("--news-csv", help="CSV de noticias (mesmo de Common\\Files) para a sonda P122")
    sy = sub.add_parser("sync"); sy.add_argument("--ea", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "checklist":
        txt = _header(None) + checklist_markdown()
        Path(a.out).write_text(txt, encoding="utf-8") if a.out else print(txt)
    elif a.cmd == "probes":
        paths = make_probes(a.baseline, a.out)
        res = run_probes(a.baseline, a.ticks, a.spec, a.warmup, deposit=a.deposit) if a.ticks and a.spec else None
        (Path(a.out) / "plano_de_teste.md").write_text(plan_markdown(res), encoding="utf-8")
        print(f"{len(paths)} sondas em {a.out} + plano_de_teste.md")
    elif a.cmd == "run":
        res = run_probes(a.baseline, a.ticks, a.spec, a.warmup, a.reports, deposit=a.deposit, news_csv=a.news_csv)
        verd = {k: v["verdict"] for k, v in res.items() if "verdict" in v}
        body = _header(verd) + "## Por input\n\n" + checklist_markdown(verd) + "\n\n## Por sonda\n\n"
        for k, v in res.items():
            body += f"### {k} - {v.get('verdict', 'sem relatorio')}\nmotor: {v['trades']} trades, {v['net_r']:+.1f}R; recusas {v['skipped']}\n"
            if "detail" in v and v["verdict"] == "FAIL":
                body += "```\n" + v["detail"] + "\n```\n"
        Path(a.out).write_text(body, encoding="utf-8")
        print(f"{len(verd)} relatorios comparados; escrito {a.out}")
        return 0 if all(x == "PASS" for x in verd.values()) else 1
    elif a.cmd == "sync":
        print(sync_report(a.ea))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
