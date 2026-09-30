# Revisao de inputs - WRX Engine

142 inputs classificados: PORTED 123, PARTIAL 2, DEFERRED 0, INERT 2, UI 15.

**PORTED nao quer dizer verificado**: so a paridade com o Tester (`Veredito`) verifica. `DEFERRED` = o motor recusa o set se o input estiver ligado.

| Input | Status | Sondas | Veredito | Nota |
|---|---|---|---|---|
| `ADX_Limiar` | PORTED | P57_adx, P58_adx_di, P70_adx_tf_period | a testar | HIPOTESE: iADX com EMA (alpha 2/(n+1)) em +DI/-DI/DX |
| `ADX_Period` | PORTED | P70_adx_tf_period | a testar | HIPOTESE: iADX com EMA (alpha 2/(n+1)) em +DI/-DI/DX |
| `ADX_TimeFrame` | PORTED | P70_adx_tf_period | a testar | HIPOTESE: iADX com EMA (alpha 2/(n+1)) em +DI/-DI/DX |
| `AtivarBreakeven` | PORTED | P03_breakeven, P68_safety_points, P83_signal_only, P97_sltp_trail, P100_grid_fixed, P101_grid_monetary, P102_grid_atr_only, P103_grid_stop, P104_grid_mult, P105_grid_distance, P106_grid_both, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit, PB12_be_bb, PC10_breakeven | a testar | reavaliado so nas decisoes (1x/minuto) |
| `AtivarFiltroADX` | PORTED | P57_adx, P58_adx_di, P70_adx_tf_period | a testar | HIPOTESE: iADX com EMA (alpha 2/(n+1)) em +DI/-DI/DX |
| `AtivarFiltroMA` | PORTED | P52_ma_price_slope, P53_ma_price, P54_ma_slope, P55_ma_or, P56_ma_sma_h1, P66_reversal_exit_filters, P69_ma_price_lookback | a testar |  |
| `AtivarFiltroMTF` | PORTED | P50_mtf_any, P51_mtf_both | a testar | TFs superiores = GetHigherTimeframes(TimeFrame) (confirmado no OnInit) |
| `AtivarFiltroNoticias` | PORTED | P122_news, P125_news_window | a testar | eventos vem de load_news_csv (mesmo CSV do exportador); moedas manuais ou base+cotacao de simbolo de 6 letras |
| `AtivarStop` | PORTED | P00_base, P83_signal_only, P100_grid_fixed, P101_grid_monetary, P102_grid_atr_only, P103_grid_stop, P104_grid_mult, P105_grid_distance, P106_grid_both, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit, PB10_stop_bb_rev, PB11_stop_bb_breakout | a testar | SL por perna; o trailing cria SL em posicao sem SL |
| `AtivarTake` | PORTED | P00_base, P10_no_take, P83_signal_only, P90_trail_close, P91_trail_open, P92_trail_high, P93_trail_low, P94_trail_price, P95_trail_profit_only, P96_trail_vela, P97_sltp_trail, P98_organic_take, P100_grid_fixed, P101_grid_monetary, P102_grid_atr_only, P103_grid_stop, P104_grid_mult, P105_grid_distance, P106_grid_both, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit, PB09_take_bb, PB10_stop_bb_rev, PB14_trail | a testar |  |
| `AtivarTrailATR` | PORTED | P90_trail_close, P91_trail_open, P92_trail_high, P93_trail_low, P94_trail_price, P95_trail_profit_only, P96_trail_vela, P97_sltp_trail, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit, PB14_trail | a testar | TrailingStopSet 1x por barra do TF de entrada; na piramide tambem ha o trailing da cesta |
| `AtivarWFO` | PORTED | P75_wfo_in_plus_out, P124_wfo_in_sample | a testar | janelas IS/OOS, bloqueio de entrada, carencia de grid, retirada do lucro; inicio = 1a barra M1 do teste (hipotese) |
| `ATR_TimeFrame` | PORTED | P07_atr_m5 | a testar | iATR = SMA do True Range (hipotese); ATR[0] parcial no 1o tick |
| `BandsDeviation` | PORTED | PB00_reversal, PB05_dev15 | a testar | iBands: base SMA, desvio padrao populacional; preco = InpAppliedPrice (o mesmo input do indicador de entrada) |
| `BandsPeriod` | PORTED | PB00_reversal, PB04_period10 | a testar | iBands: base SMA, desvio padrao populacional; preco = InpAppliedPrice (o mesmo input do indicador de entrada) |
| `BollingerEntryMode` | PORTED | PB00_reversal, PB01_breakout, PB02_squeeze, PB03_squeeze_params, PB07_both_hedge, PB11_stop_bb_breakout | a testar | 0 reversao, 1 rompimento, 2 squeeze (largura na barra 2 vs minimo de N barras) |
| `BreakevenBolinger` | PORTED | PB12_be_bb | a testar | saidas alternativas por banda (Take/BE so no modo Reversal) |
| `BreakevenDistancia` | PORTED | P03_breakeven, PC10_breakeven | a testar | reavaliado so nas decisoes (1x/minuto) |
| `CandleIndex1` | PORTED | PC00_one_slot, PC01_index0, PC02_index2 | a testar | 3 slots: applied price x open; indice 0 = candle em formacao (parcial) |
| `CandleIndex2` | PORTED | PC00_one_slot, PC01_index0, PC02_index2, PC05_mixed_index | a testar | 3 slots: applied price x open; indice 0 = candle em formacao (parcial) |
| `CandleIndex3` | PORTED | PC00_one_slot, PC01_index0, PC02_index2, PC05_mixed_index | a testar | 3 slots: applied price x open; indice 0 = candle em formacao (parcial) |
| `CandleTF1` | PORTED | PC00_one_slot, PC04_tf_m5 | a testar | 3 slots: applied price x open; indice 0 = candle em formacao (parcial) |
| `CandleTF2` | PORTED | PC00_one_slot, PC03_mtf_slots, PC04_tf_m5 | a testar | 3 slots: applied price x open; indice 0 = candle em formacao (parcial) |
| `CandleTF3` | PORTED | PC00_one_slot, PC03_mtf_slots, PC04_tf_m5 | a testar | 3 slots: applied price x open; indice 0 = candle em formacao (parcial) |
| `CapitalBaseR` | PORTED | P00_base, P12_small_capital, P13_no_guard | a testar | Fixed-R |
| `DailyLossLimitPercent` | PORTED | P118_daily_loss | a testar | pior caso do dia = fechado desde a ancora + perda no SL das abertas (bloqueia ENTRADA nova) |
| `DAlembertStep` | PORTED | P89_dalembert | a testar | historico de ciclos por lado (ApplyRecoveryOperation) |
| `DistanciaMinima` | PORTED | P100_grid_fixed, P101_grid_monetary, P102_grid_atr_only, P103_grid_stop, P104_grid_mult, P105_grid_distance, P106_grid_both, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit | a testar | 1 = grid classico (alvo monetario congelado na semente); 3 = piramide; 2 e invalido (o EA recusa) |
| `EntradaATR` | PORTED | P59_vol_high, P60_vol_low, P71_vol_mult_baseline, PB15_vol_filter | a testar | baseline inclui o ATR[0] parcial |
| `EntryIndicator` | PORTED | P00_base, P21_ind_01, P22_ind_02, P23_ind_03, P24_ind_04, P25_ind_05, P26_ind_06, P27_ind_07, P28_ind_08, P29_ind_09, P30_ind_10, P31_ind_11, P47_ichi_no_kumo, P48_ichi_chikou, P49_stoch_close | a testar | os 12 (MACD, EMA, Momentum, Stochastic, TRIX, RSI, CCI, WPR, DeMarker, MFI, OsMA, Ichimoku) |
| `EntryMethod` | PORTED | P00_base, P40_method_0, P41_method_1, P42_method_2, P43_method_3, P44_method_4, P45_method_5 | a testar | 7 metodos |
| `EntryOrderType` | PORTED | P112_pend_stop, P113_pend_limit, P114_pend_oco, P115_pend_extreme, P116_pend_expiry, P117_pend_session | a testar | Stop/Limit/OCO/sessao; preenchimento: stop no tick, limit no preco (calibrar: pending_fill) |
| `Fast_EMA` | PORTED | P00_base, P21_ind_01, P22_ind_02, P23_ind_03, P24_ind_04, P25_ind_05, P26_ind_06, P27_ind_07, P28_ind_08, P29_ind_09, P30_ind_10, P31_ind_11, P47_ichi_no_kumo, P48_ichi_chikou, P49_stoch_close | a testar | significado depende do indicador (ver signals.build_entry_series) |
| `Fecharordensforadohorario` | PORTED | P67_close_outside | a testar | roda antes de checar se ha dados prontos |
| `GridMode` | PORTED | P100_grid_fixed, P101_grid_monetary, P102_grid_atr_only, P103_grid_stop, P104_grid_mult, P105_grid_distance, P106_grid_both, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit | a testar | 1 = grid classico (alvo monetario congelado na semente); 3 = piramide; 2 e invalido (o EA recusa) |
| `Hedging` | PORTED | P02_both_hedge, P65_reversal_exit, P66_reversal_exit_filters, P83_signal_only, P99_reversal_opposite, P100_grid_fixed, P101_grid_monetary, P102_grid_atr_only, P103_grid_stop, P104_grid_mult, P105_grid_distance, P106_grid_both, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit, P114_pend_oco, P117_pend_session, PB07_both_hedge, PB13_both_sides_rev, PC09_both_hedge, PC11_reversal_exit | a testar |  |
| `IchimokuChikouFilter` | PORTED | P48_ichi_chikou | a testar | nuvem calculada Kijun barras atras (como o comentario do .mq5) |
| `IchimokuUseKumo` | PORTED | P47_ichi_no_kumo | a testar | nuvem calculada Kijun barras atras (como o comentario do .mq5) |
| `InpAppliedPrice` | PORTED | P00_base, P14_price_low, P15_price_weighted, PB16_price_weighted, PC00_one_slot, PC06_price_weighted, PC07_price_median | a testar | vale para MACD/EMA/Momentum/TRIX/RSI/CCI/OsMA |
| `input_end_date` | PORTED | P124_wfo_in_sample | a testar |  |
| `MA_AppliedPrice` | PORTED | P69_ma_price_lookback | a testar |  |
| `MA_Method` | PORTED | P56_ma_sma_h1 | a testar |  |
| `MA_Period` | PORTED | P52_ma_price_slope, P53_ma_price, P54_ma_slope, P55_ma_or, P56_ma_sma_h1, P66_reversal_exit_filters, P69_ma_price_lookback | a testar |  |
| `MA_SlopeLookback` | PORTED | P69_ma_price_lookback | a testar |  |
| `MA_TimeFrame` | PORTED | P56_ma_sma_h1 | a testar |  |
| `MACD_SMA` | PORTED | P00_base, P21_ind_01, P22_ind_02, P23_ind_03, P24_ind_04, P25_ind_05, P26_ind_06, P27_ind_07, P28_ind_08, P29_ind_09, P30_ind_10, P31_ind_11, P47_ichi_no_kumo, P48_ichi_chikou, P49_stoch_close | a testar | significado depende do indicador (ver signals.build_entry_series) |
| `MaxEquityDrawdownPercent` | PORTED | P119_equity_dd | a testar | trava de equity da estrategia, a cada tick; liquida e para o teste |
| `MaxLongTrades` | PORTED | P01_sell, P02_both_hedge, P65_reversal_exit, P66_reversal_exit_filters, P83_signal_only, P99_reversal_opposite, P100_grid_fixed, P101_grid_monetary, P102_grid_atr_only, P103_grid_stop, P104_grid_mult, P105_grid_distance, P106_grid_both, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit, P114_pend_oco, P117_pend_session, PB06_sell, PB07_both_hedge, PB13_both_sides_rev, PC08_sell, PC09_both_hedge, PC11_reversal_exit | a testar |  |
| `MaxMartingaleLot` | PORTED | P88_martingale_limits, P89_dalembert | a testar | historico de ciclos por lado (ApplyRecoveryOperation) |
| `MaxMartingaleSteps` | PORTED | P88_martingale_limits | a testar | historico de ciclos por lado (ApplyRecoveryOperation) |
| `MaxRiscoRelativoAoLoteMinimo` | PORTED | P00_base, P13_no_guard | a testar | Fixed-R |
| `MaxRiscoTradeR` | PORTED | P11_maxrisk, P87_martingale_fixedr | a testar | Fixed-R |
| `MaxShortTrades` | PORTED | P01_sell, P02_both_hedge, P65_reversal_exit, P66_reversal_exit_filters, P83_signal_only, P99_reversal_opposite, P100_grid_fixed, P101_grid_monetary, P102_grid_atr_only, P103_grid_stop, P104_grid_mult, P105_grid_distance, P106_grid_both, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit, P114_pend_oco, P117_pend_session, PB06_sell, PB07_both_hedge, PB13_both_sides_rev, PC08_sell, PC09_both_hedge, PC11_reversal_exit | a testar |  |
| `MaxSpread` | PORTED | P64_spread | a testar | spread em pontos inteiros do tick |
| `MetodoADX` | PORTED | P57_adx, P58_adx_di | a testar | HIPOTESE: iADX com EMA (alpha 2/(n+1)) em +DI/-DI/DX |
| `MetodoDeCalculo` | PORTED | P91_trail_open, P92_trail_high, P93_trail_low, P94_trail_price | a testar | TrailingStopSet 1x por barra do TF de entrada; na piramide tambem ha o trailing da cesta |
| `MetodoDeEntradawfo` | PORTED | P75_wfo_in_plus_out, P124_wfo_in_sample | a testar | janelas IS/OOS, bloqueio de entrada, carencia de grid, retirada do lucro; inicio = 1a barra M1 do teste (hipotese) |
| `MetodoMA` | PORTED | P52_ma_price_slope, P53_ma_price, P54_ma_slope, P55_ma_or, P69_ma_price_lookback | a testar |  |
| `ModificationSafetyPoints` | PORTED | P68_safety_points | a testar |  |
| `MTF_RequererAmbos` | PORTED | P50_mtf_any, P51_mtf_both | a testar | TFs superiores = GetHigherTimeframes(TimeFrame) (confirmado no OnInit) |
| `Multiplicador` | PORTED | P84_martingale_fixed, P85_martingale_monetary, P86_martingale_pct, P87_martingale_fixedr, P88_martingale_limits, P104_grid_mult, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit | a testar | historico de ciclos por lado (ApplyRecoveryOperation) |
| `MultiplicadorATR` | PORTED | P71_vol_mult_baseline, PB15_vol_filter | a testar | baseline inclui o ATR[0] parcial |
| `NewsCSVFile` | PORTED | P125_news_window | a testar | eventos vem de load_news_csv (mesmo CSV do exportador); moedas manuais ou base+cotacao de simbolo de 6 letras |
| `NewsMinutosAntes` | PORTED | P125_news_window | a testar | eventos vem de load_news_csv (mesmo CSV do exportador); moedas manuais ou base+cotacao de simbolo de 6 letras |
| `NewsMinutosDepois` | PORTED | P125_news_window | a testar | eventos vem de load_news_csv (mesmo CSV do exportador); moedas manuais ou base+cotacao de simbolo de 6 letras |
| `NewsMoedasManual` | PORTED | P122_news, P125_news_window | a testar | eventos vem de load_news_csv (mesmo CSV do exportador); moedas manuais ou base+cotacao de simbolo de 6 letras |
| `NewsSomenteAltoImpacto` | PORTED | P125_news_window | a testar | eventos vem de load_news_csv (mesmo CSV do exportador); moedas manuais ou base+cotacao de simbolo de 6 letras |
| `PendingDistanciaATR` | PORTED | P115_pend_extreme | a testar | Stop/Limit/OCO/sessao; preenchimento: stop no tick, limit no preco (calibrar: pending_fill) |
| `PendingExpiracaoBarras` | PORTED | P116_pend_expiry | a testar | Stop/Limit/OCO/sessao; preenchimento: stop no tick, limit no preco (calibrar: pending_fill) |
| `PendingFaixaBarras` | PORTED | P117_pend_session | a testar | Stop/Limit/OCO/sessao; preenchimento: stop no tick, limit no preco (calibrar: pending_fill) |
| `PendingGatilho` | PORTED | P117_pend_session | a testar | Stop/Limit/OCO/sessao; preenchimento: stop no tick, limit no preco (calibrar: pending_fill) |
| `PendingHoraSessao` | PORTED | P117_pend_session | a testar | Stop/Limit/OCO/sessao; preenchimento: stop no tick, limit no preco (calibrar: pending_fill) |
| `PendingReferencia` | PORTED | P115_pend_extreme | a testar | Stop/Limit/OCO/sessao; preenchimento: stop no tick, limit no preco (calibrar: pending_fill) |
| `PeriodoATR` | PORTED | P00_base, P09_atr_period | a testar | iATR = SMA do True Range (hipotese); ATR[0] parcial no 1o tick |
| `PeriodoBaselineATR` | PORTED | P71_vol_mult_baseline, PB15_vol_filter | a testar | baseline inclui o ATR[0] parcial |
| `PositionSizeMode` | PORTED | P00_base, P80_fixed_lot, P81_monetary, P82_percentage, P83_signal_only, P84_martingale_fixed, P85_martingale_monetary, P86_martingale_pct, P87_martingale_fixedr, P88_martingale_limits, P89_dalembert, P100_grid_fixed, P101_grid_monetary, P102_grid_atr_only, P103_grid_stop, P104_grid_mult, P105_grid_distance, P106_grid_both, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit | a testar | Percentage (saldo ao vivo), Monetary (capital inicial), FixedLot, FixedR |
| `PositionSizeValue` | PORTED | P00_base, P80_fixed_lot, P81_monetary, P82_percentage, P83_signal_only, P84_martingale_fixed, P85_martingale_monetary, P86_martingale_pct, P88_martingale_limits, P89_dalembert, P100_grid_fixed, P101_grid_monetary, P102_grid_atr_only, P103_grid_stop, P104_grid_mult, P105_grid_distance, P106_grid_both, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit | a testar | Percentage (saldo ao vivo), Monetary (capital inicial), FixedLot, FixedR |
| `Protecao_Fecha_Posicoes` | PORTED | P121_gp_total_noclose | a testar | equity da conta (aqui = 1 simbolo); estado do GlobalVariable assumido limpo a cada teste |
| `PyramidLevelOnlyInProfit` | PORTED | P110_pyr_level_profit | a testar |  |
| `PyramidTrailSoLucro` | PORTED | P111_pyr_trail_profit | a testar |  |
| `RecoveryMode` | PORTED | P84_martingale_fixed, P85_martingale_monetary, P86_martingale_pct, P87_martingale_fixedr, P88_martingale_limits, P89_dalembert | a testar | historico de ciclos por lado (ApplyRecoveryOperation) |
| `ReversalExitMode` | PORTED | P65_reversal_exit, P66_reversal_exit_filters, P83_signal_only, P99_reversal_opposite, PC11_reversal_exit | a testar | 0, 1 (ordem oposta, exige hedging) e 2 (sinal contrario) |
| `ReversalExitUseEntryFilters` | PORTED | P66_reversal_exit_filters | a testar |  |
| `selectedFormula` | PORTED | P126_fitness_levain | a testar | so afeta o fitness (`fitness.py`: 15 formulas + ConsistencyFactor); nao altera a simulacao |
| `SentidoMA` | PORTED | P55_ma_or | a testar |  |
| `Slow_EMA` | PORTED | P00_base, P21_ind_01, P30_ind_10, P31_ind_11, P47_ichi_no_kumo, P48_ichi_chikou | a testar | significado depende do indicador (ver signals.build_entry_series) |
| `SqueezeLookback` | PORTED | PB02_squeeze, PB03_squeeze_params | a testar | 0 reversao, 1 rompimento, 2 squeeze (largura na barra 2 vs minimo de N barras) |
| `SqueezeTolerancePct` | PORTED | PB02_squeeze, PB03_squeeze_params | a testar | 0 reversao, 1 rompimento, 2 squeeze (largura na barra 2 vs minimo de N barras) |
| `StochasticMethod` | PORTED | P49_stoch_close | a testar | HIPOTESE: slowing por soma/soma; metodo aplica ao %D |
| `StochasticPriceField` | PORTED | P49_stoch_close | a testar | HIPOTESE: slowing por soma/soma; metodo aplica ao %D |
| `StochasticSlowing` | PORTED | P49_stoch_close | a testar | HIPOTESE: slowing por soma/soma; metodo aplica ao %D |
| `Stop` | PORTED | P00_base, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit | a testar | SL por perna; o trailing cria SL em posicao sem SL |
| `StopBolinger` | PORTED | PB10_stop_bb_rev, PB11_stop_bb_breakout | a testar | saidas alternativas por banda (Take/BE so no modo Reversal) |
| `Take` | PORTED | P00_base | a testar |  |
| `TakeBolinger` | PORTED | PB09_take_bb | a testar | saidas alternativas por banda (Take/BE so no modo Reversal) |
| `TakeOrganico` | PORTED | P98_organic_take | a testar | fecha a mercado quando bid > abertura da posicao mais recente + ATR*Take (LastTradePrice = posicao ABERTA) |
| `TimeFrame` | PORTED | P04_tf_m5, P05_tf_m15, P06_tf_h1, PB08_tf_m5 | a testar | M1..W1; sinal 1x por barra deste TF (exige >= 50 barras do TF) |
| `TOD_From_Hour` | PORTED | P61_hours, P62_hours_overnight, P67_close_outside, P72_hours_minutes | a testar |  |
| `TOD_From_Min` | PORTED | P72_hours_minutes | a testar |  |
| `TOD_To_Hour` | PORTED | P61_hours, P62_hours_overnight, P67_close_outside, P72_hours_minutes | a testar |  |
| `TOD_To_Min` | PORTED | P61_hours, P62_hours_overnight, P67_close_outside, P72_hours_minutes | a testar |  |
| `TradeCapitalPercentage` | PORTED | P00_base | a testar | Fixed-R |
| `TradeFriday` | PORTED | P63_no_friday, P73_monday_only | a testar |  |
| `TradeMonday` | PORTED | P73_monday_only | a testar |  |
| `TradeSaturday` | PORTED | P74_weekend_days | a testar |  |
| `TradeSunday` | PORTED | P74_weekend_days | a testar |  |
| `TradeThursday` | PORTED | P73_monday_only, P74_weekend_days | a testar |  |
| `TradeTuesday` | PORTED | P73_monday_only, P74_weekend_days | a testar |  |
| `TradeWednesday` | PORTED | P73_monday_only | a testar |  |
| `Trail` | PORTED | P96_trail_vela, P107_pyr_fixed, P108_pyr_fixedr, P109_pyr_pct, P110_pyr_level_profit, P111_pyr_trail_profit, PB14_trail | a testar | TrailingStopSet 1x por barra do TF de entrada; na piramide tambem ha o trailing da cesta |
| `TrailSoLucro` | PORTED | P95_trail_profit_only | a testar | TrailingStopSet 1x por barra do TF de entrada; na piramide tambem ha o trailing da cesta |
| `TrailVela` | PORTED | P96_trail_vela | a testar | TrailingStopSet 1x por barra do TF de entrada; na piramide tambem ha o trailing da cesta |
| `Trava_Diaria_Percent` | PORTED | P120_gp_daily | a testar | equity da conta (aqui = 1 simbolo); estado do GlobalVariable assumido limpo a cada teste |
| `Trava_Total_Percent` | PORTED | P121_gp_total_noclose | a testar | equity da conta (aqui = 1 simbolo); estado do GlobalVariable assumido limpo a cada teste |
| `UsarsomenteATRGRID` | PORTED | P102_grid_atr_only | a testar | 1 = grid classico (alvo monetario congelado na semente); 3 = piramide; 2 e invalido (o EA recusa) |
| `VelaStop` | PORTED | P08_velas | a testar | SL por perna; o trailing cria SL em posicao sem SL |
| `VelaTake` | PORTED | P08_velas | a testar |  |
| `VolatilityFilter` | PORTED | P59_vol_high, P60_vol_low, P71_vol_mult_baseline | a testar | baseline inclui o ATR[0] parcial |
| `WFO_CarenciaPercentil` | PORTED | P124_wfo_in_sample | a testar |  |
| `wfo_customStepSizePercent` | PORTED | P124_wfo_in_sample | a testar |  |
| `wfo_customWindowSizeDays` | PORTED | P124_wfo_in_sample | a testar |  |
| `wfo_stepSize` | PORTED | P124_wfo_in_sample | a testar |  |
| `wfo_windowSize` | PORTED | P124_wfo_in_sample | a testar |  |
| `BandsShift` | PARTIAL | PB00_reversal | a testar | so 0 (deslocamento horizontal nao portado; o motor recusa != 0) |
| `MinFreeMarginPercent` | PARTIAL | P123_min_free_margin | a testar | depende da margem da corretora: preencha margin_a/margin_b no SymbolSpec (sem isso nao e modelada) |
| `MagicNumber` | INERT | - | - | so identifica ordens; o motor simula um unico magic |
| `MaxSlippage` | INERT | - | - | Tester ideal executa sem desvio; slippage nao e modelado (so entra na validacao do OnInit) |
| `ApplyEmbeddedChartTheme` | UI | - | - |  |
| `ChartTheme` | UI | - | - |  |
| `ClosedDealLabelFontSize` | UI | - | - |  |
| `DASH_C_DEAL_BG` | UI | - | - |  |
| `DASH_C_PANEL_BG` | UI | - | - |  |
| `DashboardCorner` | UI | - | - |  |
| `DashboardOffsetX` | UI | - | - |  |
| `DashboardOffsetY` | UI | - | - |  |
| `DashboardPanelOpacityPct` | UI | - | - |  |
| `EnableChartDashboard` | UI | - | - |  |
| `InterfaceLanguage` | UI | - | - |  |
| `MaxVisibleDealLabels` | UI | - | - |  |
| `NomedaEstrategia` | UI | - | - |  |
| `PlotIndicatorsOnChart` | UI | - | - |  |
| `ShowClosedDealLabels` | UI | - | - |  |