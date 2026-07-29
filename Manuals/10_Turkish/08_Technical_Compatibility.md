# White Rabbit X — Teknik Uyumluluk

Güncel EA kaynağı ve set manifestosundan üretilen yetkili referans — EA 1.11 — 127 inputs — 3738 sets

## Kapsam ve doğruluk kaynakları

EA kaynağı inputs, varsayılanlar ve özellikleri; manifesto her set, durum, yol ve SHA-256 değerini tanımlar. Eski Quantum arşivi yalnızca tarihseldir.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Üretilmiş belgedir; parametre adları EA ile tam olarak aynıdır.

## Döngü dashboard telemetrisi

Panel lot hesabı ve sepet kapatmayla aynı durum snapshot'larını kullanır.

- Periyodik tick yenilemesi saniyede birle sınırlıdır; başlatma ve trade olayları hemen yenileyebilir.
- Balance ve Equity tüm hesaptır. Closed P&L OnInit sonrası değişimdir; Open P&L ve positions günceldir ve Symbol + Magic ile filtrelenir.
- Martingale BUY/SELL için ardışık kayıp, döngü kayıp sayısı ve brüt tutar, recovered, deficit ve deficit × Multiplicador target gösterir.
- MaxMartingaleSteps aşılırsa hard reset eski deficit'i siler ve sonraki emir base lot kullanır. Taraf başına en fazla bir açık pozisyon.
- D'Alembert BUY/SELL güncel seviye ve normalize edilmiş sonraki lotu gösterir.
- Grid legs/volume, maliyetler dahil realized, open P&L, cycle P&L, başlangıçta sabit target ve remaining gösterir.
- Anchor en son onaylı pozisyondur. BUY kesin olarak anchor − ATR × DistanciaMinima altı, SELL kesin olarak üstü ister; ilerleme ATR cinsindendir.
- Separate yalnız flat olan tarafın döngüsünü bitirir; Unified iki taraf da flat olunca biter. İşlemdeki emirler reset'i geciktirir.
- Target kapanış isteğini tetikler; gerçek çıkış komisyonu, fee ve slippage sonucu hedefin biraz altında bırakabilir.
- InterfaceLanguage 11 dili korur. Auto Tester'da English, live'da terminal dilini kullanır; çevrilmemiş label English'e döner.

## Uyumluluk ve kısıtlar

Temkinli kurallardır; daha sıkı broker limitleri önceliklidir.

- Percentage ve Fixed-R için AtivarStop=true gerekir.
- Grid yalnızca Monetary/Fixed Lot, Recovery_None ve hedging hesap destekler.
- Grid için take, pozitif DistanciaMinima ve en az iki limit gerekir.
- Sepet açık kaldığı sürece döngünün gerçekleşmiş zararları, swap, komisyon ve ücretleri hedefe ulaşmak için gereken sonuçta kalır; tek bir ayağın kârı bu maliyetleri silmez.
- Grid_SeparateProfit modunda BUY ve SELL döngüleri bağımsızdır. Bir taraftaki tüm pozisyonlar kaybolursa o tarafın döngüsü biter; sonraki giriş kapanmış açığı taşımadan yeni döngü başlatır.
- D'Alembert yalnızca Fixed Lot, Grid_Disabled ve DAlembertStep>0.
- Martingale MaxMartingaleSteps ve MaxMartingaleLot sınırlarına uyar.
- OnOppositeOrder hedging, iki yön ve grid kapalı ister.
- News backtest Common\Files içinde CSV ister.
- Zamanlama broker sunucu saatini kullanır.
- Her broker için suffix ve sembol özelliklerini doğrulayın.

## Sinyaller ve giriş yöntemleri

Altı motor reversal, signal/reference cross ve baseline/reference cross olaylarını paylaşır. And aynı kapanmış barı; All herhangi bir olayı ifade eder.

- EntryIndicator: MACD, EMA_Cross, Momentum, Stochastic, TRIX, RSI, CCI, WPR, DeMarker, MFI, OsMA, Ichimoku.
- EntryMethod: Reversal, SignalCross, ReferenceCross, ReversalAndSignalCross, ReversalAndReferenceCross, SignalAndReferenceCross, All.
- PositionSizeMode: Percentage, Monetary, FixedLot, FixedR.
- RecoveryMode: None, Martingale, DAlembert.
- GridMode: Disabled, SeparateProfit, UnifiedProfit.

## News filter and CSV workflow

Live mode reads the MT5 Economic Calendar in broker-server time and blocks new entries if the calendar query fails. Backtests cannot read that live calendar: run MQL5\Scripts\White Rabbit News Exporter on a live/demo chart, cover the entire test interval, and write NewsCSVFile to the terminal Common\Files folder. The semicolon-delimited header is datetime;currency;importance;event_name, where importance 2 is moderate and 3 is high. Use the same broker/server timezone; for suffixed or non-FX symbols set ExportMoedas and NewsMoedasManual explicitly. Manual currencies take precedence over automatic symbol parsing.

## Grid cycle and ATR spacing

Every additional grid leg is measured from the newest already-confirmed position on that side and must satisfy ATR × DistanciaMinima. The initial order cannot recursively trigger another leg in the same calculation event; it becomes the anchor on the following cycle. Individual grid take-profits are disabled: Separate mode evaluates independent BUY/SELL cycles against frozen monetary targets and ends a side when it becomes flat; Unified evaluates the aggregate BUY+SELL basket and ends when both sides are flat. Realized commissions, swap, fees and stopped legs remain in the result while the corresponding cycle is open. The target triggers a close request, so actual exit costs and slippage can leave the final result slightly below it. Live cycle state is persisted across an EA restart. Grid is hedging-only and must be reoptimized after any EA, broker-contract or cost change.

## Durumlar ve karar

Asıl durum korunur ve USE, REOPTIMIZE, RESEARCH veya HOLD olarak temkinli eşlenir.

| Sistem | Yönetim | Set |
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

## Risk uyarısı

EA, set veya geçmiş sonuç geleceği garanti etmez. OOS ve demo ile doğrulayın.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
