# -*- coding: utf-8 -*-
"""Backfill do campanha_resultados.jsonl (ledger de ready_library.py/
campanha.py) com os campeoes ATUALMENTE implantados (VALIDADO_*.set na raiz
do Tester), reconstruindo cada registro a partir do JSON final que o proprio
optimize_two_stage.py ja imprimiu no log de sweep da formula vencedora --
mesma fonte que reality_check_wrx.py usa (parse_log_formula()), nao um
segundo lugar novo pra guardar isso.

Motivo: a recalibracao de 24-28/08 rodou por scripts diretos (nao por
campanha.py), entao o ledger nunca recebeu os resultados desses campeoes --
achado ao testar o gate relativo pela primeira vez (carregar_campeao_atual()
em optimize_two_stage.py). Sem isso, o gate novo e um no-op pra todo mundo
por falta de baseline, nao porque a logica esteja errada.

Cada VALIDADO_*.set pode ter mais de uma formula que passou (cada uma
reescreve o MESMO nome de arquivo) -- pega-se o log de sweep com o MTIME
mais recente entre os que imprimiram a linha "set gravado ...: <esse
arquivo>", que e o que efetivamente produziu o arquivo que esta no disco
agora.

Uso: python _backfill_ledger_campeoes.py [--aplicar]
Sem --aplicar so mostra o que seria escrito (dry-run). Idempotente: pula
combo que ja tem entrada no ledger.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import ready_library as rl

AQUI = Path(__file__).resolve().parent


def achar_json_vencedor(nome_set: str) -> tuple[dict, Path] | tuple[None, None]:
    marcador = f"set gravado (WFO desligado): {nome_set}"
    candidatos: list[tuple[float, dict, Path]] = []
    for log in AQUI.glob("sweep_*.log"):
        try:
            texto = log.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, linha in enumerate(texto):
            if marcador not in linha:
                continue
            for seguinte in texto[i + 1:]:
                seguinte = seguinte.strip()
                if not seguinte:
                    continue
                if seguinte.startswith("{"):
                    try:
                        reg = json.loads(seguinte)
                    except json.JSONDecodeError:
                        break
                    candidatos.append((log.stat().st_mtime, reg, log))
                break
    if not candidatos:
        return None, None
    candidatos.sort(key=lambda t: t[0])
    _, reg, log = candidatos[-1]
    return reg, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aplicar", action="store_true",
                    help="grava no ledger de verdade; sem isso e dry-run")
    args = ap.parse_args()

    existentes = rl.metricas_do_ledger(rl.LEDGER)
    linhas_novas = []
    for origem in sorted(rl.TESTER.glob("VALIDADO_*.set")):
        info = rl.analisar_nome(origem.name)
        if info is None:
            print(f"  [pula] nome fora do padrao: {origem.name}")
            continue
        chave = (info["simbolo"], info["sistema"], info["variante"])
        if chave in existentes:
            print(f"  [ja no ledger] {origem.name}")
            continue
        reg, log = achar_json_vencedor(origem.name)
        if reg is None:
            print(f"  [SEM LOG] {origem.name}: nenhum sweep_*.log imprimiu "
                  "esse arquivo -- fica de fora do backfill.")
            continue
        reg["quando"] = datetime.fromtimestamp(log.stat().st_mtime).isoformat(
            timespec="seconds")
        reg["minutos"] = None
        reg["aprovado"] = True
        reg["origem_backfill"] = str(log.name)
        linhas_novas.append(reg)
        print(f"  [OK] {origem.name} <- {log.name} "
              f"(expectancy_r={reg.get('expectancy_r')}, "
              f"retencao_oos={reg.get('retencao_oos')})")

    print(f"\n{len(linhas_novas)} registro(s) novo(s) pro ledger "
          f"({'aplicando' if args.aplicar else 'dry-run, nada gravado'}).")
    if args.aplicar and linhas_novas:
        with rl.LEDGER.open("a", encoding="utf-8") as fh:
            for reg in linhas_novas:
                fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
        print(f"gravado em {rl.LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
