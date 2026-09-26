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
  CALIBRACAO_  -- (2026-09-25) saida de um SWEEP de formula
                  (sweep_formulas.py), nao da campanha oficial. O sweep grava
                  o mesmo nome VALIDADO_ quando os gates passam, mas NAO
                  escreve no ledger -- o dashboard casava o arquivo do sweep
                  com a linha do ledger de OUTRA corrida (a oficial) e
                  mostrava as metricas dela como se fossem dele. Os
                  parametros podem ate ser bons; so nao sao o campeao.

Roda uma vez por instalacao (passe WRX_MT5_DATA_DIR/WRX_MT5_INSTALL_DIR do
alvo antes de chamar, como sempre).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

import campanha
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
    # ---- 2026-09-25 (dono: "limpeza no dashboard se tiver campeao teste").
    # O ORIGINAL guardava dois VALIDADO_ que eram saida de SWEEP, e o
    # dashboard (que so lia o ORIGINAL) os exibia como campeoes com as
    # metricas da campanha oficial do CLONE. Estas entradas levam um 7o
    # campo: "data" = data de modificacao esperada do arquivo (sem ela bater
    # nao mexe -- um VALIDADO_ legitimo futuro com o mesmo nome fica a
    # salvo de uma re-execucao) e "rebaixar_ledger" = acrescentar linha
    # aprovado=false (so onde o ledger ainda diz "aprovado" pra ESTE set).
    ("XAUUSD", "04_SLTP_TRAIL", "BUY_MULTI", "CALIBRACAO",
     "sweep da formula 12 (SystemRobustness), 20/09 09:06, ANTES da "
     "correcao da contaminacao ALL_FORMULAS e do WFA cego -- parametros "
     "de entrada diferentes do oficial. O campeao oficial (formula 11, "
     "21/09) mora no CLONE e nao e tocado. "
     "Revalidacao da f12: 3a +17010 em 2665 trades (+0.063R), WFA 3/4 "
     "WFE 38% -- edge fraco, bem abaixo da f11.",
     INSTALACAO_ORIGINAL, {"data": "2026-09-20"}),
    ("XAUUSD", "11_SIGNAL_ONLY", "BUY_MULTI", "CALIBRACAO",
     "sweep da formula 10 (ResilienceToDrawdown), 23/09 12:00, ja sob o "
     "pipeline corrigido (3a +1429/576 tr, anterior +807, WFA 4/4 WFE 47%). "
     "Mas a campanha OFICIAL do 11_SIGNAL_ONLY XAUUSD BUY foi REPROVADA "
     "(stop de emergencia por DD) e o dashboard mostrava as metricas "
     "dessa reprovacao ao lado deste arquivo. Candidato a refazer na "
     "campanha oficial com a formula 10; ate la nao e campeao.",
     INSTALACAO_ORIGINAL, {"data": "2026-09-23"}),
    ("GBPUSD", "02_SLTP_ORGANIC", "BOTH_BOLLINGER", "DESATUALIZADO",
     "arquivo de 13/09, ANTES de todas as correcoes (contaminacao "
     "ALL_FORMULAS 20/09, WFA cego 21/09, piso do WFA) -- mesmo criterio "
     "da limpeza de 24/09, que so olhou 14/09-20/09 e deixou este de fora. "
     "WFE 116% e WFA 4/4 foram medidos com a medicao contaminada. Nunca "
     "revalidado.",
     INSTALACAO_CLONE, {"data": "2026-09-13", "rebaixar_ledger": True}),
]


def rebaixar_no_ledger(simbolo: str, sistema: str, variante: str,
                       versao: int | None, motivo: str) -> None:
    """Mesmo formato de rebaixar_campeoes.py: linha NOVA (append-only, com o
    lock do ledger via campanha.registrar) -- nunca reescreve a antiga."""
    antigo = ready_library.metricas_do_ledger(ready_library.LEDGER).get(
        (simbolo.replace(".", "_"), sistema, variante), {})
    if not antigo.get("aprovado"):
        print("  ledger ja nao diz 'aprovado' -- nenhuma linha acrescentada.")
        return
    novo = dict(antigo)
    novo.update({
        "aprovado": False,
        "quando": datetime.now().isoformat(timespec="seconds"),
        "rebaixado": True,
        "rebaixado_de": {"quando": antigo.get("quando"),
                         "retencao_oos": antigo.get("retencao_oos"),
                         "versao_arquivada": versao},
        "motivo_rebaixamento": "limpeza 2026-09-25: " + motivo,
    })
    campanha.registrar(novo)
    print("  linha de rebaixamento acrescentada no ledger.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    print("pasta de dados:", ready_library.TESTER)
    for simbolo, sistema, variante, destino, motivo, so_instalacao, *resto in ALVOS:
        extra = resto[0] if resto else {}
        print(f"\n{simbolo} {sistema} {variante}")
        if so_instalacao and so_instalacao not in str(ready_library.TESTER):
            print(f"  (entrada e so pra outra instalacao -- pulando aqui)")
            continue
        arq = ready_library.TESTER / f"VALIDADO_{simbolo}_{sistema}_{variante}.set"
        if not arq.exists():
            print(f"  {arq.name}: nao existe nesta instalacao -- nada a fazer")
            continue
        data_arq = datetime.fromtimestamp(arq.stat().st_mtime).date().isoformat()
        if extra.get("data") and data_arq != extra["data"]:
            print(f"  {arq.name}: data {data_arq} != esperada {extra['data']} "
                  "-- e outro arquivo, nao mexo.")
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
        if extra.get("rebaixar_ledger"):
            rebaixar_no_ledger(simbolo, sistema, variante, versao, motivo)
    if args.dry:
        print("\n(dry-run: nada foi alterado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
