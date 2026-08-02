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
8. 勝者はリアルティックで検証します。OHLC との乖離とアウトオブサンプル保持率が決め手であり、インサンプル利益ではありません。リアルティックの結果が OHLC の結果と 30% を超えて乖離する候補は却下してください——両者は結果の符号だけでなく、形状についても一致すべきです。
8a. Monte Carlo で生存者をゲートします。トレード列を（通貨ではなく R 倍数で）ブートストラップ再サンプリングし、95 パーセンタイルのドローダウンが実測ドローダウンの 2 倍を超える場合、または再サンプリングした破産確率が 5% を超える場合は却下します。トレードが発生したたまたまの順序のせいで安定しているように見えるだけのセットは、安定しているとは言えません。
8b. 6 つの Fixed-R システム（`01`〜`06`）については、アウトオブサンプルの R 期待値がプラスであることを要求します。アウトオブサンプルで収支が均衡したか R を失ったセットは、インサンプルでの成績にかかわらず昇格させません。
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

## 数式：何を最適化し、何が結果を報告するか

`selectedFormula` は、遺伝的最適化器に OnTester が何を返すか——各パスがランク付けされる唯一の数値——を決定します。これは「出荷されるセットが何の単位で結果を報告するか」とは別の問題です。この回路はタスクごとに異なる数式を使います。初期のフェーズでは、特定の経路だけで高得点になる狭い数式ではなく、広く十分にデータが集まった結果に報酬を与える数式を優先します（遺伝的探索が登るための勾配を持てるようにするためです）。

6 つの Fixed-R システムについては、出荷されるセットの最終レポートは **SomaR**（R 倍数によるトレード結果の合計）を使用します。候補がすでに保持率、乖離、Monte Carlo、および上記の R 期待値ゲートを通過した後、SomaR はこのガイドの他の部分が銘柄とシステムを比較するのに使うのと同じ単位——通貨ではなく R——で結果を表します。これは勝者を決めるものではなく、すでに勝者となったものの結果を比較可能な単位で報告するものです。

## Autobot と Historical Tool Manager

このライブラリは検証済みの状態で出荷されますが、上記の回路はブラックボックスではありません——このマニュアルが置かれているのと同じリポジトリ内に **Autobot**（`Autobot/`）として公開されている、本ガイドの各ステップを実際に実行するコードです。セットがどのようにその地位を得たのかを正確に確認するために読むことも、ご自身のブローカー、銘柄リスト、期間に対して自分で実行することもできます。

リアルティック確認のステップは、照合するための実際の tick データがあることに依存します。**Historical Tool Manager**（MQL5 Market: https://www.mql5.com/pt/market/product/188711）は、ブローカー自身の履歴が十分に遡れない銘柄について、深い tick 履歴と M1 履歴を Custom Symbol として MT5 にインポートします——Autobot を実行する場合でも、手動テスト用により長い履歴が欲しいだけの場合でも役立ちます。

## リスク警告

EA、set、過去結果は将来を保証しません。OOS と demo で検証してください。

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
