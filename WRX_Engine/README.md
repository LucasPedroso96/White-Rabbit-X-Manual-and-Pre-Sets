# WRX Engine — backtest próprio da White Rabbit X (o MT5 só executa)

> Código-fonte da EA que este motor porta: `Metatrader5EAS/White Rabbit/EA/` (repo privado). Esta pasta (`WRX_Engine/`) é autocontida para migrar para lá quando quiser.

Porta a semântica do `EA/White Rabbit X (Global Multi-Indicator).mq5` para Python, para
rodar a peneira de otimização fora do Strategy Tester. Mesma regra de adoção do simulador
do Zeus: **o motor só substitui o Tester depois que a paridade trade a trade fechar contra
rodadas reais em _Every tick based on real ticks_**. Antes disso é ferramenta de estudo.

> **Estado honesto (passo 1):** 39 testes passam, mas eles provam a *lógica* contra cenários
> construídos à mão e contra laços ingênuos escritos a partir do `.mq5`. **Nada foi comparado
> ainda com uma saída real do MT5** — não havia terminal MT5 no ambiente onde isto foi escrito.
> O primeiro trabalho real é rodar o passo "Paridade" abaixo na sua máquina.

## Escopo do passo 1

| Portado | Recusado (o motor levanta `UnsupportedConfig`, nunca ignora em silêncio) |
|---|---|
| `01_SLTP`: MACD (`EntryMethod` 0–6), SL/TP em ATR, lote **Fixed-R** | Outros 11 indicadores, Ichimoku |
| Decisão 1×/minuto no 1º tick; sinal 1×/barra do `TimeFrame`; `ATR[0]` parcial | Trailing, TakeOrganico, ReversalExit |
| Gate de risco de `myOrderSend`, piso de lote e guarda anti-oversizing | Grid, Pirâmide, Martingale, D'Alembert |
| Breakeven (só reavaliado nas decisões, `CanModifyPositionStops`) | Filtros MTF/MA/ADX/ATR/Notícias, entradas pendentes |
| Dias/horário/`MaxSpread`, `stops_level`, `Hedging`, `MaxLong/ShortTrades` | Travas de conta/margem (`MaxEquityDrawdownPercent`, `MinFreeMarginPercent`, `Trava_*`, `DailyLossLimitPercent`) |
| `.set` UTF‑16 com `atual\|\|início\|\|passo\|\|fim\|\|Y` | WFO `In Sample` (bloqueia entrada fora da janela IS) |

Cuidado com os **defaults do EA quando o input não está no `.set`**: `ReversalExitMode` vale 2,
`MaxEquityDrawdownPercent` 30 e `MinFreeMarginPercent` 50 — a guarda os acusa. O `01_SLTP` que vem
em `Sets/` traz `AtivarWFO=true` + `In Sample`; para comparar, rode o Tester com `AtivarWFO=false`.

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
| EMA semeia no 1º preço; SMA no sinal do `iMACD` | `indicators.macd` | sinais desalinhados nas primeiras horas (dependem do aquecimento) |
| SL executa no **preço do SL** (`stop_fill="level"`); a alternativa é o tick que rompeu | `run_backtest(stop_fill=…)` / `--stop-fill` | preço de saída dos SL diferente, principalmente em gaps |
| Barras M1 vêm do **bid** dos ticks | `bars.m1_from_ticks` | ATR parcial e sinais discordam |
| `tick_value` constante | `SymbolSpec` | lucro diverge em cruzados/índices (o Tester converte no tempo) |
| Sem swap, sem margem/stop‑out, execução ideal (sem atraso) | — | lucro líquido e trades finais diferem |
| Regra `ultimaAtualizacao == TimeCurrent()` ignorada | `OnTick` | só relevante com dois minutos no mesmo segundo (raro) |

Não testável com floats: o `>` estrito no cruzamento da referência (`main==0` exato). Foi copiado do fonte.

## Testes

```
pip install -r requirements.txt
python -m pytest -q tests
```

Os testes incluem verificações de mutação feitas à mão (trocar ask/bid no SL do sell, inverter o
sinal, errar os shifts, usar 50 em vez de 100 barras, sinal a cada M1 com TF>M1, tirar o gate de
risco/intervalo mínimo) — todas fazem algum teste falhar.

## Próximos passos (na ordem)

1. **Fechar a paridade do `01_SLTP`+MACD** (acima).
2. Trailing, `TakeOrganico`, `ReversalExit` (`03`–`06`) → recovery (`09`,`10`) → grid/pirâmide (`07`,`08`,`12`), estes
   em tick (o OHLC subestima perda em 3,3× no trailing e 23× no grid — números do README do repo de sets).
3. Demais indicadores e filtros; travas de conta.
4. Ligar como estágio alternativo do Autobot, gravando o mesmo formato que o `portfolio_builder` lê.
