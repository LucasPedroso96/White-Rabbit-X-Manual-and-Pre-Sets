# White Rabbit X — Tutorial do Ecossistema de Sets

Referência autoritativa gerada da fonte atual da EA e do manifesto de sets — EA 1.11 — 127 inputs — 3738 sets

## Escopo e fontes de verdade

A fonte da EA define o esquema de inputs, padrões, enums e recursos atuais. O manifesto define cada set, família, status, caminho e hash de integridade. O material Quantum antigo é apenas histórico e não deve orientar a versão atual.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Material gerado. Os identificadores dos parâmetros permanecem idênticos aos declarados pela EA.

## Instalação e primeiro teste

Instale ou compile o EX5 correspondente, copie os sets ao perfil Tester, selecione o símbolo correto do broker, carregue um set em Inputs e confira cada mensagem de validação.

## Biblioteca de sets detectada

Cada .set é uma hipótese de pesquisa ou otimização. Todas as contagens vêm do sistema de arquivos e do manifesto atual; nenhuma quantidade está fixa no modelo deste documento. Contagens e fingerprints foram lidos no momento da geração.

| Pasta | Sets | Finalidade |
| --- | --- | --- |
| 01_Forex | 168 | Baselines por ativo — Forex. |
| 02_Metals | 18 | Baselines por ativo — Metals. |
| 03_Cryptocurrencies | 36 | Baselines por ativo — Cryptocurrencies. |
| 04_Indices_Energies | 42 | Baselines por ativo — Indices Energies. |
| 05_US_Stocks_CFD | 300 | Baselines por ativo — US Stocks CFD. |
| 06_Research_Matrix | 935 | Pesquisa controlada de um eixo. |
| 07_Entry_System_Matrix | 3360 | Matriz indicador × método × gestão. |
| 08_Filter_Stack_Matrix | 320 | Combinações dos filtros de sinal. |
| 09_Risk_Engine_Matrix | 130 | Modelos de tamanho, risco e recuperação compatíveis. |
| 10_Exit_Stack_Matrix | 720 | Combinações dos controles de saída. |

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

## Filtro de notícias e fluxo do CSV

No mercado ao vivo, a EA consulta o Calendário Econômico do MT5 no horário do servidor e bloqueia novas entradas se a consulta falhar. O tester não acessa esse calendário: execute MQL5\Scripts\White Rabbit News Exporter em um gráfico de conta real/demo, cubra todo o período do teste e grave NewsCSVFile em Common\Files. O cabeçalho separado por ponto e vírgula é datetime;currency;importance;event_name; importância 2 é moderada e 3 é alta. Use o mesmo broker/fuso do servidor. Em símbolos com sufixo ou não-FX, informe ExportMoedas e NewsMoedasManual; as moedas manuais têm prioridade.

## Ciclo do grid e espaçamento por ATR

Cada perna adicional mede a distância a partir da posição confirmada mais recente do mesmo lado e exige ATR × DistanciaMinima. A ordem inicial não pode disparar outra recursivamente no mesmo cálculo; no ciclo seguinte ela já é a âncora. O grid não usa TPs individuais: Separate avalia ciclos BUY/SELL independentes contra alvos congelados e encerra um lado quando ele fica flat; Unified avalia a cesta BUY+SELL agregada e termina quando ambos ficam flat. Comissões, swap, taxas e pernas já estopadas continuam no resultado enquanto o ciclo correspondente permanece aberto. O alvo dispara a solicitação de fechamento; custos reais e slippage da saída podem deixar o resultado final ligeiramente abaixo dele. No mercado ao vivo, o estado é preservado ao reiniciar a EA. Grid exige conta hedge real e nova otimização após mudança de EA, contrato ou custos.

## Diagnóstico e utilitários fornecidos

As abas Experts/Diário são a referência para inputs rejeitados, falhas de OrderCheck, indisponibilidade do calendário e tentativas de fechamento. Compile e execute MQL5\Scripts\WhiteRabbit Filters SelfTest; a última linha deve indicar zero falhas. Use White Rabbit News Exporter para criar o CSV e confirme período, moedas, delimitador e pasta Common\Files antes de um backtest com notícias.

## Aviso de risco

Nenhuma EA, set, indicador, otimização ou resultado histórico garante desempenho futuro. Valide símbolo, custos, execução, amostra fora do período e forward demo antes de assumir risco.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
