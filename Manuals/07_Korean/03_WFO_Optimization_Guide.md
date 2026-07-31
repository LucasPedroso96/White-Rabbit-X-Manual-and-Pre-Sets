# White Rabbit X — WFO 최적화 가이드

현재 EA 소스와 set 매니페스트에서 생성한 공식 참조 — EA 1.11 — 127 inputs — 3738 sets

**날짜에 주의하십시오.** WFO를 켜면 OnTester가 테스트의 실제 종료 시점을 input_end_date와 비교하여, 테스트가 더 일찍 끝났으면 0을 반환합니다(허용 오차 80시간). 날짜가 틀리면 모든 패스가 0이 되고 최적화 전체가 고장난 것처럼 보입니다. input_end_date를 전략 테스터에 설정한 종료일과 동일하게 맞추십시오.

## 범위와 기준 데이터

EA 소스가 inputs, 기본값, 기능을 정의하고 매니페스트가 각 set의 상태, 경로, SHA-256을 정의합니다. 구 Quantum 자료는 기록용입니다.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

자동 생성 문서이며 파라미터 식별자는 EA와 정확히 같습니다.

## Walk-forward 방법

현실적인 spread, commission, swap, slippage로 IS, OOS, forward demo를 시간순 실행합니다.

## 안전한 절차

단계마다 한 매트릭스만 변경하고 근거를 보관하십시오.

1. EX5, 소스, set schema, 매니페스트 버전을 일치시킵니다.
2. Strategy Tester Inputs에서 라이브러리를 로드합니다.
3. 정확한 브로커 심볼과 suffix를 매핑합니다.
4. 클래스와 종목으로 탐색합니다. 각 종목에는 11개 시스템 유형(01_SLTP~11_SIGNAL_ONLY)이 있고, 방향별 set 하나(BUY/SELL, 통합 그리드는 BOTH), 진입은 두 변형 — MULTI는 단일 축에서 지표 0–10을 경쟁시키고 ICHIMOKU는 전용 파일입니다.
5. 1단계는 영역 탐색입니다. set을 그대로 유전 최적화에 돌립니다 — 진입 그룹 전체(지표, 방식, 타임프레임, applied price, 기간), 시스템의 청산, 필터 스위치를 한 번에 모두 엽니다.
6. 다음 라운드부터는 이전 단계에서 결정된 ‘문자형’ 입력(enum·bool)을 Y→N으로 잠그고 숫자형만 열어 둡니다. 필터 미세 조정은 스위치가 켜진 채 살아남은 경우에만 들어갑니다.
7. ATR 진입 필터(EntradaATR)는 그리드 시스템에만 존재하며, 그 외에서는 설계상 꺼져 있습니다.
8. 승자는 실제 틱으로 검증합니다. OHLC 대비 괴리와 표본 외 보존율이 결정하며, 표본 내 수익이 아닙니다.
9. 실제 틱 이후 포지션 사이징을 Percentage로 바꿔 다시 실행하고, 이것도 통과할 때만 승격합니다 — set이 운용될 모드도 바로 이것입니다.

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

> 이 섹션은 현재 영어로만 제공됩니다.

## Modeling mode: use real ticks

In the Strategy Tester's **Settings** tab, **Modeling** field:

```
Every tick based on real ticks   <- use this
OHLC 1 minute                    <- only 01_SLTP and 02_SLTP_ORGANIC
```

This is not a preference. Measuring the same set in both modes across three
years, the OHLC mode **understated losses by 3.3x on trailing systems and 23x
on grid** — always in the optimistic direction. Only fixed SL/TP stayed within
3%.

The cause is structural: trailing and grid depend on **when** price touched each
level inside the bar. OHLC mode interpolates that from four prices per minute
and smooths away exactly the adverse excursions that would have closed the
position. Optimizing a trailing system on interpolated bars selects parameters
that survived a price path which never happened.

Real ticks cost roughly 20x more time per pass. It is worth it: that is the
difference between a result and a number.

### If you must save time, save it in the right place

Signals are evaluated at BAR CLOSE, so choosing indicator, method or timeframe
gives the same entry instant in both modes. Stop, target and trailing, on the
other hand, depend on the intrabar path.

So use each model where it is reliable: OHLC to narrow the switches (indicator,
method, timeframe, periods) and real ticks for the exit geometry. With the
signal locked the search space collapses by orders of magnitude, and real ticks
stop being prohibitive.

## Fixed-R to research, percentage to trade

Optimize in **Fixed-R**: with the base capital frozen, passes stay comparable to
each other and across symbols. +40R on gold and +40R on EURUSD mean the same
thing, while "+3,200 USD" means nothing without knowing the lot and the balance.

Live, **Percentage** usually makes more sense: it tracks the account, compounds
as it grows and cuts exposure as it shrinks — protection Fixed-R cannot give,
because it deliberately ignores the running balance. Both modes report in R, so
the record stays readable after the switch.

그래서 이 절차는 최종 패스를 Percentage 모드로 반복한 뒤에만 승인된 set을 저장합니다. 복리 하에서 결과가 유지되지 않으면 아직 준비되지 않은 것이며, 검증된 set은 바로 그 모드로 제공됩니다.

## 위험 경고

EA, set, 과거 결과는 미래 성과를 보장하지 않습니다. OOS와 demo로 검증하십시오.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
