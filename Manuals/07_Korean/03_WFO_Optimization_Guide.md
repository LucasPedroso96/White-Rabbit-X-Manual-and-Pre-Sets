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
8. 승자는 실제 틱으로 검증합니다. OHLC 대비 괴리와 표본 외 보존율이 결정하며, 표본 내 수익이 아닙니다. 실제 틱 결과가 OHLC 결과와 30%를 넘게 벌어지는 후보는 탈락시키십시오 — 둘은 부호뿐 아니라 결과의 형태에서도 일치해야 합니다.
8a. Monte Carlo로 생존자를 게이트합니다: 거래 순서를 (통화가 아닌 R 배수로) 부트스트랩 재표본추출하고, 95번째 백분위 드로다운이 관측된 드로다운의 두 배를 넘거나 재표본 파산 확률이 5%를 넘으면 탈락시킵니다. 거래가 우연히 발생한 특정 순서 때문에 안정적으로 보이기만 하는 세트는 안정적인 것이 아닙니다.
8b. 여섯 개의 Fixed-R 시스템(`01`~`06`)에 대해서는 표본 외 R-기댓값이 양수일 것을 요구합니다. 표본 외에서 손익분기 또는 R 손실을 낸 세트는 표본 내 점수와 관계없이 승격되지 않습니다.
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

## 공식: 무엇을 최적화하고, 무엇이 결과를 보고하는가

`selectedFormula`는 OnTester가 유전 최적화기에 무엇을 반환할지 — 각 패스가 순위 매겨지는 단일 숫자 — 를 결정합니다. 이는 "제공되는 세트가 어떤 단위로 결과를 보고하는가"와는 다른 질문입니다. 이 절차는 작업마다 다른 공식을 사용합니다: 초기 단계는 하나의 경로에서만 높은 점수를 받는 좁은 공식이 아니라, 유전 탐색이 오를 기울기를 가질 수 있도록 넓고 잘 채워진 결과에 보상하는 공식을 선호합니다.

여섯 개의 Fixed-R 시스템의 경우, 제공되는 세트의 최종 보고서는 **SomaR**(R 배수로 표시한 거래 결과의 합)를 사용합니다: 후보가 이미 보존율, 괴리, Monte Carlo, 그리고 위의 R-기댓값 게이트를 통과한 뒤에는, SomaR가 이 가이드의 나머지 부분이 종목과 시스템을 비교하는 데 쓰는 것과 같은 단위 — 통화가 아닌 R — 로 결과를 표시합니다. 이는 승자를 결정하는 것이 아니라, 이미 승자가 된 세트의 결과를 비교 가능한 단위로 보고할 뿐입니다.

## Autobot과 Historical Tool Manager

이 라이브러리는 사전 검증된 상태로 제공되지만, 위의 절차는 블랙박스가 아닙니다 — 이 매뉴얼이 있는 동일한 저장소에 **Autobot**(`Autobot/`)으로 공개되어 있으며, 이 가이드의 모든 단계를 실제로 실행하는 코드입니다. 세트가 정확히 어떻게 그 지위를 얻었는지 확인하려면 읽어 보거나, 자신의 브로커, 종목 목록, 기간에 대해 직접 실행해 볼 수 있습니다.

실제 틱 확인 단계는 대조할 실제 틱 데이터가 있어야 합니다. **Historical Tool Manager**(MQL5 Market: https://www.mql5.com/pt/market/product/188711)는 브로커 자체의 이력이 충분히 오래되지 않은 종목에 대해 깊은 tick 및 M1 이력을 Custom Symbol 형태로 MT5에 가져옵니다 — Autobot을 실행하든, 수동 테스트를 위해 더 많은 이력을 원하든 유용합니다.

## 위험 경고

EA, set, 과거 결과는 미래 성과를 보장하지 않습니다. OOS와 demo로 검증하십시오.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
