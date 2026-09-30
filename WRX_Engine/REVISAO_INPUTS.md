# Revisao de inputs - WRX Engine

127 inputs classificados: PORTED 63, PARTIAL 5, DEFERRED 42, INERT 2, UI 15.

**PORTED nao quer dizer verificado**: so a paridade com o Tester (`Veredito`) verifica. `DEFERRED` = o motor recusa o set se o input estiver ligado.

| Input | Status | Sondas | Veredito | Nota |
|---|---|---|---|---|
| `ADX_Limiar` | PORTED | P57_adx, P58_adx_di, P70_adx_tf_period | a testar | HIPOTESE: iADX com EMA (alpha 2/(n+1)) em +DI/-DI/DX |
| `ADX_Period` | PORTED | P70_adx_tf_period | a testar | HIPOTESE: iADX com EMA (alpha 2/(n+1)) em +DI/-DI/DX |
| `ADX_TimeFrame` | PORTED | P70_adx_tf_period | a testar | HIPOTESE: iADX com EMA (alpha 2/(n+1)) em +DI/-DI/DX |
| `AtivarBreakeven` | PORTED | P03_breakeven, P68_safety_points | a testar | reavaliado so nas decisoes (1x/minuto) |
| `AtivarFiltroADX` | PORTED | P57_adx, P58_adx_di, P70_adx_tf_period | a testar | HIPOTESE: iADX com EMA (alpha 2/(n+1)) em +DI/-DI/DX |
| `AtivarFiltroMA` | PORTED | P52_ma_price_slope, P53_ma_price, P54_ma_slope, P55_ma_or, P56_ma_sma_h1, P66_reversal_exit_filters, P69_ma_price_lookback | a testar |  |
| `AtivarFiltroMTF` | PORTED | P50_mtf_any, P51_mtf_both | a testar | HIPOTESE: TFs superiores = GetHigherTimeframes(TimeFrame) (OnInit nao lido) |
| `AtivarStop` | PORTED | P00_base | a testar | so com FixedR por enquanto |
| `AtivarTake` | PORTED | P00_base, P10_no_take | a testar |  |
| `ATR_TimeFrame` | PORTED | P07_atr_m5 | a testar | iATR = SMA do True Range (hipotese); ATR[0] parcial no 1o tick |
| `BreakevenDistancia` | PORTED | P03_breakeven | a testar | reavaliado so nas decisoes (1x/minuto) |
| `CapitalBaseR` | PORTED | P00_base, P12_small_capital, P13_no_guard | a testar | Fixed-R |
| `EntradaATR` | PORTED | P59_vol_high, P60_vol_low, P71_vol_mult_baseline | a testar | baseline inclui o ATR[0] parcial |
| `EntryIndicator` | PORTED | P00_base, P21_ind_01, P22_ind_02, P23_ind_03, P24_ind_04, P25_ind_05, P26_ind_06, P27_ind_07, P28_ind_08, P29_ind_09, P30_ind_10, P31_ind_11, P47_ichi_no_kumo, P48_ichi_chikou, P49_stoch_close | a testar | os 12 (MACD, EMA, Momentum, Stochastic, TRIX, RSI, CCI, WPR, DeMarker, MFI, OsMA, Ichimoku) |
| `EntryMethod` | PORTED | P00_base, P40_method_0, P41_method_1, P42_method_2, P43_method_3, P44_method_4, P45_method_5 | a testar | 7 metodos |
| `Fast_EMA` | PORTED | P00_base, P21_ind_01, P22_ind_02, P23_ind_03, P24_ind_04, P25_ind_05, P26_ind_06, P27_ind_07, P28_ind_08, P29_ind_09, P30_ind_10, P31_ind_11, P47_ichi_no_kumo, P48_ichi_chikou, P49_stoch_close | a testar | significado depende do indicador (ver signals.build_entry_series) |
| `Fecharordensforadohorario` | PORTED | P67_close_outside | a testar | roda antes de checar se ha dados prontos |
| `Hedging` | PORTED | P02_both_hedge, P65_reversal_exit, P66_reversal_exit_filters | a testar |  |
| `IchimokuChikouFilter` | PORTED | P48_ichi_chikou | a testar | nuvem calculada Kijun barras atras (como o comentario do .mq5) |
| `IchimokuUseKumo` | PORTED | P47_ichi_no_kumo | a testar | nuvem calculada Kijun barras atras (como o comentario do .mq5) |
| `InpAppliedPrice` | PORTED | P00_base, P14_price_low, P15_price_weighted | a testar | vale para MACD/EMA/Momentum/TRIX/RSI/CCI/OsMA |
| `MA_AppliedPrice` | PORTED | P69_ma_price_lookback | a testar |  |
| `MA_Method` | PORTED | P56_ma_sma_h1 | a testar |  |
| `MA_Period` | PORTED | P52_ma_price_slope, P53_ma_price, P54_ma_slope, P55_ma_or, P56_ma_sma_h1, P66_reversal_exit_filters, P69_ma_price_lookback | a testar |  |
| `MA_SlopeLookback` | PORTED | P69_ma_price_lookback | a testar |  |
| `MA_TimeFrame` | PORTED | P56_ma_sma_h1 | a testar |  |
| `MACD_SMA` | PORTED | P00_base, P21_ind_01, P22_ind_02, P23_ind_03, P24_ind_04, P25_ind_05, P26_ind_06, P27_ind_07, P28_ind_08, P29_ind_09, P30_ind_10, P31_ind_11, P47_ichi_no_kumo, P48_ichi_chikou, P49_stoch_close | a testar | significado depende do indicador (ver signals.build_entry_series) |
| `MaxLongTrades` | PORTED | P01_sell, P02_both_hedge, P65_reversal_exit, P66_reversal_exit_filters | a testar |  |
| `MaxRiscoRelativoAoLoteMinimo` | PORTED | P00_base, P13_no_guard | a testar | Fixed-R |
| `MaxRiscoTradeR` | PORTED | P11_maxrisk | a testar | Fixed-R |
| `MaxShortTrades` | PORTED | P01_sell, P02_both_hedge, P65_reversal_exit, P66_reversal_exit_filters | a testar |  |
| `MaxSpread` | PORTED | P64_spread | a testar | spread em pontos inteiros do tick |
| `MetodoADX` | PORTED | P57_adx, P58_adx_di | a testar | HIPOTESE: iADX com EMA (alpha 2/(n+1)) em +DI/-DI/DX |
| `MetodoMA` | PORTED | P52_ma_price_slope, P53_ma_price, P54_ma_slope, P55_ma_or, P69_ma_price_lookback | a testar |  |
| `ModificationSafetyPoints` | PORTED | P68_safety_points | a testar |  |
| `MTF_RequererAmbos` | PORTED | P50_mtf_any, P51_mtf_both | a testar | HIPOTESE: TFs superiores = GetHigherTimeframes(TimeFrame) (OnInit nao lido) |
| `MultiplicadorATR` | PORTED | P71_vol_mult_baseline | a testar | baseline inclui o ATR[0] parcial |
| `PeriodoATR` | PORTED | P00_base, P09_atr_period | a testar | iATR = SMA do True Range (hipotese); ATR[0] parcial no 1o tick |
| `PeriodoBaselineATR` | PORTED | P71_vol_mult_baseline | a testar | baseline inclui o ATR[0] parcial |
| `ReversalExitUseEntryFilters` | PORTED | P66_reversal_exit_filters | a testar |  |
| `SentidoMA` | PORTED | P55_ma_or | a testar |  |
| `Slow_EMA` | PORTED | P00_base, P21_ind_01, P30_ind_10, P31_ind_11, P47_ichi_no_kumo, P48_ichi_chikou | a testar | significado depende do indicador (ver signals.build_entry_series) |
| `StochasticMethod` | PORTED | P49_stoch_close | a testar | HIPOTESE: slowing por soma/soma; metodo aplica ao %D |
| `StochasticPriceField` | PORTED | P49_stoch_close | a testar | HIPOTESE: slowing por soma/soma; metodo aplica ao %D |
| `StochasticSlowing` | PORTED | P49_stoch_close | a testar | HIPOTESE: slowing por soma/soma; metodo aplica ao %D |
| `Stop` | PORTED | P00_base | a testar | so com FixedR por enquanto |
| `Take` | PORTED | P00_base | a testar |  |
| `TimeFrame` | PORTED | P04_tf_m5, P05_tf_m15, P06_tf_h1 | a testar | M1..W1; sinal 1x por barra deste TF |
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
| `VelaStop` | PORTED | P08_velas | a testar | so com FixedR por enquanto |
| `VelaTake` | PORTED | P08_velas | a testar |  |
| `VolatilityFilter` | PORTED | P59_vol_high, P60_vol_low, P71_vol_mult_baseline | a testar | baseline inclui o ATR[0] parcial |
| `AtivarWFO` | PARTIAL | P75_wfo_in_plus_out | a testar | so false, ou true com 'In Sample + Out Sample' (nao bloqueia entradas) |
| `MetodoDeEntradawfo` | PARTIAL | P75_wfo_in_plus_out | a testar | 0 (In Sample) com AtivarWFO=true e recusado |
| `PositionSizeMode` | PARTIAL | P00_base | a testar | so FixedR; Percentage/Monetary/FixedLot adiados |
| `PositionSizeValue` | PARTIAL | P00_base | a testar | so FixedR; Percentage/Monetary/FixedLot adiados |
| `ReversalExitMode` | PARTIAL | P65_reversal_exit, P66_reversal_exit_filters | a testar | 0 e 2 portados; 1 (OnOppositeOrder) recusado |
| `AtivarFiltroNoticias` | DEFERRED | - | nao portado | WhiteRabbitNewsFilter.mqh nao lido |
| `AtivarTrailATR` | DEFERRED | - | nao portado | TrailingStopSet() nao lido |
| `DailyLossLimitPercent` | DEFERRED | - | nao portado | zere no set (os defaults do EA sao 0/30/50!) |
| `DAlembertStep` | DEFERRED | - | nao portado | historico de ciclos lido; sizing de Percentage/Monetary/Fixed nao |
| `DistanciaMinima` | DEFERRED | - | nao portado | grid/piramide nao lidos |
| `EntryOrderType` | DEFERRED | - | nao portado |  |
| `GridMode` | DEFERRED | - | nao portado | grid/piramide nao lidos |
| `input_end_date` | DEFERRED | - | nao portado | janelas IS/OOS |
| `MaxEquityDrawdownPercent` | DEFERRED | - | nao portado | zere no set (os defaults do EA sao 0/30/50!) |
| `MaxMartingaleLot` | DEFERRED | - | nao portado | historico de ciclos lido; sizing de Percentage/Monetary/Fixed nao |
| `MaxMartingaleSteps` | DEFERRED | - | nao portado | historico de ciclos lido; sizing de Percentage/Monetary/Fixed nao |
| `MetodoDeCalculo` | DEFERRED | - | nao portado | TrailingStopSet() nao lido |
| `MinFreeMarginPercent` | DEFERRED | - | nao portado | zere no set (os defaults do EA sao 0/30/50!) |
| `Multiplicador` | DEFERRED | - | nao portado | historico de ciclos lido; sizing de Percentage/Monetary/Fixed nao |
| `NewsCSVFile` | DEFERRED | - | nao portado | WhiteRabbitNewsFilter.mqh nao lido |
| `NewsMinutosAntes` | DEFERRED | - | nao portado | WhiteRabbitNewsFilter.mqh nao lido |
| `NewsMinutosDepois` | DEFERRED | - | nao portado | WhiteRabbitNewsFilter.mqh nao lido |
| `NewsMoedasManual` | DEFERRED | - | nao portado | WhiteRabbitNewsFilter.mqh nao lido |
| `NewsSomenteAltoImpacto` | DEFERRED | - | nao portado | WhiteRabbitNewsFilter.mqh nao lido |
| `PendingDistanciaATR` | DEFERRED | - | nao portado |  |
| `PendingExpiracaoBarras` | DEFERRED | - | nao portado |  |
| `PendingFaixaBarras` | DEFERRED | - | nao portado |  |
| `PendingGatilho` | DEFERRED | - | nao portado |  |
| `PendingHoraSessao` | DEFERRED | - | nao portado |  |
| `PendingReferencia` | DEFERRED | - | nao portado |  |
| `Protecao_Fecha_Posicoes` | DEFERRED | - | nao portado | WhiteRabbitGlobalProtection.mqh nao lido |
| `PyramidLevelOnlyInProfit` | DEFERRED | - | nao portado | grid/piramide nao lidos |
| `PyramidTrailSoLucro` | DEFERRED | - | nao portado | grid/piramide nao lidos |
| `RecoveryMode` | DEFERRED | - | nao portado | historico de ciclos lido; sizing de Percentage/Monetary/Fixed nao |
| `selectedFormula` | DEFERRED | - | nao portado | formulas de OnTester (fitness) ainda nao portadas |
| `TakeOrganico` | DEFERRED | - | nao portado | depende de LastTradePrice() (nao lido): pode ancorar no trade ANTERIOR |
| `Trail` | DEFERRED | - | nao portado | TrailingStopSet() nao lido |
| `TrailSoLucro` | DEFERRED | - | nao portado | TrailingStopSet() nao lido |
| `TrailVela` | DEFERRED | - | nao portado | TrailingStopSet() nao lido |
| `Trava_Diaria_Percent` | DEFERRED | - | nao portado | WhiteRabbitGlobalProtection.mqh nao lido |
| `Trava_Total_Percent` | DEFERRED | - | nao portado | WhiteRabbitGlobalProtection.mqh nao lido |
| `UsarsomenteATRGRID` | DEFERRED | - | nao portado | grid/piramide nao lidos |
| `WFO_CarenciaPercentil` | DEFERRED | - | nao portado | janelas IS/OOS |
| `wfo_customStepSizePercent` | DEFERRED | - | nao portado | janelas IS/OOS |
| `wfo_customWindowSizeDays` | DEFERRED | - | nao portado | janelas IS/OOS |
| `wfo_stepSize` | DEFERRED | - | nao portado | janelas IS/OOS |
| `wfo_windowSize` | DEFERRED | - | nao portado | janelas IS/OOS |
| `MagicNumber` | INERT | - | - | so identifica ordens; o motor simula um unico magic |
| `MaxSlippage` | INERT | - | - | Tester ideal executa sem desvio; slippage nao e modelado |
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