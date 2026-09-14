# -*- coding: utf-8 -*-
"""Bateria de logica de entradas e inputs: varre CADA eixo que o template
otimiza, um de cada vez, e checa se o comportamento faz sentido.

Existe porque os validadores que ja havia olham outra coisa (dono,
2026-09-14: "verificacao de logica de entradas e inputs, busca de falhas
sistematica"):
  validate_system_sets  reimplementa o OnInit -- pega combinacao RECUSADA.
  smoke_test_sets       roda uma amostra -- pega set que nao opera.
  audit_wfo_sets        so o bloco WFO.
Nenhum pegaria o bug achado em 2026-09-14 na Candles: InpAppliedPrice=LOW
passava no OnInit, operava 752 vezes -- todas vendas, zero compras, num
combo BOTH -- e fechava com saldo MELHOR que o CLOSE. Valido, operando, e
sem sentido. E essa classe de defeito que esta bateria procura.

Cada eixo com faixa no .set e variado sozinho (o resto no valor do
template), num passe unico curto, em OHLC -- a pergunta e de LOGICA, nao de
precisao de tick. Antes de variar um eixo, liga a dependencia dele (GATES:
CandleTF3 so vale com AtivarSlot3; INDICADOR_USA: Slow_EMA so com MACD/EMA/
OsMA), senao todo eixo dependente pareceria morto. As invariantes sao
medidas DENTRO do proprio eixo -- um valor contra os outros valores do
mesmo eixo --, entao nao dependem de a base estar bem configurada:

  ERRO        erro de runtime no log (array out of range, zero divide...)
  LADO_MUDO   num combo BOTH, um valor zera compras OU vendas enquanto outro
              valor do mesmo eixo opera os dois lados
  VALOR_MORTO um valor zera os trades enquanto outro valor do eixo opera
  RECUSA      valores que o OnInit recusa -- orcamento do genetico perdido
  SEM_EFEITO  todos os valores dao resultado identico (eixo morto ou efeito
              raro na janela -- verificar)

    python bateria_logica.py --familias CANDLES --planejar
    python bateria_logica.py --familias CANDLES --saida bateria_logica/original.jsonl
    python bateria_logica.py --estatico
    python bateria_logica.py --analisar

Qual instalacao do MT5 usar vem de WRX_MT5_DATA_DIR/WRX_MT5_INSTALL_DIR,
setadas ANTES de rodar (mesmo esquema de campanha.py). Retomavel: pula o
que ja esta na --saida.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import optimize_sets as base
import optimize_two_stage as ots

AQUI = Path(__file__).resolve().parent
DIR_SAIDA = AQUI / "bateria_logica"
SISTEMAS = ["01_SLTP", "02_SLTP_ORGANIC", "03_TRAIL_ONLY", "04_SLTP_TRAIL",
            "05_BE_TRAIL", "06_REVERSAL_EXIT", "07_GRID_SEPARATE",
            "11_SIGNAL_ONLY", "12_GRID_INVERSO"]
# Chaves do .set que nao sao logica de entrada/saida: o WFO e desligado de
# proposito (backtest continuo, uma variavel por vez) e o idioma e cosmetico.
FORA = {"AtivarWFO", "MetodoDeEntradawfo", "input_end_date", "wfo_windowSize",
        "wfo_customWindowSizeDays", "wfo_stepSize",
        "wfo_customStepSizePercent", "InterfaceLanguage"}
ERROS_RUNTIME = re.compile(r"critical error|array out of range|zero divide|"
                           r"invalid pointer|stack overflow|cannot load|"
                           r"failed to create", re.I)
RECUSA = re.compile(r"incorrect input parameters", re.I)
MOTIVO = re.compile(r"(Invalid [^\r\n]{0,150}|[A-Za-z_]+ requires [^\r\n]{0,150})")


def valores_do_eixo(partes: list[str], max_valores: int) -> list[str]:
    _, start, step, stop, _ = partes
    if {start.lower(), stop.lower()} & {"true", "false"}:
        return ["false", "true"]
    try:
        a, s, b = float(start), float(step), float(stop)
    except ValueError:
        return []
    if s <= 0:
        return []
    n = int(round((b - a) / s)) + 1
    vals = [a + i * s for i in range(max(n, 1))]
    if len(vals) > max_valores:
        idx = sorted({round(i * (len(vals) - 1) / (max_valores - 1))
                      for i in range(max_valores)})
        vals = [vals[i] for i in idx]
    return list(dict.fromkeys(ots._formatar_valor_eixo(v, start, stop)
                              for v in vals))


def eixos(origem: Path) -> dict[str, list[str]]:
    return {n: p for n, p in ots.parametros_do_set(origem).items()
            if p[1] != p[3] and n not in FORA}


def travar_para(nome: str, valor: str, params: dict[str, list[str]]) -> dict:
    """Valor do eixo + a dependencia que faz ele valer alguma coisa."""
    t = {"AtivarWFO": "false", "InterfaceLanguage": "1", nome: valor}
    gate = ots.GATES.get(nome)
    if gate:
        t[gate] = "true"
    usa = ots.INDICADOR_USA.get(nome)
    ind = params.get("EntryIndicator")
    if usa and ind and ind[1] != ind[3]:
        faixa = {int(float(x)) for x in valores_do_eixo(ind, 99)}
        if int(float(ind[0])) not in usa and faixa & usa:
            t["EntryIndicator"] = str(min(faixa & usa))
    return t


def plano(familias: list[str], simbolo: str, sistema_base: str,
          saidas_em: set[str], max_valores: int) -> list[dict]:
    """Lista de passes: o sistema-base com TODOS os eixos, e -- so nas
    familias de `saidas_em` -- cada outro sistema apenas com os eixos que
    diferem do sistema-base (geometria de saida, grid). Os eixos de entrada
    e filtro sao os mesmos em todo sistema; testar de novo so gastaria
    tempo."""
    passes = []
    for fam in familias:
        var = f"BOTH_{fam}"
        origem_b = base.achar_set(simbolo, sistema_base, var)
        if origem_b is None:
            print(f"!! sem set {simbolo}/{sistema_base}/{var}")
            continue
        eixos_b = eixos(origem_b)
        alvos = [(sistema_base, origem_b, eixos_b)]
        if fam in saidas_em:
            for sis in SISTEMAS:
                if sis == sistema_base:
                    continue
                o = base.achar_set(simbolo, sis, var)
                if o is None:
                    continue
                ex = eixos(o)
                proprios = {n: p for n, p in ex.items()
                            if n not in eixos_b or p[1:4] != eixos_b[n][1:4]}
                alvos.append((sis, o, proprios))
        for sis, origem, lista in alvos:
            todos = ots.parametros_do_set(origem)
            passes.append({"familia": fam, "sistema": sis, "variante": var,
                           "eixo": "__base__", "valor": "",
                           "travar": {"AtivarWFO": "false",
                                      "InterfaceLanguage": "1"},
                           "origem": str(origem)})
            for nome, partes in sorted(lista.items()):
                for v in valores_do_eixo(partes, max_valores):
                    passes.append({"familia": fam, "sistema": sis,
                                   "variante": var, "eixo": nome, "valor": v,
                                   "travar": travar_para(nome, v, todos),
                                   "origem": str(origem)})
    return passes


def lados(html: str) -> tuple[int, int]:
    c = v = 0
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
        cel = {re.sub(r"<[^>]+>", "", x).strip().lower()
               for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)}
        if not ({"in", "entrada"} & cel):
            continue
        if {"buy", "compra"} & cel:
            c += 1
        elif {"sell", "venda"} & cel:
            v += 1
    return c, v


def chave(p: dict, simbolo: str, inicio: str, fim: str) -> tuple:
    return (p["familia"], p["sistema"], p["eixo"], p["valor"],
            simbolo, inicio, fim)


def rodar(passes: list[dict], simbolo: str, inicio: str, fim: str,
          saida: Path, partes: frozenset[int] = frozenset({1}),
          n_partes: int = 1, parte_em: set[str] | None = None) -> None:
    """`partes`/`n_partes` dividem os passes entre terminais pela CHAVE do
    passe (crc32 -- hash() do Python muda a cada processo e nao serve pra
    isto), so nas familias de `parte_em`; as demais rodam inteiras. Um
    terminal pode pegar mais de uma fatia ({1,2} de 3) pra compensar carga
    desigual. Ja feito e lido de TODOS os .jsonl da pasta, nao so da propria
    --saida: um terminal nunca repete o que o outro gravou, mesmo depois de
    trocar a divisao no meio (dono, 2026-09-14: "usa os dois terminais")."""
    import zlib
    import campanha  # tardio: so quem roda paga o import
    saida.parent.mkdir(parents=True, exist_ok=True)
    feitos = set()
    for arq in saida.parent.glob("*.jsonl"):
        for linha in arq.read_text(encoding="utf-8").splitlines():
            if linha.strip():
                r = json.loads(linha)
                feitos.add((r["familia"], r["sistema"], r["eixo"], r["valor"],
                            r["simbolo"], r["inicio"], r["fim"]))
    def minha(p: dict) -> bool:
        if n_partes <= 1 or (parte_em and p["familia"] not in parte_em):
            return True
        k = "|".join(map(str, chave(p, simbolo, inicio, fim)))
        return zlib.crc32(k.encode("utf-8")) % n_partes + 1 in partes

    pendentes = [p for p in passes
                 if chave(p, simbolo, inicio, fim) not in feitos and minha(p)]
    print(f"terminal: {base.TERMINAL}\n{len(passes)} passes no plano | "
          f"{len(passes) - len(pendentes)} ja feitos | "
          f"{len(pendentes)} a rodar", flush=True)
    deposito = campanha.resolver_deposito(simbolo, None)
    trab = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_BATERIA.set"
    rel = base.DADOS / "conf_wrx.htm"
    t0 = time.time()
    for i, p in enumerate(pendentes, 1):
        rel.unlink(missing_ok=True)
        ots.reescrever(Path(p["origem"]), trab, [], p["travar"])
        antes = base.marcar_logs()
        tp = time.time()
        r = ots.passe_unico(trab, simbolo, "M1", inicio, fim, deposito, 1,
                            timeout=600, variante=p["variante"])
        dt = time.time() - tp
        log = base.texto_novo(antes)
        c, v = (lados(rel.read_text(encoding="utf-16", errors="replace"))
                if rel.exists() else (0, 0))
        motivo = MOTIVO.search(log)
        reg = {**{k: p[k] for k in ("familia", "sistema", "variante",
                                    "eixo", "valor")},
               "travar": p["travar"], "simbolo": simbolo, "inicio": inicio,
               "fim": fim, "trades": r.get("trades"), "saldo": r.get("saldo"),
               "compras": c, "vendas": v,
               "recusado": bool(RECUSA.search(log)) or bool(
                   motivo and r.get("trades") is None and c + v == 0),
               "motivo": motivo.group(1) if motivo else None,
               "erros": sorted({m.group(0).lower()
                                for m in ERROS_RUNTIME.finditer(log)}),
               "abortos": r.get("abortos"), "segundos": round(dt, 1),
               "quando": datetime.now().isoformat(timespec="seconds")}
        with saida.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
        resto = (time.time() - t0) / i * (len(pendentes) - i) / 60
        print(f"[{i}/{len(pendentes)}] {p['familia']} {p['sistema']} "
              f"{p['eixo']}={p['valor']}: trades={reg['trades']} "
              f"c/v={c}/{v}{' RECUSADO' if reg['recusado'] else ''}"
              f"{' ERRO' if reg['erros'] else ''} ({dt:.0f}s, "
              f"~{resto:.0f} min restantes)", flush=True)
    trab.unlink(missing_ok=True)


def analisar(arquivos: list[Path]) -> str:
    regs = []
    for a in arquivos:
        regs += [json.loads(l) for l in a.read_text(encoding="utf-8")
                 .splitlines() if l.strip()]
    grupos: dict[tuple, list[dict]] = defaultdict(list)
    for r in regs:
        if r["eixo"] != "__base__":
            grupos[(r["familia"], r["sistema"], r["eixo"])].append(r)
    achados = []
    for (fam, sis, eixo), rs in sorted(grupos.items()):
        ok = [r for r in rs if not r["recusado"]]
        operou = [r for r in ok if (r["trades"] or 0) > 0]
        dois_lados = [r for r in ok if r["compras"] > 0 and r["vendas"] > 0]
        tag = f"{fam:<9} {sis:<16} {eixo}"
        for r in rs:
            if r["erros"]:
                achados.append(("1 ERRO", tag, f"{eixo}={r['valor']}: "
                                f"{', '.join(r['erros'])}"))
        if dois_lados:
            for r in ok:
                if (r["trades"] or 0) > 0 and (r["compras"] == 0) != (
                        r["vendas"] == 0):
                    achados.append(("2 LADO_MUDO", tag,
                                    f"{eixo}={r['valor']}: compras/vendas="
                                    f"{r['compras']}/{r['vendas']} (outros "
                                    f"valores operam os dois lados)"))
        if operou:
            for r in ok:
                if not (r["trades"] or 0):
                    achados.append(("3 VALOR_MORTO", tag,
                                    f"{eixo}={r['valor']}: 0 trades (outros "
                                    f"valores operam)"))
        recusados = [r["valor"] for r in rs if r["recusado"]]
        if recusados:
            motivo = next((r["motivo"] for r in rs if r["motivo"]), "")
            achados.append(("4 RECUSA", tag, f"{len(recusados)}/{len(rs)} "
                            f"valores recusados {recusados} {motivo or ''}"))
        if len(ok) >= 2 and len({(r["trades"], r["saldo"]) for r in ok}) == 1:
            achados.append(("5 SEM_EFEITO", tag,
                            f"{len(ok)} valores, todos trades="
                            f"{ok[0]['trades']} saldo={ok[0]['saldo']}"))
    linhas = [f"Bateria de logica -- {len(regs)} passes, "
              f"{len(grupos)} eixos testados, {len(achados)} achados", ""]
    cont = Counter(a[0] for a in achados)
    linhas += [f"  {k[2:]:<12} {cont[k]}" for k in sorted(cont)] + [""]
    atual = None
    for sev, tag, det in sorted(achados):
        if sev != atual:
            linhas += ["", f"== {sev[2:]} =="]
            atual = sev
        linhas.append(f"  {tag:<48} {det}")
    return "\n".join(linhas)


def estatico() -> str:
    """Audita a biblioteca inteira de templates sem terminal: faixa
    impossivel, eixo Y amarrado a um gate cravado em false (morto no set),
    e valores que o OnInit ja recusa por construcao."""
    problemas: dict[str, list[str]] = defaultdict(list)
    n_sets = 0
    for s in sorted(base.SETS.rglob("*.set")):
        n_sets += 1
        params = ots.parametros_do_set(s)
        rotulo = str(s.relative_to(base.SETS))
        for nome, (cur, start, step, stop, flag) in params.items():
            if flag != "Y" or nome in FORA:
                continue
            boolv = {start.lower(), stop.lower()} & {"true", "false"}
            if not boolv:
                try:
                    a, st, b = float(start), float(step), float(stop)
                    if st <= 0 or a > b:
                        problemas["faixa impossivel"].append(
                            f"{rotulo}: {nome}={start}..{stop} passo {step}")
                except ValueError:
                    problemas["faixa nao numerica"].append(f"{rotulo}: {nome}")
            gate = ots.GATES.get(nome)
            if gate and gate in params:
                g = params[gate]
                if g[1] == g[3] and g[0].lower() == "false":
                    problemas["eixo Y com gate cravado false"].append(
                        f"{rotulo}: {nome} (gate {gate})")
        if s.stem.endswith("CANDLES") and "InpAppliedPrice" in params:
            p = params["InpAppliedPrice"]
            faixa = {int(float(x)) for x in valores_do_eixo(p, 99)}
            if p[4] == "Y" and faixa & {2, 3, 4}:
                problemas["CANDLES: InpAppliedPrice inclui OPEN/HIGH/LOW "
                          "(recusados no OnInit)"].append(rotulo)
    linhas = [f"Auditoria estatica -- {n_sets} sets em {base.SETS}", ""]
    if not problemas:
        linhas.append("nenhum problema estrutural")
    for tipo, lst in sorted(problemas.items(), key=lambda x: -len(x[1])):
        linhas.append(f"{tipo}: {len(lst)}")
        linhas += [f"    {x}" for x in lst[:6]]
        if len(lst) > 6:
            linhas.append(f"    ... +{len(lst) - 6}")
    return "\n".join(linhas)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--familias", default="MULTI,ICHIMOKU,BOLLINGER,CANDLES")
    ap.add_argument("--simbolo", default="EURUSD")
    ap.add_argument("--inicio", default="2026.03.18")
    ap.add_argument("--fim", default="2026.09.14")
    ap.add_argument("--sistema-base", default="01_SLTP")
    ap.add_argument("--saidas-em", default="MULTI",
                    help="familias onde os eixos proprios de cada sistema "
                         "(saida/grid) tambem sao varridos")
    ap.add_argument("--max-valores", type=int, default=6)
    ap.add_argument("--saida", default=str(DIR_SAIDA / "resultados.jsonl"))
    ap.add_argument("--planejar", action="store_true")
    ap.add_argument("--analisar", action="store_true")
    ap.add_argument("--estatico", action="store_true")
    ap.add_argument("--parte", default="1/1",
                    help="fatia(s) deste terminal, ex.: 1/2 ou 1,2/3")
    ap.add_argument("--parte-em", default="",
                    help="familias divididas por --parte (vazio = todas)")
    a = ap.parse_args()

    if a.estatico:
        txt = estatico()
        DIR_SAIDA.mkdir(exist_ok=True)
        (DIR_SAIDA / "estatico.txt").write_text(txt, encoding="utf-8")
        print(txt)
        return
    if a.analisar:
        arqs = sorted(DIR_SAIDA.glob("*.jsonl"))
        txt = analisar(arqs)
        (DIR_SAIDA / "relatorio.txt").write_text(txt, encoding="utf-8")
        print(txt)
        return
    fams = [f.strip().upper() for f in a.familias.split(",") if f.strip()]
    passes = plano(fams, a.simbolo, a.sistema_base,
                   {f.strip().upper() for f in a.saidas_em.split(",")},
                   a.max_valores)
    if a.planejar:
        por = Counter((p["familia"], p["sistema"]) for p in passes)
        for (fam, sis), n in sorted(por.items()):
            neixos = len({p["eixo"] for p in passes
                          if (p["familia"], p["sistema"]) == (fam, sis)}) - 1
            print(f"{fam:<10} {sis:<17} {neixos:>3} eixos {n:>4} passes")
        print(f"TOTAL {len(passes)} passes (~{len(passes) * 10 / 60:.0f} min "
              f"a ~10s por passe)")
        return
    idx, _, n = a.parte.partition("/")
    partes = frozenset(int(x) for x in idx.split(",") if x.strip())
    parte_em = {f.strip().upper() for f in a.parte_em.split(",") if f.strip()}
    rodar(passes, a.simbolo, a.inicio, a.fim, Path(a.saida),
          partes=partes, n_partes=int(n or 1), parte_em=parte_em or None)


if __name__ == "__main__":
    main()
