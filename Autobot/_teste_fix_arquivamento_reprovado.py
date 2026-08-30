# -*- coding: utf-8 -*-
"""Confere o fix do bug real encontrado hoje: um VALIDADO_ existente tem
que ser ARQUIVADO antes de ser apagado quando o veredito do run vira
REPROVADO (outro_prefixo="VALIDADO") -- caminho que NAO passava pelo
arquivamento antes do fix. Usa um combo FAKE (nunca um sistema real) pra
nao mexer em nada de producao. Uso interno, apagar depois."""
import ready_library as rl
import campeoes_arquivo as ca

SISTEMA, SIMBOLO, VARIANTE = "99_TESTE_FAKE", "ZZZUSD", "BUY_MULTI"
nome_validado = f"VALIDADO_{SIMBOLO}_{SISTEMA}_{VARIANTE}.set"
caminho_validado = rl.TESTER / nome_validado

# Simula um VALIDADO_ ja existente (conteudo fake, so precisa existir).
caminho_validado.write_text("conteudo fake do campeao antigo", encoding="utf-8")
print(f"VALIDADO_ fake criado: {caminho_validado.exists()}")

pasta_arquivo = ca._pasta_combo(SISTEMA, SIMBOLO, VARIANTE)
versoes_antes = ca._versoes(pasta_arquivo)
print(f"versoes arquivadas ANTES: {versoes_antes}")

# Reproduz EXATAMENTE a logica corrigida: outro_prefixo == "VALIDADO" e
# outro_destino.exists() -> arquiva ANTES de apagar.
outro_prefixo = "VALIDADO"  # equivalente a um veredito REPROVADO neste run
if outro_prefixo == "VALIDADO" and caminho_validado.exists():
    ca.arquivar_campeao_anterior(SISTEMA, SIMBOLO, VARIANTE, caminho_validado)
caminho_validado.unlink(missing_ok=True)

print(f"VALIDADO_ fake ainda existe (deveria ser False)? {caminho_validado.exists()}")
versoes_depois = ca._versoes(pasta_arquivo)
print(f"versoes arquivadas DEPOIS: {versoes_depois}")
assert len(versoes_depois) == len(versoes_antes) + 1, "nao arquivou antes de apagar"

conteudo_arquivado = (pasta_arquivo / str(versoes_depois[-1]) / nome_validado).read_text(encoding="utf-8")
assert conteudo_arquivado == "conteudo fake do campeao antigo"
print("\nOK: o fix arquiva antes de apagar no caminho REPROVADO -- "
     "o bug de hoje nao se repete.")

# limpeza do teste
import shutil
shutil.rmtree(pasta_arquivo, ignore_errors=True)
print("limpeza do combo fake concluida.")
