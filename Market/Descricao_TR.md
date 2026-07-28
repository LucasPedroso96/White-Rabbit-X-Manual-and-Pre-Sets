# White Rabbit X

On iki yerel giriş motoru. On bir çıkış mimarisi. Tek bir Expert Advisor.

Çoğu EA size hazır bir strateji verir. Bu EA atölyeyi verir: sinyal motorunu, pozisyon yönetim iskeletini ve filtreleri siz seçersiniz; yerleşik walk-forward ise sonucun örneklem dışında ayakta kalıp kalmadığını söyler.

## On iki giriş motoru, hepsi yerel

MACD · EMA Cross · Momentum · Stochastic · TRIX · RSI · CCI · Williams %R · DeMarker · MFI · OsMA · Ichimoku

Hepsi MetaTrader'ın yerleşik göstergeleridir: kurulacak özel gösterge dosyası yok, terminal güncellemesinde bozulacak bir şey yok.

Ichimoku beş tamponun tamamını okur: referans tetikleyici Tenkan/Kijun kesişimi değil, bulut (Kumo) kırılımıdır ve Chikou onay filtresi olarak kullanılabilir. Stokastik; yumuşatma periyodunu, yumuşatma yöntemini ve Low/High ile Close/Close fiyat alanını açar — çoğu EA'nın koda gömdüğü üç parametre.

Üç tetikleyici türü birleşerek yedi giriş yöntemi oluşturur.

## On bir çıkış mimarisi

SL/TP · organik hedef · yalnızca trailing · trailing'li SL/TP · başabaş ve trailing · ters sinyalde çıkış · ayrık grid · birleşik grid · martingale · D'Alembert · yalnızca sinyal.

Yönetim iskeleti stratejinin sabit parçası değil, sizin seçiminizdir.

## EA'nın içine gömülü walk-forward

Test cihazının Forward sekmesi değildir. EA dönemi örneklem içi ve örneklem dışı pencerelere böler ve optimizasyon modunda yalnızca örneklem içini işler: genetik algoritma, kendisinin değerlendirileceği veriyi hiç görmez.

Üç pencere modu: ardışık, kayan (klasik olan — aynı geçmişten yaklaşık üç kat fazla döngü) ve sabitlenmiş.

Rapor, döngü başına Walk Forward Efficiency değerini ortalama ve standart sapmayla birlikte verir. Her döngüde %70 getiren bir EA ile bir döngüde %200, kalanlarda −%20 getiren bir EA aynı ortalamaya sahiptir; sağlam olan yalnızca ilkidir ve ikisini ayıran şey dağılımdır.

## Risk R cinsinden ölçülür

Fixed-R modu, değişen bakiye yerine sabit bir temel sermaye üzerinden hesap yaparak her işlemin tam olarak 1R risk almasını sağlar. Sonuçlar böylece enstrümanlar, hesaplar ve testler arasında karşılaştırılabilir hale gelir: altında +40R ile EURUSD'de +40R aynı anlama gelir, oysa "+3.200 USD" lot ve bakiye bilinmeden hiçbir şey ifade etmez.

On beş optimizasyon kriteri; bunlardan bileşik puan, otuz işlemin altında sıfır döndürür — bu tek başına üç şanslı işlem üzerine kurulu klasik "kazanan"ı eler.

## Emirden önce devreye giren koruma

Günlük azami zarar, öz sermaye üzerinden düşüş tavanı, asgari serbest teminat, spread sınırı, seans ve hafta günü pencereleri ve geriye dönük test için CSV önbellekli haber filtresi. Freeze level ve stops level mesafeleri her istekten önce denetlenir; böylece günlük, aracı kurum retleriyle dolmak yerine okunabilir kalır.

## Grafik paneli

Strateji, gösterge ve etkin parametreler, hesap ve EA sermayesi, kapanmış, açık ve net K/Z, açık pozisyonlar ve — martingale, D'Alembert veya grid çalışırken — güncel döngü: ardışık zararlar, kapanmamış açık, geri kazanılan tutar, hedef, emirler, referans ve ATR aralığı.

Arayüz on bir dilde.

## Pakete dahil olanlar

- MetaTrader 5 için Expert Advisor — belgelenmiş 136 parametre
- 3.738 hazır .set dosyası: 89 enstrüman × 11 sistem × her iki yön
- Otomatik kurulum programı: terminalinizi bulur, setleri kopyalar ve aracı kurumunuzun sembol ekine ve asgari lotuna uyarlar
- Kılavuz, WFO rehberi, parametre referansı, set eğitimi ve SSS — on bir dilde
- Resmî kanal üzerinden destek ve güncellemeler

## Satın almadan önce

Bu bir araştırma çerçevesidir; açıp unutulacak bir sinyal hizmeti değildir. Her set bir hipotezdir: gerçek parayla çalışmadan önce optimizasyon, örneklem dışı doğrulama ve ileri yönlü demo gerektirir.

Grid, martingale ve D'Alembert risk eğrisinin doğasını değiştirir. Grid gerçek bir hedging hesabı gerektirir.

Hiçbir Expert Advisor, hazır ayar veya geçmiş sonuç gelecekteki performansı garanti etmez.

---

Resmî kanal: https://t.me/MrRabbit_MT5 — ücretsiz set kütüphanesi, kendi dilinizde kılavuzlar ve güncelleme duyuruları. EA yalnızca burada, MQL5 Market üzerinden satılır; setler yalnızca yukarıdaki kanalda ücretsiz dağıtılır.
