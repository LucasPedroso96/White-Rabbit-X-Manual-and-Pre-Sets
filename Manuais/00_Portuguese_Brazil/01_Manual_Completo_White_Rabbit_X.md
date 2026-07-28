# White Rabbit X — Manual Completo

Referência autoritativa gerada da fonte atual da EA e do manifesto de sets — EA 1.11 — 127 inputs — 3738 sets

## Escopo e fontes de verdade

A fonte da EA define o esquema de inputs, padrões, enums e recursos atuais. O manifesto define cada set, família, status, caminho e hash de integridade. O material Quantum antigo é apenas histórico e não deve orientar a versão atual.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Material gerado. Os identificadores dos parâmetros permanecem idênticos aos declarados pela EA.

## Instalação e primeiro teste

Instale ou compile o EX5 correspondente, copie os sets ao perfil Tester, selecione o símbolo correto do broker, carregue um set em Inputs e confira cada mensagem de validação.

## Motores de sinal e métodos de entrada

O indicador escolhido fornece três eventos universais: reversão, cruzamento de sinal/referência e cruzamento de base/referência. Métodos com “And” exigem os eventos na mesma barra fechada; “All” aceita qualquer um dos três. Há no máximo um despacho por lado em cada barra de sinal selecionada.

- Doze motores nativos: MACD, cruzamento de EMA, Momentum, Estocástico, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA e Ichimoku.
- Sete métodos de gatilho com semântica explícita de reversão, cruzamentos, AND e OR.
- Filtros independentes MTF/MACD, média móvel, ADX, volatilidade ATR e notícias.
- Tamanho Percentage, Monetary, Fixed Lot ou Fixed-R, com proteções globais de risco.
- Stop, take ATR, breakeven, trailing e reversão formam a pilha de saída.
- Painel, marcações de negócios, idiomas, agenda semanal e WFO integram a operação.
- EntryIndicator: MACD, EMA_Cross, Momentum, Stochastic, TRIX, RSI, CCI, WPR, DeMarker, MFI, OsMA, Ichimoku.
- EntryMethod: Reversal, SignalCross, ReferenceCross, ReversalAndSignalCross, ReversalAndReferenceCross, SignalAndReferenceCross, All.
- PositionSizeMode: Percentage, Monetary, FixedLot, FixedR.
- RecoveryMode: None, Martingale, DAlembert.
- GridMode: Disabled, SeparateProfit, UnifiedProfit.

## Filtros

O alinhamento MTF é uma camada MACD em timeframes superiores. MA, ADX, volatilidade ATR e notícias são filtros independentes. Empilhar filtros reduz a amostra e deve ser tratado como hipótese de pesquisa.

## Filtro de notícias e fluxo do CSV

No mercado ao vivo, a EA consulta o Calendário Econômico do MT5 no horário do servidor e bloqueia novas entradas se a consulta falhar. O tester não acessa esse calendário: execute MQL5\Scripts\White Rabbit News Exporter em um gráfico de conta real/demo, cubra todo o período do teste e grave NewsCSVFile em Common\Files. O cabeçalho separado por ponto e vírgula é datetime;currency;importance;event_name; importância 2 é moderada e 3 é alta. Use o mesmo broker/fuso do servidor. Em símbolos com sufixo ou não-FX, informe ExportMoedas e NewsMoedasManual; as moedas manuais têm prioridade.

## Execução e gestão de posições

Spread, margem, passo de volume, tick size, stops level e freeze level do broker afetam a execução. SL/TP habilitados integram a solicitação de entrada. Fechamentos podem exigir nova tentativa; confirme tudo no Diário.

## Ciclo do grid e espaçamento por ATR

Cada perna adicional mede a distância a partir da posição confirmada mais recente do mesmo lado e exige ATR × DistanciaMinima. A ordem inicial não pode disparar outra recursivamente no mesmo cálculo; no ciclo seguinte ela já é a âncora. O grid não usa TPs individuais: Separate avalia ciclos BUY/SELL independentes contra alvos congelados e encerra um lado quando ele fica flat; Unified avalia a cesta BUY+SELL agregada e termina quando ambos ficam flat. Comissões, swap, taxas e pernas já estopadas continuam no resultado enquanto o ciclo correspondente permanece aberto. O alvo dispara a solicitação de fechamento; custos reais e slippage da saída podem deixar o resultado final ligeiramente abaixo dele. No mercado ao vivo, o estado é preservado ao reiniciar a EA. Grid exige conta hedge real e nova otimização após mudança de EA, contrato ou custos.

## Pilha de saídas

Stop, take ATR orgânico, breakeven, trailing ATR e saída por reversão são controles separados. A saída por indicador usa o sinal oposto bruto por padrão; ative ReversalExitUseEntryFilters apenas para exigir também os filtros de entrada.

## Risco e recuperação

Escolha um único PositionSizeMode. Percentage e Fixed-R exigem stop válido. Grid, Martingale e D'Alembert são modos de recuperação para pesquisa. Limites de exposição, perda diária, drawdown e margem livre são proteções rígidas.

## Horários, interface e WFO

O horário usa o servidor do broker e pode atravessar a meia-noite. Sábado e domingo têm controles explícitos. O painel é opcional. Os inputs WFO definem janela in-sample, passo out-of-sample e critério de otimização.

## Diagnóstico e utilitários fornecidos

As abas Experts/Diário são a referência para inputs rejeitados, falhas de OrderCheck, indisponibilidade do calendário e tentativas de fechamento. Compile e execute MQL5\Scripts\WhiteRabbit Filters SelfTest; a última linha deve indicar zero falhas. Use White Rabbit News Exporter para criar o CSV e confirme período, moedas, delimitador e pasta Common\Files antes de um backtest com notícias.

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

## Aviso de risco

Nenhuma EA, set, indicador, otimização ou resultado histórico garante desempenho futuro. Valide símbolo, custos, execução, amostra fora do período e forward demo antes de assumir risco.

## Referência completa dos inputs

A tabela segue a ordem exata da declaração. Strings separadoras fazem parte do esquema .set e devem permanecer, embora não alterem a lógica. A coluna Descrição da fonte é copiada literalmente do .mq5 em inglês para permitir auditoria direta.

| Nº | Seção | Subseção | Parâmetro | Tipo | Padrão | Descrição da fonte | Opções do enum | Notas operacionais |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | General | — | NomedaEstrategia | string | "White Rabbit X" | Strategy Name | — | Use dentro de sua seção e valide a combinação completa. |
| 2 | Entries, Signal and Position Management | — | TimeFrame | ENUM_ALLOWED_TIMEFRAMES | M1 | Entry timeframe | M1, M5, M15, M30, H1, H4, D1, W1 | Signal evaluation is gated to one decision per closed bar of this timeframe. |
| 3 | Entries, Signal and Position Management | Entry Indicator | myBlankSpaceEntryIndicator | string | "" | \|\|================== Entry Indicator ==================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 4 | Entries, Signal and Position Management | Entry Indicator | EntryIndicator | ENUM_ENTRY_INDICATOR | EntryIndicator_MACD | Selects the indicator used by Entry Method | EntryIndicator_MACD, EntryIndicator_EMA_Cross, EntryIndicator_Momentum, EntryIndicator_Stochastic, EntryIndicator_TRIX, EntryIndicator_RSI, EntryIndicator_CCI, EntryIndicator_WPR, EntryIndicator_DeMarker, EntryIndicator_MFI, EntryIndicator_OsMA, EntryIndicator_Ichimoku | Selects the engine; Fast_EMA, Slow_EMA and MACD_SMA are reused by that engine. |
| 5 | Entries, Signal and Position Management | Entry Indicator | InpAppliedPrice | ENUM_APPLIED_PRICE | PRICE_CLOSE | Applied price used by the selected indicator | — | Use dentro de sua seção e valide a combinação completa. |
| 6 | Entries, Signal and Position Management | Entry Indicator | Fast_EMA | int | 12 | First period: MACD/EMA fast; oscillator period; Stochastic %K; Ichimoku Tenkan | — | First sequential period; for Ichimoku this is Tenkan. |
| 7 | Entries, Signal and Position Management | Entry Indicator | Slow_EMA | int | 26 | Second period: MACD/EMA slow; Ichimoku Kijun | — | Second sequential period; for Ichimoku this is Kijun. |
| 8 | Entries, Signal and Position Management | Entry Indicator | MACD_SMA | int | 9 | Third period: MACD signal; oscillator signal; Stochastic %D; Ichimoku Senkou B | — | Third sequential period; for Ichimoku this is Senkou Span B. |
| 9 | Entries, Signal and Position Management | Entry Method | myBlankSpace1 | string | "" | \|\|===================== Entry Method =======================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 10 | Entries, Signal and Position Management | Entry Method | EntryMethod | ENUM_ENTRY_TRIGGER_MODE | EntryTrigger_All | Reversal, signal cross, reference cross or their combinations | EntryTrigger_Reversal, EntryTrigger_SignalCross, EntryTrigger_ReferenceCross, EntryTrigger_ReversalAndSignalCross, EntryTrigger_ReversalAndReferenceCross, EntryTrigger_SignalAndReferenceCross, EntryTrigger_All | And modes require both events on the same closed bar; All is OR. |
| 11 | Entries, Signal and Position Management | ATR Settings | myBlankSpace42 | string | "" | \|\|==================== ATR Settings =====================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 12 | Entries, Signal and Position Management | ATR Settings | ATR_TimeFrame | ENUM_ALLOWED_TIMEFRAMES | M1 | Time Frame ATR | M1, M5, M15, M30, H1, H4, D1, W1 | Use dentro de sua seção e valide a combinação completa. |
| 13 | Entries, Signal and Position Management | ATR Settings | PeriodoATR | int | 14 | ATR Period | — | Use dentro de sua seção e valide a combinação completa. |
| 14 | Entries, Signal and Position Management | Stop Loss | myBlankSpace4s2 | string | "" | \|\|====================== Stop Loss ======================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 15 | Entries, Signal and Position Management | Stop Loss | AtivarStop | bool | true | Enable Stop Loss | — | Required by Percentage and Fixed-R sizing; recommended for every non-grid baseline. |
| 16 | Entries, Signal and Position Management | Stop Loss | VelaStop | int | 0 | Stop Loss Candle | — | Use dentro de sua seção e valide a combinação completa. |
| 17 | Entries, Signal and Position Management | Stop Loss | Stop | double | 3 | Stop Loss ATR Multiplier | — | Use dentro de sua seção e valide a combinação completa. |
| 18 | Entries, Signal and Position Management | Take Profit | myBlankSpace101 | string | "" | \|\|===================== Take Profit =====================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 19 | Entries, Signal and Position Management | Take Profit | TakeOrganico | bool | false | Enable Organic ATR Take Profit | — | Use dentro de sua seção e valide a combinação completa. |
| 20 | Entries, Signal and Position Management | Take Profit | AtivarTake | bool | true | Enable Take Profit | — | Required by supported grid operation. |
| 21 | Entries, Signal and Position Management | Take Profit | VelaTake | int | 0 | Take Profit Candle | — | Use dentro de sua seção e valide a combinação completa. |
| 22 | Entries, Signal and Position Management | Take Profit | Take | double | 3 | Take Profit ATR Multiplier | — | Use dentro de sua seção e valide a combinação completa. |
| 23 | Signal Filters | MTF Alignment | myBlankSpaceMTF | string | "" | \|\|==================== MTF Alignment ====================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 24 | Signal Filters | MTF Alignment | AtivarFiltroMTF | bool | false | Enable MTF Filter | — | Higher-timeframe alignment uses the EA's MACD trend layer. |
| 25 | Signal Filters | MTF Alignment | MTF_RequererAmbos | bool | false | Require Both Higher Timeframes Aligned | — | Use dentro de sua seção e valide a combinação completa. |
| 26 | Signal Filters | Moving Average Filter | myBlankSpaceMA | string | "" | \|\|================ Moving Average Filter ================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 27 | Signal Filters | Moving Average Filter | AtivarFiltroMA | bool | false | Enable Moving Average Filter | — | Use dentro de sua seção e valide a combinação completa. |
| 28 | Signal Filters | Moving Average Filter | MA_TimeFrame | ENUM_ALLOWED_TIMEFRAMES | M1 | MA Timeframe | M1, M5, M15, M30, H1, H4, D1, W1 | Use dentro de sua seção e valide a combinação completa. |
| 29 | Signal Filters | Moving Average Filter | MA_Period | int | 200 | MA Period | — | Use dentro de sua seção e valide a combinação completa. |
| 30 | Signal Filters | Moving Average Filter | MA_Method | ENUM_MA_METHOD | MODE_EMA | MA Method | — | Use dentro de sua seção e valide a combinação completa. |
| 31 | Signal Filters | Moving Average Filter | MA_AppliedPrice | ENUM_APPLIED_PRICE | PRICE_CLOSE | Applied Price | — | Use dentro de sua seção e valide a combinação completa. |
| 32 | Signal Filters | Moving Average Filter | MetodoMA | MetodoFiltroMA | MA_PrecoEInclinacao | Price and Slope Rule | MA_ApenasPreco, MA_ApenasInclinacao, MA_PrecoEInclinacao, MA_PrecoOuInclinacao | Use dentro de sua seção e valide a combinação completa. |
| 33 | Signal Filters | Moving Average Filter | SentidoMA | SentidoFiltroMA | MA_Tendencia | Trend or Reversal Direction | MA_Tendencia, MA_Reversao | Use dentro de sua seção e valide a combinação completa. |
| 34 | Signal Filters | Moving Average Filter | MA_SlopeLookback | int | 3 | Slope Lookback Bars | — | Use dentro de sua seção e valide a combinação completa. |
| 35 | Signal Filters | ADX Filter | myBlankSpaceMA1 | string | "" | \|\|===================== ADX Filter ======================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 36 | Signal Filters | ADX Filter | AtivarFiltroADX | bool | false | Enable ADX Trend Strength Filter | — | Use dentro de sua seção e valide a combinação completa. |
| 37 | Signal Filters | ADX Filter | ADX_TimeFrame | ENUM_ALLOWED_TIMEFRAMES | M1 | ADX Timeframe | M1, M5, M15, M30, H1, H4, D1, W1 | Use dentro de sua seção e valide a combinação completa. |
| 38 | Signal Filters | ADX Filter | ADX_Period | int | 14 | ADX Period | — | Use dentro de sua seção e valide a combinação completa. |
| 39 | Signal Filters | ADX Filter | ADX_Limiar | double | 25 | Minimum ADX Value | — | Use dentro de sua seção e valide a combinação completa. |
| 40 | Signal Filters | ADX Filter | MetodoADX | MetodoFiltroADX | ADX_ApenasForca | Strength or Strength Plus Direction | ADX_ApenasForca, ADX_ForcaMaisDirecaoDI | Use dentro de sua seção e valide a combinação completa. |
| 41 | Signal Filters | Volatility Filter | myBlankSpaceVolatility | string | "" | \|\|================== Volatility Filter ==================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 42 | Signal Filters | Volatility Filter | EntradaATR | bool | false | Enable ATR Volatility Filter | — | Use dentro de sua seção e valide a combinação completa. |
| 43 | Signal Filters | Volatility Filter | VolatilityFilter | ENUM_VOLATILITY_MODE | VOL_HIGH | Trade Volatility Condition | VOL_LOW, VOL_HIGH | Use dentro de sua seção e valide a combinação completa. |
| 44 | Signal Filters | News Filter | myBlankSpaceNews | string | "" | \|\|===================== News Filter =====================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 45 | Signal Filters | News Filter | AtivarFiltroNoticias | bool | false | Enable News Filter | — | Live calendar errors block new entries; backtests require the exported CSV under Common\\Files. |
| 46 | Signal Filters | News Filter | NewsSomenteAltoImpacto | bool | false | High Impact Only | — | Use dentro de sua seção e valide a combinação completa. |
| 47 | Signal Filters | News Filter | NewsMinutosAntes | int | 15 | Minutes Blocked Before Event | — | Use dentro de sua seção e valide a combinação completa. |
| 48 | Signal Filters | News Filter | NewsMinutosDepois | int | 15 | Minutes Blocked After Event | — | Use dentro de sua seção e valide a combinação completa. |
| 49 | Signal Filters | News Filter | NewsMoedasManual | string | "" | Manual Currencies (e.g. "USD,EUR"); empty = auto by symbol | — | When non-empty, overrides automatic currency extraction; required for most suffixed/non-FX symbols. |
| 50 | Signal Filters | News Filter | NewsCSVFile | string | "WhiteRabbit_News.csv" | Common\\Files CSV for Backtests | — | Semicolon CSV in Common\\Files: datetime;currency;importance;event_name, using broker-server time. |
| 51 | Exit Management | — | AtivarBreakeven | bool | true | Enable Breakeven | — | Use dentro de sua seção e valide a combinação completa. |
| 52 | Exit Management | — | BreakevenDistancia | double | 1.0 | Breakeven Distance (SL or ATR Stop Multiplier) | — | Use dentro de sua seção e valide a combinação completa. |
| 53 | Exit Management | ATR Trailing | myBlankSpace46 | string | "" | \|\|==================== ATR Trailing =====================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 54 | Exit Management | ATR Trailing | AtivarTrailATR | bool | false | Enable ATR Trailing Stop | — | Use dentro de sua seção e valide a combinação completa. |
| 55 | Exit Management | ATR Trailing | MetodoDeCalculo | Candlesticktype | CandleClose | Trailing Price Source | CandleOpen, CandleClose, CandleHigh, CandleLow, Preco | Use dentro de sua seção e valide a combinação completa. |
| 56 | Exit Management | ATR Trailing | TrailVela | int | 0 | Trailing Candle | — | Use dentro de sua seção e valide a combinação completa. |
| 57 | Exit Management | ATR Trailing | Trail | double | 3 | Trail | — | Use dentro de sua seção e valide a combinação completa. |
| 58 | Exit Management | Reversal Exit | myBlankSpace10 | string | "" | \|\|==================== Reversal Exit ====================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 59 | Exit Management | Reversal Exit | ReversalExitMode | ENUM_REVERSAL_EXIT_MODE | ReversalExit_OnIndicatorSignal | Declared at source line 319. | ReversalExit_Disabled, ReversalExit_OnOppositeOrder, ReversalExit_OnIndicatorSignal | OnOppositeOrder requires a hedging account, both sides and grid disabled. |
| 60 | Exit Management | Reversal Exit | ReversalExitUseEntryFilters | bool | false | Apply entry filters to indicator exits | — | False uses the raw opposite indicator signal; true also requires entry filters. |
| 61 | Risk and Position Size | — | TradeCapitalPercentage | double | 100 | Percentage of Total Capital Allocated to EA | — | Allocation must be positive and no greater than the whole EA capital base. |
| 62 | Risk and Position Size | — | PositionSizeMode | ENUM_POSITION_SIZE_MODE | PositionSize_FixedLot | Declared at source line 351. | PositionSize_Percentage, PositionSize_Monetary, PositionSize_FixedLot, PositionSize_FixedR | Exactly one model is active; compatibility depends on stop and grid selections. |
| 63 | Risk and Position Size | — | PositionSizeValue | double | 0.01 | Percentage=% risk; Monetary=currency per 1.00 lot; Fixed Lot=lots; Fixed R=% of base capital per 1R | — | Meaning changes with PositionSizeMode; never compare raw values across modes. |
| 64 | Risk and Position Size | Fixed-R Controls | myBlankSpaceRF | string | "" | \|\|================== Fixed-R Controls ===================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 65 | Risk and Position Size | Fixed-R Controls | CapitalBaseR | double | 0 | Base Capital for 1R (0 = balance at OnInit) | — | Zero captures balance at initialization; Fixed-R only. |
| 66 | Risk and Position Size | Fixed-R Controls | MaxRiscoTradeR | double | 0 | Maximum Risk per Trade in R (0 = no cap) | — | Zero disables this additional Fixed-R cap. |
| 67 | Risk and Position Size | Daily Loss Limit | myBlankSpaceDL | string | "" | \|\|================== Daily Loss Limit ===================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 68 | Risk and Position Size | Daily Loss Limit | DailyLossLimitPercent | double | 0 | Maximum Daily Loss Percentage (0 = disabled) | — | Zero disables the daily limit; use a value below a total account loss. |
| 69 | Risk and Position Size | Equity/Margin Protection | myBlankSpaceRiskProtection | string | "" | \|\|============== Equity/Margin Protection ===============\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 70 | Risk and Position Size | Equity/Margin Protection | MaxEquityDrawdownPercent | double | 30.0 | Maximum EA drawdown before closing positions (0 = disabled) | — | Zero disables the EA equity stop. |
| 71 | Risk and Position Size | Equity/Margin Protection | MinFreeMarginPercent | double | 50.0 | Minimum free margin to preserve after a new entry (0 = disabled) | — | Zero disables the post-entry free-margin reserve. |
| 72 | Grid and Recovery | — | RecoveryMode | ENUM_RECOVERY_MODE | Recovery_None | Declared at source line 368. | Recovery_None, Recovery_Martingale, Recovery_DAlembert | None, Martingale or D'Alembert are mutually exclusive. |
| 73 | Grid and Recovery | Recovery Target | myBlankSpace457 | string | "" | \|\|=================== Recovery Target ===================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 74 | Grid and Recovery | Recovery Target | Multiplicador | double | 1 | Martingale or Grid Target Profit Multiplier | — | Recovery/grid target multiplier; validate a value greater than one where escalation is intended. |
| 75 | Grid and Recovery | Martingale Limits | myBlankSpace16 | string | "" | \|\|================== Martingale Limits ==================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 76 | Grid and Recovery | Martingale Limits | MaxMartingaleSteps | int | 0 | Consecutive Losses Before Reset (0 = no limit) | — | Zero means no step limit; exceeding a positive limit hard-resets the old deficit and forces the next order to the base lot. |
| 77 | Grid and Recovery | Martingale Limits | MaxMartingaleLot | double | 0.0 | Maximum Martingale or D'Alembert Lot (0 = broker limit only) | — | Zero means broker maximum only. |
| 78 | Grid and Recovery | DAlembert Settings | myBlankSpace_dal | string | "" | \|\|================= DAlembert Settings ==================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 79 | Grid and Recovery | DAlembert Settings | DAlembertStep | double | 0.01 | Lot Increment per Loss for D'Alembert | — | Must be positive; supported with Fixed Lot and grid disabled. |
| 80 | Grid and Recovery | Grid Settings | myBlankSpace17 | string | "" | \|\|==================== Grid Settings ====================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 81 | Grid and Recovery | Grid Settings | GridMode | ENUM_GRID_MODE | Grid_Disabled | Declared at source line 385. | Grid_Disabled, Grid_SeparateProfit, Grid_UnifiedProfit | Supported with Monetary or Fixed Lot sizing, Recovery_None and a hedging account; targets are frozen per cycle. |
| 82 | Grid and Recovery | Grid Settings | UsarsomenteATRGRID | bool | false | Use ATR Only as Grid Signal | — | Research switch; require an existing basket anchor before adding a grid leg. |
| 83 | Grid and Recovery | Grid Settings | DistanciaMinima | double | 2 | ATR Distance Multiplier for Next Grid Order | — | Positive ATR-distance multiplier between grid entries. |
| 84 | Trading Schedule | Trading Hours | myBlankSpaceTradingHours | string | "" | \|\|==================== Trading Hours ====================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 85 | Trading Schedule | Trading Hours | Fecharordensforadohorario | bool | false | Close Positions Outside Trading Hours | — | When enabled, positions are closed whenever server time is outside the interval. |
| 86 | Trading Schedule | Trading Hours | TOD_From_Hour | int | 00 | Trading Start Hour | — | Use dentro de sua seção e valide a combinação completa. |
| 87 | Trading Schedule | Trading Hours | TOD_From_Min | int | 00 | Trading Start Minute | — | Use dentro de sua seção e valide a combinação completa. |
| 88 | Trading Schedule | Trading Hours | TOD_To_Hour | int | 23 | Trading End Hour | — | Use dentro de sua seção e valide a combinação completa. |
| 89 | Trading Schedule | Trading Hours | TOD_To_Min | int | 55 | Trading End Minute | — | Use dentro de sua seção e valide a combinação completa. |
| 90 | Trading Schedule | Trading Days | myBlankSpaceTradingDays | string | "" | \|\|==================== Trading Days =====================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 91 | Trading Schedule | Trading Days | TradeMonday | bool | true | Allow Trading on Monday | — | Use dentro de sua seção e valide a combinação completa. |
| 92 | Trading Schedule | Trading Days | TradeTuesday | bool | true | Allow Trading on Tuesday | — | Use dentro de sua seção e valide a combinação completa. |
| 93 | Trading Schedule | Trading Days | TradeWednesday | bool | true | Allow Trading on Wednesday | — | Use dentro de sua seção e valide a combinação completa. |
| 94 | Trading Schedule | Trading Days | TradeThursday | bool | true | Allow Trading on Thursday | — | Use dentro de sua seção e valide a combinação completa. |
| 95 | Trading Schedule | Trading Days | TradeFriday | bool | true | Allow Trading on Friday | — | Use dentro de sua seção e valide a combinação completa. |
| 96 | Trading Schedule | Trading Days | TradeSaturday | bool | false | Allow Trading on Saturday | — | Explicit weekend permission; useful only when the broker symbol trades Saturday. |
| 97 | Trading Schedule | Trading Days | TradeSunday | bool | false | Allow Trading on Sunday | — | Explicit weekend permission; useful only when the broker symbol trades Sunday. |
| 98 | General Settings | Market Execution | myBlankSpaceExecution | string | "" | \|\|================== Market Execution ===================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 99 | General Settings | Market Execution | MaxSpread | double | 0 | Maximum Allowed Spread for New Trades | — | Zero disables the entry spread ceiling. |
| 100 | General Settings | Market Execution | MaxSlippage | int | 10 | Slippage, ajustado no OnInit | — | Use dentro de sua seção e valide a combinação completa. |
| 101 | General Settings | Position Exposure | myBlankSpaceExposure | string | "" | \|\|================== Position Exposure ==================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 102 | General Settings | Position Exposure | MaxLongTrades | int | 1 | Maximum Simultaneous BUY Positions | — | Zero disables BUY entries; grid sides require zero or at least two, while Martingale permits at most one. |
| 103 | General Settings | Position Exposure | MaxShortTrades | int | 1 | Maximum Simultaneous SELL Positions | — | Zero disables SELL entries; grid sides require zero or at least two, while Martingale permits at most one. |
| 104 | General Settings | Position Exposure | Hedging | bool | false | Allow Hedging | — | Does not change the account type; the real MT5 account must also support hedging. |
| 105 | General Settings | Identity and Interface | myBlankSpaceInterface | string | "" | \|\|=============== Identity and Interface ================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 106 | General Settings | Identity and Interface | MagicNumber | int | 384457 | Magic Number | — | Must be unique for each independent strategy/symbol scope. |
| 107 | General Settings | Identity and Interface | ModificationSafetyPoints | int | 0 | Optional extra distance beyond broker limits and current spread | — | Additional points beyond broker distance/spread constraints. |
| 108 | General Settings | Identity and Interface | InterfaceLanguage | ENUM_INTERFACE_LANGUAGE | Language_Auto | Live chart interface language | Language_Auto, Language_English, Language_Portuguese, Language_Russian, Language_Chinese, Language_Spanish, Language_Japanese, Language_German, Language_Korean, Language_French, Language_Italian, Language_Turkish | Eleven live/visual UI languages; Auto uses English in Tester and untranslated labels fall back to English. |
| 109 | General Settings | Chart Dashboard | myBlankSpaceDashboard | string | "" | \|\|================== Chart Dashboard ==================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 110 | General Settings | Chart Dashboard | EnableChartDashboard | bool | true | Show visual P&L panel on live and visual tester charts | — | Live/visual panel; periodic tick refresh is capped at once per second. |
| 111 | General Settings | Chart Dashboard | DashboardCorner | ENUM_BASE_CORNER | CORNER_LEFT_UPPER | Dashboard chart corner | — | Use dentro de sua seção e valide a combinação completa. |
| 112 | General Settings | Chart Dashboard | DashboardOffsetX | int | 12 | Horizontal offset in pixels | — | Use dentro de sua seção e valide a combinação completa. |
| 113 | General Settings | Chart Dashboard | DashboardOffsetY | int | 24 | Vertical offset in pixels | — | Use dentro de sua seção e valide a combinação completa. |
| 114 | General Settings | Chart Dashboard | ShowClosedDealLabels | bool | true | Show monetary and percentage result at each closed trade | — | Use dentro de sua seção e valide a combinação completa. |
| 115 | General Settings | Chart Dashboard | MaxVisibleDealLabels | int | 120 | Maximum closed-trade labels kept on chart | — | Use dentro de sua seção e valide a combinação completa. |
| 116 | General Settings | Chart Dashboard | ClosedDealLabelFontSize | int | 10 | Closed-trade label font size | — | Use dentro de sua seção e valide a combinação completa. |
| 117 | General Settings | Chart Dashboard | ApplyEmbeddedChartTheme | bool | true | Apply the White Rabbit X clean chart style on every machine | — | Use dentro de sua seção e valide a combinação completa. |
| 118 | Optimization (WFO) | — | AtivarWFO | bool | false | Enable WFO | — | Enables the internal WFO boundary logic; still requires an external chronological process. |
| 119 | Optimization (WFO) | — | MetodoDeEntradawfo | WFOTIPO | Insample | Optimization Mode | Insample, InSampleAndOutSample | Use dentro de sua seção e valide a combinação completa. |
| 120 | Optimization (WFO) | — | input_end_date | string | "2025.02.28" | Backtest End Date (manual) | — | Manual tester end date; keep synchronized with the selected test range. |
| 121 | Optimization (WFO) | WFO Periods | myBlankSpaceWFOPeriods | string | "" | \|\|===================== WFO Periods =====================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 122 | Optimization (WFO) | WFO Periods | wfo_windowSize | WFO_TIME_PERIOD | Ano | In-Sample Window Size | Nenhum, Ano, Semestre, Trimestre, Mes, Semana, Dia, Custom | Use dentro de sua seção e valide a combinação completa. |
| 123 | Optimization (WFO) | WFO Periods | wfo_customWindowSizeDays | int | 0 | Custom Window Size in Days (0 = unused) | — | Use dentro de sua seção e valide a combinação completa. |
| 124 | Optimization (WFO) | WFO Periods | wfo_stepSize | WFO_TIME_PERIOD | Semestre | Out-of-Sample Step Size | Nenhum, Ano, Semestre, Trimestre, Mes, Semana, Dia, Custom | Use dentro de sua seção e valide a combinação completa. |
| 125 | Optimization (WFO) | WFO Periods | wfo_customStepSizePercent | int | 0 | Custom Step Size in Days or Percentage | — | Custom step: positive=percentage of IS; negative=fixed number of OOS days (for example -61). |
| 126 | Optimization (WFO) | Optimization Criterion | myBlankSpace4447 | string | "" | \|\|=============== Optimization Criterion ================\|\| | — | Separador visual mantido para compatibilidade do esquema .set; não otimizar. |
| 127 | Optimization (WFO) | Optimization Criterion | selectedFormula | CustomFormulaType | Formula_ProfitPerTradeAdjustedByDD | Custom Optimization Formula | Formula_None, Formula_GridSurvivalScore, Formula_Profit, Formula_ProfitWinTradeDD, Formula_EfficiencyRelativeToDeposit, Formula_AdjustedEfficiencyForGrid, Formula_ProfitRelativeToDDAndDeposit, Formula_ProfitPerTradeAdjustedByDD, Formula_SharpeAdjustedByDD, Formula_PessimisticProfit, Formula_ResilienceToDrawdown, Formula_ReturnUniformity, Formula_SystemRobustness, Formula_LevainCompositeScore, Formula_SomaR | Optimization criterion only; inspect stability and OOS results before selection. |

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
