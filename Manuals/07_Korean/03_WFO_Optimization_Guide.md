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
4. 01–05 baseline에서 BUY/SELL을 분리해 시작합니다.
5. 06은 단일 축 연구입니다.
6. 07 진입, 08 필터, 09 위험, 10 청산 순서입니다.
7. IS, OOS, forward demo를 시간순 실행합니다.
8. Status, RelativePath, SHA256을 확인합니다.
9. 명시적 USE만 정의된 환경의 사용 후보입니다.

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

## 위험 경고

EA, set, 과거 결과는 미래 성과를 보장하지 않습니다. OOS와 demo로 검증하십시오.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
