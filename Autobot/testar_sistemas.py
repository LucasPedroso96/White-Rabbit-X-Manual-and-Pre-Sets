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
import sys
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path

import testar_pendentes as tp
from testar_pendentes import Resultado, _flt, _int, parse_relatorio

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


def _entradas_de_ordens(ordens: list[dict]) -> list[dict]:
    """Ordens que abriram posicao (executadas/preenchidas), a mercado ou pendente."""
    return [o for o in ordens if o["estado"] == "filled"]


def checar_assinatura(sistema: str, variante: str, ordens: list[dict], deals: list[dict],
                      info: dict, res: Resultado) -> None:
    ass = ASSINATURA[sistema]
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

    # -- rastro de trailing / breakeven --------------------------------------
    sl_exits = [p for p in fechadas if p["classe"] == "sl" and p["sl"] > 0]
    if ass.trail or ass.be:
        movidas = benef = 0
        for p in sl_exits:
            sinal = 1 if p["lado"] == "buy" else -1
            dist0 = abs(p["preco"] - p["sl"])
            if not dist0:
                continue
            ganho = sinal * (p["preco_out"] - p["preco"])
            if sinal * (p["preco_out"] - p["sl"]) > 0.05 * dist0:      # saiu ACIMA do SL inicial
                movidas += 1
                if ganho > 0.05 * dist0:
                    benef += 1
        res.metricas["sl_movido"] = movidas
        res.metricas["sl_movido_no_lucro"] = benef
        if len(sl_exits) >= AMOSTRA_RASTRO and not movidas:
            res.aviso("rastro", f"{len(sl_exits)} saidas por SL e NENHUMA com o stop arrastado "
                      f"({'trailing' if ass.trail else 'breakeven'} sem efeito?)")
        if ass.trail and len(sl_exits) >= AMOSTRA_RASTRO and movidas and not benef:
            res.aviso("rastro", "stops arrastados mas nenhum fechou no lucro (trailing so no breakeven?)")

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
        r = _flt(params, "PositionSizeValue") / 100.0 * (
            _flt(params, "CapitalBaseR") or _flt(params, "_deposito"))
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
        r = _flt(params, "PositionSizeValue") / 100.0 * (_flt(params, "CapitalBaseR")
                                                          or _flt(params, "_deposito"))
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
                checar_assinatura(c.sistema, c.variante, ordens, deals, info, res)
            else:
                checar_recuperacao(c.sistema, params, ordens, deals, info, res)
            tp.checar_log(log, res)
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
                  if n.startswith("s1_") else
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
    args = ap.parse_args()
    if args.listar:
        for c in catalogo():
            print(c.nome, c.sistema, c.variante, c.sobrepor)
        return 0
    if args.rodar:
        _preparar()
        i, n = (int(x) for x in args.shard.split("/"))
        todos = [c for c in catalogo() if not args.so or args.so in c.nome]
        for idx, c in enumerate(todos):
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
