# WRX Autobot — Pasta de Prontos, Entradas Completas e Metodologia

Data: 2026-07-31. Pedido do dono (verbatim, condensado): o autobot deve ter uma
**pasta clone igual às que contêm os templates de set**, marcada **com `*` onde
tem set pronto** ("assim fica mais fácil de subir os sets"); nela fica **o
portfólio daquele algoritmo**; atenção **nas entradas** ("nem as entradas com
todos indicadores sendo testados foi feito") **e na metodologia de treino**.

## Diagnóstico (estado em 2026-07-31)

1. **Biblioteca** `White_Rabbit_X_Sets` (3.738 sets, classe/ativo/sistema/
   variante) cobre os 12 indicadores: `EntryIndicator=0..10||Y` nos `*_MULTI`,
   Ichimoku (11) em arquivo próprio.
2. **Furo real das entradas**: `campanha.py` só enfileira `*_MULTI` — as
   variantes `*_ICHIMOKU` **nunca são testadas**. E o estágio 1 do circuito
   promove apenas `melhores[0]` (maior lucro in-sample): um genético que
   convergiu cedo para um indicador enterra os outros dez sem que nenhum tenha
   sido *medido*. Inconsistente com o resto do circuito, que decide tudo por
   retenção out-of-sample.
3. **Nenhuma organização dos prontos**: sets `VALIDADO_*.set` caem soltos na
   raiz de `Profiles/Tester`. Hoje: 8 REPROVADO, 0 VALIDADO, ledger resetado
   (metodologia nova de torneio ainda sem rodada completa).

## Decisões

### D1 — Pasta clone: `White_Rabbit_X_Sets_PRONTOS`

Espelho 1:1 da árvore da biblioteca (todas as pastas classe/ativo/sistema),
criado ao lado dela em `Profiles/Tester` — assim o diálogo "Load" do Strategy
Tester navega nela igual navega na biblioteca. Onde existe set validado, o set
de entrega (WFO desligado) é copiado para o nó espelho com o **marcador `＊`**
no nome: `＊BUY_MULTI.set`.

> **Por que `＊` (U+FF0A) e não `*`**: o Windows proíbe `*` literal em nomes de
> arquivo (`\ / : * ? " < > |`). O asterisco de largura total é visualmente
> idêntico, válido no NTFS e ordena o arquivo no topo da pasta. No `MAPA.md`
> (texto) o `*` é o verdadeiro.

Conteúdo gerado na raiz do clone:

- `MAPA.md` — árvore compacta com `*` em cada (ativo, sistema, variante)
  pronto + contagem geral. Ativos sem nenhum pronto viram uma linha-resumo.
- `_PORTFOLIOS/<sistema>.md` — **o portfólio daquele algoritmo**: tabela com
  os membros validados (símbolo, variante, retenção OOS, expectancy R, trades,
  `CapitalBaseR` lido do próprio set), capital total requerido e observação de
  correlação (o refino por correlação continua no `portfolio_builder.py`, que
  precisa dos relatórios HTML).

Sincronização: `ready_library.py` (novo, standalone e importável).
Fonte da verdade = arquivos `VALIDADO_*.set` presentes na raiz do tester
(nome carrega o veredito — decisão antiga) + métricas do ledger
`campanha_resultados.jsonl` quando existirem. Sync é idempotente e remove do
clone marcadores cujo `VALIDADO_*.set` de origem sumiu (rebaixado/refeito).
`campanha.py` sincroniza após **cada** combo registrado (falha de sync é
ruidosa mas não derruba a campanha).

### D2 — Entradas: todos os 12 indicadores medidos

1. `campanha.py`: fila passa a incluir `SELL/BUY_ICHIMOKU` (e `BOTH_ICHIMOKU`
   no bilateral), depois das MULTI — mantém o retrato "largura primeiro".
2. `optimize_two_stage.py`, estágio 1: em vez de promover `melhores[0]`, o
   circuito agrupa os passes aptos por `EntryIndicator`, pega **o melhor de
   CADA indicador** e roda o `torneio_retencao` (OHLC, ~2s cada, ≤11 passes)
   entre eles. O sinal vencedor é escolhido por **retenção OOS**, como todo o
   resto do circuito. Imprime cobertura: indicadores visitados pelo genético,
   aptos, e ausentes (com nome, não só número).

### D3 — Metodologia de treino (revisão)

O circuito de 4 estágios (sinal → gestão → motor → confirmação em tick real)
está sólido: WFO In-Sample na busca, torneios por retenção, gate do motor
("só adota se melhorar a retenção"), entrega com WFO desligado e
`conferir_set()` como guarda. A única quebra de coerência era o estágio 1
decidir por lucro in-sample — corrigida em D2.2. "Sequência lógica de acordo
com capital": a ordem de símbolos da campanha já vai do menor capital base
(forex majors) ao maior (metais); os portfólios por algoritmo somam o
`CapitalBaseR` dos membros para o dono decidir o que sobe primeiro.

### D4 — Filtros em funil (aditivo do dono, mid-sessão)

Pedido verbatim: "os demais indicadores de filtros como ma e adx devem ser
opcionais nas primeiras etapas! intenção é ir diminuindo os passos de acordo
com as etapas!". Implementação:

- **Templates** (`generate_system_sets.py`): as flags `AtivarFiltroMA`,
  `AtivarFiltroADX`, `AtivarFiltroMTF` e `EntradaATR` viram eixo `false..true`
  **ativo (Y)** na fase 1 — o genético decide *se* o filtro existe junto com o
  sinal. O ajuste dos filtros continua estagiado em N.
- **Circuito** (`optimize_two_stage.py`): flags movem-se de GESTAO para
  SINAL (estágio 1); ajuste grosso (`MA_Period`, `MetodoMA`, `ADX_Limiar`,
  `MTF_RequererAmbos`, `VolatilityFilter`) no estágio 2; ajuste fino
  (`MA_Method`, `SentidoMA`, `MA_AppliedPrice`, `MA_SlopeLookback`,
  `ADX_Period`, `MetodoADX`) no estágio 3 (MOTOR). `GATES` estendido: tudo
  que é ajuste de filtro só entra se a flag sobreviveu cravada em `true`.
- Efeito: os passos **diminuem etapa a etapa** — 1ª decide o quê (sinal +
  existência dos filtros), 2ª a geometria de quem vive, 3ª a base de cálculo,
  4ª só confirma. Requer **regenerar a biblioteca** (as flags hoje não têm
  faixa nos .set).

### D9 — Pente fino: eixos condicionais ao indicador (733× de corte)

Dono: *"tem que ter pente fino nos setores que estão false para não queimar
inputs à toa"*. A auditoria de bool morta (`GATES`) já cobria setor desligado,
mas faltava a classe **condicionada ao indicador**. Lido na criação dos
handles do EA (~1234-1290):

| Parâmetro | Indicadores que realmente usam |
|---|---|
| `Slow_EMA` | MACD, EMA_Cross, OsMA, Ichimoku (Kijun) |
| `MACD_SMA` | MACD, Stochastic (%D), OsMA, Ichimoku (Senkou B) |
| `StochasticSlowing/Method/PriceField` | apenas Stochastic |

Num set MULTI o indicador varia 0–10, então esses eixos produziam **cópias
idênticas** para os 8 indicadores que os ignoram. Correção: saem da fase 1
(N, com faixa preservada) e o circuito abre na fase 2 **só os que o vencedor
usa** (`INDICADOR_USA` + `eixos_do_indicador()`, com log do que foi cortado).
Efeito: espaço máximo de busca **1,79e16 → 2,44e13**.

### D10 — Hedge, multiplicador e fórmulas

- **Hedge é eixo em sistemas BUY+SELL juntos** (`08_GRID_UNIFIED`): permitir
  posições opostas simultâneas é decisão de estratégia. O OnInit só rejeita
  `Hedging=true` em conta netting; o terminal de teste é hedging.
- **`Multiplicador` fixo em 1** (07, 08, 09). O input é *"Target Profit
  Multiplier"*: no recovery o alvo é `|perda acumulada| × Multiplicador` e o
  lote sai de `|perda| × Multiplicador / (stop × tickValue)`; no grid,
  `lucroPorLote × volume × Multiplicador`. Com 1 a matemática fecha (recupera
  exatamente o perdido). A faixa anterior do martingale começava em **1,2** —
  a recuperação fechada nunca havia sido testada.
- **Fórmula por sistema** (`FORMULA_POR_SISTEMA`): 9 Pessimistic (geometria
  fixa 01/02, saída por sinal 06/11), 8 Sharpe-adjusted-by-DD (trailing
  03/04/05), 10 Resilience-to-DD (recovery 09/10), 1 Grid Survival (07/08).
  Não usadas de propósito: 13 (satura em 1.0) e 11 (ignora tamanho).
- **Estágio de filtros usa critério próprio: 7** (lucro por trade ajustado por
  DD). Filtro reduz trades por construção; julgar por lucro total puniria o
  filtro que corta operação ruim.
- **Notícias**: `AtivarFiltroNoticias=false` fixo e todos os parâmetros em N —
  nunca entram em otimização (confirmado nos sets).
- **Campanha**: EURUSD apenas, 42 combos, ordem grid → trailing → só-indicador
  → geometria fixa → recovery.

### D7 — Circuito v3: repetição, WFE obrigatório, execução por último

Diretrizes do dono (2026-07-31, fim da tarde):

1. **Fase 1 repete até 3×** — `optimize_two_stage.py` roda o genético de
   REGIÕES em até 3 rodadas acumulando os relatórios (relançar continua a
   mesma busca). Parada inteligente: a partir da 2ª rodada, só paga a
   seguinte se **melhorou o retrato** (lucro do topo +5% ou um indicador novo
   virou apto).
2. **Bool morta mata o setor** — já era o comportamento (`GATES`), e o combo 1
   comprovou: MTF/MA morreram `false` na fase 1 e a fase 2 abriu só 12 eixos,
   com ADX (sobrevivente) afinado em período e limiar.
3. **WFO obrigatório** — biblioteca inteira sai com `AtivarWFO=true` +
   In-Sample. Entrega continua WFO off.
4. **Filtros de execução por último, em IS+OOS** — novo estágio 3
   (`EXEC_FILTROS`): `TOD_From_Hour`/`TOD_To_Hour` (0–23, janela invertida =
   sessão noturna é válida no EA), dias da semana, `Fecharordensforadohorario`
   e `MaxSpread` (0 = sem filtro, escala ancorada no slippage da classe;
   sábado/domingo só têm faixa em cripto). Otimiza em IS+OOS por decisão
   explícita do dono; proteção: só é adotado se **melhorar a retenção**.

Circuito final: **1** regiões (≤3 rodadas) → **2** números → **3** execução
(IS+OOS) → **4** tick real → **5** prova em %.

### D8 — Colapso de sistemas: 05_BE_TRAIL ⊂ 03_TRAIL_ONLY (corrigido)

Auditoria de esqueleto de saída (produto cartesiano das flags alcançáveis por
sistema) encontrou `05_BE_TRAIL` **inteiramente contido** em
`03_TRAIL_ONLY`: 03 tinha `AtivarBreakeven` como eixo, alcançando as duas
configurações que 05 fixa. Efeito: ~2h de campanha por símbolo/lado medindo
esqueleto duplicado, e um vencedor de "TRAIL_ONLY" podendo sair com BE ligado.
Correção: 03 crava `AtivarBreakeven=false` — 03 mede o trailing sozinho, 05
mede o que o BE **acrescenta**. Auditoria pós-fix: 0 colapsos, 0 eixos inertes
nos 11 sistemas.

**Inércia condicional conhecida (sem correção possível)**:
`ReversalExitUseEntryFilters` (06 e 11) depende da *conjunção*
`EntradaATR ∧ MTF ∧ MA ∧ ADX` — se todos morrerem `false`, o eixo é inerte.
Um `.set` não expressa eixo condicional, e o parâmetro está em `ESCRITA`
(travado após a fase 1), então o custo é um 2× na fase 1 desses dois sistemas.

### D6 — REGIÕES → NÚMEROS (correção do dono, mid-sessão — SUPERSEDE D4)

Pedido verbatim: "nas primeiras fases os valores completos do grupo
[Entradas]... deve otimizar nesse primeiro momento as saidas tambem!
estamos descobrindo regioes nesse primeiro setor dai em diante vamos tirando
inputs de escrita e deixando somente de numeros! e ATR entrada é somente
para Grid!". O circuito virou 4 estágios:

1. **REGIÕES** (OHLC): grupo de Entradas COMPLETO (indicador, método, TF,
   applied price, períodos, Stochastic inteiro, Ichimoku, ATR_TimeFrame,
   PeriodoATR) + SAÍDAS do sistema (velas, Stop, Take, Trail, BE, grid,
   martingale/d'alembert) + flags de filtro. Torneio de retenção entre um
   campeão POR INDICADOR; do vencedor travam-se só os inputs DE ESCRITA
   (enums/bools — conjunto `ESCRITA`).
2. **NÚMEROS** (OHLC): escrita travada; refinam-se eixos numéricos + ajuste
   dos filtros sobreviventes (GATES). Torneio de retenção.
3. **Tick real**: confirmação (retenção IS+OOS + divergência).
4. **Percentual**: prova em % e entrega no modo provado (era o D5).

Gerador: fase 1 dos templates agora carrega tudo isso em Y;
`EntradaATR`/`VolatilityFilter` só existem como eixo nos sistemas de grid
(07/08) — nos demais, cravados (`apply_core(grid=...)`). Auditoria: todos os
eixos das listas conferidos contra os 132 `input` do .mq5 e contra o schema
dos sets (script inline, 2026-07-31). Regra do dono: **commit/push dos repos
só depois de validar os métodos de treino em backtest real** (campanha).

### D5 — Prova em PERCENTUAL antes de salvar (aditivo do dono, mid-sessão)

Pedido verbatim: "depois do teste tick real para validar deve ser alterado
para % testado novamente se passar ai salva". Racional: o circuito mede em
Fixed-R com capital base fixo (scale-invariant, sem juros compostos); a conta
real opera em % do saldo, onde a *sequência* das perdas importa. Estágio 5:
aprovado nos estágios 1–4 → `PositionSizeMode=0` (Percentage) → novo passe em
tick real IS+OOS → retenção ≥ `--min-retencao` para salvar. A entrega sai em
modo % (o modo provado). Sistemas sem Fixed-R (grid/martingale/d'alembert,
lote fixo) pulam a prova — o EA proíbe % sem stop. Guarda extra: o número de
trades é invariante a sizing; se mudar no passe %, a margem bloqueou ordens e
o log avisa. Veredito final ("APROVADO/REPROVADO") só é impresso depois do
estágio 5.

## Fora de escopo (YAGNI)

- Pesos por correlação dentro do clone (fica no `portfolio_builder.py`).
- Upload automático para o repositório GitHub de pre-sets.
- Reprocessar os 8 REPROVADO antigos (metodologia anterior; a campanha nova
  re-mede tudo).

## Testes (sem MT5, estilo `test_ler_metricas.py`)

`test_ready_library.py`: espelho criado, marcador `＊`, remoção de marcador
órfão, MAPA e portfólio com métricas; `melhor_por_indicador()` (agrupamento e
ordem); fila da campanha contém ICHIMOKU.
