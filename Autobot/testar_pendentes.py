# -*- coding: utf-8 -*-
"""Matriz de testes das ordens pendentes (entrada Stop / Limit / OCO) NO TESTER.

Por que existe (dono, 2026-09-29: "mas esta tudo correto e testado? as ordens
pendentes e todas opcoes desse sistema?"): ate aqui so havia CONTAGEM de ordens
colocadas/executadas/canceladas -- nao provava preco, SL/TP, lote, expiracao nem
a causa de cada cancelamento. Aqui cada cenario roda no tester com tick real e o
relatorio (tabelas Ordens e Transacoes) e conferido contra o que o codigo da EA
promete, usando as BARRAS DO PROPRIO TERMINAL como fonte independente:

  tipo       Stop/Limit/OCO x lado -> "buy stop", "sell limit"...; lado permitido
  preco      referencia (fechamento ou extremo do candle do sinal, shift 1 do TF de
             entrada; faixa das N barras no OCO por sessao) +/- k x ATR
  sl/tp      relativos ao preco DA ORDEM (nao ao mercado), lado certo
  lote       FixedLot exato; Fixed-R = R / (distancia do SL x contrato), no passo
  expiracao  cancela ao completar N barras do TF de entrada
  sobrepos.  no maximo 1 pendente por lado (bracket OCO: 1 de cada)
  execucao   Stop nao executa a favor do preco pedido, Limit nao executa contra
  OCO        perna executada -> a outra cancelada em segundos
  log        sem "Invalid pending", "not sent", "failed"

    python testar_pendentes.py --exportar-barras
    python testar_pendentes.py --rodar [--so texto] [--shard 1/2] [--refazer]
    python testar_pendentes.py --verificar [--so texto]

O relatorio de cada cenario fica em _pendentes_teste/ (nao vai pro git).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI / "_pendentes_teste"
BARRAS_DIR = SAIDA / "barras"

TF_NOMES = {0: "M1", 1: "M5", 2: "M15", 3: "M30", 4: "H1", 5: "H4", 6: "D1", 7: "W1"}
TF_SEG = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400,
          "D1": 86400, "W1": 604800}
TIPOS_PEND = {"buy stop", "buy limit", "sell stop", "sell limit"}
ACIMA_DO_MERCADO = {"buy stop", "sell limit"}       # os outros dois ficam abaixo
MODOS_SIZING = {0: "Percentage", 1: "Monetary", 2: "FixedLot", 3: "FixedR"}
RE_DATA = re.compile(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$")
# O comentario da ordem e cortado em 31 caracteres pelo MT5: em grade/piramide o rotulo
# ("07-MUL Buy / Grid / FixedLot/Pend") perde o fim -> "/Pe", "/P"...
RE_MARCA_PEND = re.compile(r"/(?:Pend|Pen|Pe|P|OCO|OC|O)?$|/Pend|/OCO")


# ---------------------------------------------------------------------------
# Relatorio do tester (tabelas Ordens e Transacoes)
# ---------------------------------------------------------------------------

def _limpa(c: str) -> str:
    c = re.sub(r"<[^>]+>", "", c)
    return c.replace("&nbsp;", " ").replace("\xa0", " ").strip()


def _num(s: str | None) -> float | None:
    if s is None:
        return None
    s = s.replace(" ", "").replace("\xa0", "")
    if s in ("", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S")


def parse_html(html: str) -> tuple[list[dict], list[dict]]:
    """(ordens, deals) do relatorio do tester. Reconhece as linhas pelo FORMATO
    (data no inicio; 11 colunas = ordem, 13 = deal), nao pelo idioma."""
    ordens: list[dict] = []
    deals: list[dict] = []
    for linha in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        c = [_limpa(x) for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", linha, re.S)]
        if not c or not RE_DATA.match(c[0]):
            continue
        if len(c) == 11:
            vols = [v.strip() for v in c[4].split("/")]
            ordens.append({
                "abertura": _dt(c[0]), "ordem": int(c[1]), "simbolo": c[2],
                "tipo": c[3].lower(), "vol": _num(vols[0]),
                "vol_exec": _num(vols[1]) if len(vols) > 1 else None,
                "preco": _num(c[5]), "sl": _num(c[6]) or 0.0, "tp": _num(c[7]) or 0.0,
                "fim": _dt(c[8]) if RE_DATA.match(c[8]) else None,
                "estado": c[9].lower(), "comentario": c[10]})
        elif len(c) == 13:
            deals.append({
                "t": _dt(c[0]), "deal": int(c[1]), "simbolo": c[2],
                "tipo": c[3].lower(), "direcao": c[4].lower(), "vol": _num(c[5]),
                "preco": _num(c[6]),
                "ordem": int(c[7]) if c[7].isdigit() else None,
                "comissao": _num(c[8]), "swap": _num(c[9]), "lucro": _num(c[10]),
                "saldo": _num(c[11]), "comentario": c[12]})
    return ordens, deals


def parse_relatorio(caminho: Path) -> tuple[list[dict], list[dict]]:
    return parse_html(caminho.read_text(encoding="utf-16", errors="replace"))


# ---------------------------------------------------------------------------
# Barras (fonte independente) e ATR
# ---------------------------------------------------------------------------

class Barras:
    """Barras OHLC por timeframe. `dfs[tf]` = DataFrame indexado pelo horario de
    ABERTURA (hora do servidor), colunas open/high/low/close."""

    def __init__(self, dfs: dict):
        self.dfs = dfs
        self._cache: dict = {}

    def pos(self, tf: str, t: datetime) -> int | None:
        """Posicao da barra que CONTEM t (ultima com abertura <= t)."""
        import pandas as pd
        i = int(self.dfs[tf].index.searchsorted(pd.Timestamp(t), side="right")) - 1
        return i if i >= 0 else None

    def barra(self, tf: str, p: int):
        return self.dfs[tf].iloc[p]

    def _tr(self, tf: str):
        chave = ("tr", tf)
        if chave not in self._cache:
            df = self.dfs[tf]
            pc = df["close"].shift(1)
            tr = (df["high"].combine(pc, max) - df["low"].combine(pc, min))
            tr.iloc[0] = df["high"].iloc[0] - df["low"].iloc[0]
            self._cache[chave] = tr
        return self._cache[chave]

    def atr_fechado(self, tf: str, periodo: int, p: int) -> float | None:
        """ATR (media simples do TR) da barra de posicao p."""
        if p is None or p < periodo:
            return None
        tr = self._tr(tf)
        return float(tr.iloc[p - periodo + 1:p + 1].mean())

    def atr_intervalo(self, tf: str, periodo: int, t: datetime,
                      shift: int) -> tuple[float, float] | None:
        """[lo, hi] do ATR[shift] visto pela EA no instante t. shift>=1: exato
        (barras fechadas). shift=0: a barra em formacao entra com o TR de
        [abertura, t]; o intervalo vai do minimo (so o gap da abertura) ao
        maximo (o range do M1 ate o minuto de t inclusive)."""
        p0 = self.pos(tf, t)
        if p0 is None:
            return None
        if shift >= 1:
            v = self.atr_fechado(tf, periodo, p0 - shift)
            return (v, v) if v is not None else None
        if p0 < periodo + 1:
            return None
        tr = self._tr(tf)
        soma = float(tr.iloc[p0 - periodo + 1:p0].sum())          # N-1 barras fechadas
        b0 = self.barra(tf, p0)
        pc = float(self.barra(tf, p0 - 1)["close"])
        lo_tr = abs(float(b0["open"]) - pc)
        # teto seguro: o TR da barra ja FECHADA (o range parcial cabe nele)
        hi_tr = max(float(b0["high"]), pc) - min(float(b0["low"]), pc)
        if "M1" in self.dfs:
            import pandas as pd
            m1 = self.dfs["M1"]
            ini = self.dfs[tf].index[p0]
            fim = pd.Timestamp(t).floor("min")
            trecho = m1.loc[ini:fim]
            if len(trecho):        # com M1 cobrindo o instante, o teto fica mais justo
                hi_m1 = max(float(trecho["high"].max()), pc) - min(float(trecho["low"].min()), pc)
                hi_tr = min(hi_tr, hi_m1)
        return ((soma + lo_tr) / periodo, (soma + max(hi_tr, lo_tr)) / periodo)


# ---------------------------------------------------------------------------
# Conferencias
# ---------------------------------------------------------------------------

@dataclass
class Resultado:
    falhas: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    metricas: dict = field(default_factory=dict)

    def falha(self, codigo: str, msg: str) -> None:
        self.falhas.append(f"[{codigo}] {msg}")

    def aviso(self, codigo: str, msg: str) -> None:
        self.avisos.append(f"[{codigo}] {msg}")


def _int(params: dict, nome: str, padrao: int = 0) -> int:
    try:
        return int(float(str(params.get(nome, padrao)).strip()))
    except ValueError:
        return padrao


def _flt(params: dict, nome: str, padrao: float = 0.0) -> float:
    try:
        return float(str(params.get(nome, padrao)).strip())
    except ValueError:
        return padrao


def _bool(params: dict, nome: str) -> bool:
    return str(params.get(nome, "false")).strip().lower() in ("true", "1")


def tf_entrada(params: dict) -> str:
    """TF de entrada: `TimeFrame` (Multi/Bollinger) ou `CandleTF1` (Candles)."""
    codigo = _int(params, "TimeFrame" if "TimeFrame" in params else "CandleTF1", 2)
    return TF_NOMES.get(codigo, "M15")


def tf_atr(params: dict) -> str:
    return TF_NOMES.get(_int(params, "ATR_TimeFrame", 2), "M15")


def pendentes(ordens: list[dict]) -> list[dict]:
    return [o for o in ordens if o["tipo"] in TIPOS_PEND]


def checar_tipos(ordens: list[dict], params: dict, res: Resultado) -> None:
    et = _int(params, "EntryOrderType")
    pend = pendentes(ordens)
    res.metricas["pendentes"] = len(pend)
    if et == 0:
        if pend:
            res.falha("tipos", f"{len(pend)} pendentes com EntryOrderType=0 (mercado)")
        return
    permitido = {1: {"buy stop", "sell stop"}, 2: {"buy limit", "sell limit"},
                 3: {"buy stop", "sell stop"}}[et]
    fora = [o for o in pend if o["tipo"] not in permitido]
    if fora:
        res.falha("tipos", f"{len(fora)} ordens de tipo inesperado: "
                  f"{sorted({o['tipo'] for o in fora})} (esperado {sorted(permitido)})")
    if _int(params, "MaxLongTrades") <= 0 and any(o["tipo"].startswith("buy") for o in pend):
        res.falha("tipos", "pendente de COMPRA num set sem compra (MaxLongTrades=0)")
    if _int(params, "MaxShortTrades") <= 0 and any(o["tipo"].startswith("sell") for o in pend):
        res.falha("tipos", "pendente de VENDA num set sem venda (MaxShortTrades=0)")
    # ordem que o broker expirou tem o comentario trocado pelo tester ("expired [data]")
    sem_marca = [o for o in pend if not RE_MARCA_PEND.search(o["comentario"])
                 and not (o["estado"] == "expired" and o["comentario"].startswith("expired ["))]
    if sem_marca:
        res.falha("tipos", f"{len(sem_marca)} pendentes sem a marca /Pend ou /OCO no comentario "
                  f"(perna de grade virando pendente?): {sem_marca[0]['comentario']!r}")
    if not pend:
        res.falha("tipos", "nenhuma pendente foi colocada -- cenario sem evidencia")


def _spread_do_mercado(barras: Barras, t: datetime, ponto: float) -> float:
    """Spread (em preco) da barra M1 do minuto de t; 0 se as barras nao trazem spread.
    O ASK = bid + spread, e o historico de barras e BID."""
    import pandas as pd
    df = barras.dfs.get("M1")
    if df is None or "spread" not in df.columns:
        return 0.0
    i = int(df.index.searchsorted(pd.Timestamp(t).floor("min"), side="left"))
    if i >= len(df) or df.index[i] != pd.Timestamp(t).floor("min"):
        return 0.0
    return float(df["spread"].iloc[i]) * ponto


def _minutos_do_mercado(barras: Barras, t: datetime):
    """(min, max) do mercado no instante t: o M1 do minuto, ou (sem M1 naquele
    instante) a barra do menor timeframe que o contenha."""
    import pandas as pd
    for tf in ("M1", "M5", "M15", "M30", "H1"):
        df = barras.dfs.get(tf)
        if df is None:
            continue
        if tf == "M1":
            i = int(df.index.searchsorted(pd.Timestamp(t).floor("min"), side="left"))
            if i >= len(df) or df.index[i] != pd.Timestamp(t).floor("min"):
                continue
            b = df.iloc[i]
        else:
            i = int(df.index.searchsorted(pd.Timestamp(t), side="right")) - 1
            if i < 0 or (pd.Timestamp(t) - df.index[i]).total_seconds() >= TF_SEG[tf]:
                continue
            b = df.iloc[i]
        return float(b["low"]), float(b["high"])
    return None


def preco_esperado(o: dict, params: dict, barras: Barras) -> dict | None:
    """Intervalo do preco esperado da pendente `o` segundo PendingEntryPrice()."""
    tf = tf_entrada(params)
    acima = o["tipo"] in ACIMA_DO_MERCADO
    p0 = barras.pos(tf, o["abertura"])
    if p0 is None or p0 < 2:
        return None
    sessao = _int(params, "PendingGatilho") == 1
    extremo = _int(params, "PendingReferencia") == 1
    if sessao:
        n = max(1, _int(params, "PendingFaixaBarras", 4))
        faixa = barras.dfs[tf].iloc[p0 - n:p0]
        ref = float(faixa["high"].max()) if acima else float(faixa["low"].min())
    elif extremo:
        b1 = barras.barra(tf, p0 - 1)
        ref = float(b1["high"]) if acima else float(b1["low"])
    else:
        ref = float(barras.barra(tf, p0 - 1)["close"])
    k = max(0.0, _flt(params, "PendingDistanciaATR"))
    iv = barras.atr_intervalo(tf_atr(params), _int(params, "PeriodoATR", 14),
                              o["abertura"], 0)
    if iv is None:
        return None
    lo_atr, hi_atr = iv
    if acima:
        lo, hi = ref + k * lo_atr, ref + k * hi_atr
    else:
        lo, hi = ref - k * hi_atr, ref - k * lo_atr
    return {"ref": ref, "lo": lo, "hi": hi, "acima": acima, "atr_hi": hi_atr}


def checar_preco(ordens: list[dict], params: dict, barras: Barras, tick: float,
                 res: Resultado) -> None:
    exatas = ajustadas = sem_dado = 0
    erros: list[str] = []
    anomalos: list[str] = []
    for o in pendentes(ordens):
        esp = preco_esperado(o, params, barras)
        if esp is None:
            sem_dado += 1
            continue
        tol = tick * 1.01
        p = o["preco"]
        if esp["lo"] - tol <= p <= esp["hi"] + tol:
            exatas += 1
            continue
        # A EA empurra o nivel para o lado do mercado (distancia minima do
        # broker): acima -> max(nivel, ask+min); abaixo -> min(nivel, bid-min).
        mm = _minutos_do_mercado(barras, o["abertura"])
        # compra Stop / venda Limit ficam acima do ASK = bid + spread (rolagem: 10+ pips)
        folga = max(0.25 * esp["atr_hi"], 30 * tick) + 1.5 * _spread_do_mercado(barras, o["abertura"], tick)
        if esp["acima"] and p > esp["hi"] + tol and mm and p <= mm[1] + folga:
            ajustadas += 1
        elif (not esp["acima"]) and p < esp["lo"] - tol and mm and p >= mm[0] - folga:
            ajustadas += 1
        else:
            msg = (f"ordem {o['ordem']} {o['tipo']} {o['abertura']:%m.%d %H:%M:%S}: "
                   f"preco {p} fora de [{esp['lo']:.5f}, {esp['hi']:.5f}] (ref {esp['ref']})")
            # Preco que o historico de barras NAO mostra em nenhum momento do minuto =
            # tick anomalo nos dados do tester (a EA reagiu ao ask que o tester lhe deu):
            # isolado e aviso, sistematico e falha.
            if mm and ((esp["acima"] and p > mm[1] + folga) or ((not esp["acima"]) and p < mm[0] - folga)):
                anomalos.append(msg)
            else:
                erros.append(msg)
    res.metricas["preco_exato"] = exatas
    res.metricas["preco_ajustado_ao_mercado"] = ajustadas
    res.metricas["preco_sem_dado"] = sem_dado
    res.metricas["preco_tick_anomalo"] = len(anomalos)
    if anomalos:
        limite = max(1, int(0.02 * len(pendentes(ordens))))
        if len(anomalos) > limite:
            res.falha("preco", f"{len(anomalos)} pendentes a preco que o historico de barras nao mostra "
                      f"(> {limite}); ex.: {anomalos[0]}")
        else:
            res.aviso("preco", f"{len(anomalos)} pendente(s) a preco que o historico de barras nao "
                      f"mostra (tick anomalo nos dados do tester?); ex.: {anomalos[0]}")
    if erros:
        res.falha("preco", f"{len(erros)} pendentes com preco errado; ex.: {erros[0]}")
    if sem_dado and sem_dado == len(pendentes(ordens)):
        res.aviso("preco", "nenhuma pendente com barras suficientes pra conferir o preco")


def checar_sl_tp(ordens: list[dict], params: dict, barras: Barras, tick: float,
                 res: Resultado) -> None:
    ruins: list[str] = []
    dist_ok = dist_fora = 0
    atr_tf, n_atr = tf_atr(params), _int(params, "PeriodoATR", 14)
    for o in pendentes(ordens):
        compra = o["tipo"].startswith("buy")
        p, sl, tp = o["preco"], o["sl"], o["tp"]
        if sl > 0 and ((compra and not sl < p) or ((not compra) and not sl > p)):
            ruins.append(f"ordem {o['ordem']}: SL {sl} do lado errado de {p}")
            continue
        if tp > 0 and ((compra and not tp > p) or ((not compra) and not tp < p)):
            ruins.append(f"ordem {o['ordem']}: TP {tp} do lado errado de {p}")
            continue
        for nome, alvo, mult_key, vela_key in (("SL", sl, "Stop", "VelaStop"),
                                               ("TP", tp, "Take", "VelaTake")):
            ativo = "AtivarStop" if nome == "SL" else "AtivarTake"
            if alvo <= 0 or not _bool(params, ativo):
                continue
            iv = barras.atr_intervalo(atr_tf, n_atr, o["abertura"], _int(params, vela_key))
            if iv is None:
                continue
            mult = _flt(params, mult_key)
            d = abs(p - alvo)
            lo, hi = mult * iv[0] - 2 * tick, mult * iv[1] + 2 * tick
            if lo <= d <= hi:
                dist_ok += 1
            else:
                dist_fora += 1
                # distancia minima do broker so AUMENTA a distancia
                if d < lo:
                    ruins.append(f"ordem {o['ordem']}: {nome} a {d:.5f} do preco da ordem, "
                                 f"esperado [{lo:.5f}, {hi:.5f}] ({mult_key}={mult})")
    res.metricas["sl_tp_dist_ok"] = dist_ok
    res.metricas["sl_tp_dist_maior_que_esperado"] = dist_fora
    if ruins:
        res.falha("sl_tp", f"{len(ruins)} problemas; ex.: {ruins[0]}")


def checar_lote(ordens: list[dict], params: dict, info: dict,
                res: Resultado) -> None:
    """Lote das pendentes conforme o modo de sizing. Percentage/Monetary sao
    comparados com o controle a mercado em `comparar_controle`."""
    modo = _int(params, "PositionSizeMode", 2)
    passo = info.get("vol_step") or 0.01
    vmin = info.get("vol_min") or passo
    contrato = info.get("contrato")
    valor = _flt(params, "PositionSizeValue")
    moeda = info.get("moeda_lucro", "USD")
    erros: list[str] = []
    if moeda != "USD" and not str(ordens[0]["simbolo"] if ordens else "").startswith("USD"):
        contrato = None          # sem taxa de conversao pra USD: nao confere o Fixed-R exato
    for o in pendentes(ordens):
        v = o["vol"]
        if v is None:
            continue
        if modo == 2:
            if _int(params, "RecoveryMode") != 0:
                # Martingale/D'Alembert somam ao lote depois de perda: o lote base e piso
                if v < valor - passo * 0.51:
                    erros.append(f"ordem {o['ordem']}: lote {v} abaixo do FixedLot {valor} com recuperacao")
            elif abs(v - valor) > passo * 0.51:
                erros.append(f"ordem {o['ordem']}: lote {v} != FixedLot {valor}")
        elif modo == 3 and contrato and o["sl"] > 0:
            r = _flt(params, "CapitalBaseR") * valor / 100.0
            dist = abs(o["preco"] - o["sl"])
            # USDJPY etc.: o lucro sai em JPY -> USD = JPY / preco
            conv = 1.0 / o["preco"] if moeda != "USD" else 1.0
            ideal = r / (dist * contrato * conv)
            esperado = max(vmin, math.floor(ideal / passo + 1e-9) * passo)
            recuperacao = _int(params, "RecoveryMode") != 0
            # Com Martingale/D'Alembert o lote cresce por passo depois de perda: o
            # Fixed-R exato vira PISO (nunca abaixo do lote base).
            if recuperacao:
                if v < esperado - passo * 1.01:
                    erros.append(f"ordem {o['ordem']}: lote {v} abaixo do lote base {esperado:.2f} "
                                 f"(R={r:g}, SL a {dist:.5f}) com recuperacao")
            elif abs(v - esperado) > passo * 1.01:
                erros.append(f"ordem {o['ordem']}: lote {v} != {esperado:.2f} "
                             f"(R={r:g}, SL a {dist:.5f})")
    res.metricas["modo_sizing"] = MODOS_SIZING.get(modo, str(modo))
    if erros:
        res.falha("lote", f"{len(erros)} pendentes com lote fora do modo "
                  f"{MODOS_SIZING.get(modo)}; ex.: {erros[0]}")


def risco_por_ordem(ordens: list[dict], info: dict,
                    deals: list[dict] | None = None) -> list[float]:
    """Risco (lote x distancia do SL x contrato) por ordem de ENTRADA. Ordem a mercado
    vem com Preco=0 no relatorio: o preco de entrada esta no deal."""
    contrato = info.get("contrato")
    if not contrato:
        return []
    entradas = {d["ordem"]: d["preco"] for d in (deals or [])
                if d["direcao"] == "in" and d["ordem"] and d["preco"]}
    saida = []
    for o in ordens:
        preco = o["preco"] or entradas.get(o["ordem"])
        if o["vol"] and o["sl"] > 0 and preco:
            saida.append(o["vol"] * abs(preco - o["sl"]) * contrato)
    return saida


def mediana(xs: list[float]) -> float | None:
    if not xs:
        return None
    ys = sorted(xs)
    m = len(ys) // 2
    return ys[m] if len(ys) % 2 else (ys[m - 1] + ys[m]) / 2


def comparar_controle(ordens_pend: list[dict], ordens_mercado: list[dict],
                      info: dict, res: Resultado, tolerancia: float = 0.25,
                      deals_mercado: list[dict] | None = None) -> None:
    """Risco mediano por ordem (lote x distancia do SL x contrato) da pendente
    contra o controle a mercado do MESMO modo de sizing."""
    rp = mediana(risco_por_ordem(pendentes(ordens_pend), info))
    entradas_mercado = [o for o in ordens_mercado if o["tipo"] in ("buy", "sell")]
    rm = mediana(risco_por_ordem(entradas_mercado, info, deals_mercado))
    res.metricas["risco_mediano_pendente"] = rp
    res.metricas["risco_mediano_mercado"] = rm
    if rp is None or rm is None:
        res.aviso("lote", "sem dado pra comparar o risco com o controle a mercado")
        return
    if not (1 - tolerancia) <= rp / rm <= (1 + tolerancia):
        res.falha("lote", f"risco mediano por ordem {rp:.2f} (pendente) vs {rm:.2f} "
                  f"(mercado): razao {rp / rm:.2f} fora de +-{tolerancia:.0%}")


def checar_expiracao(ordens: list[dict], params: dict, barras: Barras,
                     res: Resultado) -> None:
    """Cancela ao completar N barras do TF de entrada; cancelamento antes disso
    e por OUTRA causa (sinal oposto, pregao, perda diaria, WFO, parada) -- so
    contado aqui, cada causa tem cenario proprio."""
    if _int(params, "EntryOrderType") == 3:
        return
    n = max(1, _int(params, "PendingExpiracaoBarras", 3))
    tf = tf_entrada(params)
    seg = TF_SEG[tf]
    no_prazo = antes = atrasadas = expiradas_pelo_broker = expiradas_na_pausa = 0
    cedo: list[dict] = []
    sem_tick_n = 0
    exemplos: list[str] = []
    for o in pendentes(ordens):
        if o["estado"] not in ("canceled", "expired") or o["fim"] is None:
            continue
        p0 = barras.pos(tf, o["abertura"])
        if p0 is None:
            continue
        idx = barras.dfs[tf].index
        # A EA conta barras EXISTENTES (iBarShift): num fim de semana o prazo
        # cai na N-esima barra depois, nao N x TF de relogio.
        if p0 + n < len(idx):
            prazo = idx[p0 + n].to_pydatetime()
        else:
            prazo = idx[p0].to_pydatetime() + timedelta(seconds=n * seg)
        if o["estado"] == "expired":
            # Pausa diaria/fim de semana: sem barras a EA nao conta prazo e a expiracao do
            # broker (rede de seguranca) encerra a ordem -- desenho correto. Falha so se
            # ja tinham passado N barras EXISTENTES (a EA deveria ter cancelado antes).
            # == n e a borda: o broker expirou durante a pausa e o tick de reabertura
            # e o mesmo em que a EA cancelaria (iBarShift chega a N) -- inofensivo.
            p_fim = barras.pos(tf, o["fim"])
            if p_fim is not None and p_fim - p0 > n:
                expiradas_pelo_broker += 1
                exemplos.append(f"ordem {o['ordem']} expirou pelo broker apos {p_fim - p0} "
                                f"barras existentes (prazo {n})")
            else:
                expiradas_na_pausa += 1
            continue
        if o["fim"] < prazo - timedelta(seconds=2):
            antes += 1
            cedo.append(o)
        elif o["fim"] <= prazo + timedelta(seconds=150):
            no_prazo += 1
        else:
            # Sem NENHUM tick entre o prazo e o cancelamento (rolagem da meia-noite) a EA
            # nao roda: nao e atraso dela.
            m1 = barras.dfs.get("M1")
            sem_tick = (m1 is not None and len(m1.loc[prazo:o["fim"] - timedelta(seconds=60)]) == 0
                        and prazo >= m1.index[0].to_pydatetime())
            if sem_tick:
                no_prazo += 1
                sem_tick_n += 1
                continue
            atrasadas += 1
            exemplos.append(f"ordem {o['ordem']} aberta {o['abertura']:%m.%d %H:%M:%S} "
                            f"encerrada {o['fim']:%m.%d %H:%M:%S}, prazo era {prazo:%H:%M:%S}")
    res.metricas.update(cancel_no_prazo=no_prazo, cancel_antes_do_prazo=antes,
                        cancel_atrasado=atrasadas, expirada_pelo_broker=expiradas_pelo_broker,
                        expirada_na_pausa_do_mercado=expiradas_na_pausa,
                        cancel_apos_lacuna_de_ticks=sem_tick_n)
    # Set nos dois lados: cancelar antes do prazo e virar de mao (sinal oposto) -- deve
    # haver ordem do lado contrario colocada na mesma barra. Nao reprova (a entrada
    # oposta pode estar barrada por exposicao), mas aparece como metrica/aviso.
    if (_int(params, "MaxLongTrades") > 0 and _int(params, "MaxShortTrades") > 0 and cedo
            and _int(params, "GridMode") == 0):
        com_oposta = 0
        for o in cedo:
            lado = o["tipo"].split()[0]
            if any(x["tipo"].split()[0] != lado and x["tipo"] in TIPOS_PEND
                   and abs((x["abertura"] - o["fim"]).total_seconds()) <= 90 for x in ordens):
                com_oposta += 1
        res.metricas["cancel_antes_com_ordem_oposta"] = com_oposta
        if com_oposta < len(cedo):
            res.aviso("expiracao", f"{len(cedo) - com_oposta} de {len(cedo)} cancelamentos antes do "
                      "prazo sem ordem do lado contrario na mesma barra")
    if atrasadas:
        res.falha("expiracao", f"{atrasadas} pendentes vivas alem do prazo de {n} barras "
                  f"de {tf}; ex.: {exemplos[0]}")
    if expiradas_pelo_broker:
        res.falha("expiracao", f"{expiradas_pelo_broker} pendentes 'expired' fora de pausa de "
                  f"mercado -- a EA nao cancelou a tempo; ex.: {exemplos[0]}")


def checar_sobreposicao(ordens: list[dict], params: dict, res: Resultado) -> None:
    """No maximo UMA pendente viva por lado."""
    por_lado: dict[str, list[dict]] = {"buy": [], "sell": []}
    for o in pendentes(ordens):
        if o["fim"] is not None:
            por_lado[o["tipo"].split()[0]].append(o)
    for lado, lista in por_lado.items():
        lista.sort(key=lambda o: o["abertura"])
        for a, b in zip(lista, lista[1:]):
            if b["abertura"] < a["fim"] - timedelta(seconds=1):
                res.falha("sobreposicao", f"2 pendentes de {lado} vivas ao mesmo tempo: "
                          f"ordem {a['ordem']} ({a['abertura']:%m.%d %H:%M:%S}..{a['fim']:%H:%M:%S}) "
                          f"e {b['ordem']} ({b['abertura']:%H:%M:%S})")
                return


def checar_execucao(ordens: list[dict], deals: list[dict], tick: float,
                    res: Resultado) -> None:
    """Preco da execucao contra o preco pedido: Stop nunca a favor, Limit nunca
    contra."""
    entradas = {d["ordem"]: d for d in deals if d["direcao"] == "in" and d["ordem"]}
    n = piores = 0
    soma_melhora = 0.0
    for o in pendentes(ordens):
        d = entradas.get(o["ordem"])
        if d is None or d["preco"] is None:
            continue
        n += 1
        compra = o["tipo"].startswith("buy")
        stop = o["tipo"].endswith("stop")
        # para compra, "pior" = mais caro; venda, mais barato
        delta = (d["preco"] - o["preco"]) if compra else (o["preco"] - d["preco"])
        soma_melhora += -delta
        if (not stop) and delta > tick * 1.01:
            piores += 1
            res.falha("execucao", f"{o['tipo']} ordem {o['ordem']} pedida a {o['preco']} "
                      f"executou PIOR: {d['preco']}")
            break
        if stop and delta < -tick * 1.01:
            piores += 1
            res.falha("execucao", f"{o['tipo']} ordem {o['ordem']} pedida a {o['preco']} "
                      f"executou MELHOR que o gatilho: {d['preco']} (stop nao deveria)")
            break
        if d["t"] < o["abertura"] - timedelta(seconds=1) or (o["fim"] and d["t"] > o["fim"] + timedelta(seconds=1)):
            res.falha("execucao", f"ordem {o['ordem']}: deal em {d['t']} fora da vida da ordem")
            break
    res.metricas["pendentes_executadas"] = n
    res.metricas["melhora_media_vs_pedido"] = round(soma_melhora / n, 5) if n else None


def checar_oco(ordens: list[dict], deals: list[dict], params: dict,
               res: Resultado) -> None:
    if _int(params, "EntryOrderType") != 3:
        return
    pend = pendentes(ordens)
    grupos: dict[datetime, list[dict]] = {}
    for o in pend:
        grupos.setdefault(o["abertura"], []).append(o)
    quer_compra = _int(params, "MaxLongTrades") > 0
    quer_venda = _int(params, "MaxShortTrades") > 0
    esperado = sorted((["buy stop"] if quer_compra else []) + (["sell stop"] if quer_venda else []))
    incompletos = [t for t, g in grupos.items() if sorted(x["tipo"] for x in g) != esperado]
    res.metricas["brackets"] = len(grupos)
    if incompletos:
        res.falha("oco", f"{len(incompletos)} brackets diferentes de {esperado} "
                  f"(ex.: {incompletos[0]:%m.%d %H:%M:%S})")
    if len(esperado) < 2:
        return                    # um lado so: nao ha irma pra cancelar nem par pra comparar
    entradas = {d["ordem"]: d for d in deals if d["direcao"] == "in" and d["ordem"]}
    pares_ok = irma_lenta = simultaneas = 0
    for t, g in grupos.items():
        if len(g) != 2:
            continue
        compra = next(x for x in g if x["tipo"] == "buy stop")
        venda = next(x for x in g if x["tipo"] == "sell stop")
        if not compra["preco"] > venda["preco"]:
            res.falha("oco", f"bracket {t:%m.%d %H:%M:%S}: compra {compra['preco']} nao "
                      f"esta acima da venda {venda['preco']}")
            return
        exec_ = [x for x in g if x["ordem"] in entradas]
        if len(exec_) == 2:
            # As duas no MESMO instante = spread que abriu (rolagem da meia-noite) e ultrapassou
            # a largura do bracket: a EA nao tem como cancelar a irma antes. Isolado e aviso;
            # separadas por segundos, o cancelamento falhou.
            gap = abs((entradas[exec_[0]["ordem"]]["t"] - entradas[exec_[1]["ordem"]]["t"]).total_seconds())
            if gap > 2:
                res.falha("oco", f"bracket {t:%m.%d %H:%M:%S}: as duas pernas executaram com "
                          f"{gap:.0f} s de diferenca (o cancelamento da irma falhou)")
                return
            simultaneas += 1
            continue
        if len(exec_) == 1:
            outra = venda if exec_[0] is compra else compra
            t_exec = entradas[exec_[0]["ordem"]]["t"]
            if outra["estado"] != "canceled" or outra["fim"] is None:
                res.falha("oco", f"bracket {t:%m.%d %H:%M:%S}: perna irma nao foi cancelada "
                          f"(estado {outra['estado']})")
                return
            if abs((outra["fim"] - t_exec).total_seconds()) > 3:
                irma_lenta += 1
            pares_ok += 1
    res.metricas["brackets_com_execucao"] = pares_ok
    res.metricas["oco_duas_pernas_simultaneas"] = simultaneas
    if simultaneas:
        res.aviso("oco", f"{simultaneas} bracket(s) com as DUAS pernas executadas no mesmo instante "
                  "(spread aberto passou a largura do bracket -- evitar armar na rolagem / usar MaxSpread)")
    if irma_lenta:
        res.falha("oco", f"{irma_lenta} pernas irmas canceladas > 3 s depois da execucao")


def checar_sessao(ordens: list[dict], params: dict, res: Resultado) -> None:
    """OCO por sessao: 1 bracket por dia, na hora do servidor pedida."""
    if _int(params, "PendingGatilho") != 1 or _int(params, "EntryOrderType") == 0:
        return
    hora = _int(params, "PendingHoraSessao", 8)
    dias: dict = {}
    for o in pendentes(ordens):
        dias.setdefault(o["abertura"].date(), set()).add(o["abertura"])
        if o["abertura"].hour != hora:
            res.falha("sessao", f"pendente as {o['abertura']:%H:%M:%S}, esperado a hora {hora}")
            return
    multi = [d for d, ts in dias.items() if len(ts) > 1]
    if multi:
        res.falha("sessao", f"{len(multi)} dias com mais de 1 bracket (ex.: {multi[0]})")
    res.metricas["dias_com_bracket"] = len(dias)


def checar_janela(ordens: list[dict], params: dict, res: Resultado) -> None:
    """Pendentes so dentro do pregao (TOD) e nos dias permitidos."""
    ini = _int(params, "TOD_From_Hour") * 60 + _int(params, "TOD_From_Min")
    fim = _int(params, "TOD_To_Hour") * 60 + _int(params, "TOD_To_Min")
    dias = ["TradeMonday", "TradeTuesday", "TradeWednesday", "TradeThursday", "TradeFriday"]
    fora = 0
    for o in pendentes(ordens):
        m = o["abertura"].hour * 60 + o["abertura"].minute
        dentro = (ini <= m < fim) if ini < fim else (m >= ini or m < fim)
        wd = o["abertura"].weekday()
        dia_ok = (wd > 4) or _bool(params, dias[wd])
        if not dentro or not dia_ok:
            fora += 1
    res.metricas["pendentes_fora_do_pregao"] = fora
    if fora:
        res.falha("janela", f"{fora} pendentes colocadas fora do horario/dias permitidos")


def parse_janelas_wfo(log: str) -> list[tuple[datetime, datetime]]:
    """Janelas OOS impressas pela EA no OnInit ("Out-Sample (OOS): d1 - d2", datas
    inclusivas: 00:00:00 do primeiro dia a 23:59:59 do ultimo)."""
    vistas: list[tuple[datetime, datetime]] = []
    for a, b in re.findall(r"Out-Sample \(OOS\): (\d{4}\.\d{2}\.\d{2}) - (\d{4}\.\d{2}\.\d{2})", log):
        janela = (datetime.strptime(a, "%Y.%m.%d"),
                  datetime.strptime(b, "%Y.%m.%d") + timedelta(days=1) - timedelta(seconds=1))
        if janela not in vistas:
            vistas.append(janela)
    return vistas


def checar_wfo(ordens: list[dict], deals: list[dict], log: str, params: dict,
               res: Resultado, tolerancia_s: int = 120) -> None:
    """Modo In-Sample (MetodoDeEntradawfo=0): entrada nova bloqueada no OOS. Pendente
    nao nasce nem executa la; a que estava viva na borda e cancelada."""
    if not _bool(params, "AtivarWFO") or _int(params, "MetodoDeEntradawfo") != 0:
        return
    oos = parse_janelas_wfo(log)
    res.metricas["janelas_oos"] = len(oos)
    if not oos:
        res.falha("wfo", "AtivarWFO ligado mas a EA nao imprimiu nenhuma janela OOS")
        return
    tol = timedelta(seconds=tolerancia_s)
    # A EA numera as janelas a partir da PRIMEIRA barra do teste (ex.: 23:00 da sexta), nao
    # de 00:00: as datas impressas ("2026.08.10 - 2026.08.14") tem ~1 dia de folga em cada
    # ponta. Vale so o interior: do dia seguinte ao inicio impresso ate 00:00 do fim impresso.
    oos = [(ini + timedelta(days=1), fim.replace(hour=0, minute=0, second=0)) for ini, fim in oos]
    nasceu = executou = viva_na_borda = cancelada_na_borda = 0
    ex: list[str] = []
    entradas = {d["ordem"]: d for d in deals if d["direcao"] == "in" and d["ordem"]}
    for o in pendentes(ordens):
        for ini, fim in oos:
            if ini + tol <= o["abertura"] <= fim:
                nasceu += 1
                ex.append(f"ordem {o['ordem']} colocada em {o['abertura']:%m.%d %H:%M:%S} (OOS {ini:%m.%d}..{fim:%m.%d})")
            d = entradas.get(o["ordem"])
            if d and ini + tol <= d["t"] <= fim:
                executou += 1
                ex.append(f"ordem {o['ordem']} EXECUTOU em {d['t']:%m.%d %H:%M:%S} dentro do OOS ({ini:%m.%d}..{fim:%m.%d})")
            # (a borda exata nao e conferida: ver o comentario acima)
    res.metricas.update(wfo_pendentes_nascidas_no_oos=nasceu, wfo_execucoes_no_oos=executou)
    if nasceu or executou:
        res.falha("wfo", f"{len(ex)} violacoes do bloqueio de entrada no OOS; ex.: {ex[0]}")


def checar_log(log: str, res: Resultado) -> None:
    contagens = {
        "pendente_invalida": len(re.findall(r"Invalid pending entry|Invalid session trigger", log)),
        "nao_enviada": len(re.findall(r"not sent", log)),
        "falha_envio": len(re.findall(r"myOrderSend failed", log)),
        "falha_cancelar": len(re.findall(r"Pending entry cancel failed", log)),
        "abortada": len(re.findall(r"Order opening aborted", log)),
    }
    res.metricas["log"] = contagens
    if contagens["pendente_invalida"]:
        res.falha("log", "a EA recusou a configuracao (Invalid pending entry/session trigger)")
    if contagens["falha_cancelar"]:
        res.falha("log", f"{contagens['falha_cancelar']} falhas ao cancelar pendente")
    if contagens["falha_envio"] or contagens["nao_enviada"]:
        codigos = sorted(set(re.findall(r"retcode=(\d+)", log)))
        res.aviso("log", f"{contagens['falha_envio']} 'myOrderSend failed' e "
                  f"{contagens['nao_enviada']} 'not sent' (retcodes {codigos})")


def conferir_cenario(nome: str, params: dict, ordens: list[dict], deals: list[dict],
                     barras: Barras | None, info: dict, log: str,
                     esperado: dict | None = None) -> Resultado:
    """Roda todas as conferencias que se aplicam ao cenario."""
    esperado = esperado or {}
    res = Resultado()
    checar_tipos(ordens, params, res)
    if _int(params, "EntryOrderType") == 0:
        checar_log(log, res)
        return res
    tick = info.get("tick") or 0.01
    if barras is not None:
        checar_preco(ordens, params, barras, tick, res)
        checar_sl_tp(ordens, params, barras, tick, res)
        if not esperado.get("sem_expiracao"):
            checar_expiracao(ordens, params, barras, res)
    checar_lote(ordens, params, info, res)
    checar_sobreposicao(ordens, params, res)
    checar_execucao(ordens, deals, tick, res)
    checar_oco(ordens, deals, params, res)
    checar_sessao(ordens, params, res)
    checar_wfo(ordens, deals, log, params, res)
    if esperado.get("janela"):
        checar_janela(ordens, params, res)
    checar_log(log, res)
    minimo = esperado.get("min_pendentes", 5)
    if res.metricas.get("pendentes", 0) < minimo:
        res.aviso("amostra", f"so {res.metricas.get('pendentes', 0)} pendentes (< {minimo}): "
                  "evidencia fraca")
    return res


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

@dataclass
class Cenario:
    nome: str
    sistema: str
    variante: str                     # BUY_MULTI, BOTH_BOLLINGER, BOTH_CANDLES...
    sobrepor: dict = field(default_factory=dict)
    simbolo: str = "XAUUSD"
    controle: str | None = None       # nome do cenario a mercado do mesmo modo
    esperado: dict = field(default_factory=dict)
    inicio: str = "2026.08.03"          # periodo CURTO (dono, 29/09): 4 semanas, segunda a segunda
    fim: str = "2026.09.01"
    origem_arquivo: str | None = None   # set pronto (ex.: o VALIDADO_ ao vivo) em vez do template
    execucao: int | None = None         # ExecutionMode do tester: -1 atraso aleatorio, >0 ms fixos


def _nome_tipo(t: int) -> str:
    return {0: "mercado", 1: "stop", 2: "limit", 3: "oco"}[t]


def catalogo() -> list[Cenario]:
    cs: list[Cenario] = []

    def pend(tipo: int, ref: int, k: float, n: int = 3) -> dict:
        return {"EntryOrderType": str(tipo), "PendingReferencia": str(ref),
                "PendingDistanciaATR": f"{k:g}", "PendingExpiracaoBarras": str(n)}

    # G1: matriz principal (Multi, sistema 04, XAUUSD): lado x tipo x referencia x k
    for lado in ("BUY", "SELL", "BOTH"):
        cs.append(Cenario(f"g1_{lado.lower()}_mercado", "04_SLTP_TRAIL", f"{lado}_MULTI",
                          pend(0, 0, 0.5)))
        for tipo in (1, 2):
            for ref in (0, 1):
                for k in (0.0, 0.5):
                    cs.append(Cenario(
                        f"g1_{lado.lower()}_{_nome_tipo(tipo)}_{'close' if ref == 0 else 'extremo'}_k{k:g}",
                        "04_SLTP_TRAIL", f"{lado}_MULTI", pend(tipo, ref, k),
                        controle=f"g1_{lado.lower()}_mercado"))
    # G2: OCO por sinal e por sessao
    for ref in (0, 1):
        for k in (0.25, 0.75):
            cs.append(Cenario(f"g2_oco_sinal_{'close' if ref == 0 else 'extremo'}_k{k:g}",
                              "04_SLTP_TRAIL", "BOTH_MULTI",
                              {**pend(3, ref, k, 4), "Hedging": "true"}))
    cs.append(Cenario("g2_oco_sessao_h8_f4", "13_OCO_ROMPIMENTO", "BOTH_MULTI",
                      {"Hedging": "true"}))
    cs.append(Cenario("g2_oco_sessao_h14_f8_close", "13_OCO_ROMPIMENTO", "BOTH_MULTI",
                      {"Hedging": "true", "PendingHoraSessao": "14", "PendingFaixaBarras": "8",
                       "PendingReferencia": "0", "PendingDistanciaATR": "0.5"}))
    # G3: as outras EAs (mesmo motor, arquivo proprio)
    for fam in ("BOLLINGER", "CANDLES"):
        v = f"BOTH_{fam}"
        cs.append(Cenario(f"g3_{fam.lower()}_mercado", "04_SLTP_TRAIL", v, pend(0, 0, 0.5)))
        for tipo in (1, 2):
            for ref in (0, 1):
                cs.append(Cenario(
                    f"g3_{fam.lower()}_{_nome_tipo(tipo)}_{'close' if ref == 0 else 'extremo'}_k0.5",
                    "04_SLTP_TRAIL", v, pend(tipo, ref, 0.5)))
        cs.append(Cenario(f"g3_{fam.lower()}_oco_sinal", "04_SLTP_TRAIL", v,
                          {**pend(3, 1, 0.5, 4), "Hedging": "true"}))
    # G4: a semente pendente em todos os sistemas
    for sis, var in (("01_SLTP", "BUY_MULTI"), ("02_SLTP_ORGANIC", "BUY_MULTI"),
                     ("03_TRAIL_ONLY", "BUY_MULTI"), ("05_BE_TRAIL", "BUY_MULTI"),
                     ("06_REVERSAL_EXIT", "BUY_MULTI"), ("07_GRID_SEPARATE", "BOTH_MULTI"),
                     ("11_SIGNAL_ONLY", "BUY_MULTI"), ("12_GRID_INVERSO", "BOTH_MULTI")):
        for tipo in (1, 2):
            cs.append(Cenario(f"g4_{sis[:2]}_{_nome_tipo(tipo)}", sis, var, pend(tipo, 1, 0.5)))
    # 09_MARTINGALE / 10_DALEMBERT viraram booster (RecoveryMode) dos sistemas normais
    # (a EA recusa D'Alembert com Fixed-R: "an absolute volume step breaks balance
    # independence" -- o cenario dele usa lote fixo)
    for rec, modo, extra in (("martingale", "1", {"MaxMartingaleSteps": "3"}),
                             ("dalembert", "2", {"MaxMartingaleSteps": "3", "DAlembertStep": "1",
                                                 "PositionSizeMode": "2", "PositionSizeValue": "0.02",
                                                 "CapitalBaseR": "0"})):
        for tipo in (1, 2):
            cs.append(Cenario(f"g4_rec_{rec}_{_nome_tipo(tipo)}", "04_SLTP_TRAIL", "BUY_MULTI",
                              {**pend(tipo, 1, 0.5), "RecoveryMode": modo, **extra}))
    # G5: modos de sizing (04 BUY)
    # Monetary = moeda por 1.00 lote: 10000 numa conta de 10k dava 1 lote de ouro (stop out)
    valores = {0: "1", 1: "200000", 2: "0.05", 3: "1"}
    for modo in range(4):
        base = {"PositionSizeMode": str(modo), "PositionSizeValue": valores[modo],
                "CapitalBaseR": "10000" if modo == 3 else "0"}
        cs.append(Cenario(f"g5_sizing{modo}_mercado", "04_SLTP_TRAIL", "BUY_MULTI",
                          {**base, **pend(0, 0, 0.5)}))
        for tipo in (1, 2):
            cs.append(Cenario(f"g5_sizing{modo}_{_nome_tipo(tipo)}", "04_SLTP_TRAIL", "BUY_MULTI",
                              {**base, **pend(tipo, 0, 0.5)}, controle=f"g5_sizing{modo}_mercado"))
    # G6: expiracao, pregao, parada de emergencia, WFO, forex de 5 casas
    for n in (1, 3, 5):
        cs.append(Cenario(f"g6_expira_{n}barras", "04_SLTP_TRAIL", "BUY_MULTI",
                          pend(1, 1, 4.0, n)))            # longe: nunca executa
    cs.append(Cenario("g6_pregao_10_12", "04_SLTP_TRAIL", "BUY_MULTI",
                      {**pend(1, 1, 4.0, 8), "TOD_From_Hour": "10", "TOD_To_Hour": "12",
                       "Fecharordensforadohorario": "true"},
                      esperado={"janela": True, "sem_expiracao": True}))
    cs.append(Cenario("g6_parada_emergencia", "04_SLTP_TRAIL", "BUY_MULTI",
                      {**pend(2, 0, 0.0, 3), "MaxEquityDrawdownPercent": "1"},
                      esperado={"parada": True}))
    for tipo in (1, 2):
        cs.append(Cenario(f"g6_gbpusd_{_nome_tipo(tipo)}", "04_SLTP_TRAIL", "BOTH_MULTI",
                          pend(tipo, 0, 0.5), simbolo="GBPUSD"))
    # G9: WFO In-Sample (o genetico do Autobot roda assim): IS 10 dias / OOS 4 dias
    wfo = {"AtivarWFO": "true", "MetodoDeEntradawfo": "0", "wfo_windowSize": "-1",
           "wfo_customWindowSizeDays": "10", "wfo_stepSize": "-1",
           "wfo_customStepSizePercent": "-4"}
    cs.append(Cenario("g9_wfo_mercado", "04_SLTP_TRAIL", "BUY_MULTI", {**wfo, **pend(0, 0, 0.5)}))
    for tipo in (1, 2):
        cs.append(Cenario(f"g9_wfo_{_nome_tipo(tipo)}", "04_SLTP_TRAIL", "BUY_MULTI",
                          {**wfo, **pend(tipo, 0, 0.5, 8)}))
    cs.append(Cenario("g9_wfo_oco_sinal", "04_SLTP_TRAIL", "BOTH_MULTI",
                      {**wfo, **pend(3, 1, 0.5, 8), "Hedging": "true"}))
    cs.append(Cenario("g9_wfo_oco_sessao", "13_OCO_ROMPIMENTO", "BOTH_MULTI", dict(wfo)))

    # G8: 13_OCO_ROMPIMENTO (bracket de rompimento armado por sessao): hora x faixa x
    # referencia x k x expiracao, um lado so, simbolos de 2/3/5 casas
    def s13(nome: str, extra: dict, simbolo: str = "XAUUSD") -> None:
        cs.append(Cenario(f"g8_{nome}", "13_OCO_ROMPIMENTO", "BOTH_MULTI", extra, simbolo=simbolo))

    # (ouro nao tem tick na hora 0 -- pausa diaria -- entao a hora 0 vai pro forex)
    s13("h0_f2_extremo_k0.25", {"PendingHoraSessao": "0", "PendingFaixaBarras": "2",
                                 "PendingReferencia": "1", "PendingDistanciaATR": "0.25"}, "GBPUSD")
    s13("h20_f4_extremo_k0.5", {"PendingHoraSessao": "20", "PendingFaixaBarras": "4",
                                 "PendingReferencia": "1", "PendingDistanciaATR": "0.5"})
    s13("h8_f4_extremo_k0", {"PendingReferencia": "1", "PendingDistanciaATR": "0"})
    s13("h8_f4_extremo_k1", {"PendingReferencia": "1", "PendingDistanciaATR": "1"})
    s13("h8_f4_exp2", {"PendingExpiracaoBarras": "2"})
    s13("h8_f4_exp8", {"PendingExpiracaoBarras": "8"})
    s13("h8_f4_hedging", {"Hedging": "true"})
    s13("h14_f8_extremo_k0.25_so_compra", {"PendingHoraSessao": "14", "PendingFaixaBarras": "8",
                                            "MaxShortTrades": "0"})
    s13("h14_f8_extremo_k0.25_so_venda", {"PendingHoraSessao": "14", "PendingFaixaBarras": "8",
                                           "MaxLongTrades": "0"})
    s13("gbpusd_h8_f4", {}, "GBPUSD")
    s13("usdjpy_h8_f4", {}, "USDJPY")
    s13("gbpusd_h14_f8_close_k0.5", {"PendingHoraSessao": "14", "PendingFaixaBarras": "8",
                                      "PendingReferencia": "0", "PendingDistanciaATR": "0.5"}, "GBPUSD")

    # G7: o set XAUUSD 04 que vai ao ar (Limit no fechamento, 0 ATR, 1 barra) contra
    # o mesmo set a mercado, com e sem atraso de execucao, em dado que ele nunca viu.
    # Pergunta: a vantagem da Limit sobrevive a latencia de verdade?
    janelas = {"a": ("2025.05.01", "2025.07.01"), "b": ("2026.07.01", "2026.09.01")}
    for jn, (ji, jf) in janelas.items():
        for exe, en in ((0, "sem_atraso"), (-1, "atraso_aleatorio"), (800, "atraso_800ms")):
            for tipo in (2, 0):
                cs.append(Cenario(f"g7_{jn}_{_nome_tipo(tipo)}_{en}", "04_SLTP_TRAIL", "BUY_MULTI",
                                  {"EntryOrderType": str(tipo)}, inicio=ji, fim=jf,
                                  origem_arquivo="VALIDADO_XAUUSD_04_SLTP_TRAIL_BUY_MULTI.set",
                                  execucao=exe, esperado={"comparacao": True}))
    return cs


# ---------------------------------------------------------------------------
# Execucao no tester (so aqui entram MT5 e o resto do Autobot)
# ---------------------------------------------------------------------------

def info_do_simbolo(simbolo: str) -> dict:
    p = BARRAS_DIR / f"{simbolo}_info.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def carregar_barras(simbolo: str) -> Barras | None:
    import pandas as pd
    dfs = {}
    for tf in TF_SEG:
        p = BARRAS_DIR / f"{simbolo}_{tf}.parquet"
        if p.exists():
            df = pd.read_parquet(p)
            dfs[tf] = df.set_index("time").sort_index()
    return Barras(dfs) if dfs else None


def exportar_barras(simbolos: list[str], inicio: str, fim: str,
                    terminal_exe: str) -> None:
    """Barras do proprio terminal (API MetaTrader5) -- a fonte independente."""
    import MetaTrader5 as mt5
    import pandas as pd
    BARRAS_DIR.mkdir(parents=True, exist_ok=True)
    if not mt5.initialize(path=terminal_exe, timeout=120000):
        raise SystemExit(f"MT5 nao inicializou: {mt5.last_error()}")
    try:
        de = datetime.strptime(inicio, "%Y.%m.%d").replace(tzinfo=timezone.utc)
        ate = datetime.strptime(fim, "%Y.%m.%d").replace(tzinfo=timezone.utc)
        tfs = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
               "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
               "D1": mt5.TIMEFRAME_D1}
        for sim in simbolos:
            mt5.symbol_select(sim, True)
            s = mt5.symbol_info(sim)
            if s is None:
                print(f"{sim}: simbolo nao encontrado no terminal")
                continue
            info = {"digits": s.digits, "point": s.point, "tick": s.trade_tick_size,
                    "contrato": s.trade_contract_size, "vol_min": s.volume_min,
                    "vol_step": s.volume_step, "stops_level": s.trade_stops_level,
                    "moeda_lucro": s.currency_profit,
                    # o que o broker aceita pra pendente (relevante pro ao vivo)
                    "freeze_level": s.trade_freeze_level,
                    "expiration_mode": s.expiration_mode,   # bits: 1 GTC, 2 DAY, 4 SPECIFIED, 8 SPECIFIED_DAY
                    "filling_mode": s.filling_mode,         # bits: 1 FOK, 2 IOC
                    "order_mode": s.order_mode,             # bits: 1 MARKET, 2 LIMIT, 4 STOP, 8 STOP_LIMIT, 16 SL, 32 TP
                    "trade_mode": s.trade_mode, "spread_pontos": s.spread}
            (BARRAS_DIR / f"{sim}_info.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
            for nome, tf in tfs.items():
                # em pedacos: o terminal recusa (Invalid params) um periodo longo em M1/M5
                partes = []
                ini = de
                while ini < ate:
                    fim_p = min(ini + timedelta(days=20), ate)
                    r = mt5.copy_rates_range(sim, tf, ini, fim_p)
                    if r is not None and len(r):
                        partes.append(pd.DataFrame(r))
                    ini = fim_p
                if not partes:
                    print(f"{sim} {nome}: sem barras ({mt5.last_error()})")
                    continue
                df = (pd.concat(partes).drop_duplicates("time").sort_values("time")
                      .reset_index(drop=True))
                df["time"] = pd.to_datetime(df["time"], unit="s")     # rotulo = hora do servidor
                df[["time", "open", "high", "low", "close", "spread"]].to_parquet(
                    BARRAS_DIR / f"{sim}_{nome}.parquet")
                print(f"{sim} {nome}: {len(df)} barras {df['time'].iloc[0]} .. {df['time'].iloc[-1]}")
    finally:
        mt5.shutdown()


def _garantir_origem_extra(nome: str) -> Path:
    """Set pronto (ex.: o VALIDADO_ ao vivo) copiado pra esta instalacao com nome
    NEUTRO (_TESTE_ORIGEM_...): um VALIDADO_ a mais viraria linha na aba de
    implantacao."""
    import optimize_sets as base
    import wrx_paths
    destino = base.DADOS / "MQL5" / "Profiles" / "Tester" / f"_TESTE_ORIGEM_{nome}"
    if destino.exists():
        return destino
    for _rotulo, pasta in wrx_paths.pastas_de_dados_do_projeto():
        fonte = pasta / "MQL5" / "Profiles" / "Tester" / nome
        if fonte.exists():
            shutil.copy2(fonte, destino)
            return destino
    raise SystemExit(f"set {nome} nao existe em nenhuma instalacao do projeto")


def limpar_temporarios() -> None:
    """Tira da pasta do tester os sets de trabalho do harness."""
    import optimize_sets as base
    tester = base.DADOS / "MQL5" / "Profiles" / "Tester"
    for arq in list(tester.glob("_TESTE_ORIGEM_*.set")) + [tester / "_TESTE_PENDENTES.set"]:
        arq.unlink(missing_ok=True)


def rodar_cenario(c: Cenario, refazer: bool = False) -> dict | None:
    import optimize_sets as base
    import optimize_two_stage as ots
    import campanha
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino_json = SAIDA / f"{c.nome}.json"
    # feito = JSON E relatorio; JSON sozinho e de um teste que nao produziu relatorio
    if destino_json.exists() and (SAIDA / f"{c.nome}.htm").exists() and not refazer:
        return None
    if c.origem_arquivo:
        origem = _garantir_origem_extra(c.origem_arquivo)
    else:
        origem = base.achar_set(c.simbolo, c.sistema, c.variante)
    if origem is None:
        raise SystemExit(f"{c.nome}: template {c.simbolo} {c.sistema} {c.variante} nao achado")
    # VerboseErrors NAO e input (e global da EA): falha de envio so aparece no
    # log via "not sent" (OrderCheck), que e incondicional.
    params = {"AtivarWFO": "false", **c.sobrepor}
    trabalho = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_TESTE_PENDENTES.set"
    ots.reescrever(origem, trabalho, [], params)
    efetivos = ots.valores_do_set(trabalho)
    faltando = ots.conferir_set(trabalho, params)
    deposito = campanha.resolver_deposito(c.simbolo, None)
    # relatorio velho NUNCA pode ser lido como o deste cenario: se o teste nao rodar
    # (EA recusou o set, agente caiu), fica sem .htm e a verificacao reprova
    (base.DADOS / "conf_wrx.htm").unlink(missing_ok=True)
    (SAIDA / f"{c.nome}.htm").unlink(missing_ok=True)
    antes = base.marcar_logs()
    escrever_original = base.escrever_ini
    if c.execucao is not None:
        def com_atraso(destino, *a, **k):
            escrever_original(destino, *a, **k)
            import configparser
            cp = configparser.ConfigParser()
            cp.optionxform = str
            cp.read(destino, encoding="utf-16")
            cp["Tester"]["ExecutionMode"] = str(c.execucao)
            with destino.open("w", encoding="utf-16") as fh:
                cp.write(fh, space_around_delimiters=False)
        base.escrever_ini = com_atraso
    try:
        # modelo 4 = tick real (padrao); testar_sistemas usa 1 = OHLC de 1 minuto
        medida = ots.passe_unico(trabalho, c.simbolo, "M1", c.inicio, c.fim, deposito,
                                 getattr(c, "modelo", 4), variante=c.variante)
    finally:
        base.escrever_ini = escrever_original
    log = base.texto_novo(antes)
    rel = base.DADOS / "conf_wrx.htm"
    if rel.exists():
        shutil.copy2(rel, SAIDA / f"{c.nome}.htm")
    (SAIDA / f"{c.nome}.log").write_text(log[-200000:], encoding="utf-8", errors="replace")
    registro = {"nome": c.nome, "simbolo": c.simbolo, "sistema": c.sistema,
                "variante": c.variante, "janela": [c.inicio, c.fim], "deposito": deposito,
                "execucao": c.execucao,
                "medida": {k: medida.get(k) for k in ("saldo", "trades")},
                "params": efetivos, "params_faltando": faltando,
                "quando": datetime.now().isoformat(timespec="seconds")}
    destino_json.write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8")
    return registro


def verificar(so: str | None = None) -> int:
    cenarios = {c.nome: c for c in catalogo()}
    resultados: dict[str, dict] = {}
    barras_cache: dict[str, Barras | None] = {}
    ordens_cache: dict[str, list[dict]] = {}
    deals_cache: dict[str, list[dict]] = {}
    for nome, c in cenarios.items():
        if so and so not in nome:
            continue
        j = SAIDA / f"{nome}.json"
        if not j.exists():
            continue
        reg = json.loads(j.read_text(encoding="utf-8"))
        htm = SAIDA / f"{nome}.htm"
        if not htm.exists():
            resultados[nome] = {"falhas": ["[relatorio] sem relatorio do tester"], "avisos": [], "metricas": {}}
            continue
        ordens, deals = parse_relatorio(htm)
        ordens_cache[nome] = ordens
        deals_cache[nome] = deals
        if c.simbolo not in barras_cache:
            barras_cache[c.simbolo] = carregar_barras(c.simbolo)
        info = info_do_simbolo(c.simbolo)
        log = (SAIDA / f"{nome}.log").read_text(encoding="utf-8", errors="replace") \
            if (SAIDA / f"{nome}.log").exists() else ""
        res = conferir_cenario(nome, reg["params"], ordens, deals, barras_cache[c.simbolo],
                               info, log, c.esperado)
        if c.controle and c.controle in ordens_cache and _int(reg["params"], "PositionSizeMode", 2) in (0, 1):
            comparar_controle(ordens, ordens_cache[c.controle], info, res,
                              deals_mercado=deals_cache.get(c.controle))
        if c.esperado.get("parada"):
            if "Trading stopped" not in log:
                res.aviso("parada", "a parada de emergencia nao disparou nesta janela")
            else:
                _checar_parada(ordens, deals, log, res)
        if reg.get("params_faltando"):
            res.falha("set", f"set de trabalho incompleto: {reg['params_faltando']}")
        resultados[nome] = {"falhas": res.falhas, "avisos": res.avisos, "metricas": res.metricas}
    return _relatorio_final(resultados, len(cenarios))


def lucro_semanal(deals: list[dict]) -> dict:
    """Lucro liquido (lucro + comissao + swap) dos deals de SAIDA, por semana ISO."""
    semanas: dict = {}
    for d in deals:
        if d["direcao"] != "out":
            continue
        ano, sem, _ = d["t"].isocalendar()
        semanas[(ano, sem)] = semanas.get((ano, sem), 0.0) + (d["lucro"] or 0.0) \
            + (d["comissao"] or 0.0) + (d["swap"] or 0.0)
    return semanas


def comparar_semanal(deals_a: list[dict], deals_b: list[dict]) -> dict:
    """a - b semana a semana (semana sem trade conta 0): media, erro-padrao e t."""
    sa, sb = lucro_semanal(deals_a), lucro_semanal(deals_b)
    todas = sorted(set(sa) | set(sb))
    difs = [sa.get(w, 0.0) - sb.get(w, 0.0) for w in todas]
    n = len(difs)
    if n < 2:
        return {"semanas": n, "media": None, "ep": None, "t": None}
    media = sum(difs) / n
    var = sum((x - media) ** 2 for x in difs) / (n - 1)
    ep = math.sqrt(var / n)
    return {"semanas": n, "lucro_a": round(sum(sa.values()), 2), "lucro_b": round(sum(sb.values()), 2),
            "media": round(media, 2), "ep": round(ep, 2), "t": round(media / ep, 2) if ep else None}


def _checar_parada(ordens: list[dict], deals: list[dict], log: str, res: Resultado) -> None:
    """Depois de "Trading stopped" nenhuma pendente nova pode nascer."""
    m = re.search(r"Trading stopped", log)
    if not m:
        return
    # o horario do evento vem do proprio relatorio: o ultimo deal de saida forcada
    saidas = [d for d in deals if d["direcao"] == "out"]
    if not saidas:
        return
    t_stop = min(d["t"] for d in saidas if "StopLoss triggered" in d["comentario"]) \
        if any("StopLoss triggered" in d["comentario"] for d in saidas) else None
    if t_stop is None:
        return
    depois = [o for o in pendentes(ordens) if o["abertura"] > t_stop + timedelta(seconds=5)]
    res.metricas["pendentes_apos_parada"] = len(depois)
    if depois:
        res.falha("parada", f"{len(depois)} pendentes colocadas DEPOIS da parada de emergencia")


def _relatorio_final(resultados: dict, total: int) -> int:
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "resultado.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    ruins = {n: r for n, r in resultados.items() if r["falhas"]}
    com_aviso = {n: r for n, r in resultados.items() if r["avisos"] and not r["falhas"]}
    linhas = [f"cenarios rodados: {len(resultados)} de {total} | com FALHA: {len(ruins)} | "
              f"so aviso: {len(com_aviso)}"]
    for n, r in sorted(resultados.items()):
        marca = "FALHA" if r["falhas"] else ("aviso" if r["avisos"] else "ok   ")
        m = r["metricas"]
        linhas.append(f"  {marca} {n:44} pend={m.get('pendentes', '-'):>4} "
                      f"exec={m.get('pendentes_executadas', '-'):>4} "
                      f"preco_ex={m.get('preco_exato', '-')}/{m.get('preco_ajustado_ao_mercado', '-')}")
        for f in r["falhas"]:
            linhas.append(f"        {f}")
        for a in r["avisos"]:
            linhas.append(f"        (aviso) {a}")
    comp = []
    for n in sorted(resultados):
        j = SAIDA / f"{n}.json"
        if n.startswith("g7_") and j.exists():
            reg = json.loads(j.read_text(encoding="utf-8"))
            saldo = (reg.get("medida") or {}).get("saldo")
            lucro = None if saldo is None else round(saldo - reg["deposito"], 2)
            comp.append(f"  {n:40} lucro {lucro} | {(reg.get('medida') or {}).get('trades')} trades")
    pares = []
    for n in sorted(resultados):
        if n.startswith("g7_") and "_limit_" in n:
            m = n.replace("_limit_", "_mercado_")
            if (SAIDA / f"{n}.htm").exists() and (SAIDA / f"{m}.htm").exists():
                _, da = parse_relatorio(SAIDA / f"{n}.htm")
                _, db = parse_relatorio(SAIDA / f"{m}.htm")
                c = comparar_semanal(da, db)
                pares.append(f"  {n.replace('g7_', '').replace('_limit', ''):32} Limit-mercado: semanas {c['semanas']} "
                             f"| media/semana {c['media']} +- {c['ep']} (t = {c['t']}) "
                             f"| lucro Limit {c.get('lucro_a')} x mercado {c.get('lucro_b')}")
    if comp:
        linhas += ["", "G7 -- o set ao vivo do XAUUSD, Limit x mercado, com e sem atraso de execucao:"] + comp
    if pares:
        linhas += ["", "G7 -- diferenca semanal Limit - mercado (|t| < 2 = indistinguivel de ruido):"] + pares
    texto = "\n".join(linhas)
    (SAIDA / "RESULTADO.md").write_text(texto, encoding="utf-8")
    print(texto)
    return 1 if ruins else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exportar-barras", action="store_true")
    ap.add_argument("--terminal", default="",
                    help="terminal64.exe da instalacao que vai exportar as barras")
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
    if args.exportar_barras:
        # 2024.06.15 em diante: alem da janela dos cenarios, cobre o G7 (2024-25) e o
        # ano do relatorio real do XAUUSD 04 (Limit) pra conferir o PRECO dele tambem.
        exportar_barras(["XAUUSD", "GBPUSD", "USDJPY"], "2024.06.15", "2026.09.05", args.terminal)
        return 0
    if args.rodar:
        i, n = (int(x) for x in args.shard.split("/"))
        todos = [c for c in catalogo() if not args.so or args.so in c.nome]
        for idx, c in enumerate(todos):
            if idx % n != i - 1:
                continue
            print(f"[{idx + 1}/{len(todos)}] {c.nome}", flush=True)
            reg = rodar_cenario(c, args.refazer)
            print("   ->", "ja feito" if reg is None else reg["medida"], flush=True)
        limpar_temporarios()
        return 0
    if args.verificar:
        return verificar(args.so or None)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
