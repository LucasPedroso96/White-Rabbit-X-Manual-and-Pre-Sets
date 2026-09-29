# -*- coding: utf-8 -*-
"""Testa bateria_logica.py SEM MT5: gating dos eixos de booster (so valem com o modo ligado),
eixo sintetico da recuperacao e a leitura dos resultados (categorias de achado).

    python test_bateria_logica.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import bateria_logica as bl

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


def p(atual: str, start: str = "", step: str = "1", stop: str = "", flag: str = "Y") -> list[str]:
    return [atual, start or atual, step, stop or atual, flag]


# template tipico dos sistemas de mercado: pendente e recuperacao DESLIGADAS
BASE = {"EntryOrderType": p("0", "1", "1", "3"), "RecoveryMode": p("0"),
        "EntryMethod": p("0", "0", "1", "6"), "Hedging": p("false", "false", "0", "true")}
# 13_OCO_ROMPIMENTO: a pendente e o sistema (tipo 3 cravado)
OCO = {**BASE, "EntryOrderType": p("3", "3", "1", "3", "N")}

# --- valores_do_eixo ---------------------------------------------------------------
checar("valores: booleano", bl.valores_do_eixo(["false", "false", "0", "true", "Y"], 6), ["false", "true"])
checar("valores: numerico inteiro", bl.valores_do_eixo(["1", "1", "1", "3", "Y"], 6), ["1", "2", "3"])
checar("valores: limita a max_valores", len(bl.valores_do_eixo(["0", "0", "1", "50", "Y"], 5)), 5)

# --- gating dos eixos de booster ------------------------------------------------------
t = bl.travar_para("PendingDistanciaATR", "0.5", BASE)
checar("pendente: distancia liga Limit no template a mercado", t.get("EntryOrderType"), "2")
t = bl.travar_para("PendingDistanciaATR", "0.5", OCO)
checar("pendente: no 13 o OCO cravado nao vira Limit", "EntryOrderType" in t, False)
t = bl.travar_para("MaxMartingaleSteps", "3", BASE)
checar("martingale: passos ligam RecoveryMode=1", t.get("RecoveryMode"), "1")
t = bl.travar_para("DAlembertStep", "0.03", BASE)
checar("dalembert: passo liga modo 2 + Lote Fixo 0.01",
       (t.get("RecoveryMode"), t.get("PositionSizeMode"), t.get("PositionSizeValue")),
       ("2", "2", "0.01"))
com_rec = {**BASE, "RecoveryMode": p("1")}
checar("recuperacao ja ligada no template nao e trocada", "RecoveryMode" in bl.travar_para(
    "MaxMartingaleSteps", "3", com_rec), False)
t = bl.travar_para("ReversalExitMode", "1", BASE)
checar("saida por ordem oposta exige hedge", t.get("Hedging"), "true")
t = bl.travar_para("ReversalExitUseEntryFilters", "true", BASE)
checar("filtros de saida so valem com filtro de entrada ligado", t.get("AtivarFiltroMA"), "true")
t = bl.travar_para("PyramidLevelOnlyInProfit", "true", BASE)
checar("piramide so no lucro: nivel perto e breakeven longe",
       (t.get("DistanciaMinima"), t.get("BreakevenDistancia"), t.get("AtivarBreakeven")),
       ("2.5", "3.0", "true"))
# metodo de entrada: a nuvem do Ichimoku so entra no cruzamento de referencia
t = bl.travar_para("IchimokuUseKumo", "true", {**BASE, "EntryMethod": p("0", "0", "1", "6")})
checar("Kumo com metodo Reversao -> forca metodo 6", t.get("EntryMethod"), "6")
t = bl.travar_para("IchimokuUseKumo", "true", {**BASE, "EntryMethod": p("2", "2", "1", "2", "N")})
checar("Kumo com metodo Referencia nao mexe no metodo", "EntryMethod" in t, False)
# WFO sempre desligado e idioma fixo
checar("WFO desligado em todo passe", bl.travar_para("Trail", "3", BASE)["AtivarWFO"], "false")

# --- leitura dos resultados -------------------------------------------------------------------
def reg(sistema, eixo, valor, trades, saldo, c=None, v=None, recusado=False, motivo=None,
        erros=None, familia="MULTI"):
    c = trades // 2 if c is None else c
    v = trades - c if v is None else v
    return {"familia": familia, "sistema": sistema, "variante": "BOTH_MULTI", "eixo": eixo,
            "valor": valor, "travar": {}, "simbolo": "EURUSD", "inicio": "2026.03.18",
            "fim": "2026.09.14", "trades": trades, "saldo": saldo, "compras": c, "vendas": v,
            "recusado": recusado, "falha_infra": False, "motivo": motivo, "erros": erros or [],
            "abortos": 0, "segundos": 8}


bl._FLAGS[("EURUSD", "01_SLTP", "BOTH_MULTI")] = {"EixoMorto": p("1", "1", "1", "3", "Y"),
                                                   "EixoGuardado": p("1", "1", "1", "3", "N")}
regs = [
    reg("01_SLTP", "__base__", "", 100, 1050.0),
    reg("01_SLTP", "EixoMorto", "1", 100, 1050.0), reg("01_SLTP", "EixoMorto", "2", 100, 1050.0),
    reg("01_SLTP", "EixoGuardado", "1", 100, 1050.0), reg("01_SLTP", "EixoGuardado", "2", 100, 1050.0),
    reg("01_SLTP", "Vivo", "1", 100, 1050.0), reg("01_SLTP", "Vivo", "2", 90, 1010.0),
    reg("01_SLTP", "Mudo", "1", 100, 1000.0), reg("01_SLTP", "Mudo", "2", 100, 900.0, c=100, v=0),
    reg("01_SLTP", "Poucos", "1", 100, 1000.0),
    reg("01_SLTP", "Poucos", "2", 1, 999.0, c=0, v=1),
    reg("01_SLTP", "Zero", "1", 100, 1000.0), reg("01_SLTP", "Zero", "2", 0, 1000.0, c=0, v=0),
    reg("01_SLTP", "Recusa", "1", 100, 1000.0),
    reg("01_SLTP", "Recusa", "2", None, None, c=0, v=0, recusado=True,
        motivo="exit requires bilateral trading"),
    reg("01_SLTP", "Erro", "1", 100, 1000.0, erros=["array out of range"]),
    reg("01_SLTP", "Erro", "2", 90, 1001.0),
]
with tempfile.TemporaryDirectory() as tmp:
    arq = Path(tmp) / "x.jsonl"
    arq.write_text("\n".join(json.dumps(r) for r in regs), encoding="utf-8")
    txt = bl.analisar([arq])
checar("analise: eixo morto Y aparece como SEM_EFEITO [Y]",
       "EixoMorto" in txt and "[Y] 2 valores" in txt, True)
checar("analise: eixo guardado aparece como [N]", "EixoGuardado" in txt and "[N] 2 valores" in txt, True)
checar("analise: eixo que muda o resultado nao e achado", "Vivo" in txt, False)
checar("analise: lado mudo", "LADO_MUDO" in txt and "Mudo" in txt, True)
checar("analise: 1 trade so nao e lado mudo", "Poucos" in txt, False)
checar("analise: valor morto", "VALOR_MORTO" in txt and "Zero" in txt, True)
checar("analise: recusa com o motivo", "RECUSA" in txt and "exit requires bilateral" in txt, True)
checar("analise: erro de runtime", "ERRO" in txt and "array out of range" in txt, True)

# --- estatico nao quebra sem templates ----------------------------------------------------------
checar("SISTEMAS inclui o 13", "13_OCO_ROMPIMENTO" in bl.SISTEMAS, True)
checar("recuperacao sintetica cobre Martingale e D'Alembert", sorted(bl.RECUPERACAO_SINTETICA), ["1", "2"])
checar("D'Alembert sintetico usa Lote Fixo", bl.RECUPERACAO_SINTETICA["2"]["PositionSizeMode"], "2")

if FALHAS:
    print(f"{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  -", f)
    sys.exit(1)
print("bateria_logica: todos os casos passaram")
