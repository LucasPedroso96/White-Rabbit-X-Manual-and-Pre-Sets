# White Rabbit X — MQL5 Market 説明

現在の EA ソースと set マニフェストから生成した正式リファレンス — EA 1.11 — 127 inputs — 3738 sets

## ソフトウェアの目的

White Rabbit X は体系的研究、管理執行、WFO 用の MT5 マルチインジケーター EA です。

Current schema: 127 inputs. Current manifest: 3738 sets.

- 12 のネイティブエンジン: MACD、EMA Cross、Momentum、Stochastic、TRIX、RSI、CCI、Williams %R、DeMarker、MFI、OsMA、Ichimoku。
- 確定足における AND/OR を明示した 7 エントリー方式。
- 独立した MTF、MA、ADX、ATR、news フィルター。
- 4 PositionSizeMode と equity/margin 保護。
- Stop、take、breakeven、trailing、reversal の決済。
- Dashboard、時間、言語、WFO を統合。

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

## コミュニティとダウンロード

公式 Telegram チャンネルにご参加ください：**https://t.me/MrRabbit_MT5**

マニュアルとセットの全ライブラリ: **https://github.com/LucasPedroso96/White-Rabbit-X-Manual-and-Pre-Sets**

- 銘柄別・システム種別（SL/TP、トレーリング、グリッド、マーチンゲールなど）に整理された既成のセットファイル。ストラテジーテスターにそのまま読み込めます。
- **Autobot**：このライブラリの背後にある自動化プログラムで、同じリポジトリで公開されています——各セットを出荷前に生成し、walk-forward テストを行い、Monte Carlo でゲートし、リアルティックで確認する実際のコードです。ご自身のブローカーと銘柄に対して自分で実行することも、コードを読んでセットがどのようにその地位を得たのかを確認することもできます。
- お使いの言語のマニュアル：ポルトガル語、英語、ロシア語、中国語、スペイン語、日本語、ドイツ語、韓国語、フランス語、イタリア語、トルコ語。
- EA とセットライブラリの更新通知。
- サポートと他のユーザーとの情報交換。

関連製品：**Historical Tool Manager**（MQL5 Market: https://www.mql5.com/pt/market/product/188711）は、深い tick 履歴と M1 履歴を Custom Symbol として MT5 にインポートします——Autobot のリアルティック確認段階が依存するデータソースです。

> 公式チャンネルはここだけです。White Rabbit X の代理を名乗る第三者からセットや EA のコピーを購入しないでください。本 EA は MQL5 Market でのみ販売され、セットは上記チャンネルで無償配布されています。

## リスク警告

EA、set、過去結果は将来を保証しません。OOS と demo で検証してください。

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
