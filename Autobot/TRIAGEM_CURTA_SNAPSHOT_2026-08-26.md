# Snapshot da triagem curta (3 meses, 14 fórmulas) — antes da confirmação longa sobrescrever

Salvo em 2026-08-26 ~18:50, porque `_confirmacao_longa.py` reusa `sweep_formulas.py`
e sobrescreve os MESMOS nomes de log das fórmulas aprovadas conforme avança pela
fila — isso preserva os números originais da triagem pra comparação depois.
Default atual = valor em `FORMULA_POR_SISTEMA` (`generate_system_sets.py`).

## 04_SLTP_TRAIL / XAUUSD (default atual: 5 AdjustedEfficiencyForGrid)
| Fórmula | Veredito | Retenção | Expectancy |
|---|---|---|---|
| 03 ProfitWinTradeDD | APROVADO | 101,9% | +0,284R |
| 04 EfficiencyRelativeToDeposit | APROVADO | 186,2% | +0,093R |
| 11 ReturnUniformity | APROVADO | 147,8% | +0,214R |
| 14 SomaR | APROVADO | 67,7% | +0,639R |
| 05 AdjustedEfficiencyForGrid (default) | REPROVADO | 26,0% | +0,309R |
(demais 9 formulas: REPROVADO)

## 05_BE_TRAIL / XAUUSD (default atual: 6 ProfitRelativeToDDAndDeposit)
| Fórmula | Veredito | Retenção | Expectancy |
|---|---|---|---|
| 04 EfficiencyRelativeToDeposit | APROVADO | 37,9% | +1,235R |
| 07 ProfitPerTradeAdjustedByDD | APROVADO | 58,8% | +0,321R |
| 09 PessimisticProfit | APROVADO | 198,8% | +0,522R |
| 13 LevainCompositeScore | APROVADO | 80,4% | +0,236R |
| 06 ProfitRelativeToDDAndDeposit (default) | REPROVADO | -26,3% | +0,704R |
(demais 9 formulas: REPROVADO; 14 SomaR nao confirmado no ultimo check)

## 12_GRID_INVERSO / XAUUSD (default atual: 10 ResilienceToDrawdown)
| Fórmula | Veredito | Retenção | Expectancy |
|---|---|---|---|
| 07 ProfitPerTradeAdjustedByDD | APROVADO | 61,7% | +0,673R |
| 13 LevainCompositeScore | APROVADO | 217,9% | +0,259R |
| 10 ResilienceToDrawdown (default) | REPROVADO | 3,4% | +0,406R |
(01,02,04,05,06,08,12,14: REPROVADO; 03,09,11: SEM_CANDIDATO — nenhum passou os pisos)

## 09_MARTINGALE / AUDNZD (default atual: 10 ResilienceToDrawdown)
**Nenhuma fórmula aprovou.** 06 ProfitRelativeToDDAndDeposit e 08 SharpeAdjustedByDD
chegaram a REPROVADO (retenção 150,5% e -26,0% respectivamente); as outras 12,
incluindo o default (10), nunca passaram do estágio 2 ("nenhum candidato passou
os pisos de trades/profit factor") — AUDNZD parece não dar candidato viável pra
esse sistema nessa janela. Sem confirmação longa (nada pra confirmar).

## 10_DALEMBERT / AUDNZD (default atual: 5 AdjustedEfficiencyForGrid)
| Fórmula | Veredito | Retenção |
|---|---|---|
| 12 SystemRobustness | APROVADO | 119,4% |
| 04 EfficiencyRelativeToDeposit | REPROVADO | -52,4% |
| 06 ProfitRelativeToDDAndDeposit | REPROVADO | -30,6% |
(demais 11, incluindo o default 05: SEM_CANDIDATO — nunca passou do estagio 2)

## 07_GRID_SEPARATE / AUDNZD (default atual: 10 ResilienceToDrawdown)
| Fórmula | Veredito |
|---|---|
| 01 GridSurvivalScore | APROVADO (59,8%) |
| 05 AdjustedEfficiencyForGrid | APROVADO (52,8%) |
| 07 ProfitPerTradeAdjustedByDD | APROVADO (84,6%) |
| 10 ResilienceToDrawdown (default) | REPROVADO (72,4%, caiu em outro criterio) |
(demais 10: REPROVADO)

## 03_TRAIL_ONLY / XAUUSD (default atual: 11 ReturnUniformity — escolhido em 22/08, ANTES dos fixes)
| Fórmula | Veredito |
|---|---|
| 07 ProfitPerTradeAdjustedByDD | APROVADO |
| 08 SharpeAdjustedByDD | APROVADO |
| 13 LevainCompositeScore | APROVADO |
| 11 ReturnUniformity (default) | **REPROVADO** — o vencedor original nao se sustentou pos-fix |
| 14 SomaR | REPROVADO |
(demais 9: REPROVADO)

## Padrão observado em todos os 7 sistemas
O default atual em `FORMULA_POR_SISTEMA` reprovou (ou nem teve candidato) na
triagem pós-fix em **todos os 7 sistemas**, sem exceção. Nenhuma mudança em
`FORMULA_POR_SISTEMA` deve ser feita sem antes ver a confirmação longa (1 ano)
das fórmulas aprovadas acima — é o próximo estágio, em andamento.
