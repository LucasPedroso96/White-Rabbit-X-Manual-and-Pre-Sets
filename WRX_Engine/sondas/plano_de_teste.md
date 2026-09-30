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
| `P80_fixed_lot` | Lote fixo 0.05 com SL/TP |  | - |
| `P81_monetary` | Monetary: 1 lote por 10000 de capital inicial |  | - |
| `P82_percentage` | Percentage: 1% do saldo ao vivo |  | - |
| `P83_signal_only` | Sinal puro: sem SL/TP, sai no sinal contrario (dois lados) | sim | - |
| `P84_martingale_fixed` | Martingale, lote fixo x2 |  | - |
| `P85_martingale_monetary` | Martingale monetario com take (recupera a divida no TP) |  | - |
| `P86_martingale_pct` | Martingale percentual |  | - |
| `P87_martingale_fixedr` | Martingale em R com teto 3R |  | - |
| `P88_martingale_limits` | Martingale com MaxMartingaleSteps=3 e MaxMartingaleLot=0.08 |  | - |
| `P89_dalembert` | D'Alembert passo 0.01, teto 0.06 |  | - |
| `P90_trail_close` | Trailing ATR (preco de fechamento), sem TP |  | - |
| `P91_trail_open` | Trailing sobre a abertura do candle |  | - |
| `P92_trail_high` | Trailing sobre a maxima |  | - |
| `P93_trail_low` | Trailing sobre a minima |  | - |
| `P94_trail_price` | Trailing sobre o preco (bid/ask) |  | - |
| `P95_trail_profit_only` | Trailing so no lucro |  | - |
| `P96_trail_vela` | Trailing com ATR da vela 2 e Trail=2 |  | - |
| `P97_sltp_trail` | SL + TP + trailing + breakeven |  | - |
| `P98_organic_take` | Take organico junto com TP |  | - |
| `P99_reversal_opposite` | Saida por ordem oposta (hedging, dois lados) | sim | - |
| `P100_grid_fixed` | Grid classico, lote fixo | sim | - |
| `P101_grid_monetary` | Grid classico, monetary | sim | - |
| `P102_grid_atr_only` | Grid: continua so pelo ATR (sem sinal) | sim | - |
| `P103_grid_stop` | Grid com SL por perna | sim | - |
| `P104_grid_mult` | Grid com Multiplicador 1.5 no alvo | sim | - |
| `P105_grid_distance` | Grid com DistanciaMinima=3 | sim | - |
| `P106_grid_both` | Grid nos dois lados | sim | - |
| `P107_pyr_fixed` | Piramide, lote fixo | sim | - |
| `P108_pyr_fixedr` | Piramide em Fixed-R | sim | - |
| `P109_pyr_pct` | Piramide percentual | sim | - |
| `P110_pyr_level_profit` | Piramide: proximo nivel so com a ultima perna no empate | sim | - |
| `P111_pyr_trail_profit` | Piramide: trailing da cesta so no lucro | sim | - |
| `P112_pend_stop` | Entrada Stop |  | - |
| `P113_pend_limit` | Entrada Limit |  | - |
| `P114_pend_oco` | Entrada OCO (hedging, dois lados) | sim | - |
| `P115_pend_extreme` | Pendente ancorada na maxima/minima do candle, distancia 1 ATR |  | - |
| `P116_pend_expiry` | Pendente expira em 1 barra |  | - |
| `P117_pend_session` | Rompimento por sessao as 08h, faixa de 4 barras | sim | - |
| `P118_daily_loss` | DailyLossLimitPercent=0.5 |  | - |
| `P119_equity_dd` | MaxEquityDrawdownPercent=2 |  | - |
| `P120_gp_daily` | Protecao global diaria 1% (fecha tudo) |  | - |
| `P121_gp_total_noclose` | Protecao global total 3% sem fechar (so bloqueia) |  | - |
| `P122_news` | Filtro de noticias USD/EUR (precisa do CSV em Common\Files) |  | - |
| `P125_news_window` | Noticias: so alto impacto, janela 30 antes / 5 depois |  | - |
| `P123_min_free_margin` | Reserva de margem livre 50% (precisa margin_a/margin_b no spec) |  | - |
| `P124_wfo_in_sample` | WFO 'In Sample': 122 dias IS + 61 OOS (ajuste input_end_date ao fim do teste) |  | - |
| `P126_fitness_levain` | Fitness: selectedFormula = Levain (a simulacao nao muda; confira a linha ALL_FORMULAS) |  | - |
