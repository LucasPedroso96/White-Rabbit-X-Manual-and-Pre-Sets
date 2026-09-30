# WRX Engine — backtest próprio da White Rabbit X (o MT5 só executa)

> Código-fonte da EA que este motor porta: `Metatrader5EAS/White Rabbit/EA/` (repo privado). Esta pasta (`WRX_Engine/`) é autocontida para migrar para lá quando quiser.

Porta a semântica do `EA/White Rabbit X (Global Multi-Indicator).mq5` para Python, para
rodar a peneira de otimização fora do Strategy Tester. Mesma regra de adoção do simulador
do Zeus: **o motor só substitui o Tester depois que a paridade trade a trade fechar contra
rodadas reais em _Every tick based on real ticks_**. Antes disso é ferramenta de estudo.

> **Estado honesto:** 93 testes passam, mas eles provam a *lógica* contra cenários construídos à mão e contra
> laços ingênuos escritos a partir do `.mq5`. **Nada foi comparado ainda com uma saída real do MT5** — não havia
> terminal MT5 no ambiente onde isto foi escrito. O primeiro trabalho real é a revisão desta noite (abaixo).
> O que já foi portado está em `REVISAO_INPUTS.md`; o que falta e por quê, em `PORTING_STATUS.md`.

## Escopo atual

| Portado | Recusado (o motor levanta `UnsupportedConfig`, nunca ignora em silêncio) |
|---|---|
| Os **12 indicadores** de entrada (MACD, EMA, Momentum, Stochastic, TRIX, RSI, CCI, WPR, DeMarker, MFI, OsMA, Ichimoku) e os 7 `EntryMethod` | Trailing, TakeOrganico |
| Decisão 1×/minuto no 1º tick; sinal 1×/barra do `TimeFrame`; `ATR[0]` parcial | Grid, Pirâmide, Martingale, D'Alembert |
| SL/TP em ATR, lote **Fixed-R**, gate de risco de `myOrderSend`, piso de lote, guarda anti-oversizing | Lote Percentage / Monetary / FixedLot |
| Breakeven (só reavaliado nas decisões) | Entradas pendentes (Stop/Limit/OCO/sessão) |
| Filtros **MTF, MA, ADX, volatilidade ATR** | Filtro de notícias |
| `ReversalExit` por sinal contrário, `Fecharordensforadohorario` | `ReversalExit` "OnOppositeOrder" |
| Dias/horário/`MaxSpread`, `stops_level`, `Hedging`, `MaxLong/ShortTrades` | Travas de conta/margem (`MaxEquityDrawdownPercent`, `MinFreeMarginPercent`, `Trava_*`, `DailyLossLimitPercent`) |
| `.set` UTF‑16 com `atual\|\|início\|\|passo\|\|fim\|\|Y` | WFO `In Sample` (bloqueia entrada fora da janela IS) |

Cuidado com os **defaults do EA quando o input não está no `.set`**: `MaxEquityDrawdownPercent` vale 30 e
`MinFreeMarginPercent` 50 — a guarda os acusa. O `01_SLTP` que vem em `Sets/` traz `AtivarWFO=true` + `In Sample`;
para comparar, rode o Tester com `AtivarWFO=false` (as sondas já vêm assim).

## Revisão desta noite, guiada pelos inputs

```
py -m wrx_engine.review checklist --out REVISAO_INPUTS.md      # todos os inputs: status, sondas, nota
```
`sondas/` já traz **62 arquivos `.set`** (baseline seguro + um recurso ligado por vez) e `sondas/plano_de_teste.md`.
Roteiro:

1. `py tools/export_mt5_data.py --symbol EURUSD --from 2026-01-05 --to 2026-03-01 --out dados/eurusd`
   (spec, ticks reais e M1 de aquecimento; informe `--commission-per-lot-side` se houver).
2. No Tester (hedging para as sondas P02/P65/P66): **Every tick based on real ticks**, mesmo período/depósito para todas.
   Para cada `sondas/Pxx_*.set`, salve o relatório como `relatorios/Pxx_*.htm`. Comece por `P00_base`: se ela não fechar,
   nada acima dela vale.
3. `py -m wrx_engine.review run --baseline ../Sets/01_Forex/EURUSD/01_SLTP/BUY_MULTI.set --reports relatorios --ticks dados/eurusd_ticks.csv --spec dados/eurusd_spec.json --warmup dados/eurusd_m1_warmup.csv`
   → grava `REVISAO_INPUTS.md` com PASS/FAIL **por sonda e por input** e, nas que falham, o relatório de divergência
   (primeira divergência, mediana/máximo de erro por campo). Sai com código 1 se algo falhar.
4. Divergência sistemática = uma das hipóteses da tabela "Pontos a calibrar" (abaixo). Corrija uma de cada vez.
5. `py -m wrx_engine.review sync --ea "White Rabbit X (Global Multi-Indicator).mq5"` acusa `input` novo no `.mq5` sem status.

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
risco/intervalo mínimo, nível neutro, linha de sinal, filtros MA/MTF/ADX/volatilidade, reversal exit) — todas
fazem algum teste falhar. Uma exceção conhecida: o `>` estrito do cruzamento da referência (ver acima).

## Próximos passos (detalhe em PORTING_STATUS.md)

1. **Revisão desta noite**: `P00_base` primeiro, depois as demais sondas; cada FAIL aponta uma hipótese a calibrar.
2. Trailing e `TakeOrganico` (`02`–`05`), lotes Percentage/Monetary/FixedLot (`11_SIGNAL_ONLY`) → recovery (`09`,`10`) →
   grid/pirâmide (`07`,`08`,`12`), estes em tick (o OHLC subestima perda em 3,3× no trailing e 23× no grid).
3. Entradas pendentes, travas de conta/margem, notícias, janelas WFO, swap; fórmulas de fitness do `OnTester`.
4. Motores de entrada das EAs Bollinger e Candles Entry.
5. Ligar como estágio alternativo do Autobot, gravando o mesmo formato que o `portfolio_builder` lê.
