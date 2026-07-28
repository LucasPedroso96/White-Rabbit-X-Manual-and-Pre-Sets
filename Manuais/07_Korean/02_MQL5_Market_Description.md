# White Rabbit X — MQL5 Market 설명

현재 EA 소스와 set 매니페스트에서 생성한 공식 참조 — EA 1.11 — 127 inputs — 3738 sets

## 소프트웨어 기능

White Rabbit X는 체계적 연구, 통제 실행, WFO용 MT5 멀티 인디케이터 EA입니다.

Current schema: 127 inputs. Current manifest: 3738 sets.

- 12개 네이티브 엔진: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA, Ichimoku.
- 확정 봉의 AND/OR 의미가 명확한 7개 진입 방식.
- 독립적인 MTF, MA, ADX, ATR, news 필터.
- 4개 PositionSizeMode와 equity/margin 보호.
- Stop, take, breakeven, trailing, reversal 청산.
- Dashboard, 일정, 언어, WFO 통합.

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

## 커뮤니티 및 다운로드

공식 텔레그램 채널에 참여하세요: **https://t.me/MrRabbit_MT5**

- 종목별·시스템 유형별(SL/TP, 트레일링, 그리드, 마틴게일 등)로 정리된 완성 세트 파일. 전략 테스터에 바로 불러올 수 있습니다.
- 사용 언어별 매뉴얼: 포르투갈어, 영어, 러시아어, 중국어, 스페인어, 일본어, 독일어, 한국어, 프랑스어, 이탈리아어, 터키어.
- EA 및 세트 라이브러리 업데이트 공지.
- 지원 및 다른 사용자와의 경험 공유.

> 공식 채널은 이곳뿐입니다. White Rabbit X를 대리한다고 주장하는 제3자에게서 세트나 EA 사본을 구매하지 마십시오. 본 EA는 MQL5 Market에서만 판매되며 세트는 위 채널에서 무료로 배포됩니다.

## 위험 경고

EA, set, 과거 결과는 미래 성과를 보장하지 않습니다. OOS와 demo로 검증하십시오.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
