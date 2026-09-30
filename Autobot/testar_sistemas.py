# -*- coding: utf-8 -*-
"""Testes por SISTEMA e por BOOSTER no tester, em janelas curtas.

Existe porque (dono, 2026-09-29: "testar todo sistemas do que falta! verifique
o que e booster, o que e sistema!"): testar_pendentes.py prova a ENTRADA
pendente; ninguem tinha provado que cada sistema SAI como o nome promete (03
sem TP, 11 sem SL, 07/12 com varias pernas...) nem que a recuperacao muda o
lote como o codigo diz. Os validadores estaticos (validate_system_sets) olham o
.set; este olha o que a EA FEZ no tester.

  S1 assinatura   cada sistema x cada arquivo de template (12 variantes): ordens
                  com/sem SL e TP conforme a identidade, saidas so das classes
                  permitidas, lado do arquivo respeitado, grade abre 2+ pernas,
                  trailing/breakeven deixam rastro nas saidas
  S2 recuperacao  Martingale / D'Alembert: o lote de CADA entrada bate com o
                  modelo do codigo da EA (divida por lado, passos, teto de R),
                  refeito so com o historico do proprio relatorio

    python testar_sistemas.py --listar
    python testar_sistemas.py --rodar [--so texto] [--shard 1/2] [--refazer]
    python testar_sistemas.py --verificar [--so texto]

Relatorios em _sistemas_teste/ (nao vai pro git). Reusa o leitor de relatorio e
o executor de testar_pendentes.py.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, deque
from datetime import datetime, time as hora, timedelta
from dataclasses import dataclass
from pathlib import Path

import testar_pendentes as tp
from testar_pendentes import Resultado, _bool, _flt, _int, parse_relatorio

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI / "_sistemas_teste"

SIMBOLO = "XAUUSD"
JANELA = ("2026.07.06", "2026.09.01")        # 8 semanas: amostra sem gastar tick real
LADOS = ("BUY", "SELL", "BOTH")
FAMILIAS = ("MULTI", "ICHIMOKU", "BOLLINGER", "CANDLES")
SISTEMAS_S1 = ("01_SLTP", "02_SLTP_ORGANIC", "03_TRAIL_ONLY", "04_SLTP_TRAIL",
               "05_BE_TRAIL", "06_REVERSAL_EXIT", "07_GRID_SEPARATE",
               "11_SIGNAL_ONLY", "12_GRID_INVERSO", "13_OCO_ROMPIMENTO")
SO_BOTH_MULTI = {"13_OCO_ROMPIMENTO"}
# EPS de saldo: abaixo disso a operacao nao e nem perda nem ganho (mesmo da EA)
EPS = 1e-7
# OnInit recusou o set (mesma leitura da bateria_logica): sem trade nenhum, mas NAO e "sem sinal"
RECUSA = re.compile(r"incorrect input parameters", re.I)
MOTIVO = re.compile(r"(?<!\()(Invalid [^\r\n]{0,150}|[A-Za-z_']+ requires [^\r\n]{0,150})")


# ---------------------------------------------------------------------------
# Classes de saida e operacoes (entrada + saida pareadas)
# ---------------------------------------------------------------------------

def classe_saida(comentario: str) -> str:
    """Como a posicao fechou, pelo comentario do deal de saida. Stop/take do
    broker vem como "sl 4046.61"/"tp 4106.75"; as saidas da propria EA trazem o
    rotulo dela."""
    c = comentario.strip().lower().strip("()[] ")
    if not c:
        return "vazio"
    if c == "sl" or c.startswith("sl "):
        return "sl"
    if c == "tp" or c.startswith("tp "):
        return "tp"
    if "end of test" in c or "fim do teste" in c:
        return "fim"
    if "reversal" in c:
        return "reversao"
    if "basket" in c:
        return "cesta"
    if "pyramid" in c:
        return "piramide"
    if "stop out" in c or "so:" in c:
        return "stopout"
    return "outro"


def operacoes(ordens: list[dict], deals: list[dict]) -> tuple[list[dict], list[dict]]:
    """(fechadas, abertas): entrada e saida pareadas FIFO por lado. Exato onde ha
    uma posicao por lado por vez (01-06, 11, 13); em grade so vale contagem."""
    por_ordem = {o["ordem"]: o for o in ordens}
    fila: dict[str, deque] = {"buy": deque(), "sell": deque()}
    fechadas: list[dict] = []
    for d in sorted(deals, key=lambda x: (x["t"], x["deal"])):
        if d["direcao"] == "in":
            lado = "buy" if d["tipo"] == "buy" else "sell"
            o = por_ordem.get(d["ordem"], {})
            fila[lado].append({
                "lado": lado, "t_in": d["t"], "vol": d["vol"] or 0.0, "preco": d["preco"] or 0.0,
                "sl": o.get("sl", 0.0) or 0.0, "tp": o.get("tp", 0.0) or 0.0,
                "ordem": d["ordem"], "comissao": d["comissao"] or 0.0,
                "comentario": o.get("comentario", d["comentario"])})
        elif d["direcao"] == "out":
            lado = "buy" if d["tipo"] == "sell" else "sell"      # venda fecha compra
            if not fila[lado]:
                continue
            p = fila[lado].popleft()
            p.update({"t_out": d["t"], "preco_out": d["preco"] or 0.0,
                      "classe": classe_saida(d["comentario"]), "cmt_out": d["comentario"],
                      "net": (d["lucro"] or 0.0) + (d["swap"] or 0.0) + (d["comissao"] or 0.0)
                      + p["comissao"]})
            fechadas.append(p)
    abertas = [p for f in fila.values() for p in f]
    return fechadas, abertas


def concorrencia_maxima(fechadas: list[dict], abertas: list[dict]) -> dict[str, int]:
    """Maximo de posicoes abertas ao mesmo tempo por lado."""
    eventos = []
    for p in fechadas:
        eventos += [(p["t_in"], 1, p["lado"]), (p["t_out"], -1, p["lado"])]
    for p in abertas:
        eventos.append((p["t_in"], 1, p["lado"]))
    eventos.sort(key=lambda e: (e[0], e[1]))      # saida antes da entrada no mesmo instante
    atual = {"buy": 0, "sell": 0}
    pico = {"buy": 0, "sell": 0}
    for _, delta, lado in eventos:
        atual[lado] += delta
        pico[lado] = max(pico[lado], atual[lado])
    return pico


# ---------------------------------------------------------------------------
# S1: assinatura de cada sistema
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Assinatura:
    sl: bool                                   # toda ordem de entrada leva SL
    tp: bool                                   # toda ordem de entrada leva TP
    saidas: frozenset                          # classes de saida permitidas
    exige: frozenset = frozenset()             # classes que precisam aparecer
    trail: bool = False                        # SL arrastado deixa rastro nas saidas
    be: bool = False                           # breakeven ligado por padrao no template
    grade: bool = False                        # varias pernas ao mesmo tempo


def _cs(*x: str) -> frozenset:
    return frozenset(x)


# Identidade de cada sistema, de generate_system_sets.apply_system. "fim" (fim do
# teste), "stopout" e "outro" nunca reprovam sozinhos; "outro" vira aviso.
ASSINATURA = {
    "01_SLTP": Assinatura(sl=True, tp=True, saidas=_cs("sl", "tp", "fim"), be=True),
    "02_SLTP_ORGANIC": Assinatura(sl=True, tp=True, saidas=_cs("sl", "tp", "vazio", "fim"), be=True),
    "03_TRAIL_ONLY": Assinatura(sl=True, tp=False, saidas=_cs("sl", "fim"), trail=True),
    "04_SLTP_TRAIL": Assinatura(sl=True, tp=True, saidas=_cs("sl", "tp", "fim"), trail=True),
    "05_BE_TRAIL": Assinatura(sl=True, tp=False, saidas=_cs("sl", "fim"), trail=True, be=True),
    "06_REVERSAL_EXIT": Assinatura(sl=True, tp=False, saidas=_cs("sl", "reversao", "fim"),
                                   exige=_cs("reversao")),
    "07_GRID_SEPARATE": Assinatura(sl=False, tp=False, saidas=_cs("cesta", "sl", "fim"),
                                   grade=True),
    "11_SIGNAL_ONLY": Assinatura(sl=False, tp=False, saidas=_cs("reversao", "fim"),
                                 exige=_cs("reversao")),
    "12_GRID_INVERSO": Assinatura(sl=True, tp=False, saidas=_cs("piramide", "sl", "fim"),
                                  grade=True),
    "13_OCO_ROMPIMENTO": Assinatura(sl=True, tp=True, saidas=_cs("sl", "tp", "fim"), trail=True),
}
AMOSTRA_MINIMA = 8          # fechadas para cobrar "precisa aparecer"
AMOSTRA_RASTRO = 15         # fechadas por SL para cobrar rastro de trailing/BE
TOL_BE = 0.03               # |saida - entrada| / distancia do SL inicial: breakeven (spread)
TOL_SL_INTACTO = 0.05       # saida a menos de 5% do SL inicial = stop nunca mexido


def classe_sl(p: dict) -> str | None:
    """Como uma saida por SL aconteceu, pela posicao da saida em relacao ao SL inicial:
    "inicial" (stop nunca mexido), "be" (stop levado ao preco de entrada), "trail"
    (qualquer outro ponto: o stop foi arrastado)."""
    dist0 = abs(p["preco"] - p["sl"]) if p["sl"] > 0 else 0.0
    if not dist0:
        return None
    sinal = 1 if p["lado"] == "buy" else -1
    r = sinal * (p["preco_out"] - p["preco"]) / dist0
    if r <= -1.0 + TOL_SL_INTACTO:
        return "inicial"
    if abs(r) <= TOL_BE:
        return "be"
    return "trail"


def _entradas_de_ordens(ordens: list[dict]) -> list[dict]:
    """Ordens que abriram posicao (executadas/preenchidas), a mercado ou pendente."""
    return [o for o in ordens if o["estado"] == "filled"]


def checar_assinatura(sistema: str, variante: str, ordens: list[dict], deals: list[dict],
                      info: dict, res: Resultado, params: dict | None = None) -> None:
    ass = ASSINATURA[sistema]
    if params:
        # o template TEM que carregar a identidade do sistema (flags cravadas no gerador)
        if _bool(params, "AtivarStop") != ass.sl:
            res.falha("template", f"AtivarStop={params.get('AtivarStop')} no set, mas o sistema "
                      f"{'tem' if ass.sl else 'nao tem'} stop loss")
        if not ass.grade and _bool(params, "AtivarTake") != ass.tp:
            res.falha("template", f"AtivarTake={params.get('AtivarTake')} no set, mas o sistema "
                      f"{'tem' if ass.tp else 'nao tem'} take profit")
    fechadas, abertas = operacoes(ordens, deals)
    todas = fechadas + abertas
    n = len(todas)
    res.metricas.update({"entradas": n, "fechadas": len(fechadas)})
    if n == 0:
        res.aviso("amostra", "0 trades na janela: sem evidencia")
        return

    # -- lado do arquivo ----------------------------------------------------
    lado_arq = variante.split("_")[0]
    lados = Counter(p["lado"] for p in todas)
    res.metricas["compras"], res.metricas["vendas"] = lados["buy"], lados["sell"]
    if lado_arq == "BUY" and lados["sell"]:
        res.falha("lado", f"arquivo BUY abriu {lados['sell']} vendas")
    if lado_arq == "SELL" and lados["buy"]:
        res.falha("lado", f"arquivo SELL abriu {lados['buy']} compras")
    if lado_arq == "BOTH" and n >= AMOSTRA_MINIMA and (not lados["buy"] or not lados["sell"]):
        res.aviso("lado", f"arquivo BOTH so operou um lado (compras {lados['buy']}, "
                  f"vendas {lados['sell']})")

    # -- SL / TP nas ordens de entrada --------------------------------------
    sem_sl = [p for p in todas if p["sl"] <= 0]
    com_sl = [p for p in todas if p["sl"] > 0]
    sem_tp = [p for p in todas if p["tp"] <= 0]
    com_tp = [p for p in todas if p["tp"] > 0]
    if ass.sl and sem_sl:
        res.falha("sl", f"{len(sem_sl)}/{n} entradas SEM stop loss num sistema com SL "
                  f"(ex.: ordem {sem_sl[0]['ordem']})")
    if not ass.sl and com_sl:
        res.falha("sl", f"{len(com_sl)}/{n} entradas COM stop loss num sistema sem SL "
                  f"(ex.: ordem {com_sl[0]['ordem']})")
    if ass.tp and sem_tp:
        res.falha("tp", f"{len(sem_tp)}/{n} entradas SEM take profit num sistema com TP "
                  f"(ex.: ordem {sem_tp[0]['ordem']})")
    if not ass.tp and com_tp:
        res.falha("tp", f"{len(com_tp)}/{n} entradas COM take profit num sistema sem TP "
                  f"(ex.: ordem {com_tp[0]['ordem']})")

    # -- lado do SL/TP em relacao ao preco de entrada ------------------------
    torto = []
    for p in todas:
        sinal = 1 if p["lado"] == "buy" else -1
        if p["sl"] > 0 and p["preco"] and sinal * (p["preco"] - p["sl"]) <= 0:
            torto.append(f"ordem {p['ordem']}: SL {p['sl']} do lado errado de {p['preco']}")
        if p["tp"] > 0 and p["preco"] and sinal * (p["tp"] - p["preco"]) <= 0:
            torto.append(f"ordem {p['ordem']}: TP {p['tp']} do lado errado de {p['preco']}")
    if torto:
        res.falha("lado_sl_tp", f"{len(torto)} ordens com SL/TP invertido; ex.: {torto[0]}")

    # -- classes de saida -----------------------------------------------------
    cont = Counter(p["classe"] for p in fechadas)
    res.metricas["saidas"] = dict(cont)
    proibidas = {c: k for c, k in cont.items() if c not in ass.saidas and c not in ("stopout", "outro")}
    if proibidas:
        res.falha("saidas", f"saidas que o sistema nao tem: {proibidas} (permitidas: "
                  f"{sorted(ass.saidas)})")
    if cont.get("outro"):
        exemplos = sorted({p["cmt_out"] for p in fechadas if p["classe"] == "outro"})[:3]
        res.aviso("saidas", f"{cont['outro']} saidas de classe desconhecida, ex.: {exemplos}")
    if cont.get("stopout"):
        res.aviso("stopout", f"{cont['stopout']} saidas por stop out da corretora")
    if len(fechadas) >= AMOSTRA_MINIMA:
        faltam = [c for c in ass.exige if not cont.get(c)]
        if faltam:
            res.falha("saidas", f"{len(fechadas)} posicoes fechadas e nenhuma saida do tipo "
                      f"{faltam} (o sistema sai por isso)")

    # -- stops: inicial x breakeven x arrastado, conferidos contra os flags do set -----
    sl_exits = [p for p in fechadas if p["classe"] == "sl" and p["sl"] > 0]
    cats = Counter(classe_sl(p) for p in sl_exits)
    res.metricas["sl_categorias"] = dict(cats)
    if params and sl_exits:
        n_sl = len(sl_exits)
        be_on, trail_on = _bool(params, "AtivarBreakeven"), _bool(params, "AtivarTrailATR")
        if not be_on and cats["be"] >= 3 and cats["be"] >= 0.15 * n_sl:
            res.falha("breakeven", f"{cats['be']}/{n_sl} saidas por SL no preco de entrada com "
                      "AtivarBreakeven=false")
        if not trail_on and cats["trail"] >= 2:
            res.falha("trailing", f"{cats['trail']}/{n_sl} saidas por SL com o stop arrastado com "
                      "AtivarTrailATR=false")
        if not be_on and not trail_on and cats["be"] + cats["trail"] >= 2:
            res.falha("stop", "stop mexido sem breakeven nem trailing ligados "
                      f"({dict(cats)})")
        if n_sl >= AMOSTRA_RASTRO:
            if trail_on and not cats["trail"]:
                res.aviso("trailing", f"{n_sl} saidas por SL e nenhuma arrastada com "
                          "AtivarTrailATR=true (trailing sem efeito nesta janela?)")
            if be_on and not cats["be"] and not ass.grade:
                res.aviso("breakeven", f"{n_sl} saidas por SL e nenhuma no breakeven com "
                          "AtivarBreakeven=true (BE sem efeito nesta janela?)")

    # -- grade: mais de uma perna ao mesmo tempo -------------------------------
    pico = concorrencia_maxima(fechadas, abertas)
    res.metricas["pico_pernas"] = max(pico.values())
    if ass.grade and n >= AMOSTRA_MINIMA and max(pico.values()) < 2:
        res.aviso("grade", "a grade nunca abriu uma segunda perna na janela")
    if not ass.grade and max(pico.values()) > 2 and lado_arq != "BOTH":
        res.aviso("pernas", f"{max(pico.values())} posicoes simultaneas num sistema sem grade")


# ---------------------------------------------------------------------------
# S2: recuperacao (Martingale / D'Alembert)
# ---------------------------------------------------------------------------

def estado_recuperacao(ops: list[dict], max_passos: int) -> tuple[float, int, bool]:
    """(divida, perdas seguidas, forcar lote base) do LADO, na ordem das operacoes
    fechadas -- ApplyRecoveryOperation do .mq5, passo a passo."""
    divida = 0.0
    seguidas = 0
    forcar_base = False
    for op in ops:
        if forcar_base:
            forcar_base = False
        if op["net"] < -EPS:
            divida += -op["net"]
            seguidas += 1
            if max_passos > 0 and seguidas > max_passos:
                divida, seguidas, forcar_base = 0.0, 0, True
            continue
        if divida <= EPS:
            continue
        seguidas = 0
        if op["net"] > EPS:
            divida -= min(op["net"], divida)
            if divida <= EPS:
                divida, seguidas = 0.0, 0
    return divida, seguidas, forcar_base


def passos_dalembert(ops: list[dict], max_passos: int) -> int:
    """Nivel do D'Alembert do lado (RefreshDAlembertState): +1 por perda, -1 por
    ganho (piso 0), limitado a MaxMartingaleSteps."""
    n = 0
    for op in ops:
        if op["net"] < 0.0:
            n += 1
        elif op["net"] > 0.0:
            n = max(0, n - 1)
        if max_passos > 0:
            n = min(n, max_passos)
    return n


def valor_r(params: dict) -> float:
    """1R em moeda, como o OnInit da EA congela: PositionSizeValue% do capital base
    (CapitalBaseR, ou o saldo se 0), reduzido por TradeCapitalPercentage quando em (0,100]."""
    base = _flt(params, "CapitalBaseR") or _flt(params, "_deposito")
    pct = _flt(params, "TradeCapitalPercentage", 100.0)
    if 0 < pct <= 100:
        base *= pct / 100.0
    return _flt(params, "PositionSizeValue") / 100.0 * base


def _piso(valor: float, passo: float) -> float:
    return math.floor(valor / passo + 1e-9) * passo


def lotes_possiveis(p: dict, ops_antes: list[dict], ops_lado_incl: list[dict],
                    params: dict, info: dict, estrito: bool = True
                    ) -> tuple[list[tuple[float, float]], dict]:
    """Faixas [lo, hi] de lote que a EA poderia ter usado na entrada `p`, dado o
    historico do lado (faixa de largura zero = valor exato). Ha mais de uma so
    quando existe operacao fechada no MESMO segundo da entrada (ordem indefinida
    entre o fechamento e a nova entrada). `estrito=False`: o TP da ordem nao e o
    da formula (02 organico) -- vale qualquer lote entre a base e o teto de R."""
    modo = _int(params, "PositionSizeMode", 2)
    rec = _int(params, "RecoveryMode")
    passo = info.get("vol_step") or 0.01
    vmin = info.get("vol_min") or passo
    vmax = info.get("vol_max") or 1e9
    contrato = info.get("contrato") or 100.0
    conv = 1.0                                           # simbolos cotados em USD
    max_passos = _int(params, "MaxMartingaleSteps")
    mult = _flt(params, "Multiplicador", 1.0)
    estados = [ops_antes]
    if len(ops_lado_incl) != len(ops_antes):
        estados.append(ops_lado_incl)
    saida: list[tuple[float, float]] = []
    detalhe: dict = {}
    for ops in estados:
        if rec == 2:                                     # D'Alembert (Lote Fixo)
            base = _flt(params, "PositionSizeValue")
            n = passos_dalembert(ops, max_passos)
            lote = base + n * _flt(params, "DAlembertStep")
            teto = _flt(params, "MaxMartingaleLot")
            if teto > 0:
                lote = min(lote, teto)
            detalhe = {"base": base, "n": n}
            v = round(min(max(lote, vmin), vmax), 8)
            saida.append((v, v))
            continue
        divida, _, forcar = estado_recuperacao(ops, max_passos)
        detalhe = {"divida": round(divida, 2), "forcar_base": forcar}
        if modo == 2:                                    # Martingale em Lote Fixo
            base = _flt(params, "PositionSizeValue")
            lote = base
            if ops and not forcar and ops[-1]["net"] < 0 and ops[-1]["vol"] > 0:
                lote = ops[-1]["vol"] * mult
            v = round(min(max(lote, vmin), vmax), 8)
            detalhe["base"] = base
            saida.append((v, v))
            continue
        if modo != 3:
            continue                                     # outros modos nao sao cobertos
        r = valor_r(params)
        cap = _flt(params, "MaxRiscoTradeR")
        dist_sl = abs(p["preco"] - p["sl"])
        if dist_sl <= 0:
            continue
        por_lote_sl = dist_sl * contrato * conv
        base = max(vmin, _piso(r / por_lote_sl, passo))
        detalhe["base"] = base
        teto_lote = max(vmin, _piso(cap * r / por_lote_sl, passo)) if cap > 0 else vmax
        if not estrito and p["tp"] > 0 and not forcar and divida > EPS:
            saida.append((base, min(teto_lote, vmax)))
            continue
        lote = base
        if not forcar and divida > EPS:
            if p["tp"] > 0:
                alvo = divida * mult / (abs(p["tp"] - p["preco"]) * contrato * conv)
            else:
                alvo = divida * mult / por_lote_sl
            lote = max(base, alvo)
        if cap > 0:
            lote = min(lote, cap * r / por_lote_sl)
        lote = max(vmin, _piso(lote, passo))
        v = round(min(lote, vmax), 8)
        saida.append((v, v))
    return saida, detalhe


def checar_recuperacao(sistema: str, params: dict, ordens: list[dict], deals: list[dict],
                       info: dict, res: Resultado) -> None:
    rec = _int(params, "RecoveryMode")
    fechadas, abertas = operacoes(ordens, deals)
    todas = sorted(fechadas + abertas, key=lambda p: p["t_in"])
    res.metricas.update({"entradas": len(todas), "fechadas": len(fechadas),
                         "recuperacao": {1: "martingale", 2: "dalembert"}.get(rec, "nenhuma")})
    if len(todas) < 5:
        res.aviso("amostra", f"so {len(todas)} entradas: evidencia fraca")
        return
    if not info.get("contrato"):
        res.aviso("info", "sem info do simbolo (contrato/passo): o modelo de lote nao pode ser conferido")
        return
    pico = concorrencia_maxima(fechadas, abertas)
    if max(pico.values()) > 1:
        res.aviso("pareamento", f"ate {max(pico.values())} posicoes por lado ao mesmo tempo: o "
                  "pareamento FIFO entrada/saida e aproximado")
    passo = info.get("vol_step") or 0.01
    modo = _int(params, "PositionSizeMode", 2)
    conferidas = erradas = com_divida = acima_base = 0
    exemplos: list[str] = []
    lotes_base: list[float] = []
    for p in todas:
        ops_lado = sorted((f for f in fechadas if f["lado"] == p["lado"] and f is not p),
                          key=lambda f: f["t_out"])
        antes = [f for f in ops_lado if f["t_out"] < p["t_in"]]
        incl = [f for f in ops_lado if f["t_out"] <= p["t_in"]]
        possiveis, det = lotes_possiveis(p, antes, incl, params, info,
                                         estrito=sistema != "02_SLTP_ORGANIC")
        if not possiveis:
            continue
        conferidas += 1
        if det.get("divida", 0) > EPS or det.get("n", 0) > 0:
            com_divida += 1
        if any(lo - passo * 1.01 <= p["vol"] <= hi + passo * 1.01 for lo, hi in possiveis):
            if det.get("base") and p["vol"] > det["base"] + passo * 0.99:
                acima_base += 1
            continue
        erradas += 1
        if len(exemplos) < 3:
            exemplos.append(f"{p['t_in']:%m.%d %H:%M:%S} {p['lado']} lote {p['vol']} "
                            f"esperado {possiveis} ({det})")
    res.metricas.update({"conferidas": conferidas, "divergentes": erradas,
                         "entradas_com_divida": com_divida, "lote_acima_da_base": acima_base})
    if erradas:
        res.falha("lote", f"{erradas}/{conferidas} entradas com lote diferente do modelo da EA "
                  f"({'D' + chr(39) + 'Alembert' if rec == 2 else 'Martingale'}, "
                  f"{tp.MODOS_SIZING.get(modo)}); ex.: {exemplos[0]}")
    if conferidas and not com_divida:
        res.aviso("amostra", "nenhuma entrada com divida/passo ativo: a recuperacao nao foi exercitada")
    elif conferidas and com_divida and not acima_base and rec == 2:
        res.aviso("amostra", "D'Alembert nunca subiu o lote acima da base")
    teto_r = _flt(params, "MaxRiscoTradeR")
    if modo == 3 and teto_r > 0:
        r = valor_r(params)
        contrato = info.get("contrato") or 100.0
        vmin = info.get("vol_min") or passo
        # folga de um passo: o lote base promovido ao minimo do corretor pode passar do teto
        estouro = []
        for p in todas:
            if p["sl"] <= 0:
                continue
            dist = abs(p["preco"] - p["sl"])
            if p["vol"] * dist * contrato > teto_r * r + max(passo, vmin) * dist * contrato + 1e-6:
                estouro.append(p)
        res.metricas["acima_do_teto_de_R"] = len(estouro)
        if estouro:
            res.falha("teto_r", f"{len(estouro)} entradas arriscam mais que {teto_r:g}R "
                      f"(ex.: ordem {estouro[0]['ordem']})")


# ---------------------------------------------------------------------------
# S3: travas de risco da conta
# ---------------------------------------------------------------------------

FOLGA_TRAVA = 1.05          # a ancora da EA e o equity do 1o tick do dia; o saldo pode diferir um pouco


def saldo_por_fechamento(fechadas: list[dict], deposito: float) -> list[tuple[datetime, float]]:
    """[(hora do fechamento, saldo depois)] em ordem de fechamento."""
    saldo = deposito
    saida = []
    for p in sorted(fechadas, key=lambda x: x["t_out"]):
        saldo += p["net"]
        saida.append((p["t_out"], saldo))
    return saida


def violacoes_trava_diaria(fechadas: list[dict], todas: list[dict], deposito: float,
                           limite_pct: float) -> tuple[int, int]:
    """(dias em que a perda REALIZADA do dia passou o limite, entradas abertas depois disso
    no mesmo dia). A EA bloqueia por equity (que inclui o flutuante), entao ela bloqueia
    antes ou junto da perda realizada, nunca depois: entrada depois do estouro realizado
    e violacao. Dia que comeca com posicao aberta e pulado (ancora com flutuante)."""
    dias_estouro = violacoes = 0
    for dia in sorted({p["t_out"].date() for p in fechadas}):
        inicio = datetime.combine(dia, hora.min)
        if any(p["t_in"] < inicio <= p["t_out"] for p in fechadas):
            continue
        ancora = deposito + sum(p["net"] for p in fechadas if p["t_out"] < inicio)
        acumulado, t_estouro = 0.0, None
        for p in sorted((x for x in fechadas if x["t_out"].date() == dia), key=lambda x: x["t_out"]):
            acumulado += p["net"]
            if acumulado <= -limite_pct / 100.0 * ancora * FOLGA_TRAVA:
                t_estouro = p["t_out"]
                break
        if t_estouro is None:
            continue
        dias_estouro += 1
        violacoes += sum(1 for p in todas
                         if p["t_in"].date() == dia and p["t_in"] > t_estouro + timedelta(seconds=1))
    return dias_estouro, violacoes


def violacoes_trava_total(fechadas: list[dict], todas: list[dict], deposito: float,
                          limite_pct: float) -> tuple[datetime | None, int]:
    """(hora do estouro, entradas depois dele). A trava total e PERMANENTE."""
    piso = deposito * (1.0 - limite_pct / 100.0)
    for quando, saldo in saldo_por_fechamento(fechadas, deposito):
        if saldo <= piso:
            return quando, sum(1 for p in todas if p["t_in"] > quando + timedelta(seconds=1))
    return None, 0


def checar_travas(params: dict, ordens: list[dict], deals: list[dict], log: str,
                  res: Resultado) -> None:
    fechadas, abertas = operacoes(ordens, deals)
    todas = fechadas + abertas
    deposito = _flt(params, "_deposito")
    fecha = _bool(params, "Protecao_Fecha_Posicoes")
    perda_magic = _flt(params, "DailyLossLimitPercent")
    gp_dia = _flt(params, "Trava_Diaria_Percent")
    gp_total = _flt(params, "Trava_Total_Percent")
    res.metricas.update({"entradas": len(todas), "fechadas": len(fechadas)})
    if len(todas) < 5:
        res.aviso("amostra", f"so {len(todas)} entradas: evidencia fraca")
        return
    if not deposito:
        res.aviso("info", "sem deposito no registro: a trava nao pode ser conferida")
        return
    for rotulo, limite in (("perda diaria (magic)", perda_magic), ("trava diaria global", gp_dia)):
        if limite <= 0:
            continue
        dias, viol = violacoes_trava_diaria(fechadas, todas, deposito, limite)
        res.metricas[f"dias_estouro_{'magic' if 'magic' in rotulo else 'gp'}"] = dias
        res.metricas[f"entradas_apos_estouro_{'magic' if 'magic' in rotulo else 'gp'}"] = viol
        if viol:
            res.falha("trava", f"{rotulo} de {limite:g}%: {viol} entrada(s) abertas DEPOIS de a perda "
                      f"do dia passar o limite ({dias} dia(s) com estouro)")
        elif dias < 3:
            res.aviso("amostra", f"{rotulo}: so {dias} dia(s) com estouro -- a trava quase nao foi "
                      "exercitada")
    if gp_total > 0:
        quando, viol = violacoes_trava_total(fechadas, todas, deposito, gp_total)
        res.metricas["estouro_total"] = None if quando is None else f"{quando:%m.%d %H:%M:%S}"
        res.metricas["entradas_apos_estouro_total"] = viol
        if quando is None:
            res.aviso("amostra", f"trava total de {gp_total:g}% nunca foi rompida nesta janela")
        elif viol:
            res.falha("trava", f"trava TOTAL de {gp_total:g}% rompida em {quando:%m.%d %H:%M:%S} e "
                      f"{viol} entrada(s) depois (a trava e permanente)")
    if gp_dia > 0 or gp_total > 0:
        fechamentos = sum(1 for p in fechadas if p["classe"] == "vazio")
        res.metricas["fechamentos_da_protecao"] = fechamentos
        if not fecha and fechamentos:
            res.falha("trava", f"Protecao_Fecha_Posicoes=false e {fechamentos} posicao(oes) fechadas "
                      "sem SL/TP/saida da estrategia (a protecao so deveria BLOQUEAR entradas)")
        if fecha and not fechamentos:
            res.aviso("trava", "Protecao_Fecha_Posicoes=true e nenhum fechamento de emergencia "
                      "(nenhuma posicao estava aberta quando a trava rompeu?)")
        if "Protecao Global" not in log and (res.metricas.get("dias_estouro_gp")
                                             or res.metricas.get("estouro_total")):
            res.aviso("log", "trava rompida mas sem a linha '[Protecao Global]' no log")


# ---------------------------------------------------------------------------
# S4: filtros de execucao (hora, dia da semana, spread)
# ---------------------------------------------------------------------------

DIAS_MT5 = (("TradeSunday", 0), ("TradeMonday", 1), ("TradeTuesday", 2), ("TradeWednesday", 3),
            ("TradeThursday", 4), ("TradeFriday", 5), ("TradeSaturday", 6))


def dentro_da_janela(minuto: int, de: int, ate: int) -> bool:
    """inTimeInterval do .mq5: [de, ate) em minutos do dia; de == ate = 24 h; de > ate =
    sessao que atravessa a meia-noite."""
    if de == ate:
        return True
    if de < ate:
        return de <= minuto < ate
    return minuto >= de or minuto < ate


def ordens_de_entrada(ordens: list[dict], deals: list[dict]) -> list[dict]:
    """Ordens que ABREM posicao (a mercado ou pendente, executada ou nao): as de saida
    (SL/TP/reversao) tambem aparecem na tabela e nao passam por filtro nenhum."""
    entradas = {d["ordem"] for d in deals if d["direcao"] == "in"}
    return [o for o in ordens if o["tipo"] in tp.TIPOS_PEND or o["ordem"] in entradas]


def checar_filtros_execucao(params: dict, ordens: list[dict], deals: list[dict], barras,
                            res: Resultado) -> None:
    ent = ordens_de_entrada(ordens, deals)
    res.metricas["ordens_de_entrada"] = len(ent)
    if len(ent) < 5:
        res.aviso("amostra", f"so {len(ent)} ordens de entrada: evidencia fraca")
        return
    # -- janela de horario ------------------------------------------------------------
    de = _int(params, "TOD_From_Hour") * 60 + _int(params, "TOD_From_Min")
    ate = _int(params, "TOD_To_Hour") * 60 + _int(params, "TOD_To_Min")
    if de != ate:
        fora = [o for o in ent if not dentro_da_janela(o["abertura"].hour * 60
                                                       + o["abertura"].minute, de, ate)]
        res.metricas["fora_da_janela"] = len(fora)
        if fora:
            res.falha("janela", f"{len(fora)}/{len(ent)} ordens colocadas fora de "
                      f"{de // 60:02d}:{de % 60:02d}-{ate // 60:02d}:{ate % 60:02d} "
                      f"(ex.: {fora[0]['abertura']:%m.%d %H:%M:%S})")
    # -- dias da semana ------------------------------------------------------------------
    proibidos = {dow for nome, dow in DIAS_MT5 if not _bool(params, nome)}
    if proibidos:
        em_dia_proibido = [o for o in ent if (o["abertura"].weekday() + 1) % 7 in proibidos]
        res.metricas["em_dia_proibido"] = len(em_dia_proibido)
        if em_dia_proibido:
            res.falha("dia", f"{len(em_dia_proibido)}/{len(ent)} ordens em dia da semana desligado "
                      f"(ex.: {em_dia_proibido[0]['abertura']:%a %m.%d %H:%M:%S})")
    # -- spread maximo -------------------------------------------------------------------
    limite = _flt(params, "MaxSpread")
    if limite > 0:
        m1 = barras.dfs.get("M1") if barras is not None else None
        if m1 is None or "spread" not in m1.columns:
            res.aviso("spread", "sem barras M1 com spread: o filtro de spread nao pode ser conferido")
            return
        import pandas as pd
        acima = medidas = 0
        exemplo = None
        for o in ent:
            minuto = pd.Timestamp(o["abertura"]).floor("min")
            if minuto not in m1.index:
                continue
            medidas += 1
            # a EA olha o spread do tick da decisao; a barra M1 anterior cobre o caso de a
            # ordem sair no primeiro segundo de uma barra de spread diferente
            anterior = m1["spread"].get(minuto - pd.Timedelta(minutes=1))
            atual = float(m1["spread"].loc[minuto])
            if atual > limite and (anterior is None or float(anterior) > limite):
                acima += 1
                exemplo = exemplo or f"{o['abertura']:%m.%d %H:%M:%S} spread {atual:g}"
        res.metricas["spread_medidas"] = medidas
        res.metricas["acima_do_spread"] = acima
        if acima:
            res.falha("spread", f"{acima}/{medidas} ordens com spread da barra acima de {limite:g} "
                      f"pontos (ex.: {exemplo})")
        elif medidas < 5:
            res.aviso("amostra", f"so {medidas} ordens com barra M1 para conferir o spread")


# ---------------------------------------------------------------------------
# S5: ablacao de boosters -- quais combinacoes rendem mais
# ---------------------------------------------------------------------------

# Sistemas que aceitam a recuperacao (= generate_system_sets.SISTEMAS_RECUPERACAO_OPCIONAL; o teste confere)
RECUPERAVEIS = {"01_SLTP", "02_SLTP_ORGANIC", "03_TRAIL_ONLY", "04_SLTP_TRAIL", "05_BE_TRAIL",
                "06_REVERSAL_EXIT", "11_SIGNAL_ONLY"}
# a = ~90 dias que o treino dos sets nunca viu (holdout lacrado); b = os ~90 dias ANTERIORES (o
# treino ja viu a base -- serve pra ver se o efeito do booster se repete, nao como prova)
JANELAS_S5 = {"a": ("2026.06.28", "2026.09.26"), "b": ("2026.03.28", "2026.06.27")}
# chave -> (set pronto da biblioteca, simbolo, sistema, variante). Campeoes e reprovados da campanha:
# o que interessa aqui e o EFEITO do booster sobre uma config otimizada, nao o edge da base.
BASES_S5 = {
    "xau04": ("VALIDADO_XAUUSD_04_SLTP_TRAIL_BUY_MULTI.set", "XAUUSD", "04_SLTP_TRAIL", "BUY_MULTI"),
    "cad07": ("VALIDADO_USDCAD_07_GRID_SEPARATE_BUY_MULTI.set", "USDCAD", "07_GRID_SEPARATE", "BUY_MULTI"),
    "nvda04": ("REPROVADO_NVDA_04_SLTP_TRAIL_BUY_MULTI.set", "NVDA", "04_SLTP_TRAIL", "BUY_MULTI"),
    "gbp03": ("REPROVADO_GBPUSD_03_TRAIL_ONLY_BOTH_MULTI.set", "GBPUSD", "03_TRAIL_ONLY", "BOTH_MULTI"),
    "gbp02": ("REPROVADO_GBPUSD_02_SLTP_ORGANIC_BOTH_MULTI.set", "GBPUSD", "02_SLTP_ORGANIC", "BOTH_MULTI"),
}
SPREAD_S5 = {"XAUUSD": "12", "GBPUSD": "15", "USDCAD": "15"}        # pontos; acoes ficam sem
JANELA_LIVRE = {"TOD_From_Hour": "0", "TOD_From_Min": "0", "TOD_To_Hour": "23", "TOD_To_Min": "55"}
# Subtrativos: o que o circuito EMPILHOU em cada set (lido dos sets de 29/09) e que da pra tirar.
# 'so_sistema' = todos tirados de uma vez (o sistema pelado). Referencia = o campeao como salvo.
SUBTRATIVAS_S5 = {
    "xau04": [("sem_ma", {"AtivarFiltroMA": "false"}), ("sem_adx", {"AtivarFiltroADX": "false"}),
              ("sem_mtf", {"AtivarFiltroMTF": "false"}),
              ("sem_filtros", {"AtivarFiltroMA": "false", "AtivarFiltroADX": "false",
                               "AtivarFiltroMTF": "false"}),
              ("sem_janela", dict(JANELA_LIVRE)), ("sem_spread", {"MaxSpread": "0"}),
              ("so_sistema", {"EntryOrderType": "0", "AtivarFiltroMA": "false", "AtivarFiltroADX": "false",
                              "AtivarFiltroMTF": "false", "MaxSpread": "0", **JANELA_LIVRE})],
    "cad07": [("sem_janela", dict(JANELA_LIVRE))],
    "nvda04": [("sem_mtf", {"AtivarFiltroMTF": "false"})],
    "gbp03": [("sem_adx", {"AtivarFiltroADX": "false"}), ("sem_mtf", {"AtivarFiltroMTF": "false"}),
              ("sem_janela", dict(JANELA_LIVRE)), ("sem_spread", {"MaxSpread": "0"}),
              ("sem_sexta", {"TradeFriday": "true"}),
              ("so_sistema", {"AtivarFiltroADX": "false", "AtivarFiltroMTF": "false", "MaxSpread": "0",
                              "TradeFriday": "true", **JANELA_LIVRE})],
    "gbp02": [("sem_ma", {"AtivarFiltroMA": "false"}), ("sem_janela", dict(JANELA_LIVRE)),
              ("sem_spread", {"MaxSpread": "0"}), ("sem_quarta", {"TradeWednesday": "true"}),
              ("so_sistema", {"AtivarFiltroMA": "false", "MaxSpread": "0", "TradeWednesday": "true",
                              **JANELA_LIVRE})],
}
# variante que E o campeao como salvo (a mercado, exceto o XAUUSD, cujo set ja traz a Limit k=0)
CAMPEAO_S5 = {"xau04": "limit_k0"}
PENDENTE_S5 = {"PendingReferencia": "0", "PendingExpiracaoBarras": "3"}
# variante que serve de referencia pra cada uma (a soma de lotes do D'Alembert e em lote fixo)
REFERENCIA_S5 = {"dalembert": "lote_fixo"}


def referencia_s5(chave: str | None, nome: str) -> str:
    """Contra quem cada variante e comparada: os subtrativos contra o campeao como salvo, o
    D'Alembert contra o lote fixo, o resto contra a mercado."""
    if nome in REFERENCIA_S5:
        return REFERENCIA_S5[nome]
    if chave and any(nome == n for n, _ in SUBTRATIVAS_S5.get(chave, [])):
        return CAMPEAO_S5.get(chave, "mercado")
    return "mercado"


def variantes_s5(sistema: str, lado: str, simbolo: str, chave: str | None = None
                 ) -> list[tuple[str, dict]]:
    v: list[tuple[str, dict]] = [
        ("mercado", {"EntryOrderType": "0"}),
        ("limit_k0", {"EntryOrderType": "2", "PendingReferencia": "0", "PendingDistanciaATR": "0",
                      "PendingExpiracaoBarras": "1"}),
        ("limit_k05", {"EntryOrderType": "2", "PendingDistanciaATR": "0.5", **PENDENTE_S5}),
        ("stop_k05", {"EntryOrderType": "1", "PendingDistanciaATR": "0.5", **PENDENTE_S5}),
        ("janela_7_20", {"TOD_From_Hour": "7", "TOD_From_Min": "0", "TOD_To_Hour": "20",
                         "TOD_To_Min": "0"}),
        ("janela_13_20", {"TOD_From_Hour": "13", "TOD_From_Min": "0", "TOD_To_Hour": "20",
                          "TOD_To_Min": "0"}),
        ("atr_alto", {"EntradaATR": "true"}),
        ("filtro_ma", {"AtivarFiltroMA": "true"}),
        ("filtro_adx", {"AtivarFiltroADX": "true"}),
    ]
    if simbolo in SPREAD_S5:
        v.append(("spread", {"MaxSpread": SPREAD_S5[simbolo]}))
    if lado == "BOTH":
        v.append(("oco_sinal", {"EntryOrderType": "3", "PendingReferencia": "1",
                                "PendingDistanciaATR": "0.5", "PendingExpiracaoBarras": "4",
                                "Hedging": "true"}))
    if sistema in RECUPERAVEIS:
        lote_fixo = {"EntryOrderType": "0", "PositionSizeMode": "2", "PositionSizeValue": "0.01"}
        v += [("martingale", {"EntryOrderType": "0", "RecoveryMode": "1", "MaxMartingaleSteps": "3",
                              "MinFreeMarginPercent": "20"}),
              ("lote_fixo", lote_fixo),
              ("dalembert", {**lote_fixo, "RecoveryMode": "2", "DAlembertStep": "0.01",
                             "MaxMartingaleSteps": "3", "MinFreeMarginPercent": "20"})]
    if chave:
        v += SUBTRATIVAS_S5.get(chave, [])
    return v


def metricas_de_curva(fechadas: list[dict], deposito: float, r_valor: float | None = None) -> dict:
    """Lucro, PF, taxa de acerto e queda maxima da curva de saldo (fechamentos em ordem)."""
    nets = [p["net"] for p in sorted(fechadas, key=lambda x: x["t_out"])]
    ganhos = sum(x for x in nets if x > 0)
    perdas = -sum(x for x in nets if x < 0)
    saldo = pico = deposito
    dd = 0.0
    for x in nets:
        saldo += x
        pico = max(pico, saldo)
        dd = max(dd, (pico - saldo) / pico * 100.0 if pico else 0.0)
    lucro = sum(nets)
    return {"trades": len(nets), "lucro": round(lucro, 2),
            "r": None if not r_valor else round(lucro / r_valor, 2),
            "pf": None if perdas <= 0 else round(ganhos / perdas, 2),
            "acerto": None if not nets else round(100.0 * sum(1 for x in nets if x > 0) / len(nets), 1),
            "dd": round(dd, 2)}


AMOSTRA_MIN_S5 = 10        # trades dos dois lados pra dar veredito
MATERIAL_S5 = 0.01         # diferenca abaixo de 1% do deposito = irrelevante
ESVAZIOU_S5 = 0.3          # variante com menos de 30% dos trades da referencia "esvaziou" a estrategia


def tabela_ablacao(dados: dict[str, dict], chave: str | None = None) -> list[dict]:
    """dados: variante -> {"deals": [...], "fechadas": [...], "deposito": x, "r": y}. Uma linha por
    variante: metricas, diferenca de lucro e semanal (t) contra a referencia, e a CLASSE da linha
    (referencia / igual / esvaziou / pequena / irrelevante / valida)."""
    linhas = []
    for nome, d in dados.items():
        m = metricas_de_curva(d["fechadas"], d["deposito"], d.get("r"))
        ref = referencia_s5(chave, nome)
        linha = {"variante": nome, **m, "deposito": d["deposito"], "ref": ref if ref in dados else None,
                 "delta": None, "t": None, "ref_trades": None}
        if nome != ref and ref in dados:
            r = dados[ref]
            mr = metricas_de_curva(r["fechadas"], r["deposito"], r.get("r"))
            c = tp.comparar_semanal(d["deals"], r["deals"])
            linha["delta"] = round(m["lucro"] - mr["lucro"], 2)
            linha["t"] = c.get("t")
            linha["ref_trades"] = mr["trades"]
        linha["classe"] = classe_s5(linha)
        linhas.append(linha)
    return linhas


def classe_s5(linha: dict) -> str:
    if linha["ref"] is None or linha["delta"] is None:
        return "referencia"
    if linha["trades"] == linha["ref_trades"] and abs(linha["delta"]) < 0.005:
        return "igual"                                    # o set ja tinha esse booster (ou nao mudou nada)
    if linha["ref_trades"] and linha["trades"] < ESVAZIOU_S5 * linha["ref_trades"]:
        return "esvaziou"
    if min(linha["trades"], linha["ref_trades"] or 0) < AMOSTRA_MIN_S5:
        return "pequena"
    if abs(linha["delta"]) < MATERIAL_S5 * linha["deposito"]:
        return "irrelevante"
    return "valida"


def veredito_s5(linha: dict) -> str:
    c = linha["classe"]
    if c == "referencia":
        return "referencia"
    if c == "igual":
        return "sem efeito (a config ja era assim)"
    if c == "esvaziou":
        return f"esvazia a estrategia ({linha['trades']} de {linha['ref_trades']} trades)"
    if c == "pequena":
        return f"amostra pequena (< {AMOSTRA_MIN_S5} trades)"
    if c == "irrelevante":
        return f"diferenca irrelevante (< {MATERIAL_S5:.0%} do deposito)"
    lado = "melhora" if linha["delta"] > 0 else "piora"
    forte = linha["t"] is not None and abs(linha["t"]) >= 2
    return f"{lado} (significativo)" if forte else f"{lado}, mas dentro do ruido"


def prefixo_s5(janela: str) -> str:
    return "s5" if janela == "a" else f"s5{janela}"


def _dados_s5(janela: str, chave: str, sistema: str, lado_var: str, simbolo: str) -> dict:
    dados = {}
    for nome, _ in variantes_s5(sistema, lado_var.split("_")[0], simbolo, chave):
        j = SAIDA / f"{prefixo_s5(janela)}_{chave}_{nome}.json"
        htm = SAIDA / f"{prefixo_s5(janela)}_{chave}_{nome}.htm"
        if not (j.exists() and htm.exists()):
            continue
        reg = json.loads(j.read_text(encoding="utf-8"))
        ordens, deals = parse_relatorio(htm)
        fech, _ab = operacoes(ordens, deals)
        params = dict(reg["params"])
        params["_deposito"] = reg.get("deposito", 0)
        r = valor_r(params) if _int(params, "PositionSizeMode", 2) == 3 else None
        dados[nome] = {"deals": deals, "fechadas": fech, "deposito": reg.get("deposito", 0), "r": r}
    return dados


def consistencia_s5(a: dict, b: dict) -> str:
    """Leitura de uma variante nas duas janelas (linhas de tabela_ablacao)."""
    ca, cb = a.get("classe", "referencia"), b.get("classe", "referencia")
    if ca == cb == "referencia":
        return "referencia"
    if ca == "valida" and cb == "valida":
        forte = any(x.get("t") is not None and abs(x["t"]) >= 2 for x in (a, b))
        if a["delta"] > 0 and b["delta"] > 0:
            return "CANDIDATO: melhora nas duas" + (" (significativo numa)" if forte else "")
        if a["delta"] < 0 and b["delta"] < 0:
            return "piora nas duas" + (" (significativo numa)" if forte else "")
        return "inconsistente (muda de sinal)"
    if ca == "valida" or cb == "valida":
        outra = cb if ca == "valida" else ca
        return f"so uma janela tem base para julgar (a outra: {outra})"
    if ca == cb == "igual":
        return "sem efeito (a config ja era assim)"
    return f"sem base para julgar ({ca} / {cb})"


def teste_dos_sinais(pos: int, neg: int) -> float | None:
    """p-valor bilateral do teste dos sinais (binomial, p = 0.5) sobre os pares que mudaram."""
    n = pos + neg
    if n == 0:
        return None
    k = min(pos, neg)
    from math import comb
    p_unilat = sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p_unilat)


def placar_s5(por_par: dict[tuple, dict[str, dict]]) -> list[dict]:
    """por_par: (base, janela) -> {variante: linha}. Junta, por variante, os pares (base x janela) em
    que a linha e VALIDA (mesmo criterio de amostra e materialidade) e conta os sinais."""
    acum: dict[str, dict] = {}
    for _par, linhas in por_par.items():
        for nome, x in linhas.items():
            a = acum.setdefault(nome, {"variante": nome, "pares": 0, "pos": 0, "neg": 0, "esvaziou": 0,
                                       "sem_efeito": 0, "pct": []})
            if x["classe"] == "valida":
                a["pares"] += 1
                a["pct"].append(100.0 * x["delta"] / x["deposito"])
                a["pos" if x["delta"] > 0 else "neg"] += 1
            elif x["classe"] == "esvaziou":
                a["esvaziou"] += 1
            elif x["classe"] == "igual":
                a["sem_efeito"] += 1
    saida = []
    for a in acum.values():
        pcts = sorted(a["pct"])
        mediana = None if not pcts else (pcts[len(pcts) // 2] if len(pcts) % 2 else
                                         (pcts[len(pcts) // 2 - 1] + pcts[len(pcts) // 2]) / 2)
        p_ = teste_dos_sinais(a["pos"], a["neg"])
        if a["pares"] >= 5 and p_ is not None and p_ <= 0.10:
            leitura = "tende a AJUDAR" if a["pos"] > a["neg"] else "tende a ATRAPALHAR"
        elif a["pares"] < 5:
            leitura = "poucos pares validos" + (" (esvazia a estrategia)" if a["esvaziou"] >= 3 else "")
        else:
            leitura = "sem tendencia clara" + (" (esvazia a estrategia)" if a["esvaziou"] >= 3 else "")
        saida.append({**a, "mediana_pct": None if mediana is None else round(mediana, 2), "p": p_,
                      "leitura": leitura})
    return sorted(saida, key=lambda z: (z["mediana_pct"] is None, -(z["mediana_pct"] or 0)))


def relatorio_ablacao() -> str:
    _preparar()
    saida = ["ABLACAO DE BOOSTERS sobre sets ja otimizados da biblioteca",
             "janela a = " + " a ".join(JANELAS_S5["a"]) + " (o treino dos sets nunca viu); "
             "janela b = " + " a ".join(JANELAS_S5["b"]) + " (o treino viu a BASE; o booster nao foi ajustado)",
             "lucro em $; R = lucro / 1R (so sets Fixed-R); t = diferenca semanal contra a referencia. "
             f"So vira veredito a linha com >= {AMOSTRA_MIN_S5} trades nos dois lados e diferenca >= "
             f"{MATERIAL_S5:.0%} do deposito; o resto e ruido ou config que ja era assim. INDICIO, nao prova.", ""]
    por_par: dict[tuple, dict[str, dict]] = {}
    for chave, (arq, simbolo, sistema, lado_var) in BASES_S5.items():
        tabelas = {}
        for jn in JANELAS_S5:
            dados = _dados_s5(jn, chave, sistema, lado_var, simbolo)
            if not dados:
                continue
            linhas = tabela_ablacao(dados, chave)
            tabelas[jn] = {x["variante"]: x for x in linhas}
            por_par[(chave, jn)] = tabelas[jn]
            saida.append(f"== {chave}: {sistema} {lado_var} {simbolo} | janela {jn}  "
                         f"(* = o campeao como salvo no set)")
            saida.append(f"  {'variante':14} {'trades':>6} {'lucro$':>9} {'R':>7} {'PF':>5} {'acerto%':>7} "
                         f"{'queda%':>6} {'d lucro$':>9} {'t':>6}  veredito")
            campeao = CAMPEAO_S5.get(chave, "mercado")
            for x in sorted(linhas, key=lambda z: (z["variante"] != "mercado", z["variante"] != campeao,
                                                   -(z["lucro"] or 0))):
                marca = "*" if x["variante"] == campeao else " "
                saida.append(
                    f"{marca} {x['variante']:14} {x['trades']:>6} {x['lucro']:>9.2f} "
                    f"{'-' if x['r'] is None else format(x['r'], '.1f'):>7} "
                    f"{'-' if x['pf'] is None else format(x['pf'], '.2f'):>5} "
                    f"{'-' if x['acerto'] is None else format(x['acerto'], '.0f'):>7} {x['dd']:>6.1f} "
                    f"{'-' if x['delta'] is None else format(x['delta'], '+.2f'):>9} "
                    f"{'-' if x['t'] is None else format(x['t'], '+.2f'):>6}  {veredito_s5(x)}"
                    + (f" (vs {x['ref']})" if x["ref"] and x["ref"] != "mercado" else ""))
            saida.append("")
        if len(tabelas) == 2:
            saida.append(f"== {chave}: consistencia entre as duas janelas")
            saida.append(f"  {'variante':14} {'d lucro a':>10} {'d lucro b':>10}  leitura")
            for nome in tabelas["a"]:
                a, b = tabelas["a"][nome], tabelas["b"].get(nome)
                if b is None or (a["classe"] == "referencia" and b["classe"] == "referencia"):
                    continue
                fmt = lambda v: "-" if v is None else format(v, "+.2f")      # noqa: E731
                saida.append(f"  {nome:14} {fmt(a['delta']):>10} {fmt(b['delta']):>10}  "
                             f"{consistencia_s5(a, b)}")
            saida.append("")
    if por_par:
        saida.append("== PLACAR GERAL: cada booster contra a referencia, somando bases x janelas em que a linha e VALIDA")
        saida.append(f"  {'variante':14} {'pares':>5} {'+':>3} {'-':>3} {'esvaz.':>6} {'sem efeito':>10} "
                     f"{'mediana d%dep':>13} {'p(sinais)':>9}  leitura")
        for x in placar_s5(por_par):
            saida.append(f"  {x['variante']:14} {x['pares']:>5} {x['pos']:>3} {x['neg']:>3} {x['esvaziou']:>6} "
                         f"{x['sem_efeito']:>10} "
                         f"{'-' if x['mediana_pct'] is None else format(x['mediana_pct'], '+.2f'):>13} "
                         f"{'-' if x['p'] is None else format(x['p'], '.2f'):>9}  {x['leitura']}")
        saida.append("")
    texto = "\n".join(saida)
    (SAIDA / "ABLACAO.md").write_text(texto, encoding="utf-8")
    return texto


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

@dataclass
class CenarioS(tp.Cenario):
    modelo: int = 1                      # 1 = OHLC de 1 minuto (rapido; a pergunta e de logica)
    grupo: str = "s1"


def catalogo(existe=None) -> list[CenarioS]:
    """`existe(sistema, variante) -> bool` diz se o template existe (padrao: todas as
    variantes, menos as que so o BOTH_MULTI do 13 tem)."""
    def _existe(sis: str, var: str) -> bool:
        if existe is not None:
            return bool(existe(sis, var))
        return var == "BOTH_MULTI" if sis in SO_BOTH_MULTI else True

    cs: list[CenarioS] = []
    for sis in SISTEMAS_S1:
        for fam in FAMILIAS:
            for lado in LADOS:
                var = f"{lado}_{fam}"
                if _existe(sis, var):
                    cs.append(CenarioS(f"s1_{sis[:2]}_{var}", sis, var, {}, simbolo=SIMBOLO,
                                       inicio=JANELA[0], fim=JANELA[1], grupo="s1"))

    def rec(nome: str, sis: str, var: str, extra: dict) -> None:
        cs.append(CenarioS(f"s2_{nome}", sis, var,
                           {"MinFreeMarginPercent": "20", **extra}, simbolo=SIMBOLO,
                           inicio=JANELA[0], fim=JANELA[1], grupo="s2"))

    # Martingale: nos sistemas em Fixed-R o lote vem da divida (TP ou SL); no 11 (Lote Fixo)
    # do ultimo lote x Multiplicador (Estagio 2.5 abre 1.5..3.0)
    for sis in ("01_SLTP", "02_SLTP_ORGANIC", "03_TRAIL_ONLY", "04_SLTP_TRAIL", "05_BE_TRAIL",
                "06_REVERSAL_EXIT"):
        rec(f"mart_{sis[:2]}_both", sis, "BOTH_MULTI",
            {"RecoveryMode": "1", "MaxMartingaleSteps": "3"})
    rec("mart_04_both_max2", "04_SLTP_TRAIL", "BOTH_MULTI",
        {"RecoveryMode": "1", "MaxMartingaleSteps": "2"})
    rec("mart_04_both_mult2", "04_SLTP_TRAIL", "BOTH_MULTI",
        {"RecoveryMode": "1", "MaxMartingaleSteps": "4", "Multiplicador": "2"})
    rec("mart_04_buy", "04_SLTP_TRAIL", "BUY_MULTI",
        {"RecoveryMode": "1", "MaxMartingaleSteps": "3"})
    rec("mart_11_both", "11_SIGNAL_ONLY", "BOTH_MULTI",
        {"RecoveryMode": "1", "MaxMartingaleSteps": "3", "Multiplicador": "2"})
    rec("mart_11_buy", "11_SIGNAL_ONLY", "BUY_MULTI",
        {"RecoveryMode": "1", "MaxMartingaleSteps": "3", "Multiplicador": "2"})
    # D'Alembert exige Lote Fixo e passo absoluto (o Estagio 2.5 troca o sizing)
    dal = {"RecoveryMode": "2", "PositionSizeMode": "2", "PositionSizeValue": "0.01",
           "DAlembertStep": "0.01", "MaxMartingaleSteps": "3"}
    for sis in ("01_SLTP", "02_SLTP_ORGANIC", "03_TRAIL_ONLY", "04_SLTP_TRAIL", "05_BE_TRAIL",
                "06_REVERSAL_EXIT", "11_SIGNAL_ONLY"):
        rec(f"dal_{sis[:2]}_both", sis, "BOTH_MULTI", dict(dal))
    rec("dal_04_buy", "04_SLTP_TRAIL", "BUY_MULTI", dict(dal))
    rec("dal_04_both_step3", "04_SLTP_TRAIL", "BOTH_MULTI",
        {**dal, "DAlembertStep": "0.03", "MaxMartingaleSteps": "5"})
    # Bollinger e Candles: o booster tambem vive nas duas outras EAs
    for fam in ("BOLLINGER", "CANDLES"):
        rec(f"mart_04_both_{fam.lower()}", "04_SLTP_TRAIL", f"BOTH_{fam}",
            {"RecoveryMode": "1", "MaxMartingaleSteps": "3"})
        rec(f"dal_04_both_{fam.lower()}", "04_SLTP_TRAIL", f"BOTH_{fam}", dict(dal))

    # S3: travas de risco da conta (o dono pode liga-las ao vivo). 04 BUY (uma posicao por vez,
    # entao o saldo realizado vale como prova), limites apertados pra estourar varias vezes.
    def trava(nome: str, extra: dict, var: str = "BUY_MULTI") -> None:
        cs.append(CenarioS(f"s3_{nome}", "04_SLTP_TRAIL", var, extra, simbolo=SIMBOLO,
                           inicio=JANELA[0], fim=JANELA[1], grupo="s3"))

    limit = {"EntryOrderType": "2", "PendingReferencia": "0", "PendingDistanciaATR": "0.5",
             "PendingExpiracaoBarras": "8"}
    trava("perda_diaria", {"DailyLossLimitPercent": "0.5"})
    trava("gp_diaria_fecha", {"Trava_Diaria_Percent": "0.5", "Protecao_Fecha_Posicoes": "true"})
    trava("gp_diaria_bloqueia", {"Trava_Diaria_Percent": "0.5", "Protecao_Fecha_Posicoes": "false"})
    trava("gp_total_fecha", {"Trava_Total_Percent": "3", "Protecao_Fecha_Posicoes": "true"})
    trava("gp_total_bloqueia", {"Trava_Total_Percent": "3", "Protecao_Fecha_Posicoes": "false"})
    trava("perda_diaria_limit", {"DailyLossLimitPercent": "0.5", **limit})
    trava("gp_diaria_limit", {"Trava_Diaria_Percent": "0.5", "Protecao_Fecha_Posicoes": "true",
                              **limit})
    trava("gp_diaria_bollinger", {"Trava_Diaria_Percent": "0.5", "Protecao_Fecha_Posicoes": "true"},
          "BUY_BOLLINGER")
    trava("gp_diaria_candles", {"Trava_Diaria_Percent": "0.5", "Protecao_Fecha_Posicoes": "true"},
          "BUY_CANDLES")

    # S4: filtros de execucao (o booster do Estagio 3). Toda ordem de entrada colocada tem que
    # respeitar janela, dia e spread; o controle sem filtro e o s1_04_BUY_MULTI.
    def filtro(nome: str, extra: dict) -> None:
        cs.append(CenarioS(f"s4_{nome}", "04_SLTP_TRAIL", "BUY_MULTI", extra, simbolo=SIMBOLO,
                           inicio=JANELA[0], fim=JANELA[1], grupo="s4"))

    janela = {"TOD_From_Hour": "10", "TOD_From_Min": "0", "TOD_To_Hour": "12", "TOD_To_Min": "0"}
    filtro("janela_10_12", janela)
    filtro("janela_noturna_22_06", {"TOD_From_Hour": "22", "TOD_From_Min": "0",
                                    "TOD_To_Hour": "6", "TOD_To_Min": "0"})
    filtro("sem_segunda_sexta", {"TradeMonday": "false", "TradeFriday": "false"})
    filtro("so_quarta", {"TradeMonday": "false", "TradeTuesday": "false", "TradeThursday": "false",
                         "TradeFriday": "false"})
    filtro("spread_12", {"MaxSpread": "12"})
    filtro("spread_8", {"MaxSpread": "8"})
    filtro("tudo_junto", {**janela, "TradeWednesday": "false", "MaxSpread": "12"})
    filtro("janela_limit", {**janela, "EntryOrderType": "2", "PendingReferencia": "0",
                            "PendingDistanciaATR": "0.5", "PendingExpiracaoBarras": "8",
                            "Fecharordensforadohorario": "true"})

    # S5: ablacao de boosters sobre sets ja otimizados (ver relatorio_ablacao)
    for jn, (j_ini, j_fim) in JANELAS_S5.items():
        for chave, (arq, simbolo, sistema, lado_var) in BASES_S5.items():
            for nome, extra in variantes_s5(sistema, lado_var.split("_")[0], simbolo, chave):
                cs.append(CenarioS(f"{prefixo_s5(jn)}_{chave}_{nome}", sistema, lado_var, extra,
                                   simbolo=simbolo, inicio=j_ini, fim=j_fim, origem_arquivo=arq,
                                   grupo="s5"))

    # Segundo simbolo: EURUSD (forex de 5 casas, contrato 100000, tick 0.00001) -- o ouro
    # sozinho nao prova o dimensionamento nem o tamanho do tick em outra classe de ativo
    for sis in SISTEMAS_S1:
        cs.append(CenarioS(f"s1e_{sis[:2]}_BOTH_MULTI", sis, "BOTH_MULTI", {},
                           simbolo="EURUSD", inicio=JANELA[0], fim=JANELA[1], grupo="s1"))
    for nome, extra in (("mart_04_both", {"RecoveryMode": "1", "MaxMartingaleSteps": "3"}),
                        ("mart_03_both", {"RecoveryMode": "1", "MaxMartingaleSteps": "3"}),
                        ("dal_04_both", dict(dal))):
        cs.append(CenarioS(f"s2e_{nome}", "03_TRAIL_ONLY" if "_03_" in nome else "04_SLTP_TRAIL",
                           "BOTH_MULTI", {"MinFreeMarginPercent": "20", **extra},
                           simbolo="EURUSD", inicio=JANELA[0], fim=JANELA[1], grupo="s2"))
    return cs


# ---------------------------------------------------------------------------
# Execucao e verificacao
# ---------------------------------------------------------------------------

def _preparar() -> None:
    """Aponta o executor de testar_pendentes para a pasta desta bateria."""
    tp.SAIDA = SAIDA


def verificar(so: str | None = None) -> int:
    _preparar()
    cenarios = {c.nome: c for c in catalogo()}
    resultados: dict[str, dict] = {}
    for nome, c in cenarios.items():
        if so and so not in nome:
            continue
        j = SAIDA / f"{nome}.json"
        if not j.exists():
            continue
        reg = json.loads(j.read_text(encoding="utf-8"))
        htm = SAIDA / f"{nome}.htm"
        res = Resultado()
        if not htm.exists():
            res.falha("relatorio", "sem relatorio do tester")
        else:
            ordens, deals = parse_relatorio(htm)
            info = tp.info_do_simbolo(c.simbolo)
            params = dict(reg["params"])
            params["_deposito"] = reg.get("deposito", 0)
            log = (SAIDA / f"{nome}.log").read_text(encoding="utf-8", errors="replace") \
                if (SAIDA / f"{nome}.log").exists() else ""
            if c.grupo == "s1":
                checar_assinatura(c.sistema, c.variante, ordens, deals, info, res, params)
            elif c.grupo == "s3":
                checar_travas(params, ordens, deals, log, res)
            elif c.grupo == "s4":
                checar_filtros_execucao(params, ordens, deals, tp.carregar_barras(c.simbolo), res)
            elif c.grupo == "s5":
                fech_s5, ab_s5 = operacoes(ordens, deals)
                res.metricas["entradas"] = len(fech_s5) + len(ab_s5)
                if not fech_s5 and not ab_s5:
                    res.aviso("amostra", "0 trades na janela: variante sem evidencia")
            else:
                checar_recuperacao(c.sistema, params, ordens, deals, info, res)
            tp.checar_log(log, res)
            if RECUSA.search(log):
                motivo = MOTIVO.search(log)
                res.falha("recusa", "a EA recusou o set no OnInit: "
                          + (motivo.group(1) if motivo else "incorrect input parameters"))
            if reg.get("params_faltando"):
                res.falha("set", f"set de trabalho incompleto: {reg['params_faltando']}")
        resultados[nome] = {"falhas": res.falhas, "avisos": res.avisos, "metricas": res.metricas}
    return _relatorio_final(resultados, len(cenarios))


def _relatorio_final(resultados: dict, total: int) -> int:
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "resultado.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    ruins = {n: r for n, r in resultados.items() if r["falhas"]}
    avisos = {n: r for n, r in resultados.items() if r["avisos"] and not r["falhas"]}
    linhas = [f"cenarios rodados: {len(resultados)} de {total} | com FALHA: {len(ruins)} | "
              f"so aviso: {len(avisos)}"]
    for n, r in sorted(resultados.items()):
        marca = "FALHA" if r["falhas"] else ("aviso" if r["avisos"] else "ok   ")
        m = r["metricas"]
        resumo = (f"entradas={m.get('entradas', '-'):>4} saidas={m.get('saidas', '')}"
                  if n.startswith("s1") else
                  f"entradas={m.get('entradas', '-'):>4} estouros dia gp/magic="
                  f"{m.get('dias_estouro_gp', '-')}/{m.get('dias_estouro_magic', '-')} "
                  f"apos_estouro={m.get('entradas_apos_estouro_gp', m.get('entradas_apos_estouro_magic', m.get('entradas_apos_estouro_total', '-')))} "
                  f"fechamentos={m.get('fechamentos_da_protecao', '-')}"
                  if n.startswith("s3") else
                  f"ordens de entrada={m.get('ordens_de_entrada', '-'):>4} fora da janela="
                  f"{m.get('fora_da_janela', '-')} em dia proibido={m.get('em_dia_proibido', '-')} "
                  f"acima do spread={m.get('acima_do_spread', '-')}/{m.get('spread_medidas', '-')}"
                  if n.startswith("s4") else
                  f"entradas={m.get('entradas', '-'):>4}"
                  if n.startswith("s5") else
                  f"entradas={m.get('entradas', '-'):>4} conferidas={m.get('conferidas', '-')} "
                  f"diverg={m.get('divergentes', '-')} com_divida={m.get('entradas_com_divida', '-')} "
                  f"acima_base={m.get('lote_acima_da_base', '-')}")
        linhas.append(f"  {marca} {n:36} {resumo}")
        for f in r["falhas"]:
            linhas.append(f"        {f}")
        for a in r["avisos"]:
            linhas.append(f"        (aviso) {a}")
    texto = "\n".join(linhas)
    (SAIDA / "RESULTADO.md").write_text(texto, encoding="utf-8")
    print(texto)
    return 1 if ruins else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rodar", action="store_true")
    ap.add_argument("--verificar", action="store_true")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--so", default="", help="so cenarios cujo nome contem este texto")
    ap.add_argument("--shard", default="1/1", help="i/n: roda so os cenarios de indice i (base 1) mod n")
    ap.add_argument("--refazer", action="store_true")
    ap.add_argument("--reverso", action="store_true",
                    help="percorre a lista de tras pra frente: dois terminais (um normal, um --reverso) "
                         "dividem o trabalho sem shard fixo e se encontram no meio")
    ap.add_argument("--ablacao", action="store_true",
                    help="tabela dos boosters (S5) sobre os sets ja otimizados")
    args = ap.parse_args()
    if args.ablacao:
        print(relatorio_ablacao())
        return 0
    if args.listar:
        for c in catalogo():
            print(c.nome, c.sistema, c.variante, c.sobrepor)
        return 0
    if args.rodar:
        _preparar()
        i, n = (int(x) for x in args.shard.split("/"))
        todos = [c for c in catalogo() if not args.so or args.so in c.nome]
        ordem = list(enumerate(todos))
        if args.reverso:
            ordem.reverse()
        for idx, c in ordem:
            if idx % n != i - 1:
                continue
            print(f"[{idx + 1}/{len(todos)}] {c.nome}", flush=True)
            reg = tp.rodar_cenario(c, args.refazer)
            print("   ->", "ja feito" if reg is None else reg["medida"], flush=True)
        tp.limpar_temporarios()
        return 0
    if args.verificar:
        return verificar(args.so or None)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
