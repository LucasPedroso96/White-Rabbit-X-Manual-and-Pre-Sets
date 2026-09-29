# -*- coding: utf-8 -*-
"""Testa as conferencias de testar_sistemas.py SEM MT5: relatorios sinteticos com
resposta conhecida -- inclusive sistemas com comportamento ERRADO de proposito,
pra provar que o conferidor reprova o que tem que reprovar.

    python test_testar_sistemas.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta

import testar_pendentes as tp
import testar_sistemas as ts

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


T0 = datetime(2026, 8, 3, 8, 0, 0)
_seq = [0]


def _n() -> int:
    _seq[0] += 1
    return _seq[0]


def ordem(t, tipo, vol, sl, tp_, cmt="04-MUL Buy/RFixo", estado="filled"):
    n = _n()
    return {"abertura": t, "ordem": n, "simbolo": "XAUUSD", "tipo": tipo, "vol": vol,
            "vol_exec": vol, "preco": 0.0, "sl": sl, "tp": tp_, "fim": t, "estado": estado,
            "comentario": cmt}


def deal(t, tipo, direcao, vol, preco, ordem_n, lucro=0.0, cmt="", swap=0.0):
    return {"t": t, "deal": _n(), "simbolo": "XAUUSD", "tipo": tipo, "direcao": direcao,
            "vol": vol, "preco": preco, "ordem": ordem_n, "comissao": 0.0, "swap": swap,
            "lucro": lucro, "saldo": 10000.0, "comentario": cmt}


def posicao(t_in, lado, vol, preco, sl, tp_, t_out, preco_out, lucro, cmt_saida):
    """(ordem, [deal_in, deal_out]) de uma posicao completa."""
    tipo_in = "buy" if lado == "buy" else "sell"
    tipo_out = "sell" if lado == "buy" else "buy"
    o = ordem(t_in, tipo_in, vol, sl, tp_)
    return o, [deal(t_in, tipo_in, "in", vol, preco, o["ordem"]),
               deal(t_out, tipo_out, "out", vol, preco_out, _n(), lucro, cmt_saida)]


INFO = {"vol_step": 0.01, "vol_min": 0.01, "vol_max": 100.0, "contrato": 100.0, "tick": 0.01}

# --- classe de saida ----------------------------------------------------------
checar("classe: sl", ts.classe_saida("sl 4046.61"), "sl")
checar("classe: tp", ts.classe_saida("tp 4106.75"), "tp")
checar("classe: fim do teste", ts.classe_saida("end of test"), "fim")
checar("classe: reversao", ts.classe_saida("(04-MUL Indicator reversal exi)"), "reversao")
checar("classe: cesta", ts.classe_saida("(07-MUL SELL grid basket targe)"), "cesta")
checar("classe: piramide", ts.classe_saida("(12-MUL BUY pyramid trailing e)"), "piramide")
checar("classe: vazio (take organico)", ts.classe_saida(""), "vazio")
checar("classe: desconhecida", ts.classe_saida("qualquer coisa"), "outro")

# --- pareamento FIFO por lado e concorrencia -------------------------------------
o1, d1 = posicao(T0, "buy", 0.1, 4000.0, 3990.0, 4020.0, T0 + timedelta(hours=1), 4020.0, 200.0,
                 "tp 4020.00")
o2, d2 = posicao(T0 + timedelta(hours=2), "sell", 0.1, 4000.0, 4010.0, 3980.0,
                 T0 + timedelta(hours=3), 4010.0, -100.0, "sl 4010.00")
fech, abertas = ts.operacoes([o1, o2], d1 + d2)
checar("pareamento: 2 fechadas, 0 abertas", (len(fech), len(abertas)), (2, 0))
checar("pareamento: classe e lucro", (fech[0]["classe"], fech[0]["net"]), ("tp", 200.0))
checar("pareamento: venda fecha compra", (fech[0]["lado"], fech[1]["lado"]), ("buy", "sell"))
checar("concorrencia: 1 por lado", ts.concorrencia_maxima(fech, abertas), {"buy": 1, "sell": 1})
o3, d3 = posicao(T0, "buy", 0.1, 4000.0, 3990.0, 0.0, T0 + timedelta(hours=5), 4001.0, 10.0, "sl 3995")
o4, d4 = posicao(T0 + timedelta(minutes=10), "buy", 0.1, 3999.0, 3990.0, 0.0,
                 T0 + timedelta(hours=6), 4002.0, 30.0, "sl 3996")
fech2, ab2 = ts.operacoes([o3, o4], d3 + d4)
checar("concorrencia: 2 pernas do mesmo lado", ts.concorrencia_maxima(fech2, ab2)["buy"], 2)

# --- estado da recuperacao (ApplyRecoveryOperation) -----------------------------------
def op(net, vol=0.1):
    return {"net": net, "vol": vol}


checar("estado: duas perdas", ts.estado_recuperacao([op(-10), op(-20)], 3), (30.0, 2, False))
checar("estado: ganho parcial abate a divida",
       ts.estado_recuperacao([op(-10), op(4)], 3), (6.0, 0, False))
checar("estado: ganho maior zera o ciclo", ts.estado_recuperacao([op(-10), op(15)], 3),
       (0.0, 0, False))
checar("estado: 4 perdas com teto 3 forca a base e apaga a divida",
       ts.estado_recuperacao([op(-1)] * 4, 3), (0.0, 0, True))
checar("estado: a operacao seguinte ao reset consome o forcar_base",
       ts.estado_recuperacao([op(-1)] * 4 + [op(5)], 3), (0.0, 0, False))
checar("estado: ganho sem divida nao muda nada", ts.estado_recuperacao([op(5), op(3)], 3),
       (0.0, 0, False))
checar("estado: sem teto de passos a divida so cresce",
       ts.estado_recuperacao([op(-1)] * 6, 0), (6.0, 6, False))
checar("dalembert: perdas e ganhos", [ts.passos_dalembert([op(-1), op(-1), op(1), op(-1)][:i], 0)
                                       for i in range(1, 5)], [1, 2, 1, 2])
checar("dalembert: teto de passos", ts.passos_dalembert([op(-1)] * 5, 3), 3)
checar("dalembert: ganho no zero fica no zero", ts.passos_dalembert([op(1), op(1)], 3), 0)

# --- lotes esperados --------------------------------------------------------------------
def p_entrada(preco, sl, tp_, vol=0.1, lado="buy"):
    return {"lado": lado, "preco": preco, "sl": sl, "tp": tp_, "vol": vol, "ordem": 1,
            "t_in": T0}


PR = {"PositionSizeMode": "3", "PositionSizeValue": "1", "CapitalBaseR": "10000",
      "MaxRiscoTradeR": "3", "RecoveryMode": "1", "MaxMartingaleSteps": "0", "Multiplicador": "1"}
# R = 100; SL a 10 (1000 por lote) -> base 0.10; TP a 10
sem_div, det = ts.lotes_possiveis(p_entrada(4000, 3990, 4010), [], [], PR, INFO)
checar("martingale R: sem divida = lote base", sem_div, [(0.1, 0.1)])
checar("martingale R: divida 100 (1R) e TP=SL -> ainda a base",
       ts.lotes_possiveis(p_entrada(4000, 3990, 4010), [op(-100)], [op(-100)], PR, INFO)[0],
       [(0.1, 0.1)])
checar("martingale R: divida 250 -> 0.25",
       ts.lotes_possiveis(p_entrada(4000, 3990, 4010), [op(-250)], [op(-250)], PR, INFO)[0],
       [(0.25, 0.25)])
checar("martingale R: teto de 3R (0.30)",
       ts.lotes_possiveis(p_entrada(4000, 3990, 4010), [op(-400)], [op(-400)], PR, INFO)[0],
       [(0.3, 0.3)])
checar("martingale R sem TP: divida sobre o SL",
       ts.lotes_possiveis(p_entrada(4000, 3990, 0.0), [op(-200)], [op(-200)], PR, INFO)[0],
       [(0.2, 0.2)])
checar("martingale R com multiplicador 2",
       ts.lotes_possiveis(p_entrada(4000, 3990, 4010), [op(-100)], [op(-100)],
                          {**PR, "Multiplicador": "2"}, INFO)[0], [(0.2, 0.2)])
checar("martingale R: teto de passos forca a base",
       ts.lotes_possiveis(p_entrada(4000, 3990, 4010), [op(-100)] * 4, [op(-100)] * 4,
                          {**PR, "MaxMartingaleSteps": "3"}, INFO)[0], [(0.1, 0.1)])
checar("martingale R organico: qualquer lote entre a base e o teto",
       ts.lotes_possiveis(p_entrada(4000, 3990, 4010), [op(-400)], [op(-400)], PR, INFO,
                          estrito=False)[0], [(0.1, 0.3)])
checar("op fechada no mesmo segundo da entrada: duas hipoteses",
       ts.lotes_possiveis(p_entrada(4000, 3990, 4010), [], [op(-250)], PR, INFO)[0],
       [(0.1, 0.1), (0.25, 0.25)])
PL = {"PositionSizeMode": "2", "PositionSizeValue": "0.01", "RecoveryMode": "1",
      "MaxMartingaleSteps": "3", "Multiplicador": "2"}
checar("martingale lote fixo: sem perda = base",
       ts.lotes_possiveis(p_entrada(4000, 0, 0, 0.01), [op(5, 0.01)], [op(5, 0.01)], PL, INFO)[0],
       [(0.01, 0.01)])
checar("martingale lote fixo: apos perda, ultimo lote x multiplicador",
       ts.lotes_possiveis(p_entrada(4000, 0, 0, 0.02), [op(-5, 0.01)], [op(-5, 0.01)], PL, INFO)[0],
       [(0.02, 0.02)])
checar("martingale lote fixo: segunda perda dobra de novo",
       ts.lotes_possiveis(p_entrada(4000, 0, 0), [op(-5, 0.01), op(-5, 0.02)],
                          [op(-5, 0.01), op(-5, 0.02)], PL, INFO)[0], [(0.04, 0.04)])
PD = {"PositionSizeMode": "2", "PositionSizeValue": "0.01", "RecoveryMode": "2",
      "DAlembertStep": "0.01", "MaxMartingaleSteps": "3"}
checar("dalembert: duas perdas -> base + 2 passos",
       ts.lotes_possiveis(p_entrada(4000, 0, 0), [op(-1), op(-1)], [op(-1), op(-1)], PD, INFO)[0],
       [(0.03, 0.03)])
checar("dalembert: ganho volta um passo",
       ts.lotes_possiveis(p_entrada(4000, 0, 0), [op(-1), op(-1), op(1)],
                          [op(-1), op(-1), op(1)], PD, INFO)[0], [(0.02, 0.02)])

# --- checar_recuperacao ponta a ponta: D'Alembert com lotes CERTOS e ERRADO -----------------
def montar_dalembert(lotes: list[float], lucros: list[float]):
    ordens, deals = [], []
    for i, (v, lucro) in enumerate(zip(lotes, lucros)):
        t = T0 + timedelta(hours=2 * i)
        o, d = posicao(t, "buy", v, 4000.0, 0.0, 0.0, t + timedelta(hours=1), 4000.0, lucro,
                       "(11-MUL Indicator reversal exi)")
        ordens.append(o)
        deals += d
    return ordens, deals


lucros = [-5, -5, 3, -5, 4, 4]
certos = [0.01, 0.02, 0.03, 0.02, 0.03, 0.02]
o, d = montar_dalembert(certos, lucros)
r = tp.Resultado()
ts.checar_recuperacao("11_SIGNAL_ONLY", {**PD, "MaxMartingaleSteps": "0"}, o, d, INFO, r)
checar("recuperacao D'Alembert correta: sem falha", r.falhas, [])
checar("recuperacao D'Alembert correta: 6 conferidas, lote subiu", (r.metricas["conferidas"],
       r.metricas["lote_acima_da_base"] > 0), (6, True))
errados = list(certos)
errados[3] = 0.05
o, d = montar_dalembert(errados, lucros)
r = tp.Resultado()
ts.checar_recuperacao("11_SIGNAL_ONLY", {**PD, "MaxMartingaleSteps": "0"}, o, d, INFO, r)
checar("recuperacao D'Alembert com lote errado reprova", len(r.falhas), 1)
checar("recuperacao: mensagem cita o lote", "lote" in r.falhas[0], True)
chatos = [0.01] * 6                       # EA que ignorou a recuperacao
o, d = montar_dalembert(chatos, lucros)
r = tp.Resultado()
ts.checar_recuperacao("11_SIGNAL_ONLY", {**PD, "MaxMartingaleSteps": "0"}, o, d, INFO, r)
checar("D'Alembert que nunca sobe o lote reprova", len(r.falhas), 1)

# --- assinatura -----------------------------------------------------------------------------
def montar(sistema_spec: dict, n: int = 20, lado="buy"):
    """n posicoes; spec: sl, tp (0 = sem), classes de saida em rodizio."""
    ordens, deals = [], []
    classes = sistema_spec["classes"]
    for i in range(n):
        t = T0 + timedelta(hours=3 * i)
        sinal = 1 if lado == "buy" else -1
        sl = 0.0 if not sistema_spec["sl"] else 4000.0 - sinal * 10
        tp_ = 0.0 if not sistema_spec["tp"] else 4000.0 + sinal * 15
        cls = classes[i % len(classes)]
        cmt = {"sl": "sl 3990.00", "tp": "tp 4015.00", "reversao": "(04-MUL Indicator reversal exi)",
               "fim": "end of test", "cesta": "(07-MUL BUY grid basket target)",
               "piramide": "(12-MUL BUY pyramid trailing e)", "": ""}[cls]
        preco_out = 4000.0 + sinal * (
            {"sl": -10 if i % 2 else 8, "tp": 15}.get(cls, 3))     # metade dos SL sai no lucro
        o, d = posicao(t, lado, 0.1, 4000.0, sl, tp_, t + timedelta(hours=1), preco_out,
                       sinal * (preco_out - 4000.0) * 10, cmt)
        ordens.append(o)
        deals += d
    return ordens, deals


def assina(sistema, variante, spec, n=20, lado="buy"):
    o, d = montar(spec, n, lado)
    r = tp.Resultado()
    ts.checar_assinatura(sistema, variante, o, d, INFO, r)
    return r


r = assina("04_SLTP_TRAIL", "BUY_MULTI", {"sl": True, "tp": True, "classes": ["sl", "tp"]})
checar("04 correto: sem falha", r.falhas, [])
checar("04 correto: sl arrastado detectado", r.metricas["sl_categorias"].get("trail", 0) > 0, True)
r = assina("03_TRAIL_ONLY", "BUY_MULTI", {"sl": True, "tp": True, "classes": ["sl"]})
checar("03 com TP nas ordens reprova", any("[tp]" in f for f in r.falhas), True)
r = assina("03_TRAIL_ONLY", "BUY_MULTI", {"sl": True, "tp": False, "classes": ["sl", "tp"]})
checar("03 com saida por TP reprova", any("[saidas]" in f for f in r.falhas), True)
r = assina("03_TRAIL_ONLY", "BUY_MULTI", {"sl": True, "tp": False, "classes": ["sl"]})
checar("03 correto: sem falha", r.falhas, [])
r = assina("11_SIGNAL_ONLY", "BUY_MULTI", {"sl": True, "tp": False, "classes": ["reversao"]})
checar("11 com SL nas ordens reprova", any("[sl]" in f for f in r.falhas), True)
r = assina("11_SIGNAL_ONLY", "BUY_MULTI", {"sl": False, "tp": False, "classes": ["reversao", "fim"]})
checar("11 correto: sem falha", r.falhas, [])
r = assina("11_SIGNAL_ONLY", "BUY_MULTI", {"sl": False, "tp": False, "classes": ["fim"]})
checar("11 sem nenhuma saida por reversao reprova", any("[saidas]" in f for f in r.falhas), True)
r = assina("06_REVERSAL_EXIT", "BUY_MULTI", {"sl": True, "tp": False, "classes": ["reversao", "sl"]})
checar("06 correto: sem falha", r.falhas, [])
r = assina("04_SLTP_TRAIL", "SELL_MULTI", {"sl": True, "tp": True, "classes": ["sl", "tp"]}, lado="buy")
checar("arquivo SELL que compra reprova", any("[lado]" in f for f in r.falhas), True)
r = assina("04_SLTP_TRAIL", "BUY_MULTI", {"sl": True, "tp": True, "classes": ["sl", "tp"]}, lado="sell")
checar("arquivo BUY que vende reprova", any("[lado]" in f for f in r.falhas), True)
r = assina("01_SLTP", "BUY_MULTI", {"sl": True, "tp": True, "classes": ["sl", "tp", "reversao"]})
checar("01 com saida por reversao reprova", any("[saidas]" in f for f in r.falhas), True)
r = assina("07_GRID_SEPARATE", "BUY_MULTI", {"sl": False, "tp": False, "classes": ["cesta"]})
checar("07: grade que nunca abre 2 pernas so avisa",
       (r.falhas, any("[grade]" in a for a in r.avisos)), ([], True))
r = assina("04_SLTP_TRAIL", "BUY_MULTI", {"sl": True, "tp": True, "classes": ["tp"]}, n=0)
checar("zero trades: so aviso", (r.falhas, len(r.avisos)), ([], 1))
# --- stops x flags do set (inicial / breakeven / arrastado) ---------------------------------
def com_saidas_sl(ratios: list[float], sl_dist=10.0):
    """Posicoes compradas que fecharam por SL em `ratio` x distancia do SL inicial."""
    ordens, deals = [], []
    for i, rt in enumerate(ratios):
        t = T0 + timedelta(hours=3 * i)
        out = 4000.0 + rt * sl_dist
        o, d = posicao(t, "buy", 0.1, 4000.0, 4000.0 - sl_dist, 4015.0, t + timedelta(hours=1), out,
                       (out - 4000.0) * 10, "sl %.2f" % out)
        ordens.append(o)
        deals += d
    return ordens, deals


def stops(sistema, ratios, **flags):
    o, d = com_saidas_sl(ratios)
    r = tp.Resultado()
    params = {"AtivarStop": "true", "AtivarTake": "true", **flags}
    ts.checar_assinatura(sistema, "BUY_MULTI", o, d, INFO, r, params)
    return r


checar("classe_sl: inicial / be / trail", [
    ts.classe_sl({"preco": 100.0, "sl": 90.0, "preco_out": po, "lado": "buy"})
    for po in (90.0, 89.8, 100.0, 99.8, 95.0, 104.0)],
    ["inicial", "inicial", "be", "be", "trail", "trail"])
checar("classe_sl: venda espelha",
       ts.classe_sl({"preco": 100.0, "sl": 110.0, "preco_out": 96.0, "lado": "sell"}), "trail")
mistura = [-1.0] * 6 + [0.0] * 5 + [0.5] * 6 + [1.5]
r = stops("04_SLTP_TRAIL", mistura, AtivarBreakeven="true", AtivarTrailATR="true")
checar("04 com BE e trailing ligados e ambos aparecendo: limpo", (r.falhas, r.avisos), ([], []))
r = stops("03_TRAIL_ONLY", mistura, AtivarBreakeven="false", AtivarTrailATR="true",
          AtivarTake="false")
checar("BE desligado mas 5 saidas no preco de entrada reprova",
       any("[breakeven]" in f for f in r.falhas), True)
r = stops("01_SLTP", mistura, AtivarBreakeven="true", AtivarTrailATR="false")
checar("trailing desligado mas stops arrastados reprova", any("[trailing]" in f for f in r.falhas), True)
r = stops("01_SLTP", [-1.0] * 6 + [0.0] * 2, AtivarBreakeven="false", AtivarTrailATR="false")
checar("nem BE nem trailing e o stop mexeu reprova", any("[stop]" in f for f in r.falhas), True)
r = stops("01_SLTP", [-1.0] * 20, AtivarBreakeven="true", AtivarTrailATR="false")
checar("BE ligado e 20 saidas sem nenhum BE so avisa",
       (r.falhas, any("[breakeven]" in a for a in r.avisos)), ([], True))
r = stops("04_SLTP_TRAIL", [-1.0] * 10 + [0.0] * 10, AtivarBreakeven="true", AtivarTrailATR="true")
checar("trailing ligado e nenhuma saida arrastada so avisa",
       (r.falhas, any("[trailing]" in a for a in r.avisos)), ([], True))
r = stops("04_SLTP_TRAIL", mistura, AtivarStop="false", AtivarBreakeven="true", AtivarTrailATR="true")
checar("template com AtivarStop=false num sistema com SL reprova",
       any("[template]" in f for f in r.falhas), True)
r = stops("03_TRAIL_ONLY", mistura, AtivarTake="true", AtivarBreakeven="true", AtivarTrailATR="true")
checar("template com AtivarTake=true no 03 (sem TP) reprova",
       any("[template]" in f for f in r.falhas), True)

# SL com stop invertido (ordem torta) reprova
o, d = montar({"sl": True, "tp": True, "classes": ["sl", "tp"]}, 10)
for x in o:
    x["sl"] = 4010.0
r = tp.Resultado()
ts.checar_assinatura("04_SLTP_TRAIL", "BUY_MULTI", o, d, INFO, r)
checar("SL do lado errado reprova", any("[lado_sl_tp]" in f for f in r.falhas), True)

# --- catalogo -------------------------------------------------------------------------------
cat = ts.catalogo()
nomes = [c.nome for c in cat]
checar("catalogo: nomes unicos", len(nomes), len(set(nomes)))
s1 = [c for c in cat if c.grupo == "s1"]
checar("catalogo S1: 9 sistemas x 12 arquivos + 13 so BOTH_MULTI", len(s1), 9 * 12 + 1)
checar("catalogo S1: todos os sistemas", {c.sistema for c in s1}, set(ts.SISTEMAS_S1))
checar("catalogo S1: 13 so no BOTH_MULTI",
       {c.variante for c in s1 if c.sistema == "13_OCO_ROMPIMENTO"}, {"BOTH_MULTI"})
s2 = [c for c in cat if c.grupo == "s2"]
checar("catalogo S2: Martingale e D'Alembert",
       {c.sobrepor["RecoveryMode"] for c in s2}, {"1", "2"})
checar("catalogo S2: D'Alembert sempre em Lote Fixo",
       all(c.sobrepor.get("PositionSizeMode") == "2" for c in s2
           if c.sobrepor["RecoveryMode"] == "2"), True)
checar("catalogo S2: so sistemas que a EA aceita com recuperacao",
       {c.sistema for c in s2} <= {"01_SLTP", "02_SLTP_ORGANIC", "03_TRAIL_ONLY", "04_SLTP_TRAIL",
                                   "05_BE_TRAIL", "06_REVERSAL_EXIT", "11_SIGNAL_ONLY"}, True)
checar("catalogo: modelo OHLC (rapido)", {c.modelo for c in cat}, {1})
checar("catalogo: sistemas do S1 = sistemas do gerador",
       set(ts.ASSINATURA) == set(ts.SISTEMAS_S1), True)

if FALHAS:
    print(f"{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  -", f)
    sys.exit(1)
print("testar_sistemas: todos os casos passaram")
