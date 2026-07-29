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

> Bu bölüm şimdilik yalnızca İngilizce olarak mevcuttur.

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

## Risk uyarısı

EA, set veya geçmiş sonuç geleceği garanti etmez. OOS ve demo ile doğrulayın.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
