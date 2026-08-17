# Melhorias e Ativos — a partir do documento "Multiple R White Rabbit"

Fonte: `Multiple R White Rabbit.txt` (colado pelo dono em 2026-08-17). Este
arquivo cruza as recomendações do documento contra o estado REAL do código
nesta data — o que já está implementado, o que diverge, e o que é lacuna
concreta. Não é um resumo do texto original, é uma auditoria em cima dele.

## 1. R Fixo vs Porcentagem — já implementado como o documento recomenda

O guard que bloqueia `RiscoRFixo` e `Porcentagem` simultâneos já existe no
`OnInit` (mutuamente excludentes, confirmado). O padrão descrito no
documento — **pesquisar em R Fixo, entregar em %** — já é exatamente o que
`optimize_two_stage.py` faz no Stage 5 ("prova em %", `optimize_two_stage.py:1781-1819`):
mede tudo em R durante a busca, troca pra Percentage, revalida em tick real
com juros compostos, e só entrega se passar nos dois. Isso cobre os
sistemas 01-06, e a partir de hoje também 12_GRID_INVERSO e 09_MARTINGALE
(ver sessão de trabalho de 2026-08-17).

**Não implementado ainda**: o "meio-termo" que o documento recomenda pro
live — R Fixo com re-base periódico do `CapitalBaseR` (mensal ou a cada
±20-25% de variação de saldo) em vez de trocar pra % continuamente. Hoje
`CapitalBaseR` é fixo por classe de ativo só na fase de pesquisa; não existe
mecanismo de re-base automático pro live. Se for operar ao vivo em R puro
(em vez de entregar em %), vale construir isso.

## 2. Fórmula de otimização — achado real, não só confirmação

O documento recomenda **Formula_SomaR como critério PRIMÁRIO** para
sistemas de trailing (03/04/05/06), com cross-check via
`SharpeAdjustedByDD`/`ResilienceToDrawdown`, e evitar `Formula_Profit`/
`EfficiencyRelativeToDeposit` nesses sistemas por serem fáceis de overfitar.

Rastreei o que o código realmente faz e a resposta é **em camadas, não uma
fórmula só**:

| Fase | O que decide o critério | Fórmula usada hoje (03/04/06) |
|---|---|---|
| Busca (Stage 1-2) | `FORMULA_POR_SISTEMA` em `generate_system_sets.py` | `5` = `Formula_AdjustedEfficiencyForGrid` |
| Stage 3 (filtros de execução) | override explícito em `optimize_two_stage.py:1586` | `7` = `Formula_ProfitPerTradeAdjustedByDD` |
| Entrega final (só sistemas R-capable aprovados) | override em `optimize_two_stage.py:1844` | `14` = `Formula_SomaR` |

Ou seja: `SomaR` já aparece, mas só como **rótulo do candidato final
entregue**, não como o critério que guia a busca genética ao longo das
fases 1-3 pros sistemas de trailing. O documento pede o oposto: SomaR como
critério PRIMÁRIO da busca em si. Isso é uma divergência real entre a
recomendação e a prática atual — vale uma decisão consciente (trocar
`FORMULA_POR_SISTEMA` de 03/04/06 pra `14`, ou manter como está e entender
por que `AdjustedEfficiencyForGrid` foi escolhido pra eles). Não mudei nada
aqui ainda — é uma pergunta em aberto, não uma correção que já apliquei.

## 3. Timing de breakeven — parcialmente alinhado, parcialmente por design

Documento: breakeven cedo demais "mata a expectativa"; o ponto ideal é
**+1R a +1.5R**, não +0.2R como muita gente faz.

Estado atual (`generate_system_sets.py`, `BreakevenDistancia`):
- Sistemas SEM Take (03/05/06/12): faixa `0.5 – 3.0` (referência = distância
  do Stop). Isso **já cobre** a faixa 1.0-1.5 que o documento recomenda, e
  vai além (permite até 3R, mais conservador que o documento sugere).
- Sistemas COM Take (01/02/04/09/10): faixa `0.15 – 0.7` — mas a referência
  aqui é a distância do **Take**, não do Stop (mudança deliberada de
  2026-08-16, documentada no código: garante matematicamente que o gatilho
  cai antes do alvo). Não é diretamente comparável à recomendação do
  documento, que fala em termos de SL. Não é uma divergência, é uma base de
  cálculo diferente por razão própria — vale só ter isso claro.

## 4. Hierarquia de saída — o EA tem o melhor da lista, não tem os do meio

Documento: `Trailing ATR (melhor) > Chandelier Exit > Donchian Exit >
Breakeven puro > TP fixo`.

O EA implementa Trailing ATR, Breakeven e TP fixo — os três extremos da
lista. **Chandelier Exit e Donchian Exit não existem** como mecanismos
alternativos (`Candlesticktype` só escolhe a FONTE de preço do trail
existente — Open/Close/High/Low —, não um algoritmo diferente). Como o
documento já classifica ATR Trail como o melhor da lista, isso não é
urgente, mas é uma lacuna real se algum dia quiser comparar as três
abordagens de trail entre si.

## 5. Universo de ativos — a lacuna mais concreta deste documento

O documento lista repetidamente os mesmos nomes como topo de tabela pra
trend-following/geral: **XAUUSD, NAS100, SP500 (US500), DE40 (DAX), WTI,
BTCUSD, USDJPY, EURJPY, AUDJPY** — e separadamente, duas vezes, chama
**Café, Cacau e Cobre** de "commodities esquecidas" que "frequentemente
apresentam tendências mais limpas que moedas".

Conferido contra `ASSETS` em `generate_system_sets.py` (89 símbolos, 5
classes):

| Ativo sugerido | Está no universo hoje? |
|---|---|
| XAUUSD, XAGUSD, XAUEUR | ✅ (05_Metals) |
| EURUSD, USDJPY, EURJPY, GBPJPY, AUDJPY | ✅ (01_Forex) |
| BTCUSD, ETHUSD | ✅ (02_Cryptocurrencies) |
| WTI, BRENT | ✅ (03_Indices_Energies) |
| **NAS100/USTECH, US500/SP500, DE40/DAX, Nikkei225** | ❌ **ausentes** |
| **Café, Cacau, Cobre** | ❌ **ausentes** |
| Natural Gas | ❌ ausente |

`03_Indices_Energies` hoje só tem `BRENT` e `WTI` — **nenhum índice de
ações de verdade**, apesar do nome da classe e apesar do documento chamar
NAS100 de "talvez o melhor mercado para trailing stop" e "talvez o melhor
ativo do mundo para trend following". Essa é a lacuna de maior impacto
potencial identificada aqui.

**Ressalva do próprio documento, que vale repetir**: a inclusão de
Café/Cacau/Cobre é condicionada a "se a RoboForex disponibilizar esses
contratos com histórico suficiente" — preciso confirmar disponibilidade
real na corretora antes de qualquer um desses símbolos entrar em
`generate_system_sets.py`. Índices (NAS100/US500/DE40) são mais prováveis
de já estarem disponíveis (RoboForex costuma oferecer os principais), mas
também não confirmei o símbolo exato usado por essa corretora especificamente.

## 6. Afinidade sistema × classe de ativo — ideia nova, não implementada

O documento separa claramente três perfis de ativo por TIPO de sistema:

- **Grid sem SL (só TP)**: quer ranging, reversão à média, sem tendências
  extremas — EURUSD, EURGBP, AUDNZD, NZDCAD, USDCHF, AUDCAD, CADCHF, EURCHF.
- **Trend-following puro (trail sem SL fixo apertado)**: quer tendências
  macro fortes — XAUUSD, NAS100, US500, BTCUSD, WTI.
- **TP+SL com breakeven/trailing**: quer eficiência direcional (alterna
  consolidação e rompimento) — XAUUSD, NAS100, DE40, USDJPY, EURJPY.

Hoje `generate_system_sets.py` gera a matriz **sistema × TODO o universo de
ativos**, sem nenhum filtro de afinidade — 07_GRID_SEPARATE e
12_GRID_INVERSO rodam em XAUUSD (ativo de tendência forte, o pior cenário
pro grid clássico segundo o documento) tanto quanto 05_BE_TRAIL roda em
EURGBP (par lateral, onde trailing tende a ficar te cortando sem tendência
pra aproveitar). Isso não é um bug — é assim que o gate de sobrevivência
(`SISTEMAS_GATE_SOBREVIVENCIA`) e a busca genética filtram o que não
funciona, deixando o dado decidir em vez de um filtro manual a priori.
Mas para **priorizar onde rodar campanhas primeiro** (em vez de deixar tudo
pra trás igualmente), esse mapeamento do documento é um guia útil e
gratuito — não precisa de código novo, só de critério na hora de escolher
o próximo `--sistemas --simbolos` de uma campanha.

## Resumo de ações sugeridas (nenhuma aplicada ainda, aguardando decisão)

1. **Confirmar disponibilidade na RoboForex** de NAS100/US500/DE40 e, se
   houver, Café/Cacau/Cobre/Natural Gas — maior potencial de impacto, menor
   esforço de implementação (só adicionar símbolos em `ASSETS`).
2. **Decidir sobre `FORMULA_POR_SISTEMA` de 03/04/06**: manter
   `AdjustedEfficiencyForGrid` guiando a busca (estado atual) ou trocar pra
   `SomaR` (`14`) como o documento recomenda para trailing.
3. **Re-base periódico de `CapitalBaseR` no live**, se decidir operar em R
   puro em vez de entregar em % — não existe hoje.
4. Chandelier/Donchian Exit como alternativa ao trail ATR — baixa
   prioridade, o documento já indica ATR como o melhor dos três.
5. Usar o mapeamento sistema×ativo do documento como critério informal pra
   priorizar campanhas (grid em pares laterais, trend/trail em
   XAUUSD/NAS100/DE40/WTI/BTCUSD) — sem mudança de código, só de prática.
