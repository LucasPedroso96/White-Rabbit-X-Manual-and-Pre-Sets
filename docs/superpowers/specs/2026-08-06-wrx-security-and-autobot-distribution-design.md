# WRX — Remediação de senha, sincronização pública do Autobot e instalador completo para o cliente

Data: 2026-08-06. Pedido do dono (verbatim, condensado): "cuide da senha! e sim faça o
setup completo! com autobot e ele tem que estar visivel no repositorio publico."

## Contexto

Uma auditoria de integridade da instalação White Rabbit X (terminal
`RoboForex MT5 Terminal (WhiteRabbitEA)`, EA e sets) encontrou três problemas
distintos, sem relação técnica entre si mas pedidos juntos pelo dono:

1. Uma senha real de conta MT5 (RoboForex-ECN) ficou commitada em texto plano
   em 8+ arquivos do repo `Levain-2.0-` antes do commit `d22a26a7`
   (02/08/2026), que removeu o valor dos arquivos atuais mas não do
   histórico. Esse commit já está em `origin/feat/training-process-pool`,
   ou seja, o valor já foi enviado ao GitHub (repo privado, mas exposto).
2. O `Autobot/` publicado no repo público
   (`LucasPedroso96/White-Rabbit-X-Manual-and-Pre-Sets`) está 3 commits
   atrás da versão real de trabalho, que só existe em
   `Levain-2.0/white_rabbit_x_optimization_tools/` (nunca publicada).
3. O instalador que vai para o comprador (`AutoBotSetup/wrx_setup.py` →
   `White Rabbit X - Instalador.exe`, distribuído em RAR no Telegram) copia
   apenas a biblioteca `Sets/` (3.738 arquivos). O Autobot — dashboard de
   campanha + circuito de otimização de 5 estágios — nunca foi parte do
   pacote do cliente; é descrito no seu próprio README como "research
   tooling, not a turnkey signal generator". Chegou a ser interpretado como
   bug ("a pasta autobot parece não ter vindo"), mas era o comportamento
   desenhado até agora. O pedido aqui é mudar esse desenho: o comprador
   passa a receber o Autobot completo.

## Decisões

### A — Remediação da senha exposta

A correção de segurança real é **trocar a senha na conta RoboForex-ECN** —
uma vez enviado ao GitHub, mesmo repo privado, reescrever histórico não
desfaz a exposição já ocorrida, só evita que o valor continue visível
indefinidamente para quem tiver acesso ao repo. Rotação é ação do dono fora
deste repositório (não executável por mim).

Trabalho no repositório:

1. Instalar `git-filter-repo` (`pip install git-filter-repo`).
2. Localizar o valor exato da senha nos commits anteriores a `d22a26a7` e
   remover com `--replace-text` (substituição por um placeholder) em todo o
   histórico, nos branches `main` e `feat/training-process-pool`.
3. Force-push dos dois branches reescritos para `origin`.
4. `git reflog expire --expire=now --all` + `git gc --prune=now` no clone
   local para purgar o blob antigo do próprio `.git`.

Não há outro clone local do `Levain-2.0-` nesta máquina (verificado:
`Levain-2.0-backup`, `Levain 1.2.../trading_system` e
`Live (Levain)/Levain-2.0` não são repositórios git), então não há outro
checkout para reconciliar após o force-push.

Fora de escopo: rotação de outras credenciais não mencionadas pelo dono;
scrub de segredos em repositórios que não sejam o `Levain-2.0-`.

### B — Autobot sincronizado no repositório público, sanitizado

1. Copiar `white_rabbit_x_optimization_tools/` →
   `Autobot/` no clone local de `White-Rabbit-X-Manual-and-Pre-Sets`
   (`Levain-2.0/temp/White-Rabbit-X-Manual-and-Pre-Sets`), excluindo os
   mesmos padrões já usados no `.gitignore` do Levain-2.0 para esta pasta:
   `_conta_real.json`, `_custo_nativo.json`,
   `campanha_dashboard.lock.json`, `campanha_resultados.jsonl`,
   `perfil_dashboard.json`, `sets_implantados.json`,
   `campanha_relatorios/`, `portfolio_outputs/`, `campanha_checkpoints/`,
   `__pycache__/`, `*.log`.
2. As edições locais não commitadas já existentes nesse clone (arquivos do
   dashboard de uma sessão anterior — `app.js`, `index.html`,
   `styles.css`, etc.) vão para `git stash` antes da cópia — não são
   descartadas.
3. Commit no clone local com mensagem descrevendo a sincronização.
4. **Checkpoint de confirmação antes do `git push`.** Publicar em
   repositório público é ação visível a terceiros e será confirmada
   explicitamente no momento de executar, mesmo com este plano aprovado.

Fora de escopo: mudar o histórico do repositório público; publicar
`Sets/`, `Manuals/` (já sincronizados, ver auditoria de integridade
anterior nesta conversa).

### C — Instalador do cliente com Autobot completo

**Abordagem escolhida: Python embeddable oficial + scripts do Autobot sem
modificação**, em vez de recompilar cada script com PyInstaller. Motivo:
`dashboard_campanha.py` orquestra o circuito via
`subprocess.Popen([sys.executable, "script.py", ...])` — dentro de um
`.exe` congelado `sys.executable` deixa de ser um interpretador Python
genérico, então preservar esse mecanismo sem reescrevê-lo exige um Python
de verdade ao lado, não um bundle onefile.

**Cadeia de dependência real** (rastreada a partir de
`dashboard_campanha.py`, subprocess + import direto):

```
dashboard_campanha.py
 ├─ campanha.py ─────────┬─ descobrir_ativos.py ── generate_system_sets.py, optimize_sets.py
 │                        └─ optimize_two_stage.py ── custo_nativo.py, monte_carlo_wrx.py,
 │                                                     optimize_sets.py, mt5_runner.py
 ├─ generate_system_sets.py
 ├─ portfolio_builder.py (+ portfolio_html.py)
 ├─ auto_set_manager.py
 ├─ custo_nativo.py
 └─ ready_library.py (import direto)
```

**Critério de inclusão no bundle do cliente:** todo arquivo `.py` de
`white_rabbit_x_optimization_tools/`, exceto as ferramentas de bastidor sem
botão correspondente no dashboard: `align_manuals.py`, `audit_manuals.py`,
`enrich_manuals.py`, `render_manuals.py`, `sync_input_reference.py`,
`sync_set_count.py`, `update_indicator_lists.py`, `write_library_docs.py`,
`build_br_version.py`, `gerar_descricao_market.py`,
`gerar_imagens_market.py`, `glossario_br.json`, `test_*.py`. Essas
permanecem só na cópia de trabalho interna.

**Passos de empacotamento:**

1. Baixar o Python embeddable oficial (`python-3.13.x-embed-amd64.zip`,
   ~20MB) e habilitar `site-packages` nele (editar o arquivo `._pth`, que
   vem com import de site desligado por padrão no embeddable).
2. Em tempo de build (nesta máquina, não na do cliente), instalar dentro
   desse Python embarcado: `fastapi`, `uvicorn`, `MetaTrader5`, `numpy`,
   `pandas` — via `pip install --target`.
3. Estender `AutoBotSetup/wrx_setup.py`: além de copiar `Sets/` (já faz
   isso), também extrair o Python embarcado + os scripts do Autobot +
   `dashboard_static/` para
   `%USERPROFILE%\Documents\White Rabbit X\Autobot\`, e criar o atalho
   "White Rabbit X - Autobot" na área de trabalho apontando para um
   launcher (mesmo padrão do `Start_Dashboard.bat` já usado internamente,
   adaptado para o Python embarcado em vez de depender do PATH do
   sistema).
4. Recompilar `White Rabbit X - Instalador.exe` via PyInstaller
   (`--add-data` agora inclui `Sets`, o Python embarcado e os scripts do
   Autobot).

**Tamanho esperado:** ~150–220MB (o instalador atual, só com `Sets/`, já
é 88MB; `numpy`+`pandas` sozinhos somam ~98MB). Ainda cabe numa RAR do
Telegram sem mudança no canal de distribuição.

**Teste:** validar localmente rodando o Python embarcado diretamente (sem
depender do PATH do sistema, simulando "zero Python instalado na
máquina") — subir o dashboard, checar os endpoints de leitura, confirmar
que os botões de campanha disparam os subprocessos corretos com o
interpretador embarcado. **Fora do alcance desta sessão:** validar o
instalador rodando numa máquina de cliente real — fica como verificação
do dono (ou de um cliente de confiança) antes de redistribuir em massa.

## Ordem de execução

1. **A (senha)** primeiro e independente do resto — quanto antes reescrito,
   menor a janela de exposição adicional. Rotação da senha em si é ação do
   dono, fora deste repositório.
2. **B (sync público)** pode rodar em qualquer momento depois de A (não
   depende de C).
3. **C (instalador)** é o maior esforço de engenharia; roda por último,
   com seu próprio plano de implementação detalhado.

## Atualização 2026-08-06 — mudança de repositório

Depois deste desenho aprovado, o dono pediu que o WRX deixasse de viver
dentro do Levain-2.0 (sistema não relacionado). Executado antes do resto
deste plano:

- `Autobot/` (ex-`white_rabbit_x_optimization_tools/`), `AutoBotSetup/`,
  esta spec, a spec de 2026-07-31, os 4 docs de specs/plans do WRX, os
  `.bat` de compilação e o script de tradução de docs — todos migrados
  para este repositório (`Documents\White Rabbit X`, clone do
  `White-Rabbit-X-Manual-and-Pre-Sets` público), com histórico
  preservado via `git filter-repo` + `git merge --allow-unrelated-histories`
  onde havia histórico a preservar.
- Estado de runtime real (checkpoints, resultados de campanha, cache de
  conta) e o `.exe` do instalador em produção foram preservados em
  `Autobot/_runtime_migrado_do_levain/` e `AutoBotSetup/`, não descartados.
- `.codex-staging/white-rabbit` (repo aninhado com remote próprio em
  `github.com/LucasPedroso96/White-Rabbit.git`, conteúdo redundante com
  `Autobot/ea_source/`) foi removido do Levain-2.0 sem migrar — já vive no
  próprio remote dele.
- Docs genéricos do Levain (`SISTEMA_*`, `ANALISE_*`) que apenas
  mencionam White Rabbit de passagem (1-10 menções em arquivos de
  270-700+ linhas) **não** foram movidos — são sobre a arquitetura do
  próprio Levain.
- Levain-2.0 não tem mais nenhum arquivo com "white rabbit"/"wrx"/
  "autobot" no nome ou no `.gitignore`.

**Isso não muda a Decisão C.** O caminho de build do instalador do
cliente passa a ser `Documents\White Rabbit X\AutoBotSetup\wrx_setup.py`
em vez de `Levain-2.0\AutoBotSetup\wrx_setup.py`, e a fonte do Autobot
completo passa a ser `Documents\White Rabbit X\Autobot\` em vez de
`Levain-2.0\white_rabbit_x_optimization_tools\`. O comportamento final
entregue ao cliente é o mesmo desenhado originalmente.

## Riscos e limites conhecidos

- Reescrever histórico do Levain-2.0- muda o SHA de todo commit após o
  ponto da senha — aceitável aqui porque é um repo de uso único do dono,
  sem outros colaboradores ou clones locais identificados.
- O bundle do cliente sobe de 88MB para ~150-220MB; sem impacto conhecido
  no canal de distribuição atual (RAR via Telegram), mas é uma mudança de
  tamanho perceptível.
- Autobot completo no cliente muda o produto de "biblioteca de sets" para
  "laboratório de pesquisa": o comprador passa a poder disparar campanhas
  de otimização de horas/dias na própria conta, e sistemas de grid (07/08)
  exigem conta hedging. Isso já era o comportamento do Autobot para uso
  interno; a mudança é apenas de público-alvo, não de funcionamento.
- Validação real em máquina de cliente limpa não é possível nesta sessão;
  o plano de implementação deve deixar claro esse limite.
