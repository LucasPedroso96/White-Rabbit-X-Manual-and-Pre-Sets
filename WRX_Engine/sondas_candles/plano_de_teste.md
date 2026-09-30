# Plano de teste - sondas

Para cada sonda: carregue o `.set`, rode o Tester (mesmo simbolo/periodo/deposito, Every tick based on real ticks), salve o relatorio como `relatorios/<id>.htm`. As marcadas **hedging** exigem conta hedging.

| Sonda | O que muda | Hedging | Motor espera (trades / R) |
|---|---|---|---|
| `PC00_one_slot` | Candles: 1 slot (M1, candle fechado 1), so compra |  | - |
| `PC01_index0` | Slot 1 = candle em formacao (indice 0) |  | - |
| `PC02_index2` | Slots no candle 2 |  | - |
| `PC03_mtf_slots` | Slot 2 em M5 e slot 3 em M15 (todos na mesma direcao) |  | - |
| `PC04_tf_m5` | Slot 1 em M5 |  | - |
| `PC05_mixed_index` | Slot 1 indice 1, slot 2 indice 2, slot 3 indice 3 |  | - |
| `PC06_price_weighted` | Preco aplicado = Weighted (vs abertura) |  | - |
| `PC07_price_median` | Preco aplicado = Median |  | - |
| `PC08_sell` | So venda |  | - |
| `PC09_both_hedge` | Compra e venda, hedging | sim | - |
| `PC10_breakeven` | Candles + breakeven |  | - |
| `PC11_reversal_exit` | Candles + saida por sinal contrario (modo 2) | sim | - |
