# AutoBotSetup — instalador para o comprador

O MQL5 Market entrega o `.ex5` e mais nada. Os 3.738 sets de otimização ficam
de fora, e sem eles o comprador teria de descobrir a pasta de dados do
terminal, copiar os arquivos no lugar certo e ainda perceber sozinho que o
corretor dele chama `EURUSD` de `EURUSDm` — porque um `.set` com o símbolo
errado simplesmente não carrega, sem dizer o motivo.

Este instalador resolve isso em um clique duplo.

## O que ele faz

1. **Acha o MetaTrader.** Os dados do MT5 ficam num diretório cujo nome é um
   hash, fora da pasta de instalação. O instalador varre e, quando há mais de
   um, coloca **primeiro aquele onde o White Rabbit X já está baixado** — que
   é quase sempre o certo.
2. **Copia os sets** para `MQL5\Profiles\Tester\White_Rabbit_X_Sets`.
3. **Ajusta ao corretor**: descobre o sufixo real de cada símbolo, aplica o
   lote mínimo de cada um e avisa quais ativos aquele corretor não oferece.
4. **Grava `INSTALACAO.json`** com o que foi feito, para suporte.

Se o terminal estiver fechado, ele copia os sets no padrão e avisa que o
ajuste ao corretor precisa de uma segunda passada com o MT5 aberto.

## Para o comprador

Um arquivo só. Não precisa de Python nem de nada instalado:

```
White Rabbit X - Instalador.exe
```

Abrir o MetaTrader e fazer login **antes** de rodar dá o resultado completo,
porque só assim o instalador enxerga o corretor.

## Para gerar o executável

```bash
python -m PyInstaller --onefile --console \
  --name "White Rabbit X - Instalador" \
  --add-data "<caminho absoluto>/Sets;Sets" \
  --hidden-import MetaTrader5 \
  --distpath . --workpath build/tmp --specpath build --noconfirm \
  wrx_setup.py
```

A pasta `Sets` vai embutida. Uma pasta `Sets` colocada **ao lado do .exe** tem
precedência sobre a embutida — é assim que se entrega uma biblioteca
atualizada sem gerar um instalador novo.

Detalhe que quebra silenciosamente se esquecido: com `--onefile`, `__file__`
aponta para o diretório temporário que o PyInstaller extrai, não para onde o
comprador colocou o programa. O caminho "ao lado do exe" precisa sair de
`sys.executable`.

## Distribuição

O executável vai no RAR do canal do Telegram, em paralelo à venda no Market.
Antes de publicar uma versão nova, regere os sets e reconstrua o `.exe`:

```bash
python ../white_rabbit_x_optimization_tools/generate_system_sets.py
python ../white_rabbit_x_optimization_tools/validate_system_sets.py
```
