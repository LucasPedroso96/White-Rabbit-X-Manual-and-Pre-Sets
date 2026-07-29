# White Rabbit X — SSS ve Destek

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

## Operasyon yanıtları

Stop, hesap modu, suffix, sunucu zamanı, news CSV ve broker limitlerini kontrol edin.

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

## Diagnostics and supplied utilities

The Experts/Journal tab is authoritative for rejected inputs, OrderCheck failures, news-calendar errors and close retries. Compile and run MQL5\Scripts\WhiteRabbit Filters SelfTest; its final line must report zero failures. Use White Rabbit News Exporter to build the test CSV, then verify its date range, currencies, delimiter and Common\Files location before a news-enabled backtest.

## Topluluk ve indirmeler

Resmî Telegram kanalına katılın: **https://t.me/MrRabbit_MT5**

Kılavuzlar ve tam set kütüphanesi: **https://github.com/LucasPedroso96/White-Rabbit-X-Manual-and-Pre-Sets**

- Enstrümana ve sistem türüne göre (SL/TP, trailing, grid, martingale ve diğerleri) hazırlanmış set dosyaları; doğrudan Strateji Test Cihazına yüklenecek şekilde düzenlenmiştir.
- Kendi dilinizde kılavuzlar: Portekizce, İngilizce, Rusça, Çince, İspanyolca, Japonca, Almanca, Korece, Fransızca, İtalyanca ve Türkçe.
- EA ve set kütüphaneleri için güncelleme duyuruları.
- Destek ve diğer kullanıcılarla deneyim paylaşımı.

> Bu tek resmî kanaldır. White Rabbit X'i temsil ettiğini iddia eden üçüncü kişilerden set veya EA kopyası satın almayın: EA yalnızca MQL5 Market üzerinden satılır ve setler yukarıdaki kanalda ücretsiz dağıtılır.

## Risk uyarısı

EA, set veya geçmiş sonuç geleceği garanti etmez. OOS ve demo ile doğrulayın.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
