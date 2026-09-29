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


d_base, o_base = semana(1, [10, -20, 5, 8, -3, 12])
d_bom, o_bom = semana(1, [30, 10, 25, 28, 15, 32])       # ganha 20 a mais TODA semana -> t enorme
d_ruido, o_ruido = semana(1, [12, -18, 3, 9, -5, 10])     # diferenca minima e variavel
tab = {x["variante"]: x for x in ts.tabela_ablacao({
    "mercado": {"deals": d_base, "fechadas": o_base, "deposito": 1000.0},
    "limit_k0": {"deals": d_bom, "fechadas": o_bom, "deposito": 1000.0},
    "stop_k05": {"deals": d_ruido, "fechadas": o_ruido, "deposito": 1000.0}})}
checar("tabela: a referencia nao tem delta", (tab["mercado"]["delta"], tab["mercado"]["t"]), (None, None))
checar("tabela: variante que ganha sempre tem t alto", tab["limit_k0"]["t"] is None or abs(tab["limit_k0"]["t"]) >= 2
       or tab["limit_k0"]["delta"] > 0, True)
checar("tabela: delta de lucro = lucro da variante - lucro da referencia",
       tab["limit_k0"]["delta"], round(sum([30, 10, 25, 28, 15, 32]) - sum([10, -20, 5, 8, -3, 12]), 2))
checar("veredito: sem delta e referencia", ts.veredito_s5(None, None, 0, 0), "referencia")
checar("veredito: melhora significativa", ts.veredito_s5(50.0, 3.1, 1, 1), "melhora (significativo)")
checar("veredito: piora no ruido", ts.veredito_s5(-5.0, -0.6, 1, 1), "piora, mas dentro do ruido")
# D'Alembert compara com o lote fixo, nao com o mercado
tab2 = {x["variante"]: x for x in ts.tabela_ablacao({
    "mercado": {"deals": d_base, "fechadas": o_base, "deposito": 1000.0},
    "lote_fixo": {"deals": d_ruido, "fechadas": o_ruido, "deposito": 1000.0},
    "dalembert": {"deals": d_bom, "fechadas": o_bom, "deposito": 1000.0}})}
checar("D'Alembert usa lote_fixo como referencia", tab2["dalembert"]["ref"], "lote_fixo")

# consistencia entre as duas janelas
checar("prefixos das janelas", (ts.prefixo_s5("a"), ts.prefixo_s5("b")), ("s5", "s5b"))
checar("consistencia: melhora nas duas e candidato",
       ts.consistencia_s5({"delta": 50.0, "t": 2.4}, {"delta": 10.0, "t": 0.5}),
       "CANDIDATO: melhora nas duas (significativo numa)")
checar("consistencia: piora nas duas", ts.consistencia_s5({"delta": -5.0, "t": -0.4}, {"delta": -9.0, "t": -1.0}),
       "piora nas duas")
checar("consistencia: sinal muda = inconsistente",
       ts.consistencia_s5({"delta": 30.0, "t": 1.2}, {"delta": -20.0, "t": -0.9}), "inconsistente (muda de sinal)")
checar("consistencia: referencia", ts.consistencia_s5({"delta": None, "t": None}, {"delta": None, "t": None}),
       "referencia")
checar("catalogo S5: duas janelas, mesmos nomes com prefixo diferente", (
    len([c for c in ts.catalogo() if c.nome.startswith("s5_")]),
    len([c for c in ts.catalogo() if c.nome.startswith("s5b_")])), (63, 63))
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
checar("catalogo: modelo OHLC (rapido)", {c.modelo for c in cat}, {1})
checar("catalogo: sistemas do S1 = sistemas do gerador",
       set(ts.ASSINATURA) == set(ts.SISTEMAS_S1), True)

if FALHAS:
    print(f"{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  -", f)
    sys.exit(1)
print("testar_sistemas: todos os casos passaram")
