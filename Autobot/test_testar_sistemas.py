# -*- coding: utf-8 -*-
"""Testa as conferencias de testar_sistemas.py SEM MT5: relatorios sinteticos com
resposta conhecida -- inclusive sistemas com comportamento ERRADO de proposito,
pra provar que o conferidor reprova o que tem que reprovar.

    python test_testar_sistemas.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

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

# --- S3: travas de risco da conta ------------------------------------------------------------
D1 = datetime(2026, 8, 3)          # segunda


def pos_dia(dia_offset, h_in, h_out, lucro, cmt="sl 3990.00", lado="buy"):
    t_in = D1 + timedelta(days=dia_offset, hours=h_in)
    t_out = D1 + timedelta(days=dia_offset, hours=h_out)
    return posicao(t_in, lado, 0.1, 4000.0, 3990.0, 4020.0, t_out, 4000.0 + lucro / 10.0, lucro, cmt)


def montar_dias(posicoes):
    ordens, deals = [], []
    for o, d in posicoes:
        ordens.append(o)
        deals += d
    return ordens, deals


# dia 0: perde 100 (1%) as 10h e ENTRA de novo as 12h (violacao com limite de 0.5%)
# dia 1: perde so 30 (0.3%) e entra depois (permitido)
# dia 2: perde 100 as 9h e nao entra mais (correto)
posicoes = [pos_dia(0, 8, 10, -100.0), pos_dia(0, 12, 13, 50.0),
            pos_dia(1, 8, 9, -30.0), pos_dia(1, 10, 11, 40.0),
            pos_dia(2, 8, 9, -100.0), pos_dia(3, 8, 9, 20.0), pos_dia(4, 8, 9, 20.0)]
o, d = montar_dias(posicoes)
fech, ab = ts.operacoes(o, d)
dias, viol = ts.violacoes_trava_diaria(fech, fech + ab, 10000.0, 0.5)
checar("trava diaria: 2 dias estouraram, 1 entrada depois do estouro", (dias, viol), (2, 1))
dias, viol = ts.violacoes_trava_diaria(fech, fech + ab, 10000.0, 5.0)
checar("trava diaria com limite folgado (5%): nada estoura", (dias, viol), (0, 0))
# dia que comeca com posicao aberta e pulado (a ancora inclui flutuante)
noturna = [pos_dia(0, 20, 30, -100.0), pos_dia(1, 12, 13, 10.0)]     # fecha as 06h do dia 1
o, d = montar_dias(noturna)
fech, ab = ts.operacoes(o, d)
checar("trava diaria: dia que herda posicao aberta e pulado",
       ts.violacoes_trava_diaria(fech, fech + ab, 10000.0, 0.5), (0, 0))
# trava total (permanente): 3 perdas de 100 num deposito de 10000 = 3%
perdas = [pos_dia(0, 8, 9, -100.0), pos_dia(1, 8, 9, -100.0), pos_dia(2, 8, 9, -100.0),
          pos_dia(3, 8, 9, 20.0), pos_dia(4, 8, 9, 20.0)]
o, d = montar_dias(perdas)
fech, ab = ts.operacoes(o, d)
quando, viol = ts.violacoes_trava_total(fech, fech + ab, 10000.0, 3.0)
checar("trava total: rompe na 3a perda e ha 2 entradas depois", (quando, viol),
       (D1 + timedelta(days=2, hours=9), 2))
checar("trava total: limite maior que a queda nunca rompe",
       ts.violacoes_trava_total(fech, fech + ab, 10000.0, 10.0), (None, 0))

PARAMS_S3 = {"_deposito": 10000.0}


def travas(posicoes, log="", **p):
    o, d = montar_dias(posicoes)
    r = tp.Resultado()
    ts.checar_travas({**PARAMS_S3, **p}, o, d, log, r)
    return r


r = travas(posicoes, DailyLossLimitPercent="0.5")
checar("checar_travas: entrada apos estouro da perda diaria reprova",
       any("[trava]" in f and "DEPOIS" in f for f in r.falhas), True)
sem_violacao = [pos_dia(0, 8, 10, -100.0), pos_dia(1, 8, 10, -100.0), pos_dia(2, 8, 10, -100.0),
                pos_dia(3, 8, 10, 30.0), pos_dia(4, 8, 10, -100.0), pos_dia(7, 8, 10, 30.0)]
r = travas(sem_violacao, Trava_Diaria_Percent="0.5", Protecao_Fecha_Posicoes="false",
           log="[Protecao Global] Trava DIARIA rompida")
checar("checar_travas: trava respeitada nao reprova", r.falhas, [])
r = travas(sem_violacao, Trava_Diaria_Percent="0.5", Protecao_Fecha_Posicoes="true")
checar("checar_travas: fecha=true sem nenhum fechamento de emergencia so avisa",
       (r.falhas, any("fechamento de emergencia" in a for a in r.avisos)), ([], True))
com_fechamento = sem_violacao + [pos_dia(8, 8, 10, -20.0, cmt="")]
r = travas(com_fechamento, Trava_Diaria_Percent="0.5", Protecao_Fecha_Posicoes="false")
checar("checar_travas: fecha=false mas houve fechamento sem SL/TP reprova",
       any("so deveria BLOQUEAR" in f for f in r.falhas), True)
r = travas(perdas, Trava_Total_Percent="3", Protecao_Fecha_Posicoes="false")
checar("checar_travas: trava total permanente violada reprova",
       any("TOTAL" in f and "permanente" in f for f in r.falhas), True)
r = travas(posicoes[:2], DailyLossLimitPercent="0.5")
checar("checar_travas: poucas entradas so avisa", (r.falhas, len(r.avisos) >= 1), ([], True))

# --- S4: filtros de execucao (hora, dia, spread) ------------------------------------------------
import pandas as pd

checar("janela normal: [10:00, 12:00)", [ts.dentro_da_janela(m, 600, 720) for m in (599, 600, 719, 720)],
       [False, True, True, False])
checar("janela noturna 22:00-06:00", [ts.dentro_da_janela(m, 1320, 360) for m in (1319, 1320, 1439, 0, 359, 360)],
       [False, True, True, True, True, False])
checar("janela com pontas iguais = 24 h", ts.dentro_da_janela(700, 0, 0), True)

# 2026-08-03 e segunda; 08-05 quarta; 08-07 sexta
seg10 = datetime(2026, 8, 3, 10, 30, 0)


def entrada(t_in, sl=3990.0):
    o = ordem(t_in, "buy", 0.1, sl, 4020.0)
    return o, [deal(t_in, "buy", "in", 0.1, 4000.0, o["ordem"]),
               deal(t_in + timedelta(hours=1), "sell", "out", 0.1, 4001.0, _n(), 10.0, "sl 3990.00")]


def filtros(horas, params, spreads=None):
    """horas: lista de datetime das entradas; spreads: {minuto: spread} para as barras M1."""
    ordens, deals = [], []
    for h in horas:
        o, d = entrada(h)
        ordens.append(o)
        deals += d
        # a ordem de SAIDA tambem aparece na tabela e nao pode ser conferida como entrada
        ordens.append(ordem(h + timedelta(hours=1), "sell", 0.1, 0.0, 0.0, cmt="sl 3990.00"))
    barras = None
    if spreads is not None:
        idx = pd.date_range(horas[0].replace(hour=0, minute=0), horas[-1].replace(hour=23, minute=59),
                            freq="1min")
        df = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "spread": 5.0}, index=idx)
        for minuto, s in spreads.items():
            df.loc[pd.Timestamp(minuto), "spread"] = s
        barras = tp.Barras({"M1": df})
    r = tp.Resultado()
    ts.checar_filtros_execucao(params, ordens, deals, barras, r)
    return r


base = {"TOD_From_Hour": "0", "TOD_From_Min": "0", "TOD_To_Hour": "23", "TOD_To_Min": "55",
        **{n: "true" for n, _ in ts.DIAS_MT5}}
horas = [seg10 + timedelta(days=i, minutes=7 * i) for i in range(6)]      # seg..sab
r = filtros(horas[:5], base)
checar("ordens_de_entrada ignora as ordens de saida", r.metricas["ordens_de_entrada"], 5)
checar("sem filtro nenhum nao reprova", r.falhas, [])
r = filtros(horas[:5], {**base, "TOD_From_Hour": "10", "TOD_To_Hour": "12", "TOD_To_Min": "0"})
checar("janela 10-12 com todas as entradas dentro passa", r.falhas, [])
fora = [seg10 + timedelta(days=i, hours=(0 if i != 2 else 4)) for i in range(5)]     # uma as 14:30
r = filtros(fora, {**base, "TOD_From_Hour": "10", "TOD_To_Hour": "12", "TOD_To_Min": "0"})
checar("uma ordem as 14:30 fora da janela 10-12 reprova", any("[janela]" in f for f in r.falhas), True)
r = filtros(horas[:5], {**base, "TradeMonday": "false"})
checar("entrada na segunda com TradeMonday=false reprova", any("[dia]" in f for f in r.falhas), True)
r = filtros(horas[1:5], {**base, "TradeMonday": "false"})
checar("sem entradas na segunda passa", r.falhas, [])
r = filtros(horas[:5], {**base, "TradeSunday": "false", "TradeSaturday": "false"})
checar("fim de semana desligado nao afeta dias uteis", r.falhas, [])
r = filtros(horas[:5], {**base, "MaxSpread": "12"}, spreads={horas[2].replace(second=0): 30.0,
                                                          horas[2].replace(second=0) - timedelta(minutes=1): 30.0})
checar("ordem em barra de spread 30 com MaxSpread=12 reprova", any("[spread]" in f for f in r.falhas), True)
r = filtros(horas[:5], {**base, "MaxSpread": "12"}, spreads={horas[2].replace(second=0): 30.0})
checar("spread alto so na barra da ordem (anterior baixa) e tolerado", r.falhas, [])
r = filtros(horas[:5], {**base, "MaxSpread": "12"}, spreads={})
checar("spread sempre baixo passa", r.falhas, [])
r = filtros(horas[:5], {**base, "MaxSpread": "12"}, spreads=None)
checar("sem barras so avisa", (r.falhas, any("[spread]" in a for a in r.avisos)), ([], True))

# --- S5: ablacao de boosters ----------------------------------------------------------------------
import tempfile

import generate_system_sets as gss

checar("S5: sistemas recuperaveis = os do gerador", ts.RECUPERAVEIS, set(gss.SISTEMAS_RECUPERACAO_OPCIONAL))
v04 = dict(ts.variantes_s5("04_SLTP_TRAIL", "BUY", "XAUUSD"))
checar("S5: 04 BUY tem pendente, janelas, filtros, spread e recuperacao",
       {"mercado", "limit_k0", "limit_k05", "stop_k05", "janela_7_20", "janela_13_20", "atr_alto",
        "filtro_ma", "filtro_adx", "spread", "martingale", "lote_fixo", "dalembert"} <= set(v04), True)
checar("S5: BUY nao tem OCO por sinal", "oco_sinal" in v04, False)
checar("S5: a referencia e sempre a mercado", v04["mercado"], {"EntryOrderType": "0"})
checar("S5: D'Alembert vem em Lote Fixo", v04["dalembert"]["PositionSizeMode"], "2")
v07 = dict(ts.variantes_s5("07_GRID_SEPARATE", "BUY", "USDCAD"))
checar("S5: grade nao recebe recuperacao (a EA recusa)", {"martingale", "dalembert", "lote_fixo"} & set(v07), set())
vb = dict(ts.variantes_s5("03_TRAIL_ONLY", "BOTH", "GBPUSD"))
checar("S5: BOTH ganha o OCO por sinal (com hedge)", vb["oco_sinal"]["Hedging"], "true")
checar("S5: acao sem cap de spread", "spread" in dict(ts.variantes_s5("04_SLTP_TRAIL", "BUY", "NVDA")), False)

# curva: +100, -40, +60, -200 num deposito de 1000: pico 1120, fundo 920 -> queda 17.86%
ops = [{"net": n, "t_out": T0 + timedelta(hours=i)} for i, n in enumerate((100.0, -40.0, 60.0, -200.0))]
m = ts.metricas_de_curva(ops, 1000.0, 100.0)
checar("curva: lucro, R, PF, acerto e queda", (m["trades"], m["lucro"], m["r"], m["pf"], m["acerto"], m["dd"]),
       (4, -80.0, -0.8, 0.67, 50.0, 17.86))
checar("curva: sem perda nao tem PF", ts.metricas_de_curva(ops[:1], 1000.0)["pf"], None)


def semana(k, lucros):
    """k semanas de trade fechado: um deal 'out' por semana com o lucro dado."""
    deals_, ops_ = [], []
    for i, lucro in enumerate(lucros):
        t_ = datetime(2026, 8, 3) + timedelta(weeks=i, hours=10)
        deals_.append({"t": t_, "direcao": "out", "lucro": lucro, "comissao": 0.0, "swap": 0.0})
        ops_.append({"net": lucro, "t_out": t_})
    return deals_, ops_


# 12 semanas: base perde/ganha pouco; "bom" ganha 60 a mais TODA semana (delta 720 = 7,2% de 10000);
# "ruido" difere por centavos; "igual" e a propria base; "curto" so tem 4 trades
lucros_base = [10, -20, 5, 8, -3, 12, 7, -9, 14, -4, 6, 11]
d_base, o_base = semana(1, lucros_base)
d_bom, o_bom = semana(1, [x + 60 for x in lucros_base])
d_ruido, o_ruido = semana(1, [x + (0.5 if i % 2 else -0.2) for i, x in enumerate(lucros_base)])
d_curto, o_curto = semana(1, [40, 30, 50, 60])
DEP = 10000.0


def dados_s5(**variantes):
    base = {"deals": d_base, "fechadas": o_base, "deposito": DEP}
    return {"mercado": base, **variantes}


def var(deals_, ops_):
    return {"deals": deals_, "fechadas": ops_, "deposito": DEP}


tab = {x["variante"]: x for x in ts.tabela_ablacao(dados_s5(
    limit_k0=var(d_bom, o_bom), stop_k05=var(d_ruido, o_ruido), janela_7_20=var(d_curto, o_curto),
    filtro_ma=var(d_base, o_base)))}
checar("tabela: a referencia nao tem delta", (tab["mercado"]["delta"], tab["mercado"]["classe"]), (None, "referencia"))
checar("tabela: delta de lucro = lucro da variante - lucro da referencia",
       tab["limit_k0"]["delta"], round(sum(x + 60 for x in lucros_base) - sum(lucros_base), 2))
checar("classe: ganho material com amostra boa e VALIDA", tab["limit_k0"]["classe"], "valida")
checar("classe: variante identica a base e 'igual' (o set ja era assim)", tab["filtro_ma"]["classe"], "igual")
checar("classe: diferenca de centavos e irrelevante", tab["stop_k05"]["classe"], "irrelevante")
checar("classe: 4 trades contra 12 e esvaziou (< 30%? nao: 33%) -> amostra pequena", tab["janela_7_20"]["classe"],
       "pequena")
tab_v = {x["variante"]: x for x in ts.tabela_ablacao(dados_s5(vazio=var([], [])))}
checar("classe: 0 trades contra 12 esvazia a estrategia", tab_v["vazio"]["classe"], "esvaziou")
checar("veredito: referencia", ts.veredito_s5(tab["mercado"]), "referencia")
checar("veredito: sem efeito", ts.veredito_s5(tab["filtro_ma"]), "sem efeito (a config ja era assim)")
checar("veredito: amostra pequena", ts.veredito_s5(tab["janela_7_20"]), "amostra pequena (< 10 trades)")
checar("veredito: irrelevante", ts.veredito_s5(tab["stop_k05"]), "diferenca irrelevante (< 1% do deposito)")
checar("veredito: esvazia", ts.veredito_s5(tab_v["vazio"]), "esvazia a estrategia (0 de 12 trades)")
checar("veredito: melhora material e verdicto de melhora", ts.veredito_s5(tab["limit_k0"]).startswith("melhora"), True)
# D'Alembert compara com o lote fixo, nao com o mercado
tab2 = {x["variante"]: x for x in ts.tabela_ablacao(dados_s5(
    lote_fixo=var(d_ruido, o_ruido), dalembert=var(d_bom, o_bom)))}
checar("D'Alembert usa lote_fixo como referencia", tab2["dalembert"]["ref"], "lote_fixo")

# consistencia entre as duas janelas
checar("prefixos das janelas", (ts.prefixo_s5("a"), ts.prefixo_s5("b")), ("s5", "s5b"))


def lin(classe, delta=None, t_=None):
    return {"classe": classe, "delta": delta, "t": t_}


checar("consistencia: melhora nas duas e candidato",
       ts.consistencia_s5(lin("valida", 500.0, 2.4), lin("valida", 150.0, 0.5)),
       "CANDIDATO: melhora nas duas (significativo numa)")
checar("consistencia: piora nas duas", ts.consistencia_s5(lin("valida", -500.0, -0.4), lin("valida", -900.0, -1.0)),
       "piora nas duas")
checar("consistencia: sinal muda = inconsistente",
       ts.consistencia_s5(lin("valida", 300.0, 1.2), lin("valida", -200.0, -0.9)), "inconsistente (muda de sinal)")
checar("consistencia: referencia", ts.consistencia_s5(lin("referencia"), lin("referencia")), "referencia")
checar("consistencia: so uma janela valida", ts.consistencia_s5(lin("valida", 300.0, 1.2), lin("pequena", 5.0, 0.1)),
       "so uma janela tem base para julgar (a outra: pequena)")
checar("consistencia: duas janelas sem efeito", ts.consistencia_s5(lin("igual", 0.0), lin("igual", 0.0)),
       "sem efeito (a config ja era assim)")
checar("consistencia: irrelevante nas duas = sem base", ts.consistencia_s5(lin("irrelevante", 3.0), lin("pequena", 1.0)),
       "sem base para julgar (irrelevante / pequena)")

# teste dos sinais e placar
checar("sinais: 9 a 1 -> p ~ 0.021", round(ts.teste_dos_sinais(9, 1), 3), 0.021)
checar("sinais: 5 a 5 -> p = 1", ts.teste_dos_sinais(5, 5), 1.0)
checar("sinais: sem pares -> None", ts.teste_dos_sinais(0, 0), None)


def par(**v):
    return {n: {"classe": c, "delta": d, "deposito": DEP} for n, (c, d) in v.items()}


por_par = {(f"b{i}", "a"): par(bom=("valida", 300.0), ruim=("valida", -300.0), igual=("igual", 0.0),
                               vazio=("esvaziou", -100.0), misto=("valida", 200.0 if i % 2 else -200.0))
           for i in range(6)}
pl = {x["variante"]: x for x in ts.placar_s5(por_par)}
checar("placar: 6 pares positivos", (pl["bom"]["pares"], pl["bom"]["pos"], pl["bom"]["neg"]), (6, 6, 0))
checar("placar: 6 a 0 tende a AJUDAR (p = 0.03)", pl["bom"]["leitura"], "tende a AJUDAR")
checar("placar: 0 a 6 tende a ATRAPALHAR", pl["ruim"]["leitura"], "tende a ATRAPALHAR")
checar("placar: 3 a 3 sem tendencia", pl["misto"]["leitura"], "sem tendencia clara")
checar("placar: config igual nao conta como par", (pl["igual"]["pares"], pl["igual"]["sem_efeito"]), (0, 6))
checar("placar: variante que esvazia e marcada", (pl["vazio"]["esvaziou"], "esvazia a estrategia" in pl["vazio"]["leitura"]),
       (6, True))
checar("placar: mediana em % do deposito (300 de 10000 = +3%)", pl["bom"]["mediana_pct"], 3.0)
esperado_s5 = sum(len(ts.variantes_s5(sis, lv.split("_")[0], sim, ch))
                  for ch, (_a, sim, sis, lv) in ts.BASES_S5.items())
checar("catalogo S5: duas janelas, mesmos nomes com prefixo diferente", (
    len([c for c in ts.catalogo() if c.nome.startswith("s5_")]),
    len([c for c in ts.catalogo() if c.nome.startswith("s5b_")])), (esperado_s5, esperado_s5))
checar("S5: subtrativos so existem com a chave da base",
       "sem_ma" in dict(ts.variantes_s5("04_SLTP_TRAIL", "BUY", "XAUUSD", "xau04")),
       True)
checar("S5: sem a chave nao ha subtrativos", "sem_ma" in dict(ts.variantes_s5("04_SLTP_TRAIL", "BUY", "XAUUSD")),
       False)
checar("S5: referencia do subtrativo do XAU e o campeao com Limit", ts.referencia_s5("xau04", "sem_ma"), "limit_k0")
checar("S5: referencia do subtrativo das outras e a mercado", ts.referencia_s5("gbp03", "sem_adx"), "mercado")
checar("S5: referencia aditiva e a mercado", ts.referencia_s5("xau04", "stop_k05"), "mercado")
checar("S5: D'Alembert continua contra o lote fixo", ts.referencia_s5("gbp03", "dalembert"), "lote_fixo")
checar("S5: o campeao do XAU e a variante limit_k0",
       ts.CAMPEAO_S5["xau04"], "limit_k0")
checar("S5: o sistema pelado do XAU tambem tira a Limit",
       dict(ts.SUBTRATIVAS_S5["xau04"])["so_sistema"]["EntryOrderType"], "0")
checar("S5: janela livre cobre o dia inteiro", ts.dentro_da_janela(23 * 60 + 30, 0, 23 * 60 + 55)
       and ts.dentro_da_janela(0, 0, 23 * 60 + 55), True)
checar("catalogo S5: a janela b e anterior a a", ts.JANELAS_S5["b"][1] < ts.JANELAS_S5["a"][0], True)

# migracao de set antigo (sem os inputs da entrada pendente) para o template atual
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    velho = tmp / "_TESTE_ORIGEM_x.set"
    velho.write_text("Stop=4||3||1||6||Y\r\nPositionSizeMode=3||3||0||3||N\r\nObsoleto=1||1||0||1||N\r\n",
                     encoding="utf-16")
    template = tmp / "template.set"
    template.write_text("Stop=3||3||1||6||Y\r\nPositionSizeMode=3||3||0||3||N\r\n"
                        "EntryOrderType=0||1||1||3||Y\r\nPendingDistanciaATR=0.5||0||0.25||2||Y\r\n",
                        encoding="utf-16")
    novo = tp.migrar_para_template(velho, template)
    import optimize_two_stage as ots_
    vals = ots_.valores_do_set(novo)
    checar("migracao: cria o arquivo _TESTE_MIGRADO_", novo.name, "_TESTE_MIGRADO_x.set")
    checar("migracao: valor do set antigo vence o do template", vals["Stop"], "4")
    checar("migracao: input novo vem do template", (vals["EntryOrderType"], vals["PendingDistanciaATR"]), ("0", "0.5"))
    checar("migracao: chave obsoleta some", "Obsoleto" in vals, False)
    atual = tmp / "_TESTE_ORIGEM_y.set"
    atual.write_text("EntryOrderType=2||2||0||2||N\r\nStop=4||4||1||4||N\r\n", encoding="utf-16")
    checar("migracao: set que ja tem o input passa direto", tp.migrar_para_template(atual, template), atual)

# --- S6: OCO por sessao x fatores -----------------------------------------------------------
from datetime import date

import json
import tempfile
import pandas as pd


def bracket(dia, hh=8, mm=0, dur_min=60):
    """As duas pernas de um bracket armado em 2026-07-<dia> hh:mm:01."""
    t0 = datetime(2026, 7, dia, hh, mm, 1)
    a = ordem(t0, "buy stop", 0.1, 0.0, 0.0, "13-MUL Buy/OCO", "canceled")
    b = ordem(t0, "sell stop", 0.1, 0.0, 0.0, "13-MUL Sell/OCO", "canceled")
    a["fim"] = b["fim"] = t0 + timedelta(minutes=dur_min)
    return [a, b]


ctrl6 = bracket(6) + bracket(7) + bracket(8) + bracket(9)
d_ctrl = ts.dias_com_bracket(ctrl6)
checar("S6 dias: as duas pernas do mesmo dia contam 1", d_ctrl,
       {date(2026, 7, 6), date(2026, 7, 7), date(2026, 7, 8), date(2026, 7, 9)})
checar("S6 dias: ordens a mercado nao contam",
       ts.dias_com_bracket([ordem(T0, "buy", 0.1, 0.0, 0.0)]), set())

checar("S6 previsao zero: sem bracket confirma", ts.julgar_previsao("zero", set(), d_ctrl)[0], "confirma")
checar("S6 previsao zero: com bracket diverge", ts.julgar_previsao("zero", {date(2026, 7, 6)}, d_ctrl)[0],
       "diverge")
checar("S6 previsao igual: mesmos dias confirma", ts.julgar_previsao("igual", set(d_ctrl), d_ctrl)[0], "confirma")
um_a_menos = set(d_ctrl) - {date(2026, 7, 9)}
checar("S6 previsao igual: 1 dia de diferenca ainda confirma (posicao aberta bloqueando o seguinte)",
       ts.julgar_previsao("igual", um_a_menos, d_ctrl)[0], "confirma")
dois_a_menos = um_a_menos - {date(2026, 7, 8)}
checar("S6 previsao igual: 2 dias de diferenca diverge",
       ts.julgar_previsao("igual", dois_a_menos, d_ctrl)[0], "diverge")
checar("S6 previsao menos: menos dias confirma", ts.julgar_previsao("menos", um_a_menos, d_ctrl)[0], "confirma")
checar("S6 previsao menos: os mesmos dias diverge (o filtro nao vetou nada)",
       ts.julgar_previsao("menos", set(d_ctrl), d_ctrl)[0], "diverge")
checar("S6 previsao igual_a: compara com o outro cenario",
       (ts.julgar_previsao("igual_a:adx_forca", um_a_menos, d_ctrl, um_a_menos)[0],
        ts.julgar_previsao("igual_a:adx_forca", set(d_ctrl), d_ctrl, dois_a_menos)[0]), ("confirma", "diverge"))
checar("S6 previsao igual_a: sem o outro cenario nao julga",
       ts.julgar_previsao("igual_a:adx_forca", um_a_menos, d_ctrl, None)[0], "sem previsao")
checar("S6 previsao: livre nao julga", ts.julgar_previsao("livre", set(), d_ctrl)[0], "sem previsao")
checar("S6 previsao: sem controle nao julga", ts.julgar_previsao("igual", set(d_ctrl), None)[0], "sem previsao")

# Fecharordensforadohorario: janela 00:00-08:30
par6 = {"TOD_To_Hour": "8", "TOD_To_Min": "30", "Fecharordensforadohorario": "true"}
r = tp.Resultado()
ts.checar_fim_da_janela(par6, bracket(6, dur_min=29) + bracket(7, dur_min=12), [], r)
checar("S6 fim da janela: pendentes canceladas a tempo, sem falha", (r.falhas, r.metricas["pendentes_vivas_apos_a_janela"]),
       ([], 0))
r = tp.Resultado()
ts.checar_fim_da_janela(par6, bracket(6, dur_min=29) + bracket(7, dur_min=60), [], r)
checar("S6 fim da janela: pendente viva depois das 08:30 reprova",
       (len(r.falhas), r.metricas["pendentes_vivas_apos_a_janela"]), (1, 2))
o1, d1 = posicao(datetime(2026, 7, 6, 8, 10), "buy", 0.1, 100.0, 90.0, 120.0, datetime(2026, 7, 6, 8, 30, 20),
                 101.0, 10.0, "Outside trading session")
o2, d2 = posicao(datetime(2026, 7, 7, 8, 10), "buy", 0.1, 100.0, 90.0, 120.0, datetime(2026, 7, 7, 11, 0, 0),
                 101.0, 10.0, "sl 90")
r = tp.Resultado()
ts.checar_fim_da_janela(par6, [o1], d1, r)
checar("S6 fim da janela: posicao fechada as 08:30 pela EA passa e e contada",
       (r.falhas, r.metricas["fechadas_fora_do_horario"]), ([], 1))
r = tp.Resultado()
ts.checar_fim_da_janela(par6, [o2], d2, r)
checar("S6 fim da janela: posicao aberta ate as 11h reprova", len(r.falhas), 1)


class _Barras:
    def __init__(self, dfs):
        self.dfs = dfs


def m1_spread(por_dia: dict):
    """M1 de 07:59 a 09:00 de cada dia; `por_dia[dia] = (spread das 08:00, spread do resto da hora)`."""
    linhas = []
    for dia, (s_ini, s_resto) in por_dia.items():
        for i, minuto in enumerate(pd.date_range(f"2026-07-{dia:02d} 07:59", f"2026-07-{dia:02d} 09:00", freq="min")):
            linhas.append((minuto, s_ini if (minuto.hour, minuto.minute) == (8, 0) else s_resto))
    df = pd.DataFrame(linhas, columns=["time", "spread"]).set_index("time")
    return _Barras({"M1": df})


bm1 = m1_spread({6: (20, 5), 7: (5, 5), 8: (20, 20), 9: (5, 5)})
r = tp.Resultado()
ts.analisar_spread_no_gatilho({"MaxSpread": "12", "PendingHoraSessao": "8"},
                              {date(2026, 7, 7)}, set(d_ctrl), bm1, r)
checar("S6 gatilho: 3 dias perdidos; 1 por gatilho gasto (spread alto so no 1o minuto); 1 sem explicacao de spread",
       (r.metricas["dias_perdidos_vs_controle"], r.metricas["dias_perdidos_por_gatilho_gasto"],
        r.metricas["dias_perdidos_sem_explicacao_de_spread"]), (3, 1, 1))
checar("S6 gatilho: o dia do gatilho gasto vira aviso", any("[gatilho]" in a for a in r.avisos), True)
r = tp.Resultado()
ts.analisar_spread_no_gatilho({"MaxSpread": "0", "PendingHoraSessao": "8"}, set(), set(d_ctrl), bm1, r)
checar("S6 gatilho: sem teto de spread nao analisa", r.metricas, {})

# --- S6: por que faltou bracket (posicao aberta, envio recusado) ------------------------------
LOG_DE40 = (
    "RP\t2\t22:24:13.513\tCore 01\t2026.07.06 09:00:00   failed buy stop 0.15 .DE40Cash at 25848.3 "
    "sl: 25709.1 tp: 25987.5 [Market closed]\n"
    "ON\t2\t22:24:13.513\tCore 01\t2026.07.06 09:00:00   failed sell stop 0.15 .DE40Cash at 25802.0 "
    "sl: 25941.2 tp: 25662.8 [Market closed]\n"
    "QF\t2\t22:24:13.513\tCore 01\t2026.07.07 09:00:00   failed buy stop 0.13 .DE40Cash at 25856.3 "
    "sl: 25699.6 tp: 26013.0 [Invalid stops]\n")
checar("S6 envios recusados: dia e motivo", ts.envios_recusados_por_dia(LOG_DE40),
       {date(2026, 7, 6): {"Market closed"}, date(2026, 7, 7): {"Invalid stops"}})
checar("S6 envios recusados: log sem falha", ts.envios_recusados_por_dia("nada aqui"), {})
checar("S6 dias de pregao na hora: fim exclusivo",
       ts.dias_com_pregao_na_hora(bm1, 8, date(2026, 7, 6), date(2026, 7, 9)),
       [date(2026, 7, 6), date(2026, 7, 7), date(2026, 7, 8)])
checar("S6 dias de pregao na hora: sem barras nao inventa dia",
       ts.dias_com_pregao_na_hora(None, 8, date(2026, 7, 6), date(2026, 7, 9)), [])

pos7, d_pos7 = posicao(datetime(2026, 7, 6, 15, 0), "buy", 0.1, 100.0, 90.0, 120.0,
                       datetime(2026, 7, 7, 9, 30), 101.0, 5.0, "sl 90")
pos9, d_pos9 = posicao(datetime(2026, 7, 8, 15, 0), "buy", 0.1, 100.0, 90.0, 120.0,
                       datetime(2026, 7, 9, 9, 30), 101.0, 5.0, "sl 90")
viva8 = bracket(8, 7, 45, 30)                 # pendente das 07:45 ainda viva as 08:00
perdas = ts.classificar_perdas([date(2026, 7, 6), date(2026, 7, 7), date(2026, 7, 8), date(2026, 7, 9),
                                date(2026, 7, 10)], 8,
                               [pos7] + viva8, d_pos7, {date(2026, 7, 6): {"Market closed"}},
                               {date(2026, 7, 10)})
checar("S6 perdas: envio recusado / posicao aberta / pendente viva / lote abaixo do minimo / sem explicacao",
       {k: [d.day for d in v] for k, v in perdas.items()},
       {"envio": [6], "posicao": [7, 8], "lote": [10], "outras": [9]})
LOG_LOTE = ("CO\t0\t22:31:34.685\tCore 01\t2026.07.09 08:00:00   MM_Size_R: calculated volume 0.0000 < "
            "minimum 0.01 - order aborted to preserve the configured R risk\n"
            "OJ\t0\t22:31:34.685\tCore 01\t2026.07.09 08:00:00   MM_Size_R: calculated volume 0.0000 < "
            "minimum 0.01 - order aborted to preserve the configured R risk\n")
checar("S6 lote abaixo do minimo: um dia mesmo com as duas linhas (compra e venda)",
       ts.lotes_abaixo_do_minimo_por_dia(LOG_LOTE), {date(2026, 7, 9)})
checar("S6 lote abaixo do minimo: log sem a linha", ts.lotes_abaixo_do_minimo_por_dia("nada"), set())

# menos_explicado: o scenario armou 6 e 8; 7 e 9 tinham posicao aberta no gatilho
jan = (date(2026, 7, 6), date(2026, 7, 10))
par8 = {"PendingHoraSessao": "8"}
ords = bracket(6) + bracket(8) + [pos7, pos9]
r = tp.Resultado()
ts.checar_oco_fatores("menos_explicado", par8, ords, d_pos7 + d_pos9, {"ordens": ctrl6, "deals": []}, None,
                      bm1, r, "", jan)
checar("S6 menos_explicado: todo dia perdido tinha posicao aberta -> confirma",
       (r.metricas["veredito"], r.metricas["perdas_por_posicao_aberta"], r.metricas["perdas_outras"],
        r.metricas["dias_sem_bracket"], r.metricas["dias_de_pregao"]), ("confirma", 2, 0, 2, 4))
r = tp.Resultado()
ts.checar_oco_fatores("menos_explicado", par8, bracket(6) + bracket(8) + [pos7], d_pos7,
                      {"ordens": ctrl6, "deals": []}, None, bm1, r, "", jan)
checar("S6 menos_explicado: um dia perdido sem motivo -> diverge e avisa",
       (r.metricas["veredito"], r.metricas["perdas_outras"], any("[modelo]" in a for a in r.avisos)),
       ("diverge", 1, True))
r = tp.Resultado()
ts.checar_oco_fatores("menos_explicado", par8, bracket(6) + bracket(8) + [pos7], d_pos7,
                      {"ordens": ctrl6, "deals": []}, None, bm1, r, LOG_LOTE, jan)
checar("S6 menos_explicado: o dia sem posicao tem o lote abortado no log -> confirma",
       (r.metricas["veredito"], r.metricas["perdas_por_posicao_aberta"], r.metricas["perdas_por_lote_minimo"],
        r.metricas["perdas_outras"]), ("confirma", 1, 1, 0))
r = tp.Resultado()
ts.checar_oco_fatores("livre", {"PendingHoraSessao": "9"}, [], [], None, None, bm1, r, LOG_DE40,
                      (date(2026, 7, 6), date(2026, 7, 8)))
checar("S6 perdas: envio recusado aparece com os motivos (2 dias de pregao, os dois recusados)",
       (r.metricas["perdas_por_envio_recusado"], r.metricas["motivos_de_envio_recusado"]),
       (2, ["Invalid stops", "Market closed"]))

# zero previsto e medido: "cenario sem evidencia" deixa de ser falha
r = tp.Resultado()
r.falha("tipos", "nenhuma pendente foi colocada -- cenario sem evidencia")
ts.checar_oco_fatores("zero", par8, [], [], {"ordens": ctrl6, "deals": []}, None, None, r)
checar("S6 zero previsto e medido: 'sem evidencia' vira aviso, nao falha",
       (r.falhas, any("[amostra]" in a for a in r.avisos), r.metricas["veredito"]), ([], True, "confirma"))
r = tp.Resultado()
r.falha("tipos", "nenhuma pendente foi colocada -- cenario sem evidencia")
ts.checar_oco_fatores("livre", par8, [], [], None, None, None, r)
checar("S6 zero sem previsao: continua falha (sem evidencia)", len(r.falhas), 1)

# checar_oco_fatores de ponta a ponta (previsao zero, mas a EA armou brackets)
r = tp.Resultado()
ts.checar_oco_fatores("zero", {"PendingHoraSessao": "8"}, bracket(6), [], {"ordens": ctrl6, "deals": []}, None, None, r)
checar("S6 oco_fatores: previsao zero desmentida vira aviso 'modelo'",
       (r.metricas["veredito"], any("[modelo]" in a for a in r.avisos)), ("diverge", True))

# tabela
_saida = ts.SAIDA
with tempfile.TemporaryDirectory() as _d:
    ts.SAIDA = Path(_d)
    checar("relatorio_oco: sem resultado.json avisa", "rode --verificar" in ts.relatorio_oco(), True)
    (Path(_d) / "resultado.json").write_text(json.dumps({"s6_janela_sem_a_hora": {
        "falhas": [], "avisos": [], "metricas": {"dias_com_bracket": 0, "dias_controle": 40,
                                                 "veredito": "confirma", "detalhe": "nenhum bracket"}}}),
                                             encoding="utf-8")
    _txt = ts.relatorio_oco()
ts.SAIDA = _saida
checar("relatorio_oco: mostra o veredito medido e marca o que nao rodou",
       ("confirma" in _txt, "nao rodou" in _txt), (True, True))

# --- catalogo -------------------------------------------------------------------------------
cat = ts.catalogo()
nomes = [c.nome for c in cat]
checar("catalogo: nomes unicos", len(nomes), len(set(nomes)))
s1_todos = [c for c in cat if c.grupo == "s1"]
s1 = [c for c in s1_todos if c.simbolo == "XAUUSD"]
checar("catalogo S1: 9 sistemas x 12 arquivos + 13 so BOTH_MULTI (ouro)", len(s1), 9 * 12 + 1)
checar("catalogo S1: EURUSD tem os 10 sistemas em BOTH_MULTI",
       sorted(c.sistema for c in s1_todos if c.simbolo == "EURUSD"), sorted(ts.SISTEMAS_S1))
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
s3c = [c for c in cat if c.grupo == "s3"]
checar("catalogo S3: travas de perda diaria, global diaria e total", (
    any("DailyLossLimitPercent" in c.sobrepor for c in s3c),
    any("Trava_Diaria_Percent" in c.sobrepor for c in s3c),
    any("Trava_Total_Percent" in c.sobrepor for c in s3c)), (True, True, True))
checar("catalogo S3: com e sem fechamento das posicoes",
       {c.sobrepor.get("Protecao_Fecha_Posicoes") for c in s3c if "Trava_Diaria_Percent" in c.sobrepor
        or "Trava_Total_Percent" in c.sobrepor} >= {"true", "false"}, True)
checar("catalogo S3: as tres EAs", {c.variante.split("_")[-1] for c in s3c},
       {"MULTI", "BOLLINGER", "CANDLES"})
s4c = [c for c in cat if c.grupo == "s4"]
checar("catalogo S4: janela, dias e spread", (
    any("TOD_From_Hour" in c.sobrepor for c in s4c),
    any("TradeMonday" in c.sobrepor for c in s4c),
    any("MaxSpread" in c.sobrepor for c in s4c)), (True, True, True))
checar("catalogo S4: inclui a janela noturna e a pendente", (
    any(c.sobrepor.get("TOD_From_Hour") == "22" for c in s4c),
    any(c.sobrepor.get("EntryOrderType") == "2" for c in s4c)), (True, True))
s5c = [c for c in cat if c.grupo == "s5"]
checar("catalogo S5: todo cenario parte de um set pronto da biblioteca", all(c.origem_arquivo for c in s5c), True)
checar("catalogo S5: 5 bases (2 campeoes + 3 reprovados otimizados)", len({c.origem_arquivo for c in s5c}), 5)
checar("catalogo S5: toda base tem a variante de referencia a mercado", all(
    any(c.nome == f"s5_{k}_mercado" for c in s5c) for k in ts.BASES_S5), True)
s6c = [c for c in cat if c.grupo == "s6"]
checar("catalogo S6: um cenario por linha da tabela", len(s6c), len(ts.S6))
checar("catalogo S6: sempre o 13 em BOTH_MULTI", {(c.sistema, c.variante) for c in s6c},
       {("13_OCO_ROMPIMENTO", "BOTH_MULTI")})
checar("catalogo S6: previsoes validas", all(p in ts.PREVISOES_S6 or p.startswith("igual_a:")
                                             for _n, _e, p, _w, _s in ts.S6), True)
checar("catalogo S6: igual_a aponta pra cenario que existe", all(
    p.split(":", 1)[1] in {n for n, *_ in ts.S6} for _n, _e, p, _w, _s in ts.S6 if p.startswith("igual_a:")), True)
checar("catalogo S6: cobre janela, dias, spread, MA, MTF, ADX, ATR, timeframe, lote e indice", (
    any("TOD_From_Hour" in c.sobrepor for c in s6c), any("TradeFriday" in c.sobrepor for c in s6c),
    any("MaxSpread" in c.sobrepor for c in s6c), any("AtivarFiltroMA" in c.sobrepor for c in s6c),
    any("AtivarFiltroMTF" in c.sobrepor for c in s6c), any("AtivarFiltroADX" in c.sobrepor for c in s6c),
    any("EntradaATR" in c.sobrepor for c in s6c), any("TimeFrame" in c.sobrepor for c in s6c),
    any("PositionSizeMode" in c.sobrepor for c in s6c), any(c.simbolo == ".DE40Cash" for c in s6c)),
    (True,) * 10)
checar("catalogo S6: MA curta, posicao carregada e DE40 na abertura", (
    any(c.sobrepor.get("MA_Period") == "10" for c in s6c),
    any(c.nome == "s6_posicao_carregada" for c in s6c) and any(c.nome == "s6_stop_largo_lote_minimo" for c in s6c),
    ts.PREVISAO_S6["s6_de40_h9_f8"]), (True, True, "zero"))
checar("catalogo S6: o controle (S1 do 13, ouro) existe", ts.CONTROLE_S6 in nomes, True)


def perfil(sistema: str):
    ac = gss.CLASSES["05_Metals"]
    p_ = gss.Profile()
    gss.apply_defaults(p_, ac, "BOTH", 1, "x")
    gss.apply_core(p_, ac, False, grid=False)
    gss.apply_system(p_, sistema, ac, "BOTH")
    if sistema == "13_OCO_ROMPIMENTO":
        gss.aplicar_oco_sessao(p_)
    gss.apply_sizing_and_formula(p_, sistema, ac)
    p_.desativar_inertes()
    return p_.values


v13, v04_ = perfil("13_OCO_ROMPIMENTO"), perfil("04_SLTP_TRAIL")
checar("gerador do 13: MTF cravado em false (morto no gatilho da sessao) e o dependente em N",
       (v13["AtivarFiltroMTF"].split("||")[4], v13["AtivarFiltroMTF"].split("||")[0],
        v13["MTF_RequererAmbos"].split("||")[4]), ("N", "false", "N"))
checar("gerador do 13: os outros filtros e a hora da sessao continuam eixos",
       (v13["AtivarFiltroMA"].split("||")[4], v13["AtivarFiltroADX"].split("||")[4],
        v13["PendingHoraSessao"].split("||")[4]), ("Y", "Y", "Y"))
checar("gerador do 04: o MTF continua eixo", v04_["AtivarFiltroMTF"].split("||")[4], "Y")
checar("catalogo S6: mesma janela do controle",
       {(c.inicio, c.fim) for c in s6c} == {(c.inicio, c.fim) for c in cat if c.nome == ts.CONTROLE_S6}, True)
checar("catalogo: modelo OHLC (rapido)", {c.modelo for c in cat}, {1})
checar("catalogo: sistemas do S1 = sistemas do gerador",
       set(ts.ASSINATURA) == set(ts.SISTEMAS_S1), True)

if FALHAS:
    print(f"{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  -", f)
    sys.exit(1)
print("testar_sistemas: todos os casos passaram")
