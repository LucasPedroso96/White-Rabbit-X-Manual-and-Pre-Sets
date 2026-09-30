# Plano de teste - sondas

Para cada sonda: carregue o `.set`, rode o Tester (mesmo simbolo/periodo/deposito, Every tick based on real ticks), salve o relatorio como `relatorios/<id>.htm`. As marcadas **hedging** exigem conta hedging.

| Sonda | O que muda | Hedging | Motor espera (trades / R) |
|---|---|---|---|
| `PB00_reversal` | Bollinger: reversao (fecha fora da banda e volta), so compra |  | - |
| `PB01_breakout` | Bollinger: rompimento |  | - |
| `PB02_squeeze` | Bollinger: squeeze (largura no minimo) + rompimento |  | - |
| `PB03_squeeze_params` | Squeeze: lookback 10, tolerancia 25% |  | - |
| `PB04_period10` | Periodo 10 |  | - |
| `PB05_dev15` | Desvio 1.5 |  | - |
| `PB06_sell` | So venda (reversao) |  | - |
| `PB07_both_hedge` | Compra e venda, hedging (rompimento) | sim | - |
| `PB08_tf_m5` | Bandas em M5 |  | - |
| `PB09_take_bb` | TakeBolinger (reversao): fecha no lucro quando volta da banda |  | - |
| `PB10_stop_bb_rev` | StopBolinger (reversao): fecha se perde a banda oposta |  | - |
| `PB11_stop_bb_breakout` | StopBolinger (rompimento): fecha quando volta da banda |  | - |
| `PB12_be_bb` | BreakevenBolinger (reversao) |  | - |
| `PB13_both_sides_rev` | Reversao nos dois lados, sem hedging (um lado por vez) |  | - |
| `PB14_trail` | Bollinger + trailing ATR |  | - |
| `PB16_price_weighted` | Bandas sobre o preco Weighted (InpAppliedPrice) |  | - |
| `PB15_vol_filter` | Bollinger + filtro de volatilidade |  | - |
