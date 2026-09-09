# -*- coding: utf-8 -*-
"""Caso real (nao sintetico) do problema que o gate relativo resolve:
12_GRID_INVERSO/XAUUSD teve DUAS formulas aprovadas de forma independente
na confirmacao de 27/08 -- formula 7 (ProfitPerTradeAdjustedByDD, 0.240R)
e formula 13 (LevainCompositeScore, 0.577R), ambas em
sweep_12_GRID_INVERSO_XAUUSD_{07,13}_*.log. Sob a logica ANTIGA (so pisos
absolutos) as duas teriam "APROVADO: candidato pronto para a entrega." nos
seus proprios logs -- quem vira campeao dependeria SO da ordem de execucao
no sweep (7 rodou antes de 13, por sorte a melhor ganhou por ultimo e
sobrescreveu a pior). O gate relativo elimina essa dependencia de ordem.
Uso interno, apagar depois."""
import optimize_two_stage as ots

campeao = ots.carregar_campeao_atual("12_GRID_INVERSO", "XAUUSD", "BUY_MULTI")
expectancy_campeao = campeao.get("expectancy_r")
print(f"campeao no ledger (formula 13, LevainCompositeScore): "
      f"expectancy_r={expectancy_campeao}")

expectancy_formula7 = 0.240  # de sweep_12_GRID_INVERSO_XAUUSD_07_*.log, real
print(f"desafiante real (formula 7, ProfitPerTradeAdjustedByDD): "
      f"expectancy_r={expectancy_formula7}")

reprovado = expectancy_formula7 <= expectancy_campeao
print()
veredito = "REPROVADO -- nao supera o campeao" if reprovado else "APROVADO -- supera o campeao"
print(f"gate relativo: {veredito}")
assert reprovado, "esperava REPROVADO: formula 7 e genuinamente pior que a 13"
print("\nOK: confirma que o gate teria bloqueado a formula 7 de virar campea,")
print("mesmo ela tendo passado sozinha em todos os pisos absolutos antigos.")
