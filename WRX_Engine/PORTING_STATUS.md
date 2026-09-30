# Estado do porte

Legenda: ✅ portado e testado contra o que o `.mq5` define (**fidelidade ao MT5 ainda não verificada**) · 🟡 parcial · ⬜ não portado.

As três EAs foram lidas (`Multi-Indicator`, `Bollinger Bands`, `Candles Entry` + `WhiteRabbitDailyLoss/GlobalProtection/NewsFilter.mqh`).
Os fontes **não** estão neste repositório (só o porte). Nada foi comparado com saída real do MT5: isso é a revisão da noite.

| Bloco do `.mq5` | Estado | Onde no motor |
|---|---|---|
| Decisão 1×/minuto (1º tick), barras/ATR parciais, ordem completa de `ProcessNewBar` | ✅ | `sim.py`, `bars.py` |
| 12 indicadores + linha de sinal + nuvem Ichimoku; 7 `EntryMethod` | ✅ | `indicators.py`, `signals.py` |
| Filtros MTF / MA / ADX / volatilidade ATR | ✅ | `filters.py` |
| Lote Fixed-R (+ gate de risco, piso, guarda anti-oversizing), Percentage, Monetary, FixedLot | ✅ | `sizing.py`, `Sim.send_order` |
| Recovery Martingale (ciclo, `MaxMartingaleSteps`, `MaxMartingaleLot`) e D'Alembert | ✅ | `ledger.Recovery`, `sizing.py` |
| SL/TP por tick, Breakeven, Trailing ATR, TakeOrganico, ReversalExit (modos 1/2) | ✅ | `sim.py` |
| Grid clássico (separate/unified), Pirâmide (`GridMode=3`; `GridMode=2` é aposentado e o OnInit recusa) | ✅ | `sim.py`, `ledger.py` |
| Entradas pendentes Stop/Limit/OCO/gatilho de sessão, expiração, cancelamento OCO | ✅ | `sim.py` |
| `CheckStopTradingCondition`, `GlobalProtection` (diária/total), `DailyLossLimit`, filtro de notícias (CSV) | ✅ | `sim.py`, `engine.load_news_csv` |
| Janelas WFO IS/OOS, carência de grid, dias de dívida, retirada no Tester | ✅ | `wfo.py`, `sim.wfo_step` |
| Custos: comissão por lote/lado, swap (pontos, triplo no dia configurado) | ✅ | `spec.py`, `sim.py` |
| Margem / `MinFreeMarginPercent` | 🟡 | só com `margin_a/margin_b` no spec (modelo linear por lote); sem stop-out do corretor |
| Validação do `OnInit` (`InvalidConfig`) e família por chaves do `.set` | ✅ | `setfile.oninit_errors` |
| **EA Bollinger**: 3 modos (Reversal/Breakout/Squeeze), `StopBolinger`/`TakeBolinger`/`BreakevenBolinger` | ✅ | `signals.bollinger_signals`, `sim.bollinger_exits` |
| **EA Candles Entry**: 3 slots (TF + índice, índice 0 = vela em formação) | ✅ | `signals.candles_signals` |
| Fitness do `OnTester`: 15 fórmulas + `ConsistencyFactor` + linha `ALL_FORMULAS` | ✅ (estatísticas do Tester reconstruídas = hipóteses) | `fitness.py` |
| `BandsShift ≠ 0` (Bollinger) | ⬜ | o motor recusa o set |
| Stop-out do corretor, `tick_value` variável no tempo, atraso de execução | ⬜ | hipóteses listadas no README |
| Plugar como estágio do Autobot (mesmo formato do `portfolio_builder`) | ⬜ | depois da paridade |

## Decisões e achados a conhecer

- **`08_GRID_UNIFIED` usa `GridMode=2`**, que o `OnInit` do EA rejeita (aposentado). Esse set não roda no EA; o motor também recusa.
- **Notícias** exigem o CSV exportado pelo EA (`datetime;currency;importance;event_name`); sem ele o motor recusa o set em vez de ignorar.
- **WFO**: o início é assumido como a 1ª barra M1 do teste (`run_backtest(wfo_start=…)` sobrescreve).
- Nada é ignorado em silêncio: input fora do escopo → `UnsupportedConfig`; set que o EA recusaria → `InvalidConfig`.

## Onde a fidelidade é só hipótese (calibrar na revisão)

Lista completa no README ("Pontos a calibrar"). Os mais prováveis de divergir: `iATR` (SMA do TR), `iADX`, preço de execução do SL
(`stop_fill`) e de pendentes (`pending_fill`), `tick_value` constante, e — só para o fitness — Sharpe, DD de equity e
`STAT_CONLOSSMAX_TRADES`. A linha `ALL_FORMULAS` que o EA grava em `Common\Files\levain_wrx_all_formulas.txt` permite
conferir isso número a número (`review run --formulas`).
