# White Rabbit X — Guia de Otimização WFO

Referência autoritativa gerada da fonte atual da EA e do manifesto de sets — EA 1.11 — 127 inputs — 3738 sets

**Atencao a data.** Com o WFO ligado, o OnTester compara o fim real do teste com input_end_date e devolve zero se o teste terminou antes (tolerancia de 80 horas). Data errada zera todos os passes e a otimizacao inteira parece quebrada. Ajuste input_end_date para a mesma data final configurada no Strategy Tester.

## Escopo e fontes de verdade

A fonte da EA define o esquema de inputs, padrões, enums e recursos atuais. O manifesto define cada set, família, status, caminho e hash de integridade. O material Quantum antigo é apenas histórico e não deve orientar a versão atual.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Material gerado. Os identificadores dos parâmetros permanecem idênticos aos declarados pela EA.

## Método walk-forward

Use segmentos cronológicos in-sample, out-of-sample e forward demo com spread, comissão, swap e slippage realistas. Rejeite ilhas instáveis e resultados dependentes de uma única operação, regime ou artefato do broker. Com passo Custom, valor positivo em wfo_customStepSizePercent é percentual da janela in-sample; um valor negativo como -61 representa 61 dias fixos de out-of-sample.

## Fluxo seguro

Altere uma matriz por vez e retenha evidências completas para cada promoção.

1. Confirme que o EX5, a fonte auditada, o esquema dos sets e o manifesto pertencem à mesma versão.
2. Copie a biblioteca para MQL5\Profiles\Tester ou selecione-a diretamente ao carregar Inputs no Strategy Tester.
3. Mapeie o ativo ao símbolo exato do broker, incluindo sufixo, sessão, moeda de lucro e tamanho de contrato.
4. Navegue por classe e ativo: cada ativo traz os 11 tipos de sistema (01_SLTP a 11_SIGNAL_ONLY), um set por lado (BUY/SELL; BOTH no grid unificado) e duas variantes de entrada — MULTI disputa os indicadores 0–10 num eixo só e ICHIMOKU tem arquivo próprio.
5. A fase 1 é descoberta de regiões: rode o genético com o set como está — entradas completas (indicador, método, timeframe, applied price, períodos), saídas do sistema e chaves de filtro, tudo de uma vez.
6. Das rodadas seguintes em diante, trave (Y→N) os inputs de escrita — enums e booleanos — decididos na fase anterior e deixe abertos só os numéricos; o ajuste de cada filtro só entra se a chave sobreviveu ligada.
7. O filtro ATR de entrada (EntradaATR) existe apenas nos sistemas de grid; nos demais permanece desligado por construção.
8. Valide o vencedor em ticks reais: decidem a divergência contra o OHLC e a retenção out-of-sample, nunca o lucro in-sample.
9. Depois do tick real, troque o dimensionamento para Percentagem e rode de novo: só promova se passar também — e é nesse modo que o set deve operar.
10. Execute in-sample, out-of-sample e forward demo cronológicos, com custos e execução realistas.
11. Se usar notícias, gere WhiteRabbit_News.csv para todo o período e moedas antes de iniciar o tester.
12. Execute WhiteRabbit Filters SelfTest e só prossiga se a última linha informar zero falhas.
13. Consulte Status, RelativePath e SHA256 no manifesto antes de promover um resultado.
14. USE é autorização explícita para um ambiente definido; REOPTIMIZE, RESEARCH e HOLD não são presets prontos para conta real.

## Status do manifesto e decisão de liberação

O status exato do manifesto é preservado e também recebe uma decisão conservadora: USE, REOPTIMIZE, RESEARCH ou HOLD. Somente um USE explícito é tratado como pronto para o ambiente definido.

| Sistema | Gestao | Sets |
| --- | --- | ---: |
| `01_SLTP` | Stop Loss + Take Profit em multiplos de ATR | 356 |
| `02_SLTP_ORGANIC` | SL + take organico ancorado no ultimo trade | 356 |
| `03_TRAIL_ONLY` | SL + trailing, sem TP: deixa correr | 356 |
| `04_SLTP_TRAIL` | SL + TP + trailing atras | 356 |
| `05_BE_TRAIL` | Breakeven obrigatorio + trailing | 356 |
| `06_REVERSAL_EXIT` | Fecha no sinal contrario do indicador | 356 |
| `07_GRID_SEPARATE` | Grid com alvo por lado (conta hedging) | 356 |
| `08_GRID_UNIFIED` | Grid com alvo unico da cesta (conta hedging) | 356 |
| `09_MARTINGALE` | Lote dobra apos perda, 1 posicao por lado | 356 |
| `10_DALEMBERT` | Lote cresce em passo aritmetico apos perda | 356 |
| `11_SIGNAL_ONLY` | Sem SL e sem TP: mede o sinal cru | 356 |

## Modo de modelagem: use ticks reais

Na aba **Settings** do Strategy Tester, campo **Modeling**:

```
Every tick based on real ticks   <- use este
OHLC 1 minute                    <- apenas 01_SLTP e 02_SLTP_ORGANIC
```

Isto nao e preferencia. Medindo o mesmo set nos dois modos ao longo de tres
anos, o modo OHLC **subestimou a perda em 3,3x nos sistemas com trailing e em
23x no grid** — sempre para o lado otimista. Apenas SL/TP fixo ficou dentro de
3%.

A causa e estrutural: trailing e grid dependem de **quando** o preco tocou cada
nivel dentro da barra. O modo OHLC interpola isso a partir de quatro precos por
minuto e suaviza justamente as excursoes adversas que teriam encerrado a
posicao. Otimizar trailing sobre barras interpoladas seleciona parametros que
sobreviveram a um caminho de preco que nao existiu.

Ticks reais custam cerca de 20x mais tempo por passe. Vale: e a diferenca entre
um resultado e um numero.

### Se precisar economizar tempo, economize no lugar certo

Os sinais sao avaliados no FECHAMENTO da barra, entao escolher indicador,
metodo ou timeframe da o mesmo instante de entrada nos dois modos. Ja stop,
alvo e trailing dependem do caminho intrabar.

Entao use cada modelo onde ele e confiavel: OHLC para reduzir as chaves
(indicador, metodo, timeframe, periodos) e ticks reais para a geometria de
saida. Com o sinal travado o espaco de busca cai ordens de magnitude, e os
ticks reais deixam de ser proibitivos.

## Fixed-R para pesquisar, percentual para operar

Otimize em **Fixed-R**: com o capital-base congelado, os passes ficam
comparaveis entre si e entre simbolos. +40R no ouro e +40R no EURUSD significam
a mesma coisa, enquanto "+3.200 USD" nao significa nada sem saber o lote e o
saldo.

Ao vivo, o modo **Percentagem** costuma fazer mais sentido: ele acompanha a
conta, compoe quando ela cresce e reduz a exposicao quando ela encolhe —
protecao que o R fixo nao da, porque ignora o saldo corrente de proposito. Os
dois modos reportam em R, entao o historico continua legivel depois da troca.

Por isso o circuito so grava um set aprovado depois de repetir o passe final em Percentagem: se o resultado nao se sustenta sob juros compostos, ele nao estava pronto — e o set validado ja sai gravado nesse modo.

## Aviso de risco

Nenhuma EA, set, indicador, otimização ou resultado histórico garante desempenho futuro. Valide símbolo, custos, execução, amostra fora do período e forward demo antes de assumir risco.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
