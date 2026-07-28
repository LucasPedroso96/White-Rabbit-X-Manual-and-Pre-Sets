# White Rabbit X — Descrição para o MQL5 Market

Doze motores de entrada nativos. Onze arquiteturas de saída. Um Expert Advisor.

A maioria dos EAs entrega uma estratégia pronta. Este entrega a oficina: você
escolhe o motor de sinal, o esqueleto de gestão e os filtros, e o walk-forward
embutido diz se o resultado sobrevive fora da amostra.

## Doze motores de entrada, todos nativos

MACD · Cruzamento de EMA · Momentum · Estocástico · TRIX · RSI · CCI ·
Williams %R · DeMarker · MFI · OsMA · **Ichimoku com a nuvem completa**

Todos são indicadores nativos do MetaTrader — nenhum arquivo de indicador
externo para instalar, nada que quebre na próxima atualização do terminal.

O Ichimoku lê os cinco buffers. O gatilho de referência é o **rompimento da
nuvem (Kumo)**, não um cruzamento Tenkan/Kijun, e o Chikou fica disponível
como filtro de confirmação. O Estocástico expõe suavização, método de média e
o campo de preço Low/High ou Close/Close — os três parâmetros que a maioria
dos EAs deixa fixos no código.

Três tipos de gatilho (reversão, cruzamento de sinal, cruzamento de
referência) combinam em sete métodos de entrada.

## Onze arquiteturas de saída

| Sistema | Gestão |
|---|---|
| SL/TP | Stop e alvo como múltiplos de ATR |
| SL/TP orgânico | Alvo ancorado no trade anterior |
| Somente trailing | Sem alvo — deixa a tendência correr |
| SL/TP + trailing | Alvo com trailing atrás |
| Breakeven + trailing | Risco retirado cedo, depois trailing |
| Saída por reversão | Fecha no sinal contrário do indicador |
| Grid separado | Alvo independente por lado |
| Grid unificado | Alvo único da cesta |
| Martingale | Recuperação em lote fixo, uma posição por lado |
| D'Alembert | Progressão aritmética de lote |
| Signal only | Sem stop e sem alvo — mede o sinal cru |

## Walk-forward dentro do EA

Não é a aba Forward do testador — é um walk-forward que roda dentro do Expert
Advisor. Ele fatia o período em janelas in-sample e out-of-sample e, no modo
de otimização, opera **apenas o in-sample** — de modo que o algoritmo genético
nunca vê os dados pelos quais será julgado.

Três modos de janela: sequencial, **rolling** (o clássico — o in-sample desliza
pelo tamanho do out-of-sample e rende cerca de três vezes mais ciclos com o
mesmo histórico) e anchored.

O relatório traz a Walk Forward Efficiency **por ciclo**, com média e desvio
padrão. Essa distinção decide: um EA que devolve 70% em todos os ciclos e
outro que devolve 200% num único ciclo e −20% nos demais têm a mesma média —
e só o primeiro é robusto. A dispersão separa os dois.

## Risco medido em R

O modo Fixed-R dimensiona cada posição para arriscar exatamente 1R, calculado
sobre um capital base fixo em vez do saldo corrente. Os resultados ficam
comparáveis entre símbolos, contas e rodadas: +40R no ouro e +40R no EURUSD
significam a mesma coisa, enquanto "+3.200 USD" não significa nada sem saber o
lote e o saldo.

Cada passe de otimização registra R total, expectância por trade, payoff e
drawdown em R.

Quinze critérios de otimização, incluindo um score composto que pondera fator
de lucro, retorno por trade ajustado por drawdown, Sharpe e fator de
recuperação, e devolve zero abaixo de trinta trades — o que sozinho descarta o
clássico "vencedor" construído sobre três trades de sorte.

## Proteção que roda antes da ordem

Perda diária máxima, teto de drawdown sobre o patrimônio, margem livre mínima,
limite de spread, janelas de sessão e dias da semana, e filtro de notícias do
calendário econômico com cache em CSV para backtest.

As distâncias de freeze level e stops level são verificadas **antes** de cada
requisição, então o log continua legível em vez de encher de recusas do
corretor.

## Painel no gráfico

Estratégia, indicador e parâmetros ativos, capital da conta e da EA, P&L
fechado, flutuante e líquido, posições abertas e — quando Martingale,
D'Alembert ou Grid estão ativos — o ciclo em tempo real: perdas consecutivas,
débito em aberto, valor recuperado, alvo, pernas, âncora e espaçamento de ATR.

Os indicadores do próprio EA são desenhados no gráfico sem custo de memória:
os handles já existentes são reaproveitados, não recalculados.

Interface em onze idiomas: português, inglês, russo, chinês, espanhol,
japonês, alemão, coreano, francês, italiano e turco.

## O que acompanha

- Expert Advisor para MetaTrader 5 — 136 inputs documentados
- **3.738 arquivos .set prontos**: 89 ativos × 11 sistemas × os dois sentidos
- Instalador automático que encontra seu terminal, copia os sets e os adapta
  ao sufixo de símbolo e ao lote mínimo do seu corretor
- Manual completo, guia de WFO, referência de inputs, tutorial dos sets, FAQ e
  compatibilidade técnica — tudo em onze idiomas
- Suporte e atualizações pelo canal oficial

## Antes de comprar

Isto é um framework de pesquisa, não um sinal para ligar e esquecer. Cada set
é uma hipótese: precisa de otimização, validação out-of-sample e forward-demo
antes de dinheiro real.

Grid, Martingale e D'Alembert mudam a natureza da curva de risco. Grid exige
conta hedging real.

Nenhum Expert Advisor, preset ou resultado histórico garante desempenho
futuro.

---

Canal oficial: https://t.me/MrRabbit_MT5 — biblioteca de sets gratuita, manuais
no seu idioma e avisos de atualização. A EA é vendida somente aqui no MQL5
Market; os sets são distribuídos gratuitamente naquele canal e em nenhum outro
lugar.
