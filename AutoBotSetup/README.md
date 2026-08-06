# AutoBotSetup — instalador para o comprador

O MQL5 Market entrega o `.ex5` e mais nada. Os 3.738 sets de otimização ficam
de fora, e sem eles o comprador teria de descobrir a pasta de dados do
terminal, copiar os arquivos no lugar certo e ainda perceber sozinho que o
corretor dele chama `EURUSD` de `EURUSDm` — porque um `.set` com o símbolo
errado simplesmente não carrega, sem dizer o motivo.

Este instalador resolve isso em um clique duplo — e desde 2026-08-06 também
instala o Autobot (o mesmo painel de controle usado internamente), com um
Python próprio embutido, pra quem quiser rodar campanhas de otimização na
própria conta.

## O que ele faz

1. **Acha o MetaTrader.** Os dados do MT5 ficam num diretório cujo nome é um
   hash, fora da pasta de instalação. O instalador varre e, quando há mais de
   um, coloca **primeiro aquele onde o White Rabbit X já está baixado** — que
   é quase sempre o certo.
2. **Copia os sets** para `MQL5\Profiles\Tester\White_Rabbit_X_Sets`.
3. **Ajusta ao corretor**: descobre o sufixo real de cada símbolo, aplica o
   lote mínimo de cada um e avisa quais ativos aquele corretor não oferece.
4. **Instala o Autobot** (dashboard + circuito de otimização) em
   `Documents\White Rabbit X - Autobot`, com Python embutido — e cria um
   atalho "White Rabbit X - Autobot" na área de trabalho.
5. **Grava `INSTALACAO.json`** com o que foi feito, para suporte.

Se o terminal estiver fechado, ele copia os sets no padrão e avisa que o
ajuste ao corretor precisa de uma segunda passada com o MT5 aberto.

## Para o comprador

Um arquivo só. Não precisa de Python nem de nada instalado — nem pros sets,
nem pro Autobot:

```
White Rabbit X - Instalador.exe
```

Abrir o MetaTrader e fazer login **antes** de rodar dá o resultado completo,
porque só assim o instalador enxerga o corretor.

## Para gerar o executável

Duas partes: montar a pasta `AutobotRuntime` (Python embutido + Autobot) uma
vez, depois compilar o `.exe` (essa parte sim, toda vez que algo mudar).

### 1. Montar `AutobotRuntime/` (só precisa refazer se as dependências do
   Autobot mudarem — numpy/pandas/fastapi/uvicorn/MetaTrader5)

```bash
# Baixa o Python embeddable oficial (mesma versao do Python usado aqui: 3.13.6)
curl -LO https://www.python.org/ftp/python/3.13.6/python-3.13.6-embed-amd64.zip
mkdir -p AutobotRuntime/python-embed
unzip python-3.13.6-embed-amd64.zip -d AutobotRuntime/python-embed

# Habilita Lib\site-packages no ._pth (SEM habilitar "import site" -- isso
# faria o embeddable enxergar %APPDATA%\Python\PythonXXX\site-packages, ou
# seja, os pacotes pessoais de quem builda, o que quebra no cliente).
# E adiciona "..\Autobot" -- e assim que os scripts do Autobot (irmao de
# python-embed\) ficam importaveis sem PYTHONPATH, porque um arquivo ._pth
# ignora tanto PYTHONPATH quanto o "adiciona o diretorio do script" padrao
# do Python normal.
cat > AutobotRuntime/python-embed/python313._pth <<'EOF'
python313.zip
.
Lib\site-packages
..\Autobot
#import site
EOF

# Bootstrap do pip (o embeddable nao vem com pip)
curl -LO https://bootstrap.pypa.io/get-pip.py
AutobotRuntime/python-embed/python.exe get-pip.py --no-warn-script-location

# Dependencias do Autobot, DENTRO do Python embutido
AutobotRuntime/python-embed/python.exe -m pip install --no-warn-script-location \
  fastapi uvicorn MetaTrader5 numpy pandas

# Autobot: so o subconjunto operacional (dashboard + circuito de 5 estagios +
# geracao/validacao de sets) -- NAO as ferramentas de manutencao de manual
# (align_manuals, audit_manuals, enrich_manuals, render_manuals,
# sync_input_reference, sync_set_count, update_indicator_lists,
# write_library_docs, build_br_version) nem os *.ps1/test_*.py.
mkdir -p AutobotRuntime/Autobot
# copie os .py operacionais + dashboard_static/ de ../Autobot/

# Launcher (ja existe em AutobotRuntime/Iniciar_Dashboard.bat -- so confirma
# que ta la; ele chama python-embed\python.exe dashboard_campanha.py)
```

### 2. Compilar o `.exe`

```bash
python -m pip install pyinstaller
python -m PyInstaller --onefile --console \
  --name "White Rabbit X - Instalador" \
  --add-data "<caminho absoluto>/Sets;Sets" \
  --add-data "<caminho absoluto>/AutobotRuntime;AutobotRuntime" \
  --hidden-import MetaTrader5 \
  --collect-all numpy \
  --distpath . --workpath build/tmp --specpath build --noconfirm \
  wrx_setup.py
```

`--collect-all numpy` **não é opcional**: o `MetaTrader5` (módulo compilado,
não Python puro) usa numpy internamente, e o PyInstaller não enxerga essa
dependência sozinho — sem isso o instalador roda, copia os sets, mas a
etapa de ajuste ao corretor falha com
`ModuleNotFoundError: No module named 'numpy'` / `numpy._core.multiarray
failed to import`, silenciosamente (cai no fallback "sets no padrão").

As pastas `Sets` e `AutobotRuntime` vão embutidas. Uma pasta colocada **ao
lado do .exe** tem precedência sobre a embutida — é assim que se entrega uma
versão atualizada sem gerar um instalador novo.

Detalhe que quebra silenciosamente se esquecido: com `--onefile`, `__file__`
aponta para o diretório temporário que o PyInstaller extrai, não para onde o
comprador colocou o programa. O caminho "ao lado do exe" precisa sair de
`sys.executable`.

Tamanho esperado do `.exe`: ~150-220MB (`AutobotRuntime` sozinho já é
~176MB antes de compressão — numpy+pandas dominam).

## Distribuição

O executável vai no RAR do canal do Telegram, em paralelo à venda no Market.
Antes de publicar uma versão nova, regere os sets e reconstrua o `.exe`:

```bash
python ../Autobot/generate_system_sets.py
python ../Autobot/validate_system_sets.py
```
