# -*- coding: utf-8 -*-
"""Corrige o registro estagnado do ledger pra AUDNZD/07_GRID_SEPARATE:
o arquivo VALIDADO_ real (28/08 02:53) e mais novo que o ultimo registro
do ledger (19/08) -- o backfill de mais cedo hoje so ACRESCENTOU os
campos novos (PF/DD/Sharpe/composite_score) em cima do registro velho,
sem substituir os parametros/metricas base, perpetuando a divergencia.
Le o JSON real do log que produziu o arquivo atual, funde com os campos
de gate ja corretos (calculados hoje contra os parametros certos), grava
um registro novo e completo. Uso interno, apagar depois."""
import json
from pathlib import Path

import ready_library as rl

LOG_CORRETO = Path("sweep_07_GRID_SEPARATE_AUDNZD_07_ProfitPerTradeAdjustedByDD.log")

texto = LOG_CORRETO.read_text(encoding="utf-8", errors="replace")
correto = None
for linha in reversed(texto.splitlines()):
    if linha.startswith("{"):
        correto = json.loads(linha)
        break
assert correto is not None, "sem JSON no log"

ledger = rl.metricas_do_ledger(rl.LEDGER)
atual = ledger.get(("AUDNZD", "07_GRID_SEPARATE", "BUY_MULTI"), {})
print("registro atual (quando):", atual.get("quando"))
print("registro correto vem de:", LOG_CORRETO.name)

# Preserva os campos de gate ja calculados hoje contra os parametros
# certos (_backfill_gate_zeus_completo.py ja rodou um passe real com
# ESTES parametros) -- so os campos "base" (parametros, retencao_oos,
# sobrevivencia etc.) precisavam do JSON correto.
novo = dict(correto)
for campo_gate in ("profit_factor", "max_dd_pct", "sharpe", "composite_score"):
    if campo_gate in atual:
        novo[campo_gate] = atual[campo_gate]
novo["aprovado"] = True
novo["origem_correcao"] = ("registro anterior (19/08) estava desatualizado "
                           f"em relacao ao arquivo real (28/08) -- corrigido via "
                           f"{LOG_CORRETO.name}, gate fields preservados do "
                           "backfill de 30/08")

print("\nnovo registro:")
print(json.dumps(novo, ensure_ascii=False, indent=2))

with rl.LEDGER.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(novo, ensure_ascii=False) + "\n")
print(f"\ngravado em {rl.LEDGER}")
