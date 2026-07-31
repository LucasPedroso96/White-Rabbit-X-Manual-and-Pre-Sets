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
4. クラスと銘柄で辿ります。各銘柄には 11 のシステムタイプ（01_SLTP〜11_SIGNAL_ONLY）があり、方向ごとに 1 つの set（BUY/SELL、統合グリッドは BOTH）、エントリーは 2 変種 — MULTI は単一軸でインジケーター 0–10 を競わせ、ICHIMOKU は専用ファイルです。
5. フェーズ 1 は領域探索です。set をそのまま遺伝的最適化にかけます — エントリー群一式（インジケーター、メソッド、タイムフレーム、applied price、期間）、システムの決済、フィルターのスイッチを一度にすべて開きます。
6. 次のラウンド以降は、前フェーズで決まった「文字型」入力（enum と bool）を Y→N で固定し、数値型だけを開けたままにします。フィルターの調整は、そのスイッチが ON で生き残った場合にのみ入ります。
7. ATR エントリーフィルター（EntradaATR)はグリッド系のみに存在し、他では設計上オフのままです。
8. 勝者はリアルティックで検証します。OHLC との乖離とアウトオブサンプル保持率が決め手であり、インサンプル利益ではありません。
9. リアルティックの後、ロット計算を Percentage に切り替えて再実行し、これも通過した場合のみ昇格させます — set が運用されるべきモードもこれです。

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

> このセクションは現在英語のみです。

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

そのため本フローでは、最終パスを Percentage モードで再実行して初めて承認済み set を保存します。複利の下で結果が維持できなければ、それはまだ完成ではありません — 検証済み set はそのモードで出荷されます。

## リスク警告

EA、set、過去結果は将来を保証しません。OOS と demo で検証してください。

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
