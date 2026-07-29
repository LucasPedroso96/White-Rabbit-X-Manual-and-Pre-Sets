# White Rabbit X — 기술 호환성

현재 EA 소스와 set 매니페스트에서 생성한 공식 참조 — EA 1.11 — 127 inputs — 3738 sets

## 범위와 기준 데이터

EA 소스가 inputs, 기본값, 기능을 정의하고 매니페스트가 각 set의 상태, 경로, SHA-256을 정의합니다. 구 Quantum 자료는 기록용입니다.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

자동 생성 문서이며 파라미터 식별자는 EA와 정확히 같습니다.

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

## 신호와 진입 방식

6개 엔진은 reversal, signal/reference cross, baseline/reference cross를 공유합니다. And는 같은 종가 확정 봉, All은 어느 하나입니다.

- EntryIndicator: MACD, EMA_Cross, Momentum, Stochastic, TRIX, RSI, CCI, WPR, DeMarker, MFI, OsMA, Ichimoku.
- EntryMethod: Reversal, SignalCross, ReferenceCross, ReversalAndSignalCross, ReversalAndReferenceCross, SignalAndReferenceCross, All.
- PositionSizeMode: Percentage, Monetary, FixedLot, FixedR.
- RecoveryMode: None, Martingale, DAlembert.
- GridMode: Disabled, SeparateProfit, UnifiedProfit.

## News filter and CSV workflow

Live mode reads the MT5 Economic Calendar in broker-server time and blocks new entries if the calendar query fails. Backtests cannot read that live calendar: run MQL5\Scripts\White Rabbit News Exporter on a live/demo chart, cover the entire test interval, and write NewsCSVFile to the terminal Common\Files folder. The semicolon-delimited header is datetime;currency;importance;event_name, where importance 2 is moderate and 3 is high. Use the same broker/server timezone; for suffixed or non-FX symbols set ExportMoedas and NewsMoedasManual explicitly. Manual currencies take precedence over automatic symbol parsing.

## Grid cycle and ATR spacing

Every additional grid leg is measured from the newest already-confirmed position on that side and must satisfy ATR × DistanciaMinima. The initial order cannot recursively trigger another leg in the same calculation event; it becomes the anchor on the following cycle. Individual grid take-profits are disabled: Separate mode evaluates independent BUY/SELL cycles against frozen monetary targets and ends a side when it becomes flat; Unified evaluates the aggregate BUY+SELL basket and ends when both sides are flat. Realized commissions, swap, fees and stopped legs remain in the result while the corresponding cycle is open. The target triggers a close request, so actual exit costs and slippage can leave the final result slightly below it. Live cycle state is persisted across an EA restart. Grid is hedging-only and must be reoptimized after any EA, broker-contract or cost change.

## 상태와 배포 판단

원래 상태를 유지하고 USE, REOPTIMIZE, RESEARCH, HOLD로 보수적으로 매핑합니다.

| 시스템 | 관리 방식 | 세트 |
| --- | --- | ---: |
| `01_SLTP` | Stop Loss + Take Profit as ATR multiples | 356 |
| `02_SLTP_ORGANIC` | SL + organic take anchored on the last trade | 356 |
| `03_TRAIL_ONLY` | SL + trailing, no TP: let it run | 356 |
| `04_SLTP_TRAIL` | SL + TP + trailing behind | 356 |
| `05_BE_TRAIL` | Mandatory breakeven + trailing | 356 |
| `06_REVERSAL_EXIT` | Closes on the indicator's opposite signal | 356 |
| `07_GRID_SEPARATE` | Grid with a target per side (hedging account) | 356 |
| `08_GRID_UNIFIED` | Grid with a single basket target (hedging account) | 356 |
| `09_MARTINGALE` | Lot doubles after a loss, one position per side | 356 |
| `10_DALEMBERT` | Lot grows in arithmetic steps after a loss | 356 |
| `11_SIGNAL_ONLY` | No SL and no TP: measures the raw signal | 356 |

## Diagnostics and supplied utilities

The Experts/Journal tab is authoritative for rejected inputs, OrderCheck failures, news-calendar errors and close retries. Compile and run MQL5\Scripts\WhiteRabbit Filters SelfTest; its final line must report zero failures. Use White Rabbit News Exporter to build the test CSV, then verify its date range, currencies, delimiter and Common\Files location before a news-enabled backtest.

## 위험 경고

EA, set, 과거 결과는 미래 성과를 보장하지 않습니다. OOS와 demo로 검증하십시오.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
