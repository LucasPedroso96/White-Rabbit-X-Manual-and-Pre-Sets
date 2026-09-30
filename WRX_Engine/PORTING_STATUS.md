# Estado do porte (atualizado a cada fase)

Legenda: ✅ portado e testado (fidelidade ao MT5 ainda por verificar) · 🟡 parcial · ⬜ não portado · ⛔ bloqueado (ver abaixo).

| Bloco do `.mq5` | Estado | Onde no motor |
|---|---|---|
| Decisão 1×/minuto, barras/ATR parciais, `ProcessNewBar` (ordem BE → sinal → filtros → entradas) | ✅ | `engine.py`, `bars.py` |
| 12 indicadores + linha de sinal + nuvem Ichimoku | ✅ | `indicators.py`, `signals.py` |
| Filtros MTF/MA/ADX/volatilidade | ✅ | `filters.py` |
| Lote Fixed-R + gate de risco + piso | ✅ | `engine.size_fixed_r`, `_open` |
| Breakeven | ✅ | `engine._breakeven` |
| ReversalExit (sinal contrário), Fecharordensforadohorario | ✅ | `engine.run_backtest` |
| Registro de inputs, checklist, sondas, runner de paridade | ✅ | `registry.py`, `review.py`, `parity.py` |
| Lote Percentage / Monetary / FixedLot | ⬜ ⛔ | `MM_Size_Buy/Sell`, `MM_SizeMonetary`, `MM_SizeFixo*` (linhas ~3245–3760) |
| Recovery Martingale/D'Alembert | 🟡 ⛔ | histórico de ciclos já lido (`RefreshClosedOperations`, `ApplyRecoveryOperation`); faltam `ClampMartingaleLot`, `CountConsecutiveLosses`, `MM_Size*` |
| Trailing ATR, TakeOrganico | ⬜ ⛔ | `TrailingStopSet` (~7320), `LastTradePrice` (~4399) |
| Grid separate/unified, Pirâmide | ⬜ ⛔ | ~3814–4300, ~9516–9700, ~9931–10140 |
| Entradas pendentes Stop/Limit/OCO/sessão | ⬜ ⛔ | ~9184–9420 |
| Travas de conta, margem, proteção global, notícias | ⬜ ⛔ | ~7678–7890 + `Include/*.mqh` |
| Janelas WFO, retiradas | ⬜ ⛔ | ~7501–7590, `OnInit` |
| Fitness (`OnTester`, fórmulas Levain/Zeus/…) | ⬜ ⛔ | ~1839–2620 |
| ReversalExit "OnOppositeOrder"; `OnTradeTransaction`/`OnTrade` | ⬜ ⛔ | ~10138–10370 |
| Motores de entrada das EAs Bollinger e Candles Entry | ⬜ ⛔ | diferem ~700 linhas do Multi-Indicator |
| Swap, margem/stop-out, `tick_value` variável | ⬜ | modelo de custos do motor |

## ⛔ Por que parou

Ao tentar ler os trechos marcados ⛔ do `.mq5` (repo privado `Metatrader5EAS`) o ambiente negou a leitura,
sem explicação. Não reli por outro caminho. Para retomar: (a) autorizar a leitura desse arquivo na sessão, ou
(b) copiar os `.mq5`/`.mqh` para dentro deste repo (ex.: `WRX_Engine/fonte_ea/`), ou (c) colar os trechos.
Tudo acima marcado ✅ foi portado só com o que já tinha sido lido antes do bloqueio e com o CSV público de inputs.

## Arquitetura prevista para o que falta

Entre duas decisões (barras M1) o conjunto de posições/ordens é constante, então os eventos por tick
(SL/TP, alvo monetário de grid, trailing de cesta, gatilho de pendente, DD de equity) podem ser achados
**vetorizados** com `numpy` sobre o trecho de ticks, tratando o mais cedo e repetindo — mantém a velocidade
(1 ano de M1 ≈ 2 s) sem laço por tick. O `scan()` atual generaliza para isso.
