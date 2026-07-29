# White Rabbit X — 전체 사용자 설명서

현재 EA 소스와 set 매니페스트에서 생성한 공식 참조 — EA 1.11 — 127 inputs — 3738 sets

## 범위와 기준 데이터

EA 소스가 inputs, 기본값, 기능을 정의하고 매니페스트가 각 set의 상태, 경로, SHA-256을 정의합니다. 구 Quantum 자료는 기록용입니다.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

자동 생성 문서이며 파라미터 식별자는 EA와 정확히 같습니다.

## 설치와 첫 실행

일치하는 EX5를 설치하고 Tester Inputs에서 set을 로드한 뒤 정확한 심볼과 Journal을 확인합니다.

## 신호와 진입 방식

6개 엔진은 reversal, signal/reference cross, baseline/reference cross를 공유합니다. And는 같은 종가 확정 봉, All은 어느 하나입니다.

- 12개 네이티브 엔진: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA, Ichimoku.
- 확정 봉의 AND/OR 의미가 명확한 7개 진입 방식.
- 독립적인 MTF, MA, ADX, ATR, news 필터.
- 4개 PositionSizeMode와 equity/margin 보호.
- Stop, take, breakeven, trailing, reversal 청산.
- Dashboard, 일정, 언어, WFO 통합.
- EntryIndicator: MACD, EMA_Cross, Momentum, Stochastic, TRIX, RSI, CCI, WPR, DeMarker, MFI, OsMA, Ichimoku.
- EntryMethod: Reversal, SignalCross, ReferenceCross, ReversalAndSignalCross, ReversalAndReferenceCross, SignalAndReferenceCross, All.
- PositionSizeMode: Percentage, Monetary, FixedLot, FixedR.
- RecoveryMode: None, Martingale, DAlembert.
- GridMode: Disabled, SeparateProfit, UnifiedProfit.

## 필터

MTF는 상위 시간대 MACD 정렬이고 MA, ADX, ATR volatility, news는 독립적입니다.

## News filter and CSV workflow

Live mode reads the MT5 Economic Calendar in broker-server time and blocks new entries if the calendar query fails. Backtests cannot read that live calendar: run MQL5\Scripts\White Rabbit News Exporter on a live/demo chart, cover the entire test interval, and write NewsCSVFile to the terminal Common\Files folder. The semicolon-delimited header is datetime;currency;importance;event_name, where importance 2 is moderate and 3 is high. Use the same broker/server timezone; for suffixed or non-FX symbols set ExportMoedas and NewsMoedasManual explicitly. Manual currencies take precedence over automatic symbol parsing.

## 실행과 포지션 관리

spread, margin, volume step, tick size, stops/freeze 제한이 실행에 영향을 줍니다. Journal에서 확인하십시오.

## Grid cycle and ATR spacing

Every additional grid leg is measured from the newest already-confirmed position on that side and must satisfy ATR × DistanciaMinima. The initial order cannot recursively trigger another leg in the same calculation event; it becomes the anchor on the following cycle. Individual grid take-profits are disabled: Separate mode evaluates independent BUY/SELL cycles against frozen monetary targets and ends a side when it becomes flat; Unified evaluates the aggregate BUY+SELL basket and ends when both sides are flat. Realized commissions, swap, fees and stopped legs remain in the result while the corresponding cycle is open. The target triggers a close request, so actual exit costs and slippage can leave the final result slightly below it. Live cycle state is persisted across an EA restart. Grid is hedging-only and must be reoptimized after any EA, broker-contract or cost change.

## 청산 스택

Stop, ATR take, breakeven, ATR trailing, reversal exit는 독립적입니다. ReversalExitUseEntryFilters가 청산 필터를 제어합니다.

## 위험과 복구

PositionSizeMode 하나만 선택합니다. Percentage/Fixed-R은 stop이 필요하며 Grid/Martingale/D'Alembert는 연구용입니다.

## 시간, 인터페이스, WFO

브로커 서버 시간, 자정 통과, Saturday/Sunday 설정을 지원합니다. WFO는 IS/OOS를 정의합니다.

## Diagnostics and supplied utilities

The Experts/Journal tab is authoritative for rejected inputs, OrderCheck failures, news-calendar errors and close retries. Compile and run MQL5\Scripts\WhiteRabbit Filters SelfTest; its final line must report zero failures. Use White Rabbit News Exporter to build the test CSV, then verify its date range, currencies, delimiter and Common\Files location before a news-enabled backtest.

## 사이클 대시보드 텔레메트리

패널은 랏 계산과 바스켓 청산에 쓰이는 동일한 상태 스냅샷을 사용합니다.

- tick 주기 갱신은 초당 1회로 제한되며 초기화와 거래 이벤트는 즉시 갱신할 수 있습니다.
- Balance/Equity는 전체 계정입니다. Closed P&L은 OnInit 이후 변화이고 Open P&L/positions는 Symbol + Magic으로 필터한 현재 상태입니다.
- Martingale은 BUY/SELL별 연속 손실, 사이클 손실 횟수·총액, recovered, deficit, deficit × Multiplicador target을 표시합니다.
- MaxMartingaleSteps 초과 시 hard reset으로 기존 deficit을 버리고 다음 주문은 base lot을 씁니다. 방향별 최대 1개 포지션만 허용됩니다.
- D'Alembert는 BUY/SELL 현재 레벨과 정규화된 다음 랏을 표시합니다.
- Grid는 legs/volume, 비용 포함 realized, open P&L, cycle P&L, 시작 시 고정 target, remaining을 표시합니다.
- Anchor는 가장 최근 확정 포지션입니다. BUY는 anchor − ATR × DistanciaMinima 미만, SELL은 그 이상을 엄격히 요구하며 진행은 ATR로 표시됩니다.
- Separate는 flat이 된 방향의 사이클만 끝내고 Unified는 양쪽 모두 flat일 때 끝납니다. 처리 중 주문은 reset을 지연합니다.
- Target은 청산 요청을 시작할 뿐이며 실제 exit commission, fee, slippage로 최종 결과가 조금 낮을 수 있습니다.
- InterfaceLanguage는 11개 언어를 유지합니다. Auto는 Tester에서 English, live에서 터미널 언어를 사용하며 미번역 label은 English로 대체됩니다.

## 호환성과 제한

보수적인 규칙이며 브로커의 더 엄격한 제한이 우선합니다.

- Percentage와 Fixed-R은 AtivarStop=true가 필요합니다.
- Grid는 Monetary/Fixed Lot, Recovery_None, hedging account만 지원합니다.
- Grid는 take, 양수 DistanciaMinima, 최소 2의 제한이 필요합니다.
- 바스켓이 열려 있는 동안 해당 사이클의 실현 손실, swap, commission, fees는 목표 달성에 필요한 결과에 계속 포함되며 한 레그의 이익만으로 사라지지 않습니다.
- Grid_SeparateProfit에서 BUY와 SELL 사이클은 독립적입니다. 한 방향의 모든 포지션이 사라지면 그 방향 사이클은 종료되고 이후 진입은 종료된 적자를 이월하지 않는 새 사이클입니다.
- D'Alembert는 Fixed Lot, Grid_Disabled, DAlembertStep>0 전용입니다.
- Martingale은 MaxMartingaleSteps/MaxMartingaleLot을 따릅니다.
- OnOppositeOrder는 hedging, 양방향, grid 비활성이 필요합니다.
- News backtest는 Common\Files CSV가 필요합니다.
- 일정은 브로커 서버 시간을 사용합니다.
- 브로커별 suffix와 심볼 사양을 확인합니다.

## 검색된 set 라이브러리

개수는 파일과 매니페스트에서 읽습니다. 각 set은 연구 가설입니다. Counts and fingerprints were read at generation time.

| Folder | Sets | Purpose |
| --- | --- | --- |
| 01_Forex | 168 | Per-asset baselines — Forex. |
| 02_Metals | 18 | Per-asset baselines — Metals. |
| 03_Cryptocurrencies | 36 | Per-asset baselines — Cryptocurrencies. |
| 04_Indices_Energies | 42 | Per-asset baselines — Indices Energies. |
| 05_US_Stocks_CFD | 300 | Per-asset baselines — US Stocks CFD. |
| 06_Research_Matrix | 935 | Controlled one-axis research. |
| 07_Entry_System_Matrix | 3360 | Indicator × entry method × management matrix. |
| 08_Filter_Stack_Matrix | 320 | Signal-filter stack combinations. |
| 09_Risk_Engine_Matrix | 130 | Compatible sizing, risk and recovery models. |
| 10_Exit_Stack_Matrix | 720 | Exit-control stack combinations. |

## 위험 경고

EA, set, 과거 결과는 미래 성과를 보장하지 않습니다. OOS와 demo로 검증하십시오.

## 전체 inputs 참조

표는 소스 선언 순서이며 구분 문자열도 .set schema에 포함됩니다.

| No. | Section | Subsection | Parameter | Type | Default | Source description | Enum options | Operational notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | General | — | NomedaEstrategia | string | "White Rabbit X" | Strategy Name | — | Use within its declared section and validate the complete combination. |
| 2 | Entries, Signal and Position Management | — | TimeFrame | ENUM_ALLOWED_TIMEFRAMES | M1 | Entry timeframe | M1, M5, M15, M30, H1, H4, D1, W1 | Signal evaluation is gated to one decision per closed bar of this timeframe. |
| 3 | Entries, Signal and Position Management | Entry Indicator | myBlankSpaceEntryIndicator | string | "" | \|\|================== Entry Indicator ==================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 4 | Entries, Signal and Position Management | Entry Indicator | EntryIndicator | ENUM_ENTRY_INDICATOR | EntryIndicator_MACD | Selects the indicator used by Entry Method | EntryIndicator_MACD, EntryIndicator_EMA_Cross, EntryIndicator_Momentum, EntryIndicator_Stochastic, EntryIndicator_TRIX, EntryIndicator_RSI, EntryIndicator_CCI, EntryIndicator_WPR, EntryIndicator_DeMarker, EntryIndicator_MFI, EntryIndicator_OsMA, EntryIndicator_Ichimoku | Selects the engine; Fast_EMA, Slow_EMA and MACD_SMA are reused by that engine. |
| 5 | Entries, Signal and Position Management | Entry Indicator | InpAppliedPrice | ENUM_APPLIED_PRICE | PRICE_CLOSE | Applied price used by the selected indicator | — | Use within its declared section and validate the complete combination. |
| 6 | Entries, Signal and Position Management | Entry Indicator | Fast_EMA | int | 12 | First period: MACD/EMA fast; oscillator period; Stochastic %K; Ichimoku Tenkan | — | First sequential period; for Ichimoku this is Tenkan. |
| 7 | Entries, Signal and Position Management | Entry Indicator | Slow_EMA | int | 26 | Second period: MACD/EMA slow; Ichimoku Kijun | — | Second sequential period; for Ichimoku this is Kijun. |
| 8 | Entries, Signal and Position Management | Entry Indicator | MACD_SMA | int | 9 | Third period: MACD signal; oscillator signal; Stochastic %D; Ichimoku Senkou B | — | Third sequential period; for Ichimoku this is Senkou Span B. |
| 9 | Entries, Signal and Position Management | Entry Method | myBlankSpace1 | string | "" | \|\|===================== Entry Method =======================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 10 | Entries, Signal and Position Management | Entry Method | EntryMethod | ENUM_ENTRY_TRIGGER_MODE | EntryTrigger_All | Reversal, signal cross, reference cross or their combinations | EntryTrigger_Reversal, EntryTrigger_SignalCross, EntryTrigger_ReferenceCross, EntryTrigger_ReversalAndSignalCross, EntryTrigger_ReversalAndReferenceCross, EntryTrigger_SignalAndReferenceCross, EntryTrigger_All | And modes require both events on the same closed bar; All is OR. |
| 11 | Entries, Signal and Position Management | ATR Settings | myBlankSpace42 | string | "" | \|\|==================== ATR Settings =====================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 12 | Entries, Signal and Position Management | ATR Settings | ATR_TimeFrame | ENUM_ALLOWED_TIMEFRAMES | M1 | Time Frame ATR | M1, M5, M15, M30, H1, H4, D1, W1 | Use within its declared section and validate the complete combination. |
| 13 | Entries, Signal and Position Management | ATR Settings | PeriodoATR | int | 14 | ATR Period | — | Use within its declared section and validate the complete combination. |
| 14 | Entries, Signal and Position Management | Stop Loss | myBlankSpace4s2 | string | "" | \|\|====================== Stop Loss ======================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 15 | Entries, Signal and Position Management | Stop Loss | AtivarStop | bool | true | Enable Stop Loss | — | Required by Percentage and Fixed-R sizing; recommended for every non-grid baseline. |
| 16 | Entries, Signal and Position Management | Stop Loss | VelaStop | int | 0 | Stop Loss Candle | — | Use within its declared section and validate the complete combination. |
| 17 | Entries, Signal and Position Management | Stop Loss | Stop | double | 3 | Stop Loss ATR Multiplier | — | Use within its declared section and validate the complete combination. |
| 18 | Entries, Signal and Position Management | Take Profit | myBlankSpace101 | string | "" | \|\|===================== Take Profit =====================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 19 | Entries, Signal and Position Management | Take Profit | TakeOrganico | bool | false | Enable Organic ATR Take Profit | — | Use within its declared section and validate the complete combination. |
| 20 | Entries, Signal and Position Management | Take Profit | AtivarTake | bool | true | Enable Take Profit | — | Required by supported grid operation. |
| 21 | Entries, Signal and Position Management | Take Profit | VelaTake | int | 0 | Take Profit Candle | — | Use within its declared section and validate the complete combination. |
| 22 | Entries, Signal and Position Management | Take Profit | Take | double | 3 | Take Profit ATR Multiplier | — | Use within its declared section and validate the complete combination. |
| 23 | Signal Filters | MTF Alignment | myBlankSpaceMTF | string | "" | \|\|==================== MTF Alignment ====================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 24 | Signal Filters | MTF Alignment | AtivarFiltroMTF | bool | false | Enable MTF Filter | — | Higher-timeframe alignment uses the EA's MACD trend layer. |
| 25 | Signal Filters | MTF Alignment | MTF_RequererAmbos | bool | false | Require Both Higher Timeframes Aligned | — | Use within its declared section and validate the complete combination. |
| 26 | Signal Filters | Moving Average Filter | myBlankSpaceMA | string | "" | \|\|================ Moving Average Filter ================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 27 | Signal Filters | Moving Average Filter | AtivarFiltroMA | bool | false | Enable Moving Average Filter | — | Use within its declared section and validate the complete combination. |
| 28 | Signal Filters | Moving Average Filter | MA_TimeFrame | ENUM_ALLOWED_TIMEFRAMES | M1 | MA Timeframe | M1, M5, M15, M30, H1, H4, D1, W1 | Use within its declared section and validate the complete combination. |
| 29 | Signal Filters | Moving Average Filter | MA_Period | int | 200 | MA Period | — | Use within its declared section and validate the complete combination. |
| 30 | Signal Filters | Moving Average Filter | MA_Method | ENUM_MA_METHOD | MODE_EMA | MA Method | — | Use within its declared section and validate the complete combination. |
| 31 | Signal Filters | Moving Average Filter | MA_AppliedPrice | ENUM_APPLIED_PRICE | PRICE_CLOSE | Applied Price | — | Use within its declared section and validate the complete combination. |
| 32 | Signal Filters | Moving Average Filter | MetodoMA | MetodoFiltroMA | MA_PrecoEInclinacao | Price and Slope Rule | MA_ApenasPreco, MA_ApenasInclinacao, MA_PrecoEInclinacao, MA_PrecoOuInclinacao | Use within its declared section and validate the complete combination. |
| 33 | Signal Filters | Moving Average Filter | SentidoMA | SentidoFiltroMA | MA_Tendencia | Trend or Reversal Direction | MA_Tendencia, MA_Reversao | Use within its declared section and validate the complete combination. |
| 34 | Signal Filters | Moving Average Filter | MA_SlopeLookback | int | 3 | Slope Lookback Bars | — | Use within its declared section and validate the complete combination. |
| 35 | Signal Filters | ADX Filter | myBlankSpaceMA1 | string | "" | \|\|===================== ADX Filter ======================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 36 | Signal Filters | ADX Filter | AtivarFiltroADX | bool | false | Enable ADX Trend Strength Filter | — | Use within its declared section and validate the complete combination. |
| 37 | Signal Filters | ADX Filter | ADX_TimeFrame | ENUM_ALLOWED_TIMEFRAMES | M1 | ADX Timeframe | M1, M5, M15, M30, H1, H4, D1, W1 | Use within its declared section and validate the complete combination. |
| 38 | Signal Filters | ADX Filter | ADX_Period | int | 14 | ADX Period | — | Use within its declared section and validate the complete combination. |
| 39 | Signal Filters | ADX Filter | ADX_Limiar | double | 25 | Minimum ADX Value | — | Use within its declared section and validate the complete combination. |
| 40 | Signal Filters | ADX Filter | MetodoADX | MetodoFiltroADX | ADX_ApenasForca | Strength or Strength Plus Direction | ADX_ApenasForca, ADX_ForcaMaisDirecaoDI | Use within its declared section and validate the complete combination. |
| 41 | Signal Filters | Volatility Filter | myBlankSpaceVolatility | string | "" | \|\|================== Volatility Filter ==================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 42 | Signal Filters | Volatility Filter | EntradaATR | bool | false | Enable ATR Volatility Filter | — | Use within its declared section and validate the complete combination. |
| 43 | Signal Filters | Volatility Filter | VolatilityFilter | ENUM_VOLATILITY_MODE | VOL_HIGH | Trade Volatility Condition | VOL_LOW, VOL_HIGH | Use within its declared section and validate the complete combination. |
| 44 | Signal Filters | News Filter | myBlankSpaceNews | string | "" | \|\|===================== News Filter =====================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 45 | Signal Filters | News Filter | AtivarFiltroNoticias | bool | false | Enable News Filter | — | Live calendar errors block new entries; backtests require the exported CSV under Common\\Files. |
| 46 | Signal Filters | News Filter | NewsSomenteAltoImpacto | bool | false | High Impact Only | — | Use within its declared section and validate the complete combination. |
| 47 | Signal Filters | News Filter | NewsMinutosAntes | int | 15 | Minutes Blocked Before Event | — | Use within its declared section and validate the complete combination. |
| 48 | Signal Filters | News Filter | NewsMinutosDepois | int | 15 | Minutes Blocked After Event | — | Use within its declared section and validate the complete combination. |
| 49 | Signal Filters | News Filter | NewsMoedasManual | string | "" | Manual Currencies (e.g. "USD,EUR"); empty = auto by symbol | — | When non-empty, overrides automatic currency extraction; required for most suffixed/non-FX symbols. |
| 50 | Signal Filters | News Filter | NewsCSVFile | string | "WhiteRabbit_News.csv" | Common\\Files CSV for Backtests | — | Semicolon CSV in Common\\Files: datetime;currency;importance;event_name, using broker-server time. |
| 51 | Exit Management | — | AtivarBreakeven | bool | true | Enable Breakeven | — | Use within its declared section and validate the complete combination. |
| 52 | Exit Management | — | BreakevenDistancia | double | 1.0 | Breakeven Distance (SL or ATR Stop Multiplier) | — | Use within its declared section and validate the complete combination. |
| 53 | Exit Management | ATR Trailing | myBlankSpace46 | string | "" | \|\|==================== ATR Trailing =====================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 54 | Exit Management | ATR Trailing | AtivarTrailATR | bool | false | Enable ATR Trailing Stop | — | Use within its declared section and validate the complete combination. |
| 55 | Exit Management | ATR Trailing | MetodoDeCalculo | Candlesticktype | CandleClose | Trailing Price Source | CandleOpen, CandleClose, CandleHigh, CandleLow, Preco | Use within its declared section and validate the complete combination. |
| 56 | Exit Management | ATR Trailing | TrailVela | int | 0 | Trailing Candle | — | Use within its declared section and validate the complete combination. |
| 57 | Exit Management | ATR Trailing | Trail | double | 3 | Trail | — | Use within its declared section and validate the complete combination. |
| 58 | Exit Management | Reversal Exit | myBlankSpace10 | string | "" | \|\|==================== Reversal Exit ====================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 59 | Exit Management | Reversal Exit | ReversalExitMode | ENUM_REVERSAL_EXIT_MODE | ReversalExit_OnIndicatorSignal | Declared at source line 319. | ReversalExit_Disabled, ReversalExit_OnOppositeOrder, ReversalExit_OnIndicatorSignal | OnOppositeOrder requires a hedging account, both sides and grid disabled. |
| 60 | Exit Management | Reversal Exit | ReversalExitUseEntryFilters | bool | false | Apply entry filters to indicator exits | — | False uses the raw opposite indicator signal; true also requires entry filters. |
| 61 | Risk and Position Size | — | TradeCapitalPercentage | double | 100 | Percentage of Total Capital Allocated to EA | — | Allocation must be positive and no greater than the whole EA capital base. |
| 62 | Risk and Position Size | — | PositionSizeMode | ENUM_POSITION_SIZE_MODE | PositionSize_FixedLot | Declared at source line 351. | PositionSize_Percentage, PositionSize_Monetary, PositionSize_FixedLot, PositionSize_FixedR | Exactly one model is active; compatibility depends on stop and grid selections. |
| 63 | Risk and Position Size | — | PositionSizeValue | double | 0.01 | Percentage=% risk; Monetary=currency per 1.00 lot; Fixed Lot=lots; Fixed R=% of base capital per 1R | — | Meaning changes with PositionSizeMode; never compare raw values across modes. |
| 64 | Risk and Position Size | Fixed-R Controls | myBlankSpaceRF | string | "" | \|\|================== Fixed-R Controls ===================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 65 | Risk and Position Size | Fixed-R Controls | CapitalBaseR | double | 0 | Base Capital for 1R (0 = balance at OnInit) | — | Zero captures balance at initialization; Fixed-R only. |
| 66 | Risk and Position Size | Fixed-R Controls | MaxRiscoTradeR | double | 0 | Maximum Risk per Trade in R (0 = no cap) | — | Zero disables this additional Fixed-R cap. |
| 67 | Risk and Position Size | Daily Loss Limit | myBlankSpaceDL | string | "" | \|\|================== Daily Loss Limit ===================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 68 | Risk and Position Size | Daily Loss Limit | DailyLossLimitPercent | double | 0 | Maximum Daily Loss Percentage (0 = disabled) | — | Zero disables the daily limit; use a value below a total account loss. |
| 69 | Risk and Position Size | Equity/Margin Protection | myBlankSpaceRiskProtection | string | "" | \|\|============== Equity/Margin Protection ===============\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 70 | Risk and Position Size | Equity/Margin Protection | MaxEquityDrawdownPercent | double | 30.0 | Maximum EA drawdown before closing positions (0 = disabled) | — | Zero disables the EA equity stop. |
| 71 | Risk and Position Size | Equity/Margin Protection | MinFreeMarginPercent | double | 50.0 | Minimum free margin to preserve after a new entry (0 = disabled) | — | Zero disables the post-entry free-margin reserve. |
| 72 | Grid and Recovery | — | RecoveryMode | ENUM_RECOVERY_MODE | Recovery_None | Declared at source line 368. | Recovery_None, Recovery_Martingale, Recovery_DAlembert | None, Martingale or D'Alembert are mutually exclusive. |
| 73 | Grid and Recovery | Recovery Target | myBlankSpace457 | string | "" | \|\|=================== Recovery Target ===================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 74 | Grid and Recovery | Recovery Target | Multiplicador | double | 1 | Martingale or Grid Target Profit Multiplier | — | Recovery/grid target multiplier; validate a value greater than one where escalation is intended. |
| 75 | Grid and Recovery | Martingale Limits | myBlankSpace16 | string | "" | \|\|================== Martingale Limits ==================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 76 | Grid and Recovery | Martingale Limits | MaxMartingaleSteps | int | 0 | Consecutive Losses Before Reset (0 = no limit) | — | Zero means no step limit; exceeding a positive limit hard-resets the old deficit and forces the next order to the base lot. |
| 77 | Grid and Recovery | Martingale Limits | MaxMartingaleLot | double | 0.0 | Maximum Martingale or D'Alembert Lot (0 = broker limit only) | — | Zero means broker maximum only. |
| 78 | Grid and Recovery | DAlembert Settings | myBlankSpace_dal | string | "" | \|\|================= DAlembert Settings ==================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 79 | Grid and Recovery | DAlembert Settings | DAlembertStep | double | 0.01 | Lot Increment per Loss for D'Alembert | — | Must be positive; supported with Fixed Lot and grid disabled. |
| 80 | Grid and Recovery | Grid Settings | myBlankSpace17 | string | "" | \|\|==================== Grid Settings ====================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 81 | Grid and Recovery | Grid Settings | GridMode | ENUM_GRID_MODE | Grid_Disabled | Declared at source line 385. | Grid_Disabled, Grid_SeparateProfit, Grid_UnifiedProfit | Supported with Monetary or Fixed Lot sizing, Recovery_None and a hedging account; targets are frozen per cycle. |
| 82 | Grid and Recovery | Grid Settings | UsarsomenteATRGRID | bool | false | Use ATR Only as Grid Signal | — | Research switch; require an existing basket anchor before adding a grid leg. |
| 83 | Grid and Recovery | Grid Settings | DistanciaMinima | double | 2 | ATR Distance Multiplier for Next Grid Order | — | Positive ATR-distance multiplier between grid entries. |
| 84 | Trading Schedule | Trading Hours | myBlankSpaceTradingHours | string | "" | \|\|==================== Trading Hours ====================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 85 | Trading Schedule | Trading Hours | Fecharordensforadohorario | bool | false | Close Positions Outside Trading Hours | — | When enabled, positions are closed whenever server time is outside the interval. |
| 86 | Trading Schedule | Trading Hours | TOD_From_Hour | int | 00 | Trading Start Hour | — | Use within its declared section and validate the complete combination. |
| 87 | Trading Schedule | Trading Hours | TOD_From_Min | int | 00 | Trading Start Minute | — | Use within its declared section and validate the complete combination. |
| 88 | Trading Schedule | Trading Hours | TOD_To_Hour | int | 23 | Trading End Hour | — | Use within its declared section and validate the complete combination. |
| 89 | Trading Schedule | Trading Hours | TOD_To_Min | int | 55 | Trading End Minute | — | Use within its declared section and validate the complete combination. |
| 90 | Trading Schedule | Trading Days | myBlankSpaceTradingDays | string | "" | \|\|==================== Trading Days =====================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 91 | Trading Schedule | Trading Days | TradeMonday | bool | true | Allow Trading on Monday | — | Use within its declared section and validate the complete combination. |
| 92 | Trading Schedule | Trading Days | TradeTuesday | bool | true | Allow Trading on Tuesday | — | Use within its declared section and validate the complete combination. |
| 93 | Trading Schedule | Trading Days | TradeWednesday | bool | true | Allow Trading on Wednesday | — | Use within its declared section and validate the complete combination. |
| 94 | Trading Schedule | Trading Days | TradeThursday | bool | true | Allow Trading on Thursday | — | Use within its declared section and validate the complete combination. |
| 95 | Trading Schedule | Trading Days | TradeFriday | bool | true | Allow Trading on Friday | — | Use within its declared section and validate the complete combination. |
| 96 | Trading Schedule | Trading Days | TradeSaturday | bool | false | Allow Trading on Saturday | — | Explicit weekend permission; useful only when the broker symbol trades Saturday. |
| 97 | Trading Schedule | Trading Days | TradeSunday | bool | false | Allow Trading on Sunday | — | Explicit weekend permission; useful only when the broker symbol trades Sunday. |
| 98 | General Settings | Market Execution | myBlankSpaceExecution | string | "" | \|\|================== Market Execution ===================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 99 | General Settings | Market Execution | MaxSpread | double | 0 | Maximum Allowed Spread for New Trades | — | Zero disables the entry spread ceiling. |
| 100 | General Settings | Market Execution | MaxSlippage | int | 10 | Slippage, ajustado no OnInit | — | Use within its declared section and validate the complete combination. |
| 101 | General Settings | Position Exposure | myBlankSpaceExposure | string | "" | \|\|================== Position Exposure ==================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 102 | General Settings | Position Exposure | MaxLongTrades | int | 1 | Maximum Simultaneous BUY Positions | — | Zero disables BUY entries; grid sides require zero or at least two, while Martingale permits at most one. |
| 103 | General Settings | Position Exposure | MaxShortTrades | int | 1 | Maximum Simultaneous SELL Positions | — | Zero disables SELL entries; grid sides require zero or at least two, while Martingale permits at most one. |
| 104 | General Settings | Position Exposure | Hedging | bool | false | Allow Hedging | — | Does not change the account type; the real MT5 account must also support hedging. |
| 105 | General Settings | Identity and Interface | myBlankSpaceInterface | string | "" | \|\|=============== Identity and Interface ================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 106 | General Settings | Identity and Interface | MagicNumber | int | 384457 | Magic Number | — | Must be unique for each independent strategy/symbol scope. |
| 107 | General Settings | Identity and Interface | ModificationSafetyPoints | int | 0 | Optional extra distance beyond broker limits and current spread | — | Additional points beyond broker distance/spread constraints. |
| 108 | General Settings | Identity and Interface | InterfaceLanguage | ENUM_INTERFACE_LANGUAGE | Language_Auto | Live chart interface language | Language_Auto, Language_English, Language_Portuguese, Language_Russian, Language_Chinese, Language_Spanish, Language_Japanese, Language_German, Language_Korean, Language_French, Language_Italian, Language_Turkish | Eleven live/visual UI languages; Auto uses English in Tester and untranslated labels fall back to English. |
| 109 | General Settings | Chart Dashboard | myBlankSpaceDashboard | string | "" | \|\|================== Chart Dashboard ==================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 110 | General Settings | Chart Dashboard | EnableChartDashboard | bool | true | Show visual P&L panel on live and visual tester charts | — | Live/visual panel; periodic tick refresh is capped at once per second. |
| 111 | General Settings | Chart Dashboard | DashboardCorner | ENUM_BASE_CORNER | CORNER_LEFT_UPPER | Dashboard chart corner | — | Use within its declared section and validate the complete combination. |
| 112 | General Settings | Chart Dashboard | DashboardOffsetX | int | 12 | Horizontal offset in pixels | — | Use within its declared section and validate the complete combination. |
| 113 | General Settings | Chart Dashboard | DashboardOffsetY | int | 24 | Vertical offset in pixels | — | Use within its declared section and validate the complete combination. |
| 114 | General Settings | Chart Dashboard | ShowClosedDealLabels | bool | true | Show monetary and percentage result at each closed trade | — | Use within its declared section and validate the complete combination. |
| 115 | General Settings | Chart Dashboard | MaxVisibleDealLabels | int | 120 | Maximum closed-trade labels kept on chart | — | Use within its declared section and validate the complete combination. |
| 116 | General Settings | Chart Dashboard | ClosedDealLabelFontSize | int | 10 | Closed-trade label font size | — | Use within its declared section and validate the complete combination. |
| 117 | General Settings | Chart Dashboard | ApplyEmbeddedChartTheme | bool | true | Apply the White Rabbit X clean chart style on every machine | — | Use within its declared section and validate the complete combination. |
| 118 | Optimization (WFO) | — | AtivarWFO | bool | false | Enable WFO | — | Enables the internal WFO boundary logic; still requires an external chronological process. |
| 119 | Optimization (WFO) | — | MetodoDeEntradawfo | WFOTIPO | Insample | Optimization Mode | Insample, InSampleAndOutSample | Use within its declared section and validate the complete combination. |
| 120 | Optimization (WFO) | — | input_end_date | string | "2025.02.28" | Backtest End Date (manual) | — | Manual tester end date; keep synchronized with the selected test range. |
| 121 | Optimization (WFO) | WFO Periods | myBlankSpaceWFOPeriods | string | "" | \|\|===================== WFO Periods =====================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 122 | Optimization (WFO) | WFO Periods | wfo_windowSize | WFO_TIME_PERIOD | Ano | In-Sample Window Size | Nenhum, Ano, Semestre, Trimestre, Mes, Semana, Dia, Custom | Use within its declared section and validate the complete combination. |
| 123 | Optimization (WFO) | WFO Periods | wfo_customWindowSizeDays | int | 0 | Custom Window Size in Days (0 = unused) | — | Use within its declared section and validate the complete combination. |
| 124 | Optimization (WFO) | WFO Periods | wfo_stepSize | WFO_TIME_PERIOD | Semestre | Out-of-Sample Step Size | Nenhum, Ano, Semestre, Trimestre, Mes, Semana, Dia, Custom | Use within its declared section and validate the complete combination. |
| 125 | Optimization (WFO) | WFO Periods | wfo_customStepSizePercent | int | 0 | Custom Step Size in Days or Percentage | — | Custom step: positive=percentage of IS; negative=fixed number of OOS days (for example -61). |
| 126 | Optimization (WFO) | Optimization Criterion | myBlankSpace4447 | string | "" | \|\|=============== Optimization Criterion ================\|\| | — | Visual separator retained for .set schema compatibility; do not optimize. |
| 127 | Optimization (WFO) | Optimization Criterion | selectedFormula | CustomFormulaType | Formula_ProfitPerTradeAdjustedByDD | Custom Optimization Formula | Formula_None, Formula_GridSurvivalScore, Formula_Profit, Formula_ProfitWinTradeDD, Formula_EfficiencyRelativeToDeposit, Formula_AdjustedEfficiencyForGrid, Formula_ProfitRelativeToDDAndDeposit, Formula_ProfitPerTradeAdjustedByDD, Formula_SharpeAdjustedByDD, Formula_PessimisticProfit, Formula_ResilienceToDrawdown, Formula_ReturnUniformity, Formula_SystemRobustness, Formula_LevainCompositeScore, Formula_SomaR | Optimization criterion only; inspect stability and OOS results before selection. |

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
