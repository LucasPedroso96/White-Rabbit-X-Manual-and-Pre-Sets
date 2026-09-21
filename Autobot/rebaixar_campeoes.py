# -*- coding: utf-8 -*-
"""Rebaixa campeoes REAIS que nao sobreviveram a revalidacao (2026-09-21).

Dono: "sim, atualize os campeoes reais". Casos: GBPUSD/03_TRAIL_ONLY
(BOTH_MULTI) reprovou no periodo anterior ao treino (-62%); GBPUSD/
02_SLTP_ORGANIC (BOTH_MULTI) reprovou no piso do WFA (2/4 ciclos, WFE ~0%).

Nao destrutivo e coerente com o desenho do ledger (append-only; o "campeao" de
um combo e o ULTIMO registro dele -- ready_library.metricas_do_ledger):
  1. arquiva o VALIDADO_*.set atual com o registro aprovado original
     (campeoes_arquivo.arquivar_campeao_anterior; rollback possivel);
  2. renomeia VALIDADO_ -> REPROVADO_ (o prefixo carrega o veredito);
  3. ACRESCENTA uma linha no ledger (campanha.registrar, com lock) com
     aprovado=false + o motivo e os numeros da revalidacao. Linhas antigas
     ficam intactas.
Depois disso carregar_campeao_atual() devolve None (gate relativo deixa de
comparar desafiantes contra um campeao invalido).

Rode COM as variaveis do clone (os campeoes estao na pasta de dados do clone):
    WRX_MT5_DATA_DIR=... WRX_MT5_INSTALL_DIR=... python rebaixar_campeoes.py --dry
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import campanha
import campeoes_arquivo
import ready_library

AQUI = Path(__file__).resolve().parent
REVAL = AQUI / "revalidacao_resultados.jsonl"

# (simbolo, sistema, variante, rotulo na revalidacao)
CAMPEOES = [
    ("GBPUSD", "02_SLTP_ORGANIC", "BOTH_MULTI", "CAMPEAO 02_SLTP_ORGANIC GBPUSD"),
    ("GBPUSD", "03_TRAIL_ONLY", "BOTH_MULTI", "CAMPEAO 03_TRAIL_ONLY GBPUSD"),
]


def ultimo_da_revalidacao(rotulo: str) -> dict:
    """Registro FINAL mais recente do candidato (veredito preferido)."""
    out: dict = {}
    for ln in REVAL.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if r.get("rotulo") == rotulo and (r.get("veredito") or not out):
            out = r
    return out


def rejulgar_wfa(reval: dict, sistema: str) -> dict:
    """Reaplica o piso ATUAL do WFA (avaliar_wfa) sobre os numeros guardados:
    o registro do 02_SLTP_ORGANIC foi julgado pela regra antiga (WFE > 0) e
    so reprova pelo piso novo (>= 50% dos ciclos e WFE >= 20%)."""
    import optimize_two_stage as ots
    if reval.get("wfe_global_pct") is None and not reval.get("wfa_ciclos_positivos"):
        return reval
    ok, msg = ots.avaliar_wfa(reval.get("wfe_global_pct"),
                              reval.get("wfa_ciclos_positivos"), sistema)
    novo = dict(reval, wfa_ok=ok, wfa_motivo=msg)
    if not ok:
        novo["falhou_em"] = sorted(set((reval.get("falhou_em") or []) + ["wfa"]))
        novo["veredito"] = "REPROVADO"
    return novo


def motivo(reval: dict) -> str:
    if reval.get("wfa_ok") is False and reval.get("wfa_motivo"):
        base = f"WFA: {reval['wfa_motivo']} (ciclos {reval.get('wfa_ciclos_positivos')})"
        if not reval.get("anterior_ok", True):
            base = (f"periodo anterior {reval.get('anterior_lucro')} alem do piso; "
                    + base)
        return base
    if not reval.get("anterior_ok", True):
        return (f"periodo anterior ao treino: {reval.get('anterior_lucro')} "
                f"({reval.get('anterior_trades')} trades) alem do piso")
    if not reval.get("catastrofe_ok", True):
        return f"prejuizo nos 3 anos: {reval.get('tres_anos_lucro')}"
    if reval.get("wfa_ok") is False or "wfa" in (reval.get("falhou_em") or []):
        return (f"WFA: {reval.get('wfa_ciclos_positivos')} ciclos, WFE "
                f"{reval.get('wfe_global_pct')}% abaixo do piso")
    return "revalidacao nao confirmou o campeao"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    print("pasta de dados:", ready_library.TESTER)
    if "MT5_Optimizer2" not in os.environ.get("WRX_MT5_INSTALL_DIR", "") and \
            "4A85BF7B" not in str(ready_library.TESTER):
        print("ATENCAO: nao parece a pasta do CLONE (onde estao os campeoes "
              "reais); confira WRX_MT5_DATA_DIR antes de --aplicar.")
    metricas = ready_library.metricas_do_ledger(ready_library.LEDGER)
    plano = []
    for simbolo, sistema, variante, rotulo in CAMPEOES:
        arq = ready_library.TESTER / f"VALIDADO_{simbolo}_{sistema}_{variante}.set"
        antigo = metricas.get((simbolo, sistema, variante), {})
        reval = rejulgar_wfa(ultimo_da_revalidacao(rotulo), sistema)
        print(f"\n{simbolo} {sistema} {variante}")
        print(f"  arquivo: {arq.name} -> {'EXISTE' if arq.exists() else 'NAO EXISTE'}")
        print(f"  ledger (ultimo): aprovado={antigo.get('aprovado')} "
              f"ret={antigo.get('retencao_oos')} quando={antigo.get('quando')}")
        print(f"  revalidacao: veredito={reval.get('veredito')} "
              f"falhou_em={reval.get('falhou_em')} | {motivo(reval)}")
        if not arq.exists() or not antigo.get("aprovado"):
            print("  -> nada a rebaixar (ja nao e campeao).")
            continue
        plano.append((simbolo, sistema, variante, arq, antigo, reval))
    if args.dry or not plano:
        print("\n(dry-run: nada foi alterado)" if args.dry else "\nnada a fazer")
        return 0

    bak = ready_library.LEDGER.with_name(
        ready_library.LEDGER.name + ".bak_20260921_pre_rebaixar_campeoes")
    if not bak.exists():
        shutil.copy2(ready_library.LEDGER, bak)
    print("\nbackup do ledger:", bak.name)
    for simbolo, sistema, variante, arq, antigo, reval in plano:
        versao = campeoes_arquivo.arquivar_campeao_anterior(
            sistema, simbolo, variante, arq)          # ANTES de mudar o ledger
        destino = arq.with_name(arq.name.replace("VALIDADO_", "REPROVADO_", 1))
        os.replace(arq, destino)
        novo = dict(antigo)
        novo.update({
            "aprovado": False,
            "quando": datetime.now().isoformat(timespec="seconds"),
            "rebaixado": True,
            "rebaixado_de": {"quando": antigo.get("quando"),
                             "retencao_oos": antigo.get("retencao_oos"),
                             "versao_arquivada": versao},
            "motivo_rebaixamento": ("revalidacao 2026-09-21 (medicao corrigida: "
                                    "ALL_FORMULAS do vizinho + WFA cego): "
                                    + motivo(reval)),
            "revalidacao": {k: reval.get(k) for k in (
                "tres_anos_lucro", "tres_anos_trades", "tres_anos_expectancy_r",
                "anterior_lucro", "anterior_trades", "wfa_ciclos_positivos",
                "wfe_global_pct", "falhou_em", "veredito")},
        })
        campanha.registrar(novo)
        print(f"  {simbolo} {sistema} {variante}: arquivado v{versao}, "
              f"{arq.name} -> {destino.name}, linha de reprovacao acrescentada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
