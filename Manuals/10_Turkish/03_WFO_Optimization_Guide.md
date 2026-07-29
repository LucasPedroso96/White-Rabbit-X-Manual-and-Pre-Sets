# White Rabbit X — WFO Optimizasyon Kılavuzu

Güncel EA kaynağı ve set manifestosundan üretilen yetkili referans — EA 1.11 — 127 inputs — 3738 sets

**Tarihe dikkat.** WFO açıkken OnTester, testin gerçek bitişini input_end_date ile karşılaştırır ve test daha erken bittiyse sıfır döndürür (80 saatlik tolerans). Yanlış tarih tüm geçişleri sıfırlar ve optimizasyonun tamamı bozulmuş gibi görünür. input_end_date değerini Strateji Test Cihazında ayarladığınız bitiş tarihiyle aynı yapın.

## Kapsam ve doğruluk kaynakları

EA kaynağı inputs, varsayılanlar ve özellikleri; manifesto her set, durum, yol ve SHA-256 değerini tanımlar. Eski Quantum arşivi yalnızca tarihseldir.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Üretilmiş belgedir; parametre adları EA ile tam olarak aynıdır.

## Walk-forward yöntemi

Gerçekçi spread, komisyon, swap ve slippage ile kronolojik IS, OOS ve forward demo kullanın.

## Güvenli akış

Her aşamada tek matris değiştirin ve kanıtları saklayın.

1. EX5, kaynak, set şeması ve manifesto sürümünü eşleştirin.
2. Kütüphaneyi Strategy Tester Inputs ile yükleyin.
3. Broker'ın tam sembol ve suffix değerini eşleyin.
4. 01–05 baseline ile başlayıp BUY/SELL'i ayırın.
5. 06 tek eksenli araştırmadır.
6. 07 giriş, 08 filtre, 09 risk, 10 çıkıştır.
7. IS, OOS ve forward demo'yu kronolojik uygulayın.
8. Status, RelativePath ve SHA256 kontrol edin.
9. Yalnızca açık USE tanımlı ortam için adaydır.

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

## Risk uyarısı

EA, set veya geçmiş sonuç geleceği garanti etmez. OOS ve demo ile doğrulayın.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
