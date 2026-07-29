# White Rabbit X — 技術互換性

現在の EA ソースと set マニフェストから生成した正式リファレンス — EA 1.11 — 127 inputs — 3738 sets

## 範囲と正本

EA ソースが inputs、既定値、機能を定義し、マニフェストが各 set の状態、パス、SHA-256 を定義します。旧 Quantum 資料は履歴専用です。

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

自動生成資料。パラメータ識別子は EA と完全に一致します。

## サイクル・ダッシュボードのテレメトリ

パネルはロット計算とバスケット決済と同じ状態スナップショットを使用します。

- tick の定期更新は毎秒 1 回までです。初期化と取引イベントは即時更新できます。
- Balance/Equity は口座全体です。Closed P&L は OnInit 以降の差分、Open P&L と positions は Symbol + Magic で絞った現在値です。
- Martingale は BUY/SELL 別に連続損失、サイクル損失回数・総額、recovered、deficit、deficit × Multiplicador の target を表示します。
- MaxMartingaleSteps 超過で hard reset し、旧 deficit を破棄して次注文を base lot にします。各側の保有は最大 1 です。
- D'Alembert は BUY/SELL の現在レベルと正規化した次ロットを表示します。
- Grid は legs/volume、コスト込み realized、open P&L、cycle P&L、開始時に固定した target、remaining を表示します。
- Anchor は直近の確定ポジションです。BUY は anchor − ATR × DistanciaMinima 未満、SELL は anchor + ATR × DistanciaMinima 超を厳密に要求し、進捗は ATR で示します。
- Separate は flat になった側だけ終了し、Unified は BUY/SELL 両方が flat で終了します。処理中注文は reset を遅らせます。
- Target は決済要求のトリガーです。実際の exit commission、fee、slippage により最終値が少し下回る場合があります。
- InterfaceLanguage は 11 言語を維持します。Auto は Tester で English、live で端末言語を使い、未翻訳 label は English にフォールバックします。

## 互換性と制約

これは保守的な規則で、ブローカー制限が優先されます。

- Percentage と Fixed-R は AtivarStop=true が必須です。
- Grid は Monetary/Fixed Lot、Recovery_None、hedging account のみです。
- Grid は take、正の DistanciaMinima、2 以上の上限が必要です。
- バスケットが開いている間、そのサイクルの確定損失、swap、commission、fees は目標到達に必要な結果へ残り、単独レッグの利益では消えません。
- Grid_SeparateProfit では BUY/SELL のサイクルは独立します。一方の全ポジションがなくなるとその側のサイクルは終了し、次のエントリーは終了済み損失を持ち越さない新サイクルです。
- D'Alembert は Fixed Lot、Grid_Disabled、DAlembertStep>0 のみです。
- Martingale は MaxMartingaleSteps/MaxMartingaleLot に従います。
- OnOppositeOrder は hedging、両方向、grid 無効が必要です。
- News backtest は Common\Files の CSV が必要です。
- 時間はブローカーサーバー基準です。
- suffix と銘柄仕様をブローカーごとに確認します。

## シグナルとエントリー

6 エンジンは reversal、signal/reference cross、baseline/reference cross を共有します。And は同じ確定足、All はいずれかを意味します。

- EntryIndicator: MACD, EMA_Cross, Momentum, Stochastic, TRIX, RSI, CCI, WPR, DeMarker, MFI, OsMA, Ichimoku.
- EntryMethod: Reversal, SignalCross, ReferenceCross, ReversalAndSignalCross, ReversalAndReferenceCross, SignalAndReferenceCross, All.
- PositionSizeMode: Percentage, Monetary, FixedLot, FixedR.
- RecoveryMode: None, Martingale, DAlembert.
- GridMode: Disabled, SeparateProfit, UnifiedProfit.

## News filter and CSV workflow

Live mode reads the MT5 Economic Calendar in broker-server time and blocks new entries if the calendar query fails. Backtests cannot read that live calendar: run MQL5\Scripts\White Rabbit News Exporter on a live/demo chart, cover the entire test interval, and write NewsCSVFile to the terminal Common\Files folder. The semicolon-delimited header is datetime;currency;importance;event_name, where importance 2 is moderate and 3 is high. Use the same broker/server timezone; for suffixed or non-FX symbols set ExportMoedas and NewsMoedasManual explicitly. Manual currencies take precedence over automatic symbol parsing.

## Grid cycle and ATR spacing

Every additional grid leg is measured from the newest already-confirmed position on that side and must satisfy ATR × DistanciaMinima. The initial order cannot recursively trigger another leg in the same calculation event; it becomes the anchor on the following cycle. Individual grid take-profits are disabled: Separate mode evaluates independent BUY/SELL cycles against frozen monetary targets and ends a side when it becomes flat; Unified evaluates the aggregate BUY+SELL basket and ends when both sides are flat. Realized commissions, swap, fees and stopped legs remain in the result while the corresponding cycle is open. The target triggers a close request, so actual exit costs and slippage can leave the final result slightly below it. Live cycle state is persisted across an EA restart. Grid is hedging-only and must be reoptimized after any EA, broker-contract or cost change.

## 状態とリリース判断

元の状態を保持し、USE、REOPTIMIZE、RESEARCH、HOLD に保守的に分類します。

| システム | 管理方式 | セット |
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

## リスク警告

EA、set、過去結果は将来を保証しません。OOS と demo で検証してください。

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
