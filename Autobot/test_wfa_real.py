# -*- coding: utf-8 -*-
"""Testa as pecas de wfa_real.py que NAO precisam do MT5: leitura de .set,
janelas sequenciais, formula de WFE. Roda em milissegundos.

    python test_wfa_real.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from wfa_real import janelas_sequenciais, ler_valores_set, medir_holdout, wfe

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


def perto(a, b, tol=1e-6) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol


def checar_perto(rotulo: str, obtido, esperado) -> None:
    if not perto(obtido, esperado):
        FALHAS.append(f"{rotulo}: esperado ~{esperado!r}, obtido {obtido!r}")


# --- ler_valores_set: mesmo formato usado em todo o projeto -----------------
tmp = Path(tempfile.mkdtemp())
alvo = tmp / "campeao.set"
alvo.write_text(
    "EntryIndicator=3||3||1||3||N\r\nFast_EMA=12||6||2||24||N\r\n"
    "Hedging=true||true||0||true||N\r\n; comentario\r\n",
    encoding="utf-16")
valores = ler_valores_set(alvo)
checar("ler_valores_set: EntryIndicator", valores["EntryIndicator"], "3")
checar("ler_valores_set: Fast_EMA", valores["Fast_EMA"], "12")
checar("ler_valores_set: bool", valores["Hedging"], "true")
checar("ler_valores_set: comentario ignorado", "comentario" in valores, False)

# --- janelas_sequenciais: sem sobreposicao, contiguas -----------------------
janelas = janelas_sequenciais("2023.01.01", "2023.12.31", ciclos=3,
                              is_dias=22, oos_dias=8)
checar("janelas: 3 ciclos", len(janelas), 3)
is1_ini, is1_fim, oos1_ini, oos1_fim = janelas[0]
checar("janela 1: IS comeca no inicio pedido", is1_ini, "2023.01.01")
is2_ini = janelas[1][0]
# proxima janela comeca exatamente 1 dia depois do fim do OOS anterior --
# sem gap, sem sobreposicao.
from datetime import datetime, timedelta
checar("janela 1->2: contigua, sem gap/overlap",
       datetime.strptime(is2_ini, "%Y.%m.%d"),
       datetime.strptime(oos1_fim, "%Y.%m.%d") + timedelta(days=1))
checar("janela 1: IS dura 22 dias",
       (datetime.strptime(is1_fim, "%Y.%m.%d")
        - datetime.strptime(is1_ini, "%Y.%m.%d")).days + 1, 22)
checar("janela 1: OOS dura 8 dias",
       (datetime.strptime(oos1_fim, "%Y.%m.%d")
        - datetime.strptime(oos1_ini, "%Y.%m.%d")).days + 1, 8)

# --- wfe(): mesma formula do .mq5 (avgProfitOutSample/avgProfitInSample*100)
checar_perto("wfe: IS e OOS iguais por dia -> 100%",
            wfe(lucro_oos=80, dias_oos=8, lucro_is=220, dias_is=22), 100.0)
checar_perto("wfe: OOS metade do ritmo do IS -> 50%",
            wfe(lucro_oos=40, dias_oos=8, lucro_is=220, dias_is=22), 50.0)
checar("wfe: IS nao lucrativo -> None (mesmo criterio do .mq5)",
       wfe(lucro_oos=100, dias_oos=8, lucro_is=-50, dias_is=22), None)
checar("wfe: IS None -> None", wfe(None, 8, 100, 22), None)
checar("wfe: OOS None -> None", wfe(100, 8, None, 22), None)
checar_perto("wfe: OOS negativo da WFE negativa",
            wfe(lucro_oos=-40, dias_oos=8, lucro_is=220, dias_is=22), -50.0)

# --- medir_holdout(): os campos de WFO frescos TEM que vencer os do .set
# entregue -- regressao do bug achado ao vivo, 2026-09-04. O .set ENTREGUE
# sempre sai com AtivarWFO=false forcado (optimize_two_stage.py, WFO e
# andaime, nunca vai pro comprador ligado) e com wfo_customWindowSizeDays/
# wfo_customStepSizePercent/input_end_date da janela ORIGINAL de validacao
# -- nada disso serve pra medir holdout numa janela DIFERENTE. A ordem
# errada (`dict(wfo); .update(travados)`) deixava o .set entregue vencer:
# AtivarWFO acabava False e o passe virava um backtest continuo comum, sem
# holdout nenhum -- exatamente o que aconteceu no primeiro piloto real
# (01_SLTP/EURUSD: "retencao_pct": null, porque a EA so imprime "Out-of-
# Sample Retention" quando AtivarWFO e verdadeiro).
travados_entregues_com_lixo_de_wfo = {
    "EntryIndicator": "2", "Fast_EMA": "9",           # campos normais do campeao
    "AtivarWFO": "false",                             # forcado false na entrega
    "MetodoDeEntradawfo": "0",
    "wfo_customWindowSizeDays": "122",                # janela de OUTRA corrida
    "wfo_customStepSizePercent": "-61",
    "input_end_date": "2026.08.24",                   # data de OUTRA corrida
}
with patch("wfa_real.ots._medir_desempenho") as mock_medir:
    mock_medir.return_value = {"profit": 1.0, "retencao": 50.0}
    medir_holdout(Path("origem.set"), travados_entregues_com_lixo_de_wfo,
                  "EURUSD", "M1", "2023.09.04", "2026.09.04", 500)
params_usados = mock_medir.call_args[0][1]
checar("holdout: AtivarWFO forcado true (nao herda false do .set entregue)",
       params_usados["AtivarWFO"], "true")
checar("holdout: input_end_date bate com `fim` pedido (nao com o do .set velho)",
       params_usados["input_end_date"], "2026.09.04")
checar("holdout: wfo_customWindowSizeDays recalculado (nao herda 122 de outra corrida)",
       params_usados["wfo_customWindowSizeDays"] != "122", True)
checar("holdout: campos normais do campeao ainda passam", params_usados["Fast_EMA"], "9")
checar("holdout: MetodoDeEntradawfo=1 (IS+OOS, nao o 0 do .set entregue)",
       params_usados["MetodoDeEntradawfo"], "1")

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("wfa_real (pecas sem MT5): todos os casos passaram")
