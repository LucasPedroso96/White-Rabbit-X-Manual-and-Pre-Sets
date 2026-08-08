# Plano de treinamento: $100 → $1.000.000

## 1. Contexto e objetivo

Em 2026-08-07, dois bugs que vinham corrompendo a campanha de validação
foram achados e corrigidos, ambos commitados e publicados nos dois
repositórios (público `White-Rabbit-X-Manual-and-Pre-Sets`, privado
`Metatrader5EAS`):

- **Delay de ~90-100s por chamada de passe único**: o MT5 se auto-atualizou
  no meio da própria sessão de trabalho (`terminal64.exe` trocou de build
  às 15:13:59) e mudou a grafia da linha que sinaliza "teste terminado" —
  o código procurava uma grafia fixa e parou de encontrar. Corrigido pra
  aceitar as duas grafias via regex, validado ao vivo: ~100s → 7,8s por
  chamada.
- **Reprovações precoces perdiam o motivo no ledger**: quando os Estágios
  1, 2 ou 4 do circuito não achavam nenhum candidato válido, o código
  imprimia a mensagem certa mas nunca montava o JSON final que o
  `campanha.py` lê — a reprovação virava um `"erro": "sem JSON final"`
  genérico, indistinguível de uma queda de verdade. Corrigido: os 5 pontos
  de saída antecipada legítima agora emitem o JSON completo com o motivo
  real.

Com os dois bugs confirmados corrigidos numa campanha de validação rápida
(janela de ~285 dias, 4 combos rodados), este documento organiza o
próximo passo: rodar a campanha de verdade — todos os ativos reais desta
conta, os 11 sistemas, janela de 3 anos — como um programa de treinamento
rumo a **crescer de $100 até $1.000.000**.

**"$100 → $1.000.000" é a jornada que queremos contar, o crescimento
composto que buscamos provar que é possível — não uma curva de retorno
prometida.** Nenhum dado ainda sustenta uma projeção específica. Este
documento organiza a metodologia, não o resultado.

## 2. A conta real (~$114) nunca bloqueou pesquisa

O próprio código já documenta isso (`descobrir_ativos.py`, comentário do
dono): a conta real tem ~$114, abaixo até do `capital_base` da classe mais
barata (Forex, $500). Um filtro por saldo teria zerado a própria campanha
de pesquisa. Por isso `capital_base` ali é só **prioridade de ordem** na
fila de varredura de ativos, nunca portão de exclusão — pesquisa e
backtest são agnósticos a saldo por desenho.

## 3. O nuance $100 vs $500

`CapitalBaseR` (a constante de $500 pro Forex, definida em
`generate_system_sets.py`, escrita nos sets de trabalho via
`p.fix("CapitalBaseR", ...)`) serve só pra **normalizar risco durante a
pesquisa** — Estágios 1 a 4, medição em Fixed-R, pra poder comparar
sistemas e ativos diferentes numa régua comum (1R = mesmo % de risco em
qualquer ativo/capital de partida).

O set **ENTREGUE** (o que sai pronto pra rodar ao vivo) passa pelo
Estágio 5, que troca `PositionSizeMode` pra `Percentage`
(`optimize_two_stage.py:1609-1687`) — ou seja, **o risco ao vivo já escala
com o saldo real da conta no momento do trade, não com os $500 da
pesquisa.**

**Conclusão: $100 ao vivo provavelmente já é viável hoje, sem mudar código
nenhum — mas isso precisa ser confirmado empiricamente, não presumido.**
O risco residual real não é o `CapitalBaseR`: é o **lote mínimo da
corretora**. Sizing em percentual é invariante em teoria, mas numa conta
muito pequena o lote mínimo pode arredondar o risco de um trade pra cima
do percentual pretendido, especialmente em instrumentos de margem maior
(metais, cripto, CFDs de ações).

**Verificação proposta** (depois que a campanha de 3 anos produzir os
primeiros sets VALIDADOs): pegar 2-3 sets aprovados, rodar de novo com
`--deposit 100` (passe único, não precisa repetir o circuito inteiro) e
conferir se retenção/expectativa se sustentam e se o lote mínimo não
distorce o risco. Não fazer isso na campanha principal — mudar o depósito
ali quebraria a comparabilidade Fixed-R de toda a pesquisa.

## 4. Descoberta e priorização de ativos

`descobrir_ativos.py` detecta o que este terminal/conta consegue
realmente testar, tentando primeiro o símbolo `.HT` (tick real via
Historical Tool Manager) e caindo pro nativo se não existir; exige pelo
menos 180 dias de histórico D1. O catálogo completo do projeto tem 88
símbolos (`generate_system_sets.py`: 28 Forex, 3 metais, 6 cripto, 2
índices/energia, 49 ações americanas) — quantos desses realmente estão
disponíveis nesta conta só se sabe rodando a detecção.

Duas formas de usar:
- **Rodar sem flag** (`python descobrir_ativos.py`): só lista o que foi
  detectado, sem gravar nada — bom pra visibilidade antes de decidir.
- **`--gravar`**: fixa a lista detectada em `campanha_ativos.json`, que
  passa a ser usada em toda campanha futura em vez de detectar de novo a
  cada vez.

Pra este treinamento: usar a lista completa auto-detectada (não curar um
subconjunto manualmente) — o objetivo é cobertura real, e o Modo Manual do
dashboard já tem o botão "Detectar agora" que faz exatamente isso.

## 5. Ordem de execução por risco

Os 11 sistemas já têm 4 tiers de risco definidos no código
(`generate_system_sets.py`, campo `status` de cada `System`):

| Tier | Sistemas | Risco |
|---|---|---|
| `RESEARCH` | 01_SLTP, 02_SLTP_ORGANIC, 03_TRAIL_ONLY, 04_SLTP_TRAIL, 05_BE_TRAIL, 06_REVERSAL_EXIT | Fixed-R, validado por Monte Carlo (≤5% prob. de ruína) |
| `HEDGE_ACCOUNT_REQUIRED` | 07_GRID_SEPARATE, 08_GRID_UNIFIED | Precisa de conta de hedging pra operar ao vivo — pré-requisito de CONTA, não só resultado de backtest |
| `HIGH_RISK` | 09_MARTINGALE, 10_DALEMBERT | Lote fixo, progressão de recuperação |
| `HIGH_RISK_RESEARCH` | 11_SIGNAL_ONLY | Mais experimental do conjunto |

**Duas ordens diferentes, não confundir:**

- **Ordem de MEDIÇÃO** — em que sequência o `campanha.py` roda os combos.
  O Modo Manual do dashboard, marcando todos os sistemas na ordem
  01→11, já produz exatamente RESEARCH → HEDGE_ACCOUNT_REQUIRED →
  HIGH_RISK → HIGH_RISK_RESEARCH — o Modo Automático usa uma ordem
  diferente (grid primeiro, decisão antiga de prioridade de produto, não
  de risco). Pra este treinamento, **Modo Manual com todos marcados** é o
  que bate com "organizar de acordo com os riscos e sistemas".
- **Ordem de GRADUAÇÃO pra capital ao vivo** — em que ordem um sistema
  aprovado passa a operar com dinheiro de verdade, independente da ordem
  de medição: RESEARCH primeiro (menor risco estrutural, já validado por
  Monte Carlo), depois HEDGE_ACCOUNT_REQUIRED (só depois de confirmar que
  a conta ao vivo é mesmo de hedging), depois HIGH_RISK e
  HIGH_RISK_RESEARCH por último, com alocação menor — o próprio rótulo já
  avisa.

## 6. Metodologia de ranking "melhores ativos"

**O que já existe**: o painel "Certified sets" do dashboard
(`/api/implantacao`) já ranqueia por COMBO (símbolo+sistema+variante),
usando saldo final de sobrevivência como critério principal e lucro OOS
como desempate. Reaproveitar como está pra "qual set específico está
pronto pra um símbolo".

**O que falta**: nada agrega por ATIVO através de múltiplos sistemas —
não existe hoje uma resposta pronta pra "EURUSD é bom no geral?".

**Metodologia proposta** (documentada aqui, script a construir depois que
houver dado real de verdade — semanas de campanha rodada, não faz sentido
implementar em cima de 4 combos de teste):

1. Filtrar `campanha_resultados.jsonl` por `aprovado == true`.
2. Agrupar por `simbolo`.
3. Ranquear primeiro por **quantos sistemas distintos** aprovaram aquele
   símbolo (sinal de robustez através de estratégias diferentes).
4. Desempate por `retencao_oos` (maior retenção fora da amostra).
5. Segundo desempate por `mc_prob_ruina` mais conservador (menor
   probabilidade de ruína) entre as linhas RESEARCH daquele símbolo.

**Atualizado 2026-08-08**: o gate de sobrevivência de período completo
agora cobre grid (07, 08) **e também** martingale, d'alembert e
signal-only (09, 10, 11) via `SISTEMAS_GATE_SOBREVIVENCIA` — os únicos
sem essa checagem (por não serem Fixed-R, estruturalmente impossível)
são os 6 RESEARCH, que em compensação já têm Monte Carlo e a prova em %
do Estágio 5. Um script de ranking só precisa tratar
`sobrevivencia_medida == false` como normal pros 6 RESEARCH, não mais
como uma lacuna nos 3 sistemas de alto risco.

Depois do ranking por ativo individual, o passo seguinte natural é
`portfolio_builder.py` (correlação/diversificação entre os aprovados) —
"melhor ativo isolado" e "melhor portfólio" são perguntas diferentes, não
confundir uma com a outra.

## 7. Critério de graduação pra capital ao vivo

Um combo só passa a ser candidato a capital real quando, TODOS ao mesmo
tempo:

1. Foi aprovado (`aprovado == true`) na campanha de **3 anos de verdade**
   (não na janela curta de validação de hoje).
2. Respeita a ordem de graduação por risco da seção 5.
3. Passou a verificação empírica de $100 da seção 3.
4. Aparece no painel "Certified sets" do dashboard (só sets com relatório
   de validação arquivado contam — gate que já existe, não precisa
   inventar outro).

## 8. Diário de decisões

Preenchido conforme decisões reais forem tomadas.

| Data | Decisão | Motivo |
|---|---|---|
| 2026-08-07 | Ledger da janela curta (285 dias) movido pra backup antes de religar a campanha de 3 anos | `feitos()` chaveia só por símbolo+sistema+variante, sem checar janela de data — sem isso os 4 combos de teste ficariam permanentemente marcados como "já feitos" |
| 2026-08-07 | Campanha completa disparada em Modo Manual (não Automático), todos os sistemas marcados 01→11 | Bate com o pedido de organizar por ordem de risco; Modo Automático usa ordem grid-primeiro (prioridade de produto, não de risco) |
| 2026-08-07/08 | Combo canário (EURUSD/01_SLTP) rodado antes da campanha completa: 92,0 min de ponta a ponta, reprovado por divergência OHLC vs tick real (63,7%) -- gate funcionando corretamente, retenção OOS tinha sido ótima (164,5%) | Confirma os 2 bugs corrigidos hoje sobrevivem à janela real de 3 anos, não só à janela curta de validação; dá a primeira referência real de tempo por combo completo |
| 2026-08-08 | 85 símbolos auto-detectados (`/api/ativos/detectar`), campanha completa disparada com todos eles + os 11 sistemas em ordem de risco -- **3.570 combos na fila** | Cobertura real, sem curadoria manual, conforme seção 4. Escala real: a ~90min/combo (1 amostra), é uma campanha de MESES de execução contínua, não dias -- expectativa registrada aqui pra não surpreender depois |
| 2026-08-08 | Campanha de 3.570 combos interrompida no meio (dono pediu, pra priorizar). Disparado foco só em `08_GRID_UNIFIED` em 10 ativos curados: os 7 majors de forex (EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD) + EURGBP/EURCHF (cruzamentos historicamente estáveis, clássicos em grid) + XAUUSD (ouro, ativo mais usado em grid comercial apesar da volatilidade maior) -- 20 combos na fila, ordenados por prioridade (XAUUSD e majors primeiro) | Dono quer ter um grid pronto pra considerar subir amanhã (2026-08-09). Cripto/energia/as 49 ações ficaram fora desta primeira leva -- tendência forte/gap não combina com grid. **Expectativa real**: nenhuma medição de grid na janela de 3 anos ainda existe pós-fix; a única referência de Estágio 1 de grid nesta sessão (antes de qualquer fix, janela de 3 anos) levou 2h24min só nas 3 rodadas genéticas -- plausível que cada combo de grid leve 3-5h de ponta a ponta agora. Com isso, é realista esperar só uns 3-5 combos (1-3 símbolos) prontos até amanhã, não os 20 -- os demais continuam depois. |
| 2026-08-08 | Auditoria de justiça de metodologia: achado que 09_MARTINGALE/10_DALEMBERT/11_SIGNAL_ONLY (justo os tiers HIGH_RISK/HIGH_RISK_RESEARCH) não tinham NENHUMA das 3 checagens extras de robustez (MC e prova em % são estruturalmente impossíveis pra eles, e o gate de sobrevivência de período completo só cobria grid). Gate de sobrevivência estendido pra cobrir os 3 também (`SISTEMAS_GATE_SOBREVIVENCIA`, desacoplado de `SISTEMAS_GEOMETRIA_TICK_REAL` que continua só-grid) | Os sistemas com risco mais alto rotulado eram os com menos escrutínio real -- inconsistente com o próprio motivo que criou o gate (achado real de grid passando limpo em janela curta e estourando no período completo; o mesmo buraco existe em qualquer sistema sem SL nativo, não só grid). Não afeta a campanha de grid já rodando (só testa 08_GRID_UNIFIED); passa a valer quando a campanha completa chegar em 09/10/11. |
