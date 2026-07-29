# White Rabbit X — WFO 最適化ガイド

現在の EA ソースと set マニフェストから生成した正式リファレンス — EA 1.11 — 127 inputs — 3738 sets

**日付に注意。** WFO を有効にすると、OnTester はテストの実際の終了時刻を input_end_date と比較し、テストがそれより早く終わっていた場合はゼロを返します（許容範囲 80 時間）。日付を誤ると全パスがゼロになり、最適化全体が壊れているように見えます。input_end_date はストラテジーテスターで設定した終了日と同じにしてください。

## 範囲と正本

EA ソースが inputs、既定値、機能を定義し、マニフェストが各 set の状態、パス、SHA-256 を定義します。旧 Quantum 資料は履歴専用です。

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

自動生成資料。パラメータ識別子は EA と完全に一致します。

## Walk-forward 手法

時系列 IS、OOS、forward demo を現実的な spread、commission、swap、slippage で実施します。

## 安全な手順

各段階で一つのマトリクスだけ変更し、証拠を保存します。

1. EX5、ソース、set schema、マニフェストの版を一致させます。
2. Strategy Tester Inputs からライブラリを読み込みます。
3. 正確な銘柄と suffix を対応させます。
4. 01–05 baseline から BUY/SELL を別々に試します。
5. 06 は単一軸研究です。
6. 07 entry、08 filter、09 risk、10 exit の順に検証します。
7. IS、OOS、forward demo を時系列で行います。
8. Status、RelativePath、SHA256 を確認します。
9. 明示的 USE のみが定義環境での使用候補です。

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

## リスク警告

EA、set、過去結果は将来を保証しません。OOS と demo で検証してください。

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
