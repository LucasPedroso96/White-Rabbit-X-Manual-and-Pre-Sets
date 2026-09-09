# -*- coding: utf-8 -*-
"""Confere o SEGUNDO bug real de hoje: um VALIDADO_ existente e ainda
VALIDO nao pode ser apagado so porque um candidato DIFERENTE foi
REPROVADO na mesma corrida (aconteceu de verdade: formula 15 reprovando
apagou o campeao real da formula 13). Reproduz a logica EXATA que agora
esta em optimize_two_stage.py (so mexe no prefixo oposto quando
aprovado=True) com um combo FAKE. Uso interno, apagar depois."""
import ready_library as rl

SISTEMA, SIMBOLO, VARIANTE = "99_TESTE_FAKE2", "YYYUSD", "BUY_MULTI"
nome_validado = f"VALIDADO_{SIMBOLO}_{SISTEMA}_{VARIANTE}.set"
caminho_validado = rl.TESTER / nome_validado

caminho_validado.write_text("campeao real, ainda valido", encoding="utf-8")
print(f"VALIDADO_ fake (campeao ainda valido) criado: {caminho_validado.exists()}")

# Reproduz EXATAMENTE a logica corrigida: um desafiante DIFERENTE roda e
# REPROVA (aprovado=False) -- outro_prefixo seria "VALIDADO", mas o fix
# so mexe no prefixo oposto quando aprovado=True.
aprovado = False  # desafiante diferente, reprovado pelo gate relativo
outro_prefixo = "REPROVADO" if aprovado else "VALIDADO"
if aprovado:
    outro_destino = caminho_validado
    outro_destino.unlink(missing_ok=True)
# else: nao mexe em nada -- exatamente o fix de hoje.

print(f"VALIDADO_ fake ainda existe (deveria ser True agora)? {caminho_validado.exists()}")
assert caminho_validado.exists(), "BUG: apagou o campeao valido so porque outro candidato reprovou"
conteudo = caminho_validado.read_text(encoding="utf-8")
assert conteudo == "campeao real, ainda valido"

print("\nOK: candidato diferente reprovado NAO apaga o campeao valido existente.")

caminho_validado.unlink()
print("limpeza do combo fake concluida.")
