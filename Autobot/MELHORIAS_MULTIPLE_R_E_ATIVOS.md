# Sugestões de Ativos por Sistema — White Rabbit X

Fonte: `Multiple R White Rabbit.txt` (colado pelo dono, 2026-08-17), incluindo
o ranking de trend-following (5 níveis de estrela) e a lista de melhores
candidatos pra grid. Este documento pega os **11 sistemas reais** do EA
(`apply_system()` em `generate_system_sets.py`), agrupa os que têm a mesma
mecânica de risco/saída, e mapeia cada grupo contra os ativos que o
documento recomenda — cruzado com o universo atual de 89 símbolos em
`ASSETS`. `✅` = já está no universo hoje. `🆕` = recomendado, mas ausente
(precisa entrar em `ASSETS`, e confirmar antes se a RoboForex oferece).

## Arquétipo A — Grid clássico, sem Stop, fecha só a cesta em lucro
**Sistema: `07_GRID_SEPARATE`**

`AtivarStop=false` sempre — não tem risco por posição, só a cesta
inteira fechando quando bate a meta de lucro (`Multiplicador=1` fixo,
`DistanciaMinima` busca 2.5–6.0 ATR). Uma tendência forte e sustentada é o
pior cenário: a cesta continua abrindo pernas contra o movimento sem parar.
Quer **ranging, reversão à média, volatilidade estável**.

| Estrelas do documento | Ativos | No universo? |
|---|---|---|
| ⭐⭐⭐⭐⭐ | EURUSD, EURGBP, AUDNZD, NZDCAD | ✅ todos (01_Forex) |
| ⭐⭐⭐⭐ | USDCHF, AUDCAD, CADCHF, EURCHF | ✅ todos (01_Forex) |
| ⭐⭐⭐ (utilizáveis) | USDCAD, AUDUSD, NZDUSD | ✅ todos (01_Forex) |

Cobertura completa — nenhum ativo pra adicionar. É só questão de
**priorizar** esses pares nas campanhas de `07_GRID_SEPARATE` em vez de
rodar o sistema em ativos de tendência forte tipo XAUUSD.

## Arquétipo B — Recuperação por escalonamento de lote, 1 posição por lado
**Sistemas: `09_MARTINGALE`, `10_DALEMBERT`**

Diferente do grid: aqui existe SL+TP real e só 1 posição por lado
(`set_exposure(..., 1, hedging=False)`). O lote da próxima entrada cresce
pra cobrir o déficit acumulado (Martingale, `Multiplicador=1` exato) ou por
um passo fixo (`DAlembertStep`). **O documento não cobre esse arquétipo
diretamente** — isso aqui é inferência minha, não do texto original: o
risco real é uma sequência longa de perdas na MESMA direção sem o sinal
virar (`MaxMartingaleSteps` esgotando), o que é mecanicamente parecido com
o problema do grid clássico (tendência sustentada contra a posição), então
uso a mesma lista de ativos ranging/reversão à média do Arquétipo A como
ponto de partida, com menos confiança que os outros arquétipos abaixo.

## Arquétipo C — Trailing puro, sem TP, deixa o vencedor correr
**Sistemas: `03_TRAIL_ONLY`, `05_BE_TRAIL`**

`AtivarTake=false` fixo nos dois — a ÚNICA saída em lucro é o trail (mais
o breakeven em 05, sempre ligado). Sem alvo fixo, o sistema só ganha de
verdade quando o movimento continua por muito tempo. Quer exatamente o que
o documento chama de trend-following: tendências longas e sustentadas.

| Estrelas do documento | Ativos | No universo? |
|---|---|---|
| ⭐⭐⭐⭐⭐ | XAUUSD, BTCUSD, WTI, BRENT | ✅ todos |
| ⭐⭐⭐⭐⭐ | NAS100/USTECH, US500/SP500 | 🆕 ausentes |
| ⭐⭐⭐⭐ | XAGUSD, ETHUSD | ✅ ambos |
| ⭐⭐⭐⭐ | DE40/DAX, Nikkei225, Natural Gas | 🆕 ausentes |
| ⭐⭐⭐ | USDJPY, EURJPY, GBPJPY | ✅ todos |
| ⭐⭐⭐ | Cobre, Café, Cacau | 🆕 ausentes |
| ⭐⭐ (evitar) | EURUSD, GBPUSD, AUDUSD | ✅ mas evitar aqui — sem TP, um par que fica lateral vira o trail te cortando repetidamente |

## Arquétipo D — Pyramid a favor da tendência, saída por trailing na cesta
**Sistema: `12_GRID_INVERSO`**

O inverso do Arquétipo A: abre níveis A FAVOR do preço (anti-martingale),
cada perna com Stop real, sai pelo trailing de pico/vale da cesta inteira.
Ainda mais exigente que o Arquétipo C — cada novo nível pyramida só se o
preço continuar favorável, então quer a tendência MAIS forte e persistente
possível. Mesma lista do Arquétipo C, mas priorize o topo (⭐⭐⭐⭐⭐) primeiro:
XAUUSD, BTCUSD, WTI/BRENT já cobertos; NAS100/US500 seriam os candidatos
mais valiosos pra adicionar justamente pra este sistema.

## Arquétipo E — TP+SL com breakeven/trailing opcional (eficiência direcional)
**Sistemas: `01_SLTP`, `02_SLTP_ORGANIC`, `04_SLTP_TRAIL`, `06_REVERSAL_EXIT`**

Todos têm um alvo de lucro definido (TP fixo em 01/02/04, ou saída por
sinal oposto em 06) — não precisam de uma tendência que dure meses, só de
um movimento limpo até o alvo antes de reverter. É a categoria que o
documento chama de "eficiência direcional": alterna consolidação e
rompimento, não trend puro.

| Categoria do documento | Ativos | No universo? |
|---|---|---|
| Categoria 1 (melhores EAs em geral) | XAUUSD | ✅ |
| Categoria 1 | NAS100, US500 | 🆕 ausentes |
| Categoria 2 (muito bons) | WTI, BTCUSD, ETHUSD | ✅ todos |
| Categoria 2 | DE40/DAX | 🆕 ausente |
| Categoria 3 (forex que ainda vale) | USDJPY, EURJPY, GBPJPY, AUDJPY | ✅ todos |

## Arquétipo F — Sem proteção nenhuma, só sinal
**Sistema: `11_SIGNAL_ONLY`**

`AtivarStop=false`, `AtivarTake=false`, `AtivarBreakeven=false`,
`AtivarTrailATR=false` — literalmente zero gestão de risco além de fechar
no sinal oposto. **Isso também é inferência minha, o documento não fala
desse arquétipo**: sem nenhuma rede de segurança, este é o sistema mais
sensível a ruído/whipsaw de todos — um sinal falso em ativo lateral não
tem SL pra limitar o dano, só espera o próximo sinal virar. Eu priorizaria
os ativos de maior "eficiência direcional" do documento (XAUUSD, BTCUSD,
tendências limpas) e evitaria especificamente os pares que o próprio
documento já marca como propensos a range (EURUSD, GBPUSD, AUDUSD) — aqui
o custo de um whipsaw é maior que em qualquer outro sistema do EA.

## Resumo executivo

| Arquétipo | Sistemas | Quer | Ativo 🆕 mais valioso a adicionar |
|---|---|---|---|
| A — Grid clássico | 07 | Ranging | nenhum, cobertura completa |
| B — Recuperação por lote | 09, 10 | Ranging (inferência) | nenhum, cobertura completa |
| C — Trailing puro | 03, 05 | Tendência forte | NAS100/US500 |
| D — Pyramid a favor | 12 | Tendência mais forte ainda | NAS100/US500 |
| E — TP+SL direcional | 01, 02, 04, 06 | Eficiência direcional | NAS100/US500, DE40 |
| F — Só sinal | 11 | Tendência limpa, sem ruído (inferência) | NAS100/US500 |

**NAS100/US500 aparecem como o `🆕` de maior impacto em 4 dos 6 arquétipos**
— é o gap de ativo mais valioso do universo atual, seguido por DE40. Café,
Cacau, Cobre e Natural Gas só aparecem em Arquétipo C, valor mais restrito.
Antes de adicionar qualquer um, falta confirmar o símbolo exato que a
RoboForex usa pra cada um.

---

## Outros achados (menos centrais, cruzando o documento contra o código)

**R Fixo vs Porcentagem**: já implementado como o documento recomenda —
pesquisa em R Fixo, entrega em % (`optimize_two_stage.py`, Stage 5), agora
cobrindo também 12_GRID_INVERSO e 09_MARTINGALE. Falta só o re-base
periódico de `CapitalBaseR` pro live, que o documento sugere e não existe
hoje.

**Fórmula de otimização**: o documento recomenda `Formula_SomaR` como
critério primário pra sistemas de trailing (03/04/05/06). Hoje eles
buscam por `Formula_AdjustedEfficiencyForGrid` (`FORMULA_POR_SISTEMA`) —
`SomaR` só aparece como rótulo do candidato final entregue
(`optimize_two_stage.py:1844`), não como o que guia a busca genética.
Divergência real, decisão em aberto.

**Breakeven**: sistemas sem Take (03/05/06/12) já cobrem a faixa de
+1R a +1.5R que o documento recomenda como ideal.

**Hierarquia de saída**: o EA tem Trailing ATR (o melhor da lista do
documento), Breakeven e TP fixo. Chandelier Exit e Donchian Exit — os dois
do meio da hierarquia do documento — não existem como mecanismos
alternativos. Baixa prioridade, já que ATR Trail é o topo da lista mesmo.
