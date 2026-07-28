# White Rabbit X — Manuais e biblioteca de sets

[English below](#english)

Material público do **White Rabbit X**, Expert Advisor para MetaTrader 5.
Aqui ficam os manuais em 11 idiomas e a biblioteca completa de **3.738 sets**
de otimização.

> **Os sets são pontos de partida, não estratégias prontas.** Cada arquivo abre
> um sistema completo com todos os eixos marcados para otimização. Os valores
> que vêm neles são o começo da busca — não rode um set direto em conta real
> esperando resultado. O caminho é otimizar, travar o que já resolveu, e validar
> fora da amostra.

- **Expert Advisor**: [MQL5 Market](https://www.mql5.com/pt/market/product/187173)
- **Comunidade e suporte**: [Telegram](https://t.me/MrRabbit_MT5)

---

## Como usar a biblioteca

```
Sets/<classe>/<ATIVO>/<NN_SISTEMA>/<LADO>_<VARIANTE>.set
Sets/01_Forex/EURUSD/01_SLTP/BUY_MULTI.set
```

Copie a pasta `Sets/` para `MQL5\Profiles\Tester\` do seu terminal. No Strategy
Tester: aba **Inputs → Load**.

- **LADO**: `BUY` ou `SELL` em dez dos onze sistemas. O `08_GRID_UNIFIED` usa
  **`BOTH`**, porque a cesta unificada tem um alvo só cobrindo os dois lados.
- **MULTI**: o indicador de entrada é um eixo de otimização (MACD, EMA,
  Momentum, Stochastic, TRIX...).
- **ICHIMOKU**: indicador fixo, porque ele exige Tenkan < Kijun < SenkouB e não
  cabe na mesma faixa de períodos dos outros.

## Os 11 sistemas

| Sistema | Gestão de saída | Dimensionamento |
|---|---|---|
| `01_SLTP` | SL + TP em múltiplos de ATR | Fixed-R |
| `02_SLTP_ORGANIC` | TP ancorado no último trade | Fixed-R |
| `03_TRAIL_ONLY` | Só trailing, sem TP | Fixed-R |
| `04_SLTP_TRAIL` | SL + TP + trailing | Fixed-R |
| `05_BE_TRAIL` | Breakeven + trailing | Fixed-R |
| `06_REVERSAL_EXIT` | Fecha no sinal contrário | Fixed-R |
| `07_GRID_SEPARATE` | Grid, alvo por lado | Lote fixo |
| `08_GRID_UNIFIED` | Grid, alvo único da cesta | Lote fixo |
| `09_MARTINGALE` | Lote cresce após perda | Lote fixo |
| `10_DALEMBERT` | Incremento aritmético | Lote fixo |
| `11_SIGNAL_ONLY` | Sem SL/TP — mede o sinal cru | Lote fixo |

Os sistemas **01 a 06 usam Fixed-R**: o lote sai do orçamento de risco, então
eles se adaptam sozinhos ao tamanho da conta. Os **07 a 11 usam lote fixo** — o
risco deles é o que o lote mínimo custa naquele instrumento, independente do seu
saldo. Comece pelos Fixed-R.

---

## Duas coisas que mudam o seu resultado

### 1. Modo de modelagem do Strategy Tester

Na aba **Settings**, campo **Modeling**:

```
Every tick based on real ticks   <- use este
OHLC 1 minute                    <- só para 01_SLTP e 02_SLTP_ORGANIC
```

Medindo o mesmo set nos dois modos ao longo de 3 anos, o modo OHLC **subestimou
a perda em 3,3× nos sistemas de trailing e em 23× no grid** — sempre para o lado
otimista. Só SL/TP fixo ficou dentro de 3%.

O motivo é estrutural: trailing e grid dependem de **quando** o preço tocou cada
nível dentro da barra. O modo OHLC interpola isso e suaviza justamente as
excursões adversas que derrubariam a posição.

### 2. Trave o que já descobriu

Cada set abre milhões de combinações — o maior deles passa de 22 trilhões. O
caminho é iterativo: rode, descubra, e mude o `Y` do parâmetro para `N` deixando
o valor vencedor. O espaço de busca cai em ordens de magnitude e a rodada
seguinte fica muito mais precisa.

Trave primeiro as **chaves**, não a geometria: `EntryIndicator` sozinho decide se
quatro outros parâmetros significam alguma coisa. Parâmetro atrás de uma chave
desligada é tempo de otimização gasto à toa.

---

## Manuais

`Manuais/<idioma>/` — cada um em `.md`, `.pdf` e `.docx`:

| Arquivo | Conteúdo |
|---|---|
| `01_User_Manual` | Manual completo |
| `02_MQL5_Market_Description` | Descrição do produto |
| `03_WFO_Optimization_Guide` | Guia de walk-forward |
| `04_FAQ_and_Support` | Perguntas frequentes |
| `07_Set_Ecosystem_Tutorial` | Tutorial da biblioteca de sets |
| `08_Technical_Compatibility` | Compatibilidade técnica |

Português, English, Русский, 中文, Español, 日本語, Deutsch, 한국어, Français,
Italiano, Türkçe.

---

<a name="english"></a>

# White Rabbit X — Manuals and set library

Public material for **White Rabbit X**, a MetaTrader 5 Expert Advisor: manuals
in 11 languages and the full library of **3,738 optimization sets**.

> **The sets are starting points, not finished strategies.** Each file opens a
> complete system with every axis marked for optimization. The values shipped in
> them are where the search begins — do not run a set as-is on a live account.
> Optimize, lock what you have settled, and validate out of sample.

- **Expert Advisor**: [MQL5 Market](https://www.mql5.com/en/market/product/187173)
- **Community and support**: [Telegram](https://t.me/MrRabbit_MT5)

Copy `Sets/` into your terminal's `MQL5\Profiles\Tester\`, then load a file from
**Inputs → Load** in the Strategy Tester.

**Set the modeling mode to "Every tick based on real ticks".** Measured across 3
years on the same set, the OHLC mode understated losses by 3.3× on trailing
systems and 23× on grid — always in the optimistic direction. Only fixed SL/TP
stayed within 3%.
