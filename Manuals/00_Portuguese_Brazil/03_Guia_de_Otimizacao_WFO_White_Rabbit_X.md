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
4. Comece pelas pastas 01–05: carregue o baseline do ativo e teste BUY e SELL separadamente.
5. Use a pasta 06 para pesquisa controlada de um único eixo; não misture mudanças antes de medir o efeito.
6. Use a pasta 07 para comparar indicador, método de entrada e arquétipo de gestão.
7. Use a pasta 08 para empilhar filtros; confirme que ainda existe amostra estatística suficiente.
8. Use a pasta 09 para comparar motores de risco apenas em combinações declaradas como compatíveis.
9. Use a pasta 10 para testar saídas sobre uma entrada já congelada.
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

## Aviso de risco

Nenhuma EA, set, indicador, otimização ou resultado histórico garante desempenho futuro. Valide símbolo, custos, execução, amostra fora do período e forward demo antes de assumir risco.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
