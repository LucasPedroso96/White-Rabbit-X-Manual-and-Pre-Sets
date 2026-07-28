# White Rabbit X - Sets de otimizacao por SISTEMA

**3738 sets** = 89 ativos x 11 sistemas x 2 lados x 2 variantes de indicador.

Cada arquivo e um sistema de trading completo, otimizavel do inicio ao fim:
indicador de entrada, metodo de gatilho, timeframe, periodos, ATR, filtros e a
geometria de saida daquele sistema estao TODOS marcados `Y` no mesmo arquivo.
Nao existe estagio obrigatorio: voce roda, descobre, e desliga na mao (`Y` -> `N`)
o que ja resolveu antes da rodada seguinte.

## Estrutura

```
<classe>/<ATIVO>/<NN_SISTEMA>/<LADO>_<VARIANTE>.set
01_Forex/USDJPY/01_SLTP/BUY_MULTI.set
01_Forex/USDJPY/01_SLTP/BUY_ICHIMOKU.set
```

- **MULTI**: `EntryIndicator` e um eixo com 11 motores (MACD, EMA, Momentum,
  Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA).
- **ICHIMOKU**: indicador fixo em Ichimoku (valor 11), porque ele exige
  Tenkan < Kijun < SenkouB e nao cabe na mesma faixa de periodos dos outros.

## Os 11 sistemas

| Sistema | Esqueleto de gestao | Eixos proprios de saida | Espaco tipico |
|---|---|---|---:|
| `01_SLTP` | SL + TP como multiplos de ATR | Stop, Take, Breakeven on/off, distancia de BE | 7.98e+11 |
| `02_SLTP_ORGANIC` | SL + TP organico (ancora no ultimo trade) | Stop, Take, Breakeven on/off, distancia de BE | 7.98e+11 |
| `03_TRAIL_ONLY` | SL + trailing, sem TP: deixa correr | Stop, fonte do trailing, Trail, BE | 2.40e+12 |
| `04_SLTP_TRAIL` | SL + TP + trailing atras | Stop, Take, Trail, BE | 1.20e+13 |
| `05_BE_TRAIL` | Breakeven obrigatorio + trailing, sem TP | Stop, distancia de BE, fonte do trailing, Trail | 1.20e+12 |
| `06_REVERSAL_EXIT` | Fecha no sinal contrario do indicador | Stop, trailing on/off, Trail, BE, filtros na saida | 1.92e+12 |
| `07_GRID_SEPARATE` | Grid, alvo por lado | Take, Multiplicador, DistanciaMinima, n de pernas | 3.59e+12 |
| `08_GRID_UNIFIED` | Grid, alvo unico da cesta | Take, Multiplicador, DistanciaMinima, n de pernas | 1.80e+13 |
| `09_MARTINGALE` | Lote dobra apos perda, 1 posicao por lado | Stop, Take, Multiplicador, passos maximos, BE | 2.24e+13 |
| `10_DALEMBERT` | Lote cresce em passo aritmetico apos perda | Stop, Take, passo de lote, passos maximos, BE | 1.60e+13 |
| `11_SIGNAL_ONLY` | Sem SL e sem TP: mede o sinal cru | so entrada e filtros (cobertura negativa) | 3.55e+08 |

## Nucleo comum (em todos os sistemas)

| Eixo | Inicio | Passo | Fim |
|---|---:|---:|---:|
| `EntryIndicator` (MULTI) | 0 MACD | 1 | 10 OsMA |
| `EntryMethod` | 0 reversao | 1 | 6 qualquer gatilho |
| `TimeFrame` | 3 valores conforme a classe do ativo | 1 | |
| `Fast_EMA` | 6 | 3 | 18 |
| `Slow_EMA` | 21 | 6 | 45 |
| `MACD_SMA` | 3 | 3 | 15 |
| `PeriodoATR` | 7 | 7 | 28 |
| `AtivarFiltroMTF` / `AtivarFiltroMA` / `AtivarFiltroADX` / `EntradaATR` | false | | true |
| `StochasticPriceField` (MULTI) | 0 Low/High | 1 | 1 Close/Close |
| `IchimokuUseKumo` / `IchimokuChikouFilter` (ICHIMOKU) | false | | true |
| `MA_Period` | 100 | 100 | 300 |
| `MetodoMA` | 0 | 1 | 3 |
| `ADX_Limiar` | 15 | 5 | 30 |

`Fast_EMA` para em 18 e `Slow_EMA` comeca em 21 de proposito: o EA exige
fast < slow e rejeita o passe inteiro (`incorrect input parameters`) se a ordem
quebrar. O mesmo vale para o Ichimoku, que por isso tem arquivo separado.

## Como rodar

1. Strategy Tester -> `White Rabbit X (Global Multi-Indicator).ex5`, escolha o
   simbolo real do broker (confira sufixo) e o periodo de historico.
2. Aba Inputs -> **Load** -> o `.set` do ativo/sistema/lado que voce quer.
3. Otimizacao: **Fast genetic based algorithm**. Acima de 100 milhoes de
   combinacoes o MT5 ja chaveia sozinho para genetico.
4. Rode. Anote os vencedores; relancar o genetico continua a mesma busca e
   refina o resultado.
5. **Trave o que descobriu**: mude o `Y` daquele parametro para `N` e deixe o
   valor vencedor nos quatro campos. O espaco de busca cai em ordens de
   magnitude e a rodada seguinte fica muito mais precisa.
6. Repita ate sobrar so a geometria de saida; ai da para usar Complete Search.

Ordem de travamento que costuma render mais: indicador e metodo -> timeframe ->
periodos -> stack de filtros -> geometria de saida.

## Avisos por status

- `HEDGE_ACCOUNT_REQUIRED`: 534 sets
- `HIGH_RISK`: 712 sets
- `HIGH_RISK_RESEARCH`: 356 sets
- `RESEARCH`: 2136 sets

- **HEDGE_ACCOUNT_REQUIRED** (grid): exige conta MT5 hedging de verdade.
  Netting nao representa pernas independentes e o EA recusa o init.
- **HIGH_RISK** (martingale, d'alembert): a curva de risco muda de natureza.
  Otimizar sem teto de lote so e valido em pesquisa; defina um teto valido no
  broker antes de qualquer forward-demo.
- **HIGH_RISK_RESEARCH** (signal only): sem SL. Serve para medir o sinal cru,
  nunca para operar.

Nenhum destes arquivos e preset de producao. Depois de validar out-of-sample,
copie os vencedores para um arquivo novo com todas as flags em `N` e um
MagicNumber proprio.

## Ferramentas

- Gerador: `white_rabbit_x_optimization_tools/generate_system_sets.py`
- Validador: `white_rabbit_x_optimization_tools/validate_system_sets.py`

O validador reimplementa as regras do `OnInit` do EA e testa os extremos de
cada eixo em todos os arquivos: se algum `.set` puder gerar
`INIT_PARAMETERS_INCORRECT`, ele falha antes de voce descobrir no tester.

Manifesto completo (ativo, sistema, combinacoes, magic, SHA-256):
`MANIFESTO_SISTEMAS.csv`.
## Criterio de otimizacao e metricas em R

O EA calcula o proprio criterio no `OnTester` (`selectedFormula`, 0 a 14). Os
sets ja vem configurados assim:

| Sistemas | Sizing | `selectedFormula` |
|---|---|---|
| `01`..`06` (todos tem Stop Loss) | **Fixed-R**, 1R = 1% do capital base | 13 - Levain Composite Score |
| `07`, `08` (grid) | Fixed Lot 0.01 | 1 - Grid Survival Score |
| `09`, `10`, `11` | Fixed Lot 0.01 | 13 - Levain Composite Score |

### Por que Fixed-R onde da

R (multiplo de risco) e a unica unidade comparavel entre ativos e sistemas: um
resultado de +40R em ouro e +40R em EURUSD significam a mesma coisa, enquanto
"+3.200 USD" nao significa nada sem saber o lote e o saldo.

No EA, R **so existe** quando `PositionSizeMode` e Fixed-R (3) ou Percentage
(0): `ComputeRMetrics()` devolve `false` em Fixed Lot e Monetary, e a formula
`SomaR` viraria 0 em todo passe. Fixed-R tambem exige Stop Loss ativo nos dois
lados, e o EA proibe combina-lo com grid e com D'Alembert -- por isso os
sistemas `07`..`11` ficam em Fixed Lot.

Com Fixed-R ligado, o log de cada passe traz:

```
Trades: 148 | Total R: +37.40 | Average R (expectancy): +0.253
Win rate: 41.2% | Payoff: 2.11R | Largest gain: +6.20R | Largest loss: -1.00R
Maximum drawdown: 8.40R
```

### Por que o criterio NAO e `SomaR` (14)

`SomaR` devolve o R acumulado e **ignora drawdown**: ele premia um sistema com
+50R e 30R de drawdown do mesmo jeito que um com +50R e 6R. O Levain Composite
Score (13) pondera quatro coisas normalizadas de 0 a 1:

- **35%** Profit Factor (teto em 3.0)
- **30%** lucro por trade em % do deposito, ajustado por drawdown e PF
- **20%** Sharpe (teto em 2.0)
- **15%** Recovery Factor (teto em 5.0)

e devolve 0 se houver menos de 30 trades (`MinTradesOnTester`) -- o que descarta
sozinho o classico "vencedor" de 3 trades sortudos. Todos os componentes sao
razoes ou percentuais, entao o score e scale-invariant: nao muda se voce dobrar
o deposito do teste.

Nas formulas nao-grid ainda entra o `ConsistencyFactor()`, um multiplicador
suave de 0.85 a 1.00 que penaliza sequencias longas de perda.

**Resumo pratico**: otimize pelo Composite (13), leia o R no log para comparar
e para decidir se o sistema entra no portfolio. Troque para `SomaR` (14) apenas
se quiser explicitamente maximizar edge bruto ignorando o drawdown.

## Walk-Forward (WFO)

O WFO do White Rabbit X **nao e** o "Forward" nativo do Strategy Tester -- e
interno ao EA. Com `AtivarWFO=true` num backtest, o `OnInit` fatia o periodo em
janelas In-Sample e Out-of-Sample, da primeira barra do teste ate
`input_end_date`, e o `OnTick` consulta `IsInSample()` a cada barra.

| `MetodoDeEntradawfo` | Comportamento | Para que serve |
|---|---|---|
| `0` Insample | Fora das janelas IS o EA fecha posicoes, nao abre novas e retira o lucro acumulado | **Otimizar**: o genetico so ve In-Sample |
| `1` InSampleAndOutSample | Opera o periodo inteiro, mas continua marcando as janelas e o `OnTester` imprime a Walk Forward Efficiency | **Validar** o vencedor |

### A armadilha da data

O `OnTester` compara o fim real do teste com `input_end_date` e **devolve 0.0 se
o teste terminou antes** (tolerancia de 80 horas, que cobre o gap de fim de
semana). Data errada = todos os passes valem zero e a otimizacao inteira parece
quebrada. Nao configure isso na mao arquivo por arquivo -- use:

```bash
# Ligar para otimizar (so In-Sample), IS de 180 dias e OOS de 60
python configure_wfo.py --end-date 2026.07.21 --is-days 180 --oos-days 60

# Depois de escolher o vencedor: validar com WFE
python configure_wfo.py --end-date 2026.07.21 --is-days 180 --oos-days 60 \
    --mode validate --only 01_Forex/USDJPY

# Voltar ao normal
python configure_wfo.py --off
```

### Como dimensionar as janelas

- O periodo do teste precisa cobrir **pelo menos IS + OOS**; o `OnInit` rejeita
  o init se `inSampleDays + outSampleDays > totalDays`.
- A proporcao usual e **IS entre 2x e 4x o OOS**. Com 3 anos de historico:
  IS 180 / OOS 60 rende cerca de 6 ciclos -- amostra suficiente para o WFE
  significar alguma coisa.
- Janelas curtas demais (IS 30 / OOS 7) geram muitos ciclos com poucos trades
  cada; o piso de 30 trades zera o score e voce nao vai entender por que.
- `wfo_windowSize` e `wfo_stepSize` aceitam os presets em dias (360, 180, 90,
  30, 7, 1) ou `-1` (Custom). Em Custom, `wfo_customStepSizePercent`
  **negativo** significa dias fixos; positivo significa percentual do IS.

### Lendo o resultado

No modo `validate`, o `OnTester` imprime:

```
Walk Forward Efficiency (WFE): 68.40%
Average daily In-Sample profit: 12.30, average daily Out-Sample profit: 8.41
```

WFE e o lucro medio diario OOS dividido pelo IS. Leitura pratica: abaixo de
50% o sistema esta sobre-ajustado ao In-Sample; acima de 100% costuma ser
sorte de janela, nao superioridade. A faixa saudavel fica entre 50% e 100%, e o
que importa mais que o numero e ele se manter estavel entre ciclos.

