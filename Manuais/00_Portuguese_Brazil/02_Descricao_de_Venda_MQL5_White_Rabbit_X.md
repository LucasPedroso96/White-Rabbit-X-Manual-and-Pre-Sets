# White Rabbit X — Descrição para o MQL5 Market

Referência autoritativa gerada da fonte atual da EA e do manifesto de sets — EA 1.11 — 127 inputs — 3738 sets

## O que o software faz

White Rabbit X é uma EA multi-indicador para MT5 destinada a pesquisa sistemática, execução controlada e WFO. Reúne sinais, filtros opcionais, quatro modelos de lote, saídas, horários, notícias, painel e uma biblioteca orientada por manifesto.

Current schema: 127 inputs. Current manifest: 3738 sets.

- Doze motores nativos: MACD, cruzamento de EMA, Momentum, Estocástico, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA e Ichimoku.
- Sete métodos de gatilho com semântica explícita de reversão, cruzamentos, AND e OR.
- Filtros independentes MTF/MACD, média móvel, ADX, volatilidade ATR e notícias.
- Tamanho Percentage, Monetary, Fixed Lot ou Fixed-R, com proteções globais de risco.
- Stop, take ATR, breakeven, trailing e reversão formam a pilha de saída.
- Painel, marcações de negócios, idiomas, agenda semanal e WFO integram a operação.

## Telemetria do dashboard de ciclos

O painel usa os mesmos snapshots de estado empregados pelo loteamento e pelo fechamento das cestas.

- A atualização periódica por tick é limitada a uma vez por segundo; inicialização e eventos de negociação podem solicitar atualização imediata.
- Balance e Equity são da conta inteira. P&L fechado é a variação desde OnInit e P&L aberto/posições são o estado atual; estes últimos indicadores são filtrados por Symbol + Magic.
- Martingale mostra, separadamente para BUY e SELL, perdas consecutivas, quantidade e valor bruto das perdas do ciclo, valor recuperado, déficit restante e alvo igual ao déficit × Multiplicador.
- Ao exceder MaxMartingaleSteps, o ciclo Martingale sofre hard reset: o déficit antigo é descartado e a próxima ordem usa lote-base. Martingale exige no máximo uma posição aberta por lado.
- D'Alembert mostra o nível atual e o próximo lote normalizado de BUY e SELL.
- Grid mostra pernas e volume, realizado já incluindo custos, P&L aberto, P&L total do ciclo, alvo monetário congelado no início e valor que falta.
- A âncora Grid é a posição confirmada mais recente. BUY só dispara estritamente abaixo de âncora − ATR × DistanciaMinima; SELL, estritamente acima de âncora + ATR × DistanciaMinima. O progresso mostra distância adversa em ATR versus o limite.
- Em Separate, ficar flat encerra apenas o ciclo daquele lado; em Unified, o ciclo termina quando BUY e SELL ficam flat. Ordens ainda em trânsito adiam o reset.
- O alvo é o gatilho para solicitar o fechamento. Comissão, fee e slippage efetivos da saída podem deixar o resultado final ligeiramente abaixo dele.
- InterfaceLanguage preserva 11 idiomas. Auto usa inglês no Tester e o idioma do terminal ao vivo; rótulos sem tradução específica têm fallback para inglês.

## Combinações suportadas e restrições

Estas são regras operacionais conservadoras da arquitetura atual. O broker pode impor limites mais rígidos e um backtest positivo não corrige um modo de conta incompatível.

- PositionSize_Percentage e PositionSize_FixedR exigem AtivarStop=true e um stop calculável.
- Grid aceita somente PositionSize_Monetary ou PositionSize_FixedLot, Recovery_None e conta hedge real.
- Grid exige AtivarTake=true, DistanciaMinima>0 e limite ativo igual a zero ou pelo menos duas posições.
- Grid_SeparateProfit gerencia cada lado; Grid_UnifiedProfit gerencia o resultado agregado do ciclo.
- Enquanto a cesta continuar aberta, perdas realizadas, swap, comissão e taxas do ciclo permanecem incorporados ao resultado necessário para alcançar o alvo; o lucro isolado de uma perna não apaga esses custos.
- Em Grid_SeparateProfit, BUY e SELL têm ciclos independentes. Se todas as posições de um lado desaparecerem, o ciclo daquele lado termina; uma entrada futura inicia um novo ciclo, sem transportar o déficit encerrado.
- Recovery_DAlembert é exclusivo de Fixed Lot, Grid_Disabled e DAlembertStep>0.
- Recovery_Martingale respeita MaxMartingaleSteps e MaxMartingaleLot; zero significa sem teto adicional.
- ReversalExit_OnOppositeOrder exige conta hedge, Hedging=true, BUY e SELL habilitados e grid desligado.
- O backtest com notícias requer NewsCSVFile em Common\Files; NewsMoedasManual tem precedência sobre detecção automática.
- Horários usam o servidor do broker; intervalos noturnos e dias de fim de semana devem ser testados explicitamente.
- Símbolo, sufixo, tamanho de contrato, tick value, volume mínimo e custos devem ser revalidados por broker.

## Comunidade e downloads

Entre no canal oficial no Telegram: **https://t.me/MrRabbit_MT5**

- Sets prontos por ativo e por tipo de sistema (SL/TP, trailing, grid, martingale e outros), organizados para carregar direto no Strategy Tester.
- Manuais no seu idioma: portugues, ingles, russo, chines, espanhol, japones, alemao, coreano, frances, italiano e turco.
- Avisos de atualizacao da EA e das bibliotecas de sets.
- Suporte e troca de experiencia com outros usuarios.

> Este e o unico canal oficial. Nao compre sets ou copias da EA de terceiros que digam representar o White Rabbit X: a EA e vendida apenas no MQL5 Market e os sets sao distribuidos gratuitamente no canal acima.

## Aviso de risco

Nenhuma EA, set, indicador, otimização ou resultado histórico garante desempenho futuro. Valide símbolo, custos, execução, amostra fora do período e forward demo antes de assumir risco.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
