# -*- coding: utf-8 -*-
"""Testa campeoes_arquivo.py com o VALIDADO_ real do 12_GRID_INVERSO/
XAUUSD -- arquiva, lista, e testa rollback (restaura a MESMA versao que
acabou de arquivar, entao nao muda nada de verdade no arquivo ao vivo,
so exercita o mecanismo). Uso interno, apagar depois."""
import filecmp

import campeoes_arquivo as ca
import ready_library as rl

SISTEMA, SIMBOLO, VARIANTE = "12_GRID_INVERSO", "XAUUSD", "BUY_MULTI"
destino = rl.TESTER / f"VALIDADO_{SIMBOLO}_{SISTEMA}_{VARIANTE}.set"
print("arquivo ao vivo:", destino, "| existe:", destino.exists())

print("\n=== arquivar ===")
v1 = ca.arquivar_campeao_anterior(SISTEMA, SIMBOLO, VARIANTE, destino)
print("versao arquivada:", v1)

print("\n=== listar ===")
for meta in ca.listar(SISTEMA, SIMBOLO, VARIANTE):
    print(" ", meta["versao"], meta["arquivado_em"], meta["arquivo_original"],
          "expectancy_r=" + str(meta["ledger"].get("expectancy_r")))

print("\n=== rollback pra mesma versao (nao deve mudar o conteudo) ===")
v2 = ca.rollback_campeao(SISTEMA, SIMBOLO, VARIANTE, versao=v1)
print("versao restaurada:", v2)

pasta_v1 = ca._pasta_combo(SISTEMA, SIMBOLO, VARIANTE) / str(v1) / destino.name
identico = filecmp.cmp(pasta_v1, destino, shallow=False)
print(f"\narquivo ao vivo ainda identico ao v{v1} arquivado?", identico)
assert identico, "rollback mudou o conteudo -- nao deveria, mesma versao"
print("\nOK: arquivar/listar/rollback funcionando com dado real.")
