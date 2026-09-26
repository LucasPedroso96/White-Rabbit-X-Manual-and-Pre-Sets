# -*- coding: utf-8 -*-
"""Remede o PROPRIO arquivo de cada campeao (VALIDADO_*.set desta instalacao)
com a EA corrigida -- a outra metade de "refazer os aprovados" (dono,
2026-09-26: "se tiver que refazer os aprovados refaca!").

Por que nao basta a refacao pela campanha: ela roda um DESAFIANTE novo; se
ele perde (o do XAUUSD/04 reprovou na divergencia, 31%), o campeao antigo
fica, com a retencao medida pela EA que bloqueava entrada no OOS (13/09 ->
26/09 02:05, ver sonda_oos.py). Aqui o proprio arquivo do campeao passa pelo
passe IS+OOS (wfa_real.medir_holdout, o mesmo do holdout) na janela em que
foi aprovado: mesmo comprimento (janela_dias da linha), terminando no dia da
aprovacao.

Resultado vira linha NOVA no ledger (append-only, com lock) com a retencao
real, o relatorio novo (pasta propria, campanha_relatorios/<combo>__remedicao_*)
e a proveniencia (EA/Autobot). Retencao >= piso (30%): campeao confirmado.
Abaixo (ou sem medida): rebaixado -- ARQUIVADO antes (campeoes_arquivo,
rollback possivel), VALIDADO_ -> REPROVADO_. Campeao cuja linha ja e de
depois da correcao da EA e pulado.

    python remedir_campeoes.py [--dry]      (WRX_MT5_DATA_DIR da instalacao)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import campanha
import campeoes_arquivo
import optimize_two_stage as ots
import ready_library
import wfa_real

CORTE_EA_CORRIGIDA = "2026-09-26T02:06"
MIN_RETENCAO = 30.0


def ler_ledger() -> list[dict]:
    """Todas as linhas, na ordem; linha truncada nao derruba as outras."""
    saida = []
    for linha in ready_library.LEDGER.read_text(encoding="utf-8").splitlines():
        try:
            saida.append(json.loads(linha))
        except json.JSONDecodeError:
            continue
    return saida


def linha_do_arquivo(arq, linhas: list[dict]) -> dict:
    """A linha do ledger que PRODUZIU o arquivo (mesmos parametros), a mais
    recente -- mesma regra do certificado do dashboard."""
    iguais = [r for r in linhas if r.get("parametros")
              and not ots.conferir_set(arq, r["parametros"])]
    return iguais[-1] if iguais else {}


def janela(reg: dict) -> tuple[str, str]:
    fim = datetime.fromisoformat(reg["quando"])
    inicio = fim - timedelta(days=int(reg.get("janela_dias") or 360))
    return inicio.strftime("%Y.%m.%d"), fim.strftime("%Y.%m.%d")


def julgar(retencao: float | None) -> tuple[bool, str]:
    if retencao is None:
        return False, "retencao sem medida com a EA corrigida"
    if retencao < MIN_RETENCAO:
        return False, (f"retencao real {retencao:.1f}% < {MIN_RETENCAO:.0f}% "
                       "com a EA corrigida (a de antes era vazamento de borda)")
    return True, f"retencao real {retencao:.1f}% >= {MIN_RETENCAO:.0f}%"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true",
                    help="so lista o que remediria, sem rodar o MT5")
    args = ap.parse_args()
    print("pasta de dados:", ready_library.TESTER, flush=True)
    por_combo: dict[tuple, list[dict]] = {}
    for r in ler_ledger():
        por_combo.setdefault((str(r.get("simbolo", "")).replace(".", "_"),
                              r.get("sistema"), r.get("variante")), []).append(r)
    for arq in sorted(ready_library.TESTER.glob("VALIDADO_*.set")):
        info = ready_library.analisar_nome(arq.name)
        if info is None:
            continue
        sim, sis, var = info["simbolo"], info["sistema"], info["variante"]
        simbolo = info["simbolo_exibicao"]
        reg = linha_do_arquivo(arq, por_combo.get((sim, sis, var), []))
        print(f"\n{simbolo} {sis} {var}", flush=True)
        if not reg:
            print("  sem linha do ledger com estes parametros -- pulando "
                  "(o dashboard ja o mostra como nao certificado).")
            continue
        if str(reg.get("quando", "")) >= CORTE_EA_CORRIGIDA:
            print(f"  linha de {reg['quando']} ja e da EA corrigida -- pulando.")
            continue
        inicio, fim = janela(reg)
        deposito = campanha.resolver_deposito(simbolo, None)
        print(f"  aprovado em {reg['quando']} (retencao antiga "
              f"{reg.get('retencao_oos')}%); remedindo {inicio}..{fim}, "
              f"deposito {deposito}", flush=True)
        if args.dry:
            continue
        ots.ID_CORRIDA = "remedicao_" + datetime.now().strftime("%Y%m%dT%H%M%S")
        medida = wfa_real.medir_holdout(arq, {}, simbolo, "M1", inicio, fim,
                                        deposito)
        relatorio = ots.arquivar_relatorio(simbolo, sis, var)
        retencao = medida.get("retencao_pct")
        ok, motivo = julgar(retencao)
        print(f"  EA corrigida: retencao {retencao}% | lucro "
              f"{medida.get('profit')} | expectancy "
              f"{medida.get('expectancy_r')}R -> "
              + ("CONFIRMADO" if ok else "REBAIXADO") + f" ({motivo})",
              flush=True)
        novo = dict(reg)
        novo.update({
            "quando": datetime.now().isoformat(timespec="seconds"),
            "aprovado": ok,
            "retencao_oos": retencao,
            "relatorio_dir": relatorio,
            "proveniencia": ots.proveniencia(var),
            "remedicao": {"de": reg.get("quando"),
                          "retencao_antiga": reg.get("retencao_oos"),
                          "janela": [inicio, fim], "motivo": motivo,
                          "lucro": medida.get("profit"),
                          "expectancy_r": medida.get("expectancy_r")},
        })
        if not ok:
            versao = campeoes_arquivo.arquivar_campeao_anterior(sis, simbolo,
                                                                var, arq)
            os.replace(arq, arq.with_name("REPROVADO_" + arq.name[len("VALIDADO_"):]))
            novo.update({"rebaixado": True,
                         "rebaixado_de": {"quando": reg.get("quando"),
                                          "versao_arquivada": versao},
                         "motivo_rebaixamento": "remedicao pos-correcao da "
                                                "EA: " + motivo})
            print(f"  arquivado v{versao} e renomeado para REPROVADO_.",
                  flush=True)
        campanha.registrar(novo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
