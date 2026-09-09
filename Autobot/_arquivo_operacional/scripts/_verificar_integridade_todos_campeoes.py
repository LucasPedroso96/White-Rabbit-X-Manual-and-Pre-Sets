# -*- coding: utf-8 -*-
"""Confere TODOS os VALIDADO_*.set atuais contra o registro do ledger --
pedido do dono depois de dois bugs reais de arquivamento hoje: "tenha
certeza que os sistemas estao calibrados". Pra cada campeao, reconstroi o
que o arquivo DEVERIA ter (parametros do ledger) e compara com o que
realmente esta gravado (conferir_set(), mesma funcao que o proprio
circuito usa pra essa checagem). Uso interno, apagar depois."""
import optimize_two_stage as ots
import ready_library as rl

ledger = rl.metricas_do_ledger(rl.LEDGER)
problemas = []

for caminho in sorted(rl.TESTER.glob("VALIDADO_*.set")):
    info = rl.analisar_nome(caminho.name)
    if info is None:
        print(f"[?] {caminho.name}: nome fora do padrao, pulando")
        continue
    simbolo, sistema, variante = info["simbolo"], info["sistema"], info["variante"]
    chave = (simbolo, sistema, variante)
    registro = ledger.get(chave)
    if registro is None:
        print(f"[SEM LEDGER] {caminho.name}: arquivo existe, ledger nao tem "
             "registro pra conferir contra (nao e erro por si so -- so "
             "significa que nao da pra AUTO-verificar este aqui).")
        continue
    parametros = registro.get("parametros")
    if not parametros:
        print(f"[SEM PARAMETROS] {caminho.name}: registro no ledger sem "
             "'parametros' -- nao da pra conferir.")
        continue
    faltando = ots.conferir_set(caminho, parametros)
    if faltando:
        print(f"[DIVERGENTE] {caminho.name}: {len(faltando)} parametro(s) "
             f"nao batem com o ledger: {faltando}")
        problemas.append(caminho.name)
    else:
        print(f"[OK] {caminho.name}: bate exato com o ledger "
             f"(expectancy_r={registro.get('expectancy_r')}, "
             f"aprovado={registro.get('aprovado')})")

print(f"\n{'='*60}")
if problemas:
    print(f"PROBLEMAS ENCONTRADOS em {len(problemas)} arquivo(s): {problemas}")
else:
    print("Nenhuma divergencia -- todos os campeoes com registro no ledger "
         "batem exatamente com o que esta gravado no disco.")
