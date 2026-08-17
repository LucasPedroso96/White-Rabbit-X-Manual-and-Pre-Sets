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
menos 180 dias de histórico D1. O catálogo completo do projeto tem 89
símbolos (`generate_system_sets.py`: 28 Forex, 3 metais, 6 cripto, 2
índices/energia, 50 ações americanas — contagem re-verificada em
2026-08-17, era 88/49 quando este documento foi escrito) — quantos desses
realmente estão disponíveis nesta conta só se sabe rodando a detecção.

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
| `HEDGE_ACCOUNT_REQUIRED` | 07_GRID_SEPARATE, 12_GRID_INVERSO | Precisa de conta de hedging pra operar ao vivo — pré-requisito de CONTA, não só resultado de backtest |
| `HIGH_RISK` | 09_MARTINGALE, 10_DALEMBERT | Progressão de recuperação |
| `HIGH_RISK_RESEARCH` | 11_SIGNAL_ONLY | Mais experimental do conjunto |

**Atualizado 2026-08-17**: `08_GRID_UNIFIED` foi removido do sistema inteiro
(achado matematicamente redundante com `07_GRID_SEPARATE` — não só o modo do
enum, o sistema inteiro deixou de existir; `campanha.py` documenta isso no
comentário do `BILATERAL`). `12_GRID_INVERSO` ("Grid Pyramid", anti-martingale
— abre a favor do preço, sai por trailing na cesta) entrou na mesma tier que
o grid clássico. `09_MARTINGALE` e `12_GRID_INVERSO` também passaram a
suportar Fixed-R (mesma lógica do Estágio 5 dos 6 RESEARCH) — "lote fixo"
não é mais universal pra tier HEDGE_ACCOUNT_REQUIRED/HIGH_RISK, só
`07_GRID_SEPARATE`, `10_DALEMBERT` e `11_SIGNAL_ONLY` continuam
estruturalmente presos a ele (sem SL o suficiente ou sem SL nenhum pra medir
risco).

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

**Ver também** `MELHORIAS_MULTIPLE_R_E_ATIVOS.md` (2026-08-17): cobre a
MESMA pergunta por um ângulo diferente e complementar — em vez de ranking
empírico a posteriori (depois de rodar campanha), agrupa os 11 sistemas por
mecânica de risco/saída (6 arquétipos) e sugere, a priori, quais ativos
tendem a favorecer cada arquétipo. Útil como prioridade de fila ANTES de
ter resultado de campanha — o ranking desta seção é o critério depois que
o dado existe.

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

## 8. Deployment: AutoManagerLive

Este documento até aqui descreve como um combo chega a `aprovado == true` e some
dele até "Certified sets" (§7). O que falta é o próximo passo — pegar o que já
está certificado e decidir *o quê* vai pra capital real, *em quantas contas*, e
*como* o resultado ao vivo retroalimenta essa decisão. É esse o papel do
AutoManagerLive.

**Desacoplar de "conta".** A unidade de decisão não é a conta, é o *grupo de
implantação*: um conjunto de combos certificados (símbolo+sistema+variante) que
cabem juntos por risco e por correlação. Conta é só o alvo de execução que
recebe um subconjunto desse grupo. Duas ou mais contas reais rodando fatias
diferentes da mesma biblioteca certificada são *contas-irmãs* — o mesmo
catálogo, sistemas diferentes escolhidos por conta.

**Motor de sugestão.** Reaproveita a seleção gulosa por correlação que já existe
em `portfolio_builder.py` (hoje aplicada a relatórios de backtest), agora sobre
o pool de "Certified sets" do `/api/implantacao` (§7 — só combos com
`relatorio_dir` arquivado entram). Cada rodada do motor produz uma fila
**numerada** de sugestões (Sugestão #1, #2, #3...), ordenada primeiro pela
ordem de graduação por risco da §5 (RESEARCH antes de HEDGE_ACCOUNT_REQUIRED
antes de HIGH_RISK/HIGH_RISK_RESEARCH) e desempatada pelo mesmo critério de
`retencao_oos`/`mc_prob_ruina` da §6. Um número, uma vez atribuído, só muda se
a sugestão for invalidada (um combo dela perde a certificação — ex: relatório
arquivado removido/revalidado).

**Quantas contas são necessárias.** Só dispara conta adicional por restrição
dura, nunca por preferência de diversificação — correlação alta entre sistemas
na mesma conta é risco do dono, não impedimento estrutural:

| Gatilho | Regra |
|---|---|
| Mistura de tier | Sugestão contém combo `HEDGE_ACCOUNT_REQUIRED` (07/08) junto com RESEARCH/HIGH_RISK/HIGH_RISK_RESEARCH → exige conta de hedging separada pros combos 07/08 |
| Capital mínimo | Soma dos mínimos por classe de ativo (`calc_capital_base.py`) dos combos da sugestão excede o saldo informado da conta → particiona por classe até caber |

O resultado de cada sugestão sempre é declarado por extenso: "Sugestão #N cabe
em 1 conta de $X" ou "Sugestão #N precisa de 2 contas: Conta A (hedging, $Y) +
Conta B (normal, $Z)" — nunca assume 1 sugestão = 1 conta.

**Contas-irmãs na prática.** AutoManagerLive fica numa camada acima do
`auto_set_manager.py` existente: decide *o quê* e *pra qual conta*; o
`auto_set_manager` continua fazendo o encaixe físico (símbolo com sufixo do
broker, lote mínimo, risco por saldo) numa conta real específica, um
`PERFIL_MODELO` por conta. N contas reais podem existir, cada uma com seu
próprio perfil derivado de uma fatia diferente da mesma sugestão ou de
sugestões diferentes — o motor nunca assume uma cardinalidade fixa de contas.

**Medição ao vivo e critério de promoção/rebaixamento.** O baseline de
comparação é sempre o `retencao_oos`/`expectancy_r` já gravado no ledger
*daquele combo específico* (nunca uma média de tier — o mesmo motivo do
desempate por combo individual da §6: agregar mascara o que importa). Todo
combo recém-implantado entra em status `EM_PROVA`, com alocação reduzida em
relação ao que o `auto_set_manager` calcularia em regime normal, até acumular
um número mínimo de trades ao vivo — o valor exato do mínimo e da alocação
reduzida fica em aberto pra quando houver semanas de dado ao vivo de verdade,
mesmo espírito do "script a construir depois" da §6: não faz sentido cravar um
número sem nenhum trade real pra calibrar contra. Passada a prova, a
comparação é contínua: `expectancy_r` ao vivo (janela móvel) vs. `expectancy_r`
OOS do ledger, dentro de uma faixa de tolerância. Dentro da faixa mantém a
alocação atual; abaixo da faixa por N trades/dias seguidos rebaixa (reduz
alocação ou tira do live — o combo continua elegível pra reentrar numa
sugestão futura, nunca é descartado permanentemente); acima da faixa promove
(aumenta alocação até o teto que o capital/risco da conta permite). Igual à
distinção que `campanha.py:feitos()` já faz entre `"erro"` (falha de
infraestrutura) e reprovação real (entrada de 2026-08-08 no diário abaixo):
uma sequência ruim causada por fechamento do terminal, erro de conexão ou
outro evento de infraestrutura não conta como amostra pro rebaixamento.

**Fluxo de uso.** Estende o painel "Certified sets" (`/api/implantacao`) já
existente em vez de criar um painel novo. Cada sugestão numerada aparece como
um bloco expansível com os combos que a compõem e a(s) conta(s) que ela exige.
Três ações, reaproveitando o `/api/implantacao/marcar` que já existe (toggle
por chave): marcar a sugestão inteira como implantada de uma vez (uma chamada
com todas as chaves da sugestão); marcar tudo que já está ao vivo hoje, pra
sincronizar o painel com a realidade sem reclicar combo por combo; "próxima
sugestão", que só avança o cursor sem marcar nada. Toda marcação recalcula a
fila — o que já foi implantado sai do pool de candidatos a nova combinação.

**Fora de escopo por enquanto.** Execução automática de ordens ao vivo
continua fora — o export do painel já é manual (cópia pro VPS/conta), e isso
não muda. Os números exatos de tolerância, janela de prova e alocação
reduzida também ficam pra depois: exigem trades ao vivo reais pra calibrar,
não dado de backtest.

## 9. Diário de decisões

Preenchido conforme decisões reais forem tomadas.

| Data | Decisão | Motivo |
|---|---|---|
| 2026-08-07 | Ledger da janela curta (285 dias) movido pra backup antes de religar a campanha de 3 anos | `feitos()` chaveia só por símbolo+sistema+variante, sem checar janela de data — sem isso os 4 combos de teste ficariam permanentemente marcados como "já feitos" |
| 2026-08-07 | Campanha completa disparada em Modo Manual (não Automático), todos os sistemas marcados 01→11 | Bate com o pedido de organizar por ordem de risco; Modo Automático usa ordem grid-primeiro (prioridade de produto, não de risco) |
| 2026-08-07/08 | Combo canário (EURUSD/01_SLTP) rodado antes da campanha completa: 92,0 min de ponta a ponta, reprovado por divergência OHLC vs tick real (63,7%) -- gate funcionando corretamente, retenção OOS tinha sido ótima (164,5%) | Confirma os 2 bugs corrigidos hoje sobrevivem à janela real de 3 anos, não só à janela curta de validação; dá a primeira referência real de tempo por combo completo |
| 2026-08-08 | 85 símbolos auto-detectados (`/api/ativos/detectar`), campanha completa disparada com todos eles + os 11 sistemas em ordem de risco -- **3.570 combos na fila** | Cobertura real, sem curadoria manual, conforme seção 4. Escala real: a ~90min/combo (1 amostra), é uma campanha de MESES de execução contínua, não dias -- expectativa registrada aqui pra não surpreender depois |
| 2026-08-08 | Campanha de 3.570 combos interrompida no meio (dono pediu, pra priorizar). Disparado foco só em `08_GRID_UNIFIED` em 10 ativos curados: os 7 majors de forex (EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD) + EURGBP/EURCHF (cruzamentos historicamente estáveis, clássicos em grid) + XAUUSD (ouro, ativo mais usado em grid comercial apesar da volatilidade maior) -- 20 combos na fila, ordenados por prioridade (XAUUSD e majors primeiro) | Dono quer ter um grid pronto pra considerar subir amanhã (2026-08-09). Cripto/energia/as 49 ações ficaram fora desta primeira leva -- tendência forte/gap não combina com grid. **Expectativa real**: nenhuma medição de grid na janela de 3 anos ainda existe pós-fix; a única referência de Estágio 1 de grid nesta sessão (antes de qualquer fix, janela de 3 anos) levou 2h24min só nas 3 rodadas genéticas -- plausível que cada combo de grid leve 3-5h de ponta a ponta agora. Com isso, é realista esperar só uns 3-5 combos (1-3 símbolos) prontos até amanhã, não os 20 -- os demais continuam depois. |
| 2026-08-08 | Auditoria de justiça de metodologia: achado que 09_MARTINGALE/10_DALEMBERT/11_SIGNAL_ONLY (justo os tiers HIGH_RISK/HIGH_RISK_RESEARCH) não tinham NENHUMA das 3 checagens extras de robustez (MC e prova em % são estruturalmente impossíveis pra eles, e o gate de sobrevivência de período completo só cobria grid). Gate de sobrevivência estendido pra cobrir os 3 também (`SISTEMAS_GATE_SOBREVIVENCIA`, desacoplado de `SISTEMAS_GEOMETRIA_TICK_REAL` que continua só-grid) | Os sistemas com risco mais alto rotulado eram os com menos escrutínio real -- inconsistente com o próprio motivo que criou o gate (achado real de grid passando limpo em janela curta e estourando no período completo; o mesmo buraco existe em qualquer sistema sem SL nativo, não só grid). Não afeta a campanha de grid já rodando (só testa 08_GRID_UNIFIED); passa a valer quando a campanha completa chegar em 09/10/11. |
| 2026-08-08 | `input_end_date` da biblioteca (3.738 templates) estava cravado em "2026.07.21", 18 dias defasado -- `generate_system_sets.py`/`configure_wfo.py` agora calculam a data na hora (`datetime.now()`), nunca mais um literal. Biblioteca inteira já atualizada. | Mesma classe de bug do "From" do dashboard (corrigido em 2026-08-06) -- provável explicação da percepção antiga de "WFO parece parar em 2024/2025". Confirmado que NÃO afetou os combos reais da campanha (`janelas_wfo()` sempre sobrescreve com a data certa por conta própria, independente do template) -- nenhum resultado já registrado precisou ser refeito por causa disso. |
| 2026-08-08 | `descobrir_ativos.py` invertido: prioriza símbolo NATIVO da corretora, `.HT` (Historical Tool Manager) vira só fallback | Dono mediu divergência real entre os dados nativo vs `.HT`, nativo saiu melhor -- e um set validado em `.HT` não carrega em conta sem o Historical Tool Manager instalado (a maioria dos clientes). Campanha de grid reiniciada do zero com símbolos nativos (XAUUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD, EURGBP, EURCHF) -- os 4 combos já registrados em `.HT` foram pro backup e revalidados. |
| 2026-08-08 | Instalador do cliente (`White Rabbit X - Instalador.exe`) reconstruído do zero após relato de estrutura incorreta numa instalação real | `.exe` não é versionado no git (distribuição manual) -- rebuild elimina qualquer chance de estar desatualizado. Sets distribuídos já eram genéricos (símbolo nativo, não `.HT`), então a mudança de prioridade acima não muda o que o cliente recebe, só a campanha de pesquisa do dono. |
| 2026-08-08 | Campanha de grid (`08_GRID_UNIFIED`) cancelada e relançada em Modo Manual sem XAUUSD -- mantidos só os 9 majors/cruzamentos forex (EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD, EURGBP, EURCHF). Os 2 combos de XAUUSD já processados (BOTH_MULTI, BOTH_ICHIMOKU) tinham sido reprovados por retenção OOS, então nada de válido foi perdido no cancelamento; EURUSD/BOTH_MULTI retomou do checkpoint do Estágio 1 já acumulado | Dono pediu pra adaptar os ativos da campanha às regras do próprio sistema. Sistemas 07-11 (grid incluso) entregam em lote fixo (`PositionSizeMode=2`, `generate_system_sets.py:598`), que não escala com o saldo ao vivo -- ao contrário dos sistemas 01-06, que trocam pra `Percentage` no Estágio 5. `calc_capital_base.py` estima o capital mínimo por classe pro lote mínimo da corretora respeitar 1% de risco (Forex ~$500, Metais ~$10.000, 3xATR de stop): XAUUSD era o único ativo do lote de ontem na classe Metais, a mais cara e a que mais destoa de uma conta de ~$100-114; os 9 forex que restaram são a classe mais barata, a mais perto de eventualmente caber nesta conta |
| 2026-08-08 | Cliente real (`osmar`) baixou o ZIP do GitHub e rodou `wrx_setup.py`/`Instalar_White_Rabbit_X.py` (renomeado nesta mesma entrada) direto, fora do `.exe` -- instalador agora funciona de verdade nesse cenário: cai pra `Sets/` da raiz quando falta a cópia local do build, e roda `pip install -r requirements.txt` sozinho pro Autobot em vez de só mandar comprar o `.exe`. Todo texto voltado pro cliente (esse arquivo, `Iniciar_Dashboard.bat`, READMEs de instalação) traduzido pra inglês -- português ficou só nos scripts internos do Autobot | Repetição do mesmo erro (rodar a fonte crua) em dois clientes seguidos prova que só melhorar a mensagem de erro não bastava -- tinha que funcionar mesmo, não só explicar por que não funcionava |
| 2026-08-08 | `atualizar_conta_real.py` tinha o caminho do terminal do dono cravado no código (só essa máquina) -- corrigido pra `wrx_paths.terminal_exe()`, e `optimize_sets.leverage_conta()` agora chama a consulta sozinha na primeira vez que falta o cache, em vez de só avisar "rode isso na mão" | Todo combo de sistema que precisa de alavancagem real (grid) reprovava instantaneamente em qualquer PC que não fosse o do dono -- achado a partir do log de campanha do próprio `osmar` |
| 2026-08-08 | `campanha.py:feitos()` passou a ignorar entradas do ledger com `"erro"` (combo que nunca produziu JSON final -- crash de infraestrutura, não reprovação de verdade) | Combos que travaram pelo bug do cache de conta real acima ficaram marcados "feitos" pra sempre, mesmo depois do bug corrigido -- a campanha nunca tentava de novo. Não dá pra usar `retencao_oos=None` como sinal (reprovação legítima do Estágio 1/2/4 também grava isso) -- só `"erro"` distingue infraestrutura de reprovação real |
| 2026-08-08 | Biblioteca `Sets/` (3.738 arquivos) regenerada e republicada -- estava parada em 2026-08-02, 3 dias sem o fix de `AtivarBreakeven` do grid (commit `49828f95`, 2026-08-05) e sem qualquer outra mudança do gerador desde então | Achado ao conferir por que um comprador via grid sem breakeven mesmo com o código já corrigido: o código tinha o fix, a biblioteca publicada nunca foi regenerada pra pegá-lo. Sets já `VALIDADO_*` (aprovados por uma campanha real) continuam intocados de propósito -- são resultado de teste, não template, e só se corrigem re-testando o combo |
| 2026-08-09 | Seção "Deployment: AutoManagerLive" adicionada (§8): motor de sugestão de combinações certificadas (reaproveita `portfolio_builder.py` sobre o pool de "Certified sets"), regra de quantas contas são necessárias (só restrição dura: mistura de tier HEDGE_ACCOUNT_REQUIRED ou capital mínimo por classe excedido), suporte a contas-irmãs (mesma biblioteca, sistemas diferentes por conta), e critério de promoção/rebaixamento ao vivo (faixa de tolerância + período de prova, baseline por combo específico vs. tier) | Dono pediu desacoplar a implantação da ideia de 1 conta só, com sugestão numerada e fluxo de marcar (individual, tudo que já é live, ou pular pra próxima sugestão). Metodologia documentada primeiro, sem script ainda, mesmo padrão da §6 -- os números exatos de tolerância e janela de prova esperam trade ao vivo real pra calibrar, não existe esse dado ainda |
| 2026-08-09 | Modo pause adicionado à campanha: sinal em disco (`campanha_pausa.json`, só a presença importa, `optimize_sets.pausa_solicitada()`) checado em pontos SEGUROS -- fim de cada rodada do Estágio 1 (checkpoint já salvo, retomar continua exatamente dali) e entre combos (nada em andamento a perder). Nunca interrompe no meio de uma rodada/combo. Dashboard ganhou botões Pausar/Retomar (`/api/campanha/pausar`, `/api/campanha/retomar`) -- Retomar relança `campanha.py` com os mesmos parâmetros da corrida pausada, gravados no lock file na hora do Iniciar (antes só guardava pid/modo) | Dono pediu um jeito de pausar "entre um evento e outro" sem perder trabalho, distinto de Stop (que cancela e mói o ledger incompleto). Estágios 2-5 ainda não têm checkpoint próprio, então uma pausa pedida no meio deles só produz efeito no fim do combo inteiro -- documentado como limitação conhecida, não bug |
