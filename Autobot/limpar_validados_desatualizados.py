# -*- coding: utf-8 -*-
"""Limpa VALIDADO_*.set que sobraram de sweeps ANTERIORES as correcoes de bug
(contaminacao ALL_FORMULAS entre terminais, 20/09; WFA cego por input_end_date
velho, 21/09) e por isso nao merecem mais o nome "VALIDADO_" -- pedido do
dono, 2026-09-24: "faça agora!" apos eu listar as datas.

Nao apaga nada: ARQUIVA primeiro (campeoes_arquivo.arquivar_campeao_anterior,
mesmo mecanismo ja usado e testado em rebaixar_campeoes.py -- rollback
possivel) e so DEPOIS renomeia o arquivo ao vivo. Dois destinos, conforme a
evidencia real que eu tenho pra cada combo:

  REPROVADO_   -- tenho evidencia NEGATIVA real e recente (revalidacao ou
                  reproval explicito) contra esses parametros especificos.
  DESATUALIZADO_ -- nao tenho evidencia (nem a favor nem contra) desses
                  parametros especificos sob o pipeline corrigido; o arquivo
                  so existe porque um sweep de ANTES das correcoes aprovou.
                  Precisa refazer pra virar VALIDADO_ de verdade.

Roda uma vez por instalacao (passe WRX_MT5_DATA_DIR/WRX_MT5_INSTALL_DIR do
alvo antes de chamar, como sempre).
"""
from __future__ import annotations

import argparse
import os
import sys

import campeoes_arquivo
import ready_library

# ACHADO no dry-run (2026-09-24): o mesmo combo pode ter arquivos DIFERENTES
# em cada instalacao (XAUUSD/11_SIGNAL_ONLY/BUY_MULTI: CLONE = 16/09,
# pre-correcoes; ORIGINAL = 23/09, formula 10 sob o pipeline JA corrigido --
# esse e bom, nao mexer). "instalacao" filtra a entrada: None = as duas.
INSTALACAO_CLONE = "4A85BF7BB91E709E95066E8432253C88"
INSTALACAO_ORIGINAL = "D2A36B4A61A508797F5C460B1F34DC5D"

# (simbolo, sistema, variante, destino, motivo, instalacao_ou_None)
ALVOS = [
    ("EURUSD", "01_SLTP", "BUY_MULTI", "REPROVADO",
     "revalidado 2026-09-22 com a medicao corrigida: -986 em 3 anos "
     "continuos e -989 no periodo anterior ao treino (catastrofe nos dois "
     "gates). Formula de producao ja revertida (14 -> 12).", None),
    ("AUDNZD", "07_GRID_SEPARATE", "BUY_MULTI", "DESATUALIZADO",
     "arquivo de 18/09, ANTES da correcao da contaminacao ALL_FORMULAS "
     "(20/09) e do WFA cego (21/09) -- parametros nunca revalidados sob o "
     "pipeline corrigido. A formula 10 deste sistema TEM evidencia positiva "
     "(revalidacao: WFA 3/4 WFE 12-21%), mas em parametros diferentes; "
     "refazer a campanha oficial pra gerar um VALIDADO_ de verdade.", None),
    ("XAUUSD", "12_GRID_INVERSO", "BUY_MULTI", "DESATUALIZADO",
     "arquivo de 14/09, o mais antigo de todos -- nunca revalidado sob "
     "nenhuma das correcoes (contaminacao ALL_FORMULAS, WFA cego, piso do "
     "WFA). Sistema fora do escopo desta rodada de recalibracao.", None),
    # SO no CLONE (16/09, pre-correcoes). O do ORIGINAL (23/09, formula 10,
    # ja sob o pipeline corrigido) e um resultado BOM -- fica como VALIDADO_,
    # nao mexe (so nao bate com a formula 9 hoje aplicada; ver nota a parte).
    ("XAUUSD", "11_SIGNAL_ONLY", "BUY_MULTI", "DESATUALIZADO",
     "arquivo de 16/09 -- ANTES de todas as correcoes. Superado por "
     "resultado fresco (23/09, formula 10, sob pipeline corrigido) que "
     "existe na OUTRA instalacao (ORIGINAL) -- esse fica intocado.",
     INSTALACAO_CLONE),
    ("GBPUSD", "02_SLTP_ORGANIC", "BUY_MULTI", "DESATUALIZADO",
     "arquivo de 20/09 20:06, ANTES da correcao do WFA cego (21/09) -- "
     "variante BUY_MULTI nunca foi revalidada separadamente (so a variante "
     "BOTH_MULTI, o campeao real, foi revalidada e rebaixada em 2026-09-21).",
     None),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    print("pasta de dados:", ready_library.TESTER)
    for simbolo, sistema, variante, destino, motivo, so_instalacao in ALVOS:
        print(f"\n{simbolo} {sistema} {variante}")
        if so_instalacao and so_instalacao not in str(ready_library.TESTER):
            print(f"  (entrada e so pra outra instalacao -- pulando aqui)")
            continue
        arq = ready_library.TESTER / f"VALIDADO_{simbolo}_{sistema}_{variante}.set"
        if not arq.exists():
            print(f"  {arq.name}: nao existe nesta instalacao -- nada a fazer")
            continue
        novo = arq.with_name(f"{destino}_{arq.name[len('VALIDADO_'):]}")
        print(f"  {arq.name} -> {novo.name}  ({destino})")
        print(f"  motivo: {motivo}")
        if args.dry:
            continue
        versao = campeoes_arquivo.arquivar_campeao_anterior(
            sistema, simbolo, variante, arq)
        os.replace(arq, novo)
        print(f"  arquivado v{versao}, renomeado.")
    if args.dry:
        print("\n(dry-run: nada foi alterado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
