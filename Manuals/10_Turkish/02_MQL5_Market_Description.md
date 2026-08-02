# White Rabbit X — MQL5 Market Açıklaması

Güncel EA kaynağı ve set manifestosundan üretilen yetkili referans — EA 1.11 — 127 inputs — 3738 sets

## Yazılımın işlevi

White Rabbit X sistematik araştırma, kontrollü yürütme ve WFO için çok göstergeli bir MT5 EA'dır.

Current schema: 127 inputs. Current manifest: 3738 sets.

- On iki yerel motor: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA ve Ichimoku.
- Kapanmış barda açık AND/OR anlamlı yedi giriş yöntemi.
- Bağımsız MTF, MA, ADX, ATR ve news filtreleri.
- Dört PositionSizeMode ve equity/margin koruması.
- Stop, take, breakeven, trailing ve reversal çıkışı oluşturur.
- Dashboard, zamanlama, diller ve WFO bütünleşiktir.

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

## Topluluk ve indirmeler

Resmî Telegram kanalına katılın: **https://t.me/MrRabbit_MT5**

Kılavuzlar ve tam set kütüphanesi: **https://github.com/LucasPedroso96/White-Rabbit-X-Manual-and-Pre-Sets**

- Enstrümana ve sistem türüne göre (SL/TP, trailing, grid, martingale ve diğerleri) hazırlanmış set dosyaları; doğrudan Strateji Test Cihazına yüklenecek şekilde düzenlenmiştir.
- **Autobot**: bu kütüphanenin arkasındaki otomasyon, aynı depoda yayınlanır — her seti yayınlanmadan önce üreten, walk-forward testinden geçiren, Monte Carlo ile kapıdan geçiren ve gerçek tikle doğrulayan asıl koddur. Kendi brokerinize ve enstrümanlarınıza karşı kendiniz çalıştırabilir veya bir setin statüsünü nasıl kazandığını görmek için kodu okuyabilirsiniz.
- Kendi dilinizde kılavuzlar: Portekizce, İngilizce, Rusça, Çince, İspanyolca, Japonca, Almanca, Korece, Fransızca, İtalyanca ve Türkçe.
- EA ve set kütüphaneleri için güncelleme duyuruları.
- Destek ve diğer kullanıcılarla deneyim paylaşımı.

Tamamlayıcı ürün: **Historical Tool Manager** (MQL5 Market: https://www.mql5.com/pt/market/product/188711) derin tick ve M1 geçmişini MT5'e Custom Symbol olarak aktarır — Autobot'un gerçek tik doğrulama aşamasının dayandığı veri kaynağıdır.

> Bu tek resmî kanaldır. White Rabbit X'i temsil ettiğini iddia eden üçüncü kişilerden set veya EA kopyası satın almayın: EA yalnızca MQL5 Market üzerinden satılır ve setler yukarıdaki kanalda ücretsiz dağıtılır.

## Risk uyarısı

EA, set veya geçmiş sonuç geleceği garanti etmez. OOS ve demo ile doğrulayın.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
