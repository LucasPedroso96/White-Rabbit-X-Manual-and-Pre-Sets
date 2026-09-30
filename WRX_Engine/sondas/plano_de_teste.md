# Plano de teste - sondas

Para cada sonda: carregue o `.set`, rode o Tester (mesmo simbolo/periodo/deposito, Every tick based on real ticks), salve o relatorio como `relatorios/<id>.htm`. As marcadas **hedging** exigem conta hedging.

| Sonda | O que muda | Hedging | Motor espera (trades / R) |
|---|---|---|---|
| `P00_base` | Baseline: MACD, TF M1, Fixed-R, SL/TP 3xATR, so compra |  | - |
| `P01_sell` | So venda |  | - |
| `P02_both_hedge` | Compra e venda, conta hedging | sim | - |
| `P03_breakeven` | Breakeven |  | - |
| `P04_tf_m5` | Sinal em M5 |  | - |
| `P05_tf_m15` | Sinal em M15 |  | - |
| `P06_tf_h1` | Sinal em H1 |  | - |
| `P07_atr_m5` | ATR em M5 |  | - |
| `P08_velas` | Vela do ATR: SL=1, TP=2 |  | - |
| `P09_atr_period` | Periodo do ATR 7 |  | - |
| `P10_no_take` | Sem take profit |  | - |
| `P11_maxrisk` | Teto de risco 0.5R |  | - |
| `P12_small_capital` | Capital pequeno (lote minimo / guarda 1.5x) |  | - |
| `P13_no_guard` | Sem guarda anti-oversizing |  | - |
| `P14_price_low` | Applied price = Low |  | - |
| `P15_price_weighted` | Applied price = Weighted |  | - |
| `P21_ind_01` | Indicador: EMA cruzamento |  | - |
| `P22_ind_02` | Indicador: Momentum |  | - |
| `P23_ind_03` | Indicador: Stochastic |  | - |
| `P24_ind_04` | Indicador: TRIX |  | - |
| `P25_ind_05` | Indicador: RSI |  | - |
| `P26_ind_06` | Indicador: CCI |  | - |
| `P27_ind_07` | Indicador: Williams %R |  | - |
| `P28_ind_08` | Indicador: DeMarker |  | - |
| `P29_ind_09` | Indicador: MFI |  | - |
| `P30_ind_10` | Indicador: OsMA |  | - |
| `P31_ind_11` | Indicador: Ichimoku (nuvem) |  | - |
| `P40_method_0` | EntryMethod=0 |  | - |
| `P41_method_1` | EntryMethod=1 |  | - |
| `P42_method_2` | EntryMethod=2 |  | - |
| `P43_method_3` | EntryMethod=3 |  | - |
| `P44_method_4` | EntryMethod=4 |  | - |
| `P45_method_5` | EntryMethod=5 |  | - |
| `P47_ichi_no_kumo` | Ichimoku sem nuvem (preco x Kijun) |  | - |
| `P48_ichi_chikou` | Ichimoku com filtro Chikou |  | - |
| `P49_stoch_close` | Stochastic Close/Close + %D EMA |  | - |
| `P50_mtf_any` | MTF: basta um TF superior alinhado |  | - |
| `P51_mtf_both` | MTF: os dois alinhados |  | - |
| `P52_ma_price_slope` | MA: preco E inclinacao |  | - |
| `P53_ma_price` | MA: so preco |  | - |
| `P54_ma_slope` | MA: so inclinacao |  | - |
| `P55_ma_or` | MA: preco OU inclinacao, reversao |  | - |
| `P56_ma_sma_h1` | MA SMA em M15 |  | - |
| `P57_adx` | ADX so forca |  | - |
| `P58_adx_di` | ADX + direcao DI |  | - |
| `P59_vol_high` | Volatilidade alta |  | - |
| `P60_vol_low` | Volatilidade baixa |  | - |
| `P61_hours` | Janela 08:00-12:00 |  | - |
| `P62_hours_overnight` | Janela noturna 22:00-06:00 |  | - |
| `P63_no_friday` | Sem sexta |  | - |
| `P64_spread` | MaxSpread=20 |  | - |
| `P65_reversal_exit` | Saida por sinal contrario (dois lados) | sim | - |
| `P66_reversal_exit_filters` | Saida por sinal contrario respeitando filtros | sim | - |
| `P67_close_outside` | Fecha posicoes fora do horario |  | - |
| `P69_ma_price_lookback` | MA: applied price Low + lookback 10 |  | - |
| `P70_adx_tf_period` | ADX em M15 periodo 7 |  | - |
| `P71_vol_mult_baseline` | Volatilidade: mult 1.2, baseline 60 |  | - |
| `P72_hours_minutes` | Janela 08:30-11:45 |  | - |
| `P73_monday_only` | So segunda |  | - |
| `P74_weekend_days` | Sabado e domingo liberados (mercado fechado: nao deve mudar nada) |  | - |
| `P75_wfo_in_plus_out` | WFO ligado em 'In Sample + Out Sample' (nao deve bloquear entradas) |  | - |
| `P68_safety_points` | ModificationSafetyPoints=30 (com breakeven) |  | - |
