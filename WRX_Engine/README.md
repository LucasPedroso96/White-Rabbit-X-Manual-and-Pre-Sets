# WRX Engine — backtest próprio da White Rabbit X (o MT5 só executa)

> Código-fonte da EA que este motor porta: `Metatrader5EAS/White Rabbit/EA/` (repo privado). Esta pasta (`WRX_Engine/`) é autocontida para migrar para lá quando quiser.

Porta a semântica do `EA/White Rabbit X (Global Multi-Indicator).mq5` para Python, para
rodar a peneira de otimização fora do Strategy Tester. Mesma regra de adoção do simulador
do Zeus: **o motor só substitui o Tester depois que a paridade trade a trade fechar contra
rodadas reais em _Every tick based on real ticks_**. Antes disso é ferramenta de estudo.

> **Estado honesto:** 176 testes passam, mas eles provam a *lógica* contra cenários construídos à mão e contra
> laços ingênuos escritos a partir do `.mq5` (mais testes de mutação manuais). **Nada foi comparado ainda com uma
> saída real do MT5** — não havia terminal MT5 no ambiente onde isto foi escrito. O primeiro trabalho real é a
> revisão da noite (abaixo). O que foi portado está em `PORTING_STATUS.md` e `REVISAO_INPUTS.md`.

## Escopo

As três EAs estão portadas: **Multi-Indicator** (12 indicadores), **Bollinger Bands** (Reversal/Breakout/Squeeze +
`Stop/Take/BreakevenBolinger`) e **Candles Entry** (3 slots TF+índice). Toda a gestão é compartilhada: lote (Fixed-R,
Percentage, Monetary, FixedLot), Martingale/D'Alembert, SL/TP/BE/trailing/TakeOrganico, ReversalExit, grid clássico e
pirâmide, entradas pendentes (Stop/Limit/OCO/sessão), travas de conta (`CheckStopTrading`, GlobalProtection,
DailyLossLimit), filtro de notícias (CSV), janelas WFO, comissão/swap e margem opcional. Fitness do `OnTester`
(15 fórmulas + `ConsistencyFactor`) em `fitness.py`.

O motor **recusa** (nunca ignora em silêncio): inputs fora do escopo (`UnsupportedConfig`: `BandsShift≠0`,
`EntryIndicator` inválido) e sets que o `OnInit` do EA recusaria (`InvalidConfig`, ex.: `GridMode=2`, que é aposentado —
o set `08_GRID_UNIFIED` do repositório cai nisso).

Cuidado com os **defaults do EA quando o input não está no `.set`**: `MaxEquityDrawdownPercent` vale 30 e
`MinFreeMarginPercent` 50. O `01_SLTP` que vem em `Sets/` traz `AtivarWFO=true` + `In Sample`;
para comparar, rode o Tester com `AtivarWFO=false` (as sondas já vêm assim).

## Revisão da noite, guiada pelos inputs

`sondas/` (Multi, 109 `.set`), `sondas_bollinger/` (17) e `sondas_candles/` (12): baseline seguro + **um** recurso ligado
por vez, cada pasta com `plano_de_teste.md`. `REVISAO_INPUTS.md` lista os 142 inputs classificados e as sondas de cada um.

1. `py tools/export_mt5_data.py --symbol EURUSD --from 2026-01-05 --to 2026-03-01 --out dados/eurusd`
   (spec com tick value, margem e swap; ticks reais; M1 de aquecimento; `--commission-per-lot-side` se houver).
2. No Tester (hedging para as sondas marcadas): **Every tick based on real ticks**, mesmo período/depósito para todas.
   Para cada `.set`, salve o relatório como `relatorios/<id>.htm`. **Comece por `P00_base`**: se ela não fechar,
   nada acima dela vale. Opcional: copie a última linha `ALL_FORMULAS` de `Common\Files\levain_wrx_all_formulas.txt`
   de cada rodada para `formulas/<id>.txt`.
3. `py -m wrx_engine.review run --baseline ../Sets/01_Forex/EURUSD/01_SLTP/BUY_MULTI.set --reports relatorios --ticks dados/eurusd_ticks.csv --spec dados/eurusd_spec.json --warmup dados/eurusd_m1_warmup.csv [--formulas formulas]`
   grava `REVISAO_INPUTS.md` com PASS/FAIL **por sonda e por input**, a primeira divergência trade a trade, o fitness do
   motor e (com `--formulas`) cada estatística/fórmula do motor contra o MT5. Sai com código 1 se algo falhar.
   Para Bollinger/Candles: `--family bollinger|candles` (sem `--baseline`, use os `.set` de `sondas_<familia>/`).
4. Divergência sistemática = uma hipótese da tabela "Pontos a calibrar". Corrija uma de cada vez.
5. `py -m wrx_engine.review sync --ea "White Rabbit X (Global Multi-Indicator).mq5"` acusa `input` novo sem status.

## Como o EA roda (o que o motor replica)

- `OnTick` só segue quando a barra **M1** muda: **uma decisão por minuto, no 1º tick**. Sinal só na
  1ª decisão de cada barra do `TimeFrame`; usa barras **fechadas** (shift 1–3).
- `ATR[VelaStop=0]` é o ATR da barra **em formação** → no 1º tick do minuto é uma barra *parcial*
  (`bars.forming_partial`). Este é o ponto que mais separa um simulador caseiro do Tester.
- Entrada a mercado no ask/bid daquele tick, SL/TP já no pedido. SL/TP testados a **cada tick**.
- Ordem na decisão: BE buy → BE sell → sinais → filtros → entrada buy → entrada sell.
- `ProcessNewBar` retorna sem fazer nada enquanto faltarem 50 barras (TF do sinal) ou
  `max(50, PeriodoBaselineATR)`=100 barras (TF do ATR): forneça M1 de aquecimento (`--warmup`).

## Paridade (faça isto primeiro)

1. Na máquina com o MT5: `py tools/export_mt5_data.py --symbol EURUSD --from 2026-01-05 --to 2026-03-01 --out dados/eurusd`
   (gera `_spec.json`, `_ticks.csv`, `_m1_warmup.csv`; informe `--commission-per-lot-side` se houver comissão).
2. No Tester, **no mesmo terminal**: _Every tick based on real ticks_, mesmo período/depósito, o `.set`
   com `AtivarWFO=false` e as travas zeradas, `MaxLongTrades=1`. Salve o relatório (`.htm`).
3. `py -m wrx_engine.parity --report Rel.htm --set meu.set --spec dados/eurusd_spec.json --ticks dados/eurusd_ticks.csv --warmup dados/eurusd_m1_warmup.csv`
   Sai `0` se PASS, `1` se FAIL; o relatório mostra mediana/máximo do erro por campo e a **primeira divergência**.
4. Diferenças sistemáticas apontam para os botões de calibração abaixo, um de cada vez.

## Pontos a calibrar contra o Tester (hipóteses, não fatos)

| Hipótese no código | Onde | Sintoma se estiver errada |
|---|---|---|
| `iATR` = média **simples** do TR (não Wilder), `TR[0]` fora | `indicators.atr` | lote e SL/TP sempre um pouco diferentes |
| `iADX`: +DI/-DI/DX suavizados por EMA (α=2/(n+1)) | `indicators.adx` | P57/P58/P70 falham, resto passa |
| RSI/Stoch/CCI/WPR/DeMarker/MFI/TRIX nas fórmulas dos built-ins do MT5 | `indicators.*` | sondas P21–P31 divergem indicador a indicador |
| Filtro MTF usa `GetHigherTimeframes(TimeFrame)` (OnInit não lido) | `filters.higher_timeframes` | P50/P51 |
| MFI usa nº de ticks da barra como volume | `bars.m1_from_ticks` | P29 (MFI) |
| EMA semeia no 1º preço; SMA no sinal do `iMACD` | `indicators.macd` | sinais desalinhados nas primeiras horas (dependem do aquecimento) |
| SL executa no **preço do SL** (`stop_fill="level"`); a alternativa é o tick que rompeu | `run_backtest(stop_fill=…)` / `--stop-fill` | preço de saída dos SL diferente, principalmente em gaps |
| Barras M1 vêm do **bid** dos ticks | `bars.m1_from_ticks` | ATR parcial e sinais discordam |
| `tick_value` constante | `SymbolSpec` | lucro diverge em cruzados/índices (o Tester converte no tempo) |
| Execução ideal (sem atraso); swap só em modo pontos; sem stop‑out do corretor | `spec.py`, `sim.py` | lucro líquido e trades finais diferem |
| Margem = lote·(margin_a·preço + margin_b), ajuste linear de `order_calc_margin` | `spec.py` | recusas de entrada por margem; `STAT_MIN_MARGINLEVEL` |
| Fitness: Sharpe = média/desvio(n‑1) do `net` por trade; DD de equity com pico corrente (máx. em dinheiro → % do pico daquele momento); gross profit/loss por posição; `CONLOSSMAX_TRADES` = nº de trades da série de perdas de MAIOR perda em dinheiro | `fitness.compute_stats` | linha `ALL_FORMULAS` diverge (use `--formulas`) |
| Bollinger: `iBands` com SMA somada do mais novo ao mais velho e desvio populacional; Candles: índice 0 = vela em formação (parcial) | `indicators.bands`, `signals.candles_signals` | sondas PB*/PC* |
| Início do WFO = 1ª barra M1 do teste | `engine.run_backtest(wfo_start=)` | P75/P124 |
| Regra `ultimaAtualizacao == TimeCurrent()` ignorada | `OnTick` | só relevante com dois minutos no mesmo segundo (raro) |

Não testável com floats: o `>` estrito no cruzamento da referência (`main==0` exato). Foi copiado do fonte.

## Testes

```
pip install -r requirements.txt
python -m pytest -q tests
```

Os testes incluem verificações de mutação feitas à mão (trocar ask/bid no SL do sell, inverter o
sinal, errar os shifts, usar 50 em vez de 100 barras, sinal a cada M1 com TF>M1, tirar o gate de
risco/intervalo mínimo, nível neutro, linha de sinal, filtros MA/MTF/ADX/volatilidade, reversal exit) — todas
fazem algum teste falhar. Uma exceção conhecida: o `>` estrito do cruzamento da referência (ver acima).

## Próximos passos

1. **Revisão da noite**: `P00_base` primeiro, depois as demais; cada FAIL aponta uma hipótese a calibrar.
2. Calibrar as hipóteses de fitness com `--formulas` (Sharpe, DD, margem mínima) — só importa se a otimização for guiada por elas.
3. Modelar stop‑out do corretor e `tick_value` variável (cruzados/índices) se a paridade mostrar necessidade.
4. Ligar como estágio alternativo do Autobot, gravando o mesmo formato que o `portfolio_builder` lê.
