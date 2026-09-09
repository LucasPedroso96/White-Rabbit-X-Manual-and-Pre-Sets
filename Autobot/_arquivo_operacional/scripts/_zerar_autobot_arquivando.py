# -*- coding: utf-8 -*-
"""Zera o Autobot pra um estado 'virgem' -- pedido do dono (2026-08-31):
os VALIDADO_ atuais sao de calibracao manual/anterior, nao do circuito
real do Autobot (WFO + gate relativo + Zeus), entao nao contam como
estado valido hoje. Arquiva cada um (campeoes_arquivo.py, reversivel via
rollback_campeao()) antes de remover do Tester -- nada se perde de
verdade, so sai da frente pra recalibrar do zero pelo circuito real.
O ledger (campanha_resultados.jsonl) fica intacto -- e o registro
historico que o dono pediu pra manter. Uso interno, apagar depois."""
import ready_library as rl
import campeoes_arquivo

for p in sorted(rl.TESTER.glob("VALIDADO_*.set")):
    info = rl.analisar_nome(p.name)
    if info is None:
        print(f"[?] {p.name}: nome fora do padrao, pulando")
        continue
    simbolo, sistema, variante = info["simbolo"], info["sistema"], info["variante"]
    versao = campeoes_arquivo.arquivar_campeao_anterior(sistema, simbolo, variante, p)
    p.unlink()
    print(f"[OK] {p.name}: arquivado como versao {versao}, removido do Tester")

restantes = list(rl.TESTER.glob("VALIDADO_*.set"))
print(f"\nVALIDADO_*.set restantes no Tester: {len(restantes)} (esperado: 0)")
