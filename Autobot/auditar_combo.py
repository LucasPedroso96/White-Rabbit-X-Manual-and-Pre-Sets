# -*- coding: utf-8 -*-
"""Auditor de veredito: um algoritmo terminou -- a aprovacao/reprovacao foi justa?

Le o TEXTO que o circuito (optimize_two_stage.py) escreveu no log de um combo
(campanha) ou de uma formula (sweep) e devolve: veredito, motivo EXATO (qual
gate decidiu), numeros-chave e SINAIS de que a decisao merece revisao humana.

Nasceu de um caso real (2026-09-20, CHFJPY/03_TRAIL_ONLY): retencao de 1117%
parecia otima, o log dizia "nao sobreviveu aos juros compostos", e so abrindo o
log bruto do MT5 se viu que o set perdeu 99% em 3 anos (reprovacao certa, mensagem
errada). O dono pediu: "sempre que terminar um algoritmo chame voce para avaliar
se foi justa a aprovacao ou reprovacao". Este modulo e a parte mecanica; o
julgamento final e de quem le a saida (vigia_auditoria.py acorda o revisor).

Nao decide nada sozinho: SINAIS sao heuristicas (limites nomeados abaixo,
ajustaveis), nao regras de aprovacao.

    python auditar_combo.py campanha_oficial_trail.log      # ultimo combo pronto
    python auditar_combo.py sweep_04_SLTP_TRAIL_XAUUSD_11_ReturnUniformity.log
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Limites dos sinais (heuristicas de suspeita, NAO criterios de aprovacao).
RETENCAO_MIRAGEM = 500.0     # retencao acima disso: denominador (IS) ~ 0
WFE_IRREAL = 1000.0          # WFE acima disso: mesma suspeita
TRADES_FINO = 60             # holdout/historico com menos trades: amostra fina
TRADES_OOS_FINO = 30
PF_FRACO = 1.15              # aprovado com Profit Factor abaixo disso
DD_ALTO = 35.0               # drawdown (%) alto
PISO_RETENCAO = 30.0         # min_retencao padrao do circuito
FOLGA_BORDA = 10.0           # "por pouco": a ate 10 pontos do piso
SINAIS_INFORMATIVOS = ("GEOMETRIA_CORTADA", "SEM_PERIODO_ANTERIOR")

_CAB_CAMPANHA = re.compile(r"^\[(\d+)/(\d+)\] (\S+) (\S+) (\S+)\s*$", re.M)
_CAB_SWEEP = re.compile(r"^=== (\S+) (\S+) (\S+) \|", re.M)

# (rotulo, regex) na ordem em que os gates decidem no circuito.
_MOTIVOS = [
    ("Estagio 1/2 sem candidato (pisos de trades/lucro)",
     r"estagio [12]: (?:relatorio vazio|nenhum candidato)[^\n]*"),
    ("retencao fora da amostra abaixo do piso", r"REPROVADO na retencao[^\n]*"),
    ("divergencia OHLC x tick real", r"REPROVADO na divergencia[^\n]*"),
    ("gate relativo ao campeao", r"REPROVADO no gate relativo[^\n]*"),
    ("historico completo (relativo/catastrofe)",
     r"REPROVADO na confirmacao no historico completo[^\n]*"),
    ("prova em % (juros compostos)", r"REPROVADO na prova em %[^\n]*"),
    ("sobrevivencia (periodo completo)", r"REPROVADO na sobrevivencia[^\n]*"),
    ("periodo anterior ao treino", r"REPROVADO no periodo anterior[^\n]*"),
    ("holdout longo (criterio antigo)", r"REPROVADO no holdout longo[^\n]*"),
    ("WFA de reotimizacao (WFE<=0)", r"REPROVADO na WFA[^\n]*"),
]


def _f(padrao: str, texto: str, grupo: int = 1):
    m = None
    for m in re.finditer(padrao, texto):
        pass  # ultima ocorrencia
    return m.group(grupo) if m else None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def json_final(texto: str) -> dict:
    achado = {}
    for ln in texto.splitlines():
        if ln.startswith("{") and '"simbolo"' in ln:
            try:
                achado = json.loads(ln)
            except json.JSONDecodeError:
                pass
    return achado


def auditar(texto: str, rotulo: str = "") -> dict:
    """Devolve {rotulo, veredito, motivo, numeros, sinais, sugestao}."""
    js = json_final(texto)
    aprov = re.search(r"^\s+APROVADO: candidato pronto", texto, re.M) is not None
    repro = re.search(r"^\s+REPROVADO: nao promova", texto, re.M) is not None
    veredito = ("APROVADO" if aprov else "REPROVADO" if repro
                else "INCOMPLETO")

    motivo = None
    if veredito == "REPROVADO":
        for nome, padrao in _MOTIVOS:
            m = re.search(padrao, texto)
            if m:
                motivo = f"{nome}: {m.group(0).strip()[:110]}"
                break
        if motivo is None and js.get("motivo_reprovacao_precoce"):
            motivo = f"reprovado cedo: {js['motivo_reprovacao_precoce'][:110]}"
        motivo = motivo or "motivo nao identificado no log (ler o log inteiro)"

    ret_oos = _num(_f(r"retencao confirmada em tick real: (-?[\d.]+)%", texto))
    if ret_oos is None:
        ret_oos = _num(js.get("retencao_oos"))
    diverg = _num(_f(r"divergencia:\s+(-?[\d.]+)%", texto))
    ret_pct = _num(_f(r"retencao em %: (-?[\d.]+)%", texto))
    pct_nd = re.search(r"retencao em %: n/d", texto) is not None
    m_hist = re.search(
        r"historico completo \(\d+ anos continuos\): lucro (\S+) \| (\S+) trades "
        r"\| expectancy (\S+)R \| DD (\S+)% \| PF (\S+)", texto)
    hist = (dict(lucro=_num(m_hist.group(1)), trades=_num(m_hist.group(2)),
                 expectancy=_num(m_hist.group(3)), dd=_num(m_hist.group(4)),
                 pf=_num(m_hist.group(5))) if m_hist else None)
    m_ho = re.search(r"holdout longo[^:\n]*: lucro (-?[\d.]+|None) \| (\d+) trades", texto)
    holdout = (dict(lucro=_num(m_ho.group(1)), trades=int(m_ho.group(2)))
               if m_ho else None)
    m_ant = re.search(r"periodo anterior ao treino: ([^\n]+)", texto)
    wfe = _num(_f(r"WFE global (-?[\d.]+)", texto))
    ciclos = _f(r"WFE global \S+ \| (\d+/\d+) ciclos", texto)
    pf = _num(js.get("profit_factor"))
    dd = _num(js.get("max_dd_pct"))
    trades_oos = _num(js.get("trades_oos"))
    m_min = re.search(r"^-> \S+ \| retencao=\S+ \| ([\d.]+) min", texto, re.M)
    minutos = _num(m_min.group(1)) if m_min else None

    numeros = {"retencao_oos_pct": ret_oos, "divergencia_pct": diverg,
               "retencao_em_pct": ret_pct, "historico_3a": hist,
               "holdout_3a": holdout, "periodo_anterior": (
                   m_ant.group(1).strip()[:120] if m_ant else None),
               "wfe_global_pct": wfe, "wfa_ciclos": ciclos, "pf": pf,
               "dd_pct": dd, "trades_oos": trades_oos, "minutos": minutos}

    sinais: list[str] = []
    if ret_oos is not None and ret_oos > RETENCAO_MIRAGEM:
        sinais.append(f"RETENCAO_MIRAGEM: {ret_oos:.0f}% -> lucro no In-Sample "
                      "quase zero no denominador, nao e robustez")
    if wfe is not None and wfe > WFE_IRREAL:
        sinais.append(f"WFE_IRREAL: {wfe:.0f}% (mesma suspeita de denominador)")
    if hist:
        if hist["lucro"] is not None and hist["lucro"] < 0:
            sinais.append(f"HISTORICO_NEGATIVO: {hist['lucro']:.2f} em 3 anos "
                          "continuos" + (" mesmo APROVADO"
                                         if veredito == "APROVADO" else ""))
        if hist["trades"] is not None and hist["trades"] < TRADES_FINO:
            sinais.append(f"AMOSTRA_FINA: {int(hist['trades'])} trades em 3 anos")
    if holdout and holdout["trades"] < TRADES_FINO:
        sinais.append(f"AMOSTRA_FINA: holdout com {holdout['trades']} trades")
    if trades_oos is not None and trades_oos < TRADES_OOS_FINO:
        sinais.append(f"AMOSTRA_FINA: {int(trades_oos)} trades fora da amostra")
    if veredito == "APROVADO":
        if pf is not None and pf < 1.0:
            sinais.append(f"PF_INCOERENTE: PF {pf:.2f} < 1 num candidato "
                          "APROVADO com lucro positivo -- a metrica de PF do "
                          "JSON pode estar errada (nao confiar nela)")
        elif pf is not None and pf < PF_FRACO:
            sinais.append(f"PF_FRACO: {pf:.2f} aprovado com margem pequena")
        if ret_oos is not None and PISO_RETENCAO <= ret_oos < PISO_RETENCAO + FOLGA_BORDA:
            sinais.append(f"APROVADO_POR_POUCO: retencao {ret_oos:.1f}% "
                          f"(piso {PISO_RETENCAO:.0f}%)")
        if m_ant and "nao avaliado" in m_ant.group(1):
            sinais.append("SEM_PERIODO_ANTERIOR: camada 2 nao avaliou "
                          "(amostra/dias insuficientes)")
        if not m_ant and re.search(r"holdout longo", texto):
            sinais.append("SEM_PERIODO_ANTERIOR: rodou sob a regra antiga "
                          "(sem camada 2)")
    if veredito == "REPROVADO" and ret_oos is not None:
        if PISO_RETENCAO - FOLGA_BORDA <= ret_oos < PISO_RETENCAO:
            sinais.append(f"REPROVADO_POR_POUCO: retencao {ret_oos:.1f}% "
                          f"(piso {PISO_RETENCAO:.0f}%) -- conferir se a "
                          "janela foi injusta")
    if dd is not None and dd > DD_ALTO:
        sinais.append(f"DD_ALTO: {dd:.1f}%")
    if diverg is not None and diverg > 20:
        sinais.append(f"DIVERGENCIA: {diverg:.1f}% entre OHLC e tick real")
    if pct_nd:
        sinais.append("PROVA_EM_%_SEM_RETENCAO: In-Sample nao deu lucro em % "
                      "(nada a reter)")
    if "ATENCAO: trades mudaram" in texto:
        sinais.append("TRADES_MUDARAM_EM_%: caminho diferente no modo % "
                      "(margem/abortos?)")
    infra = (len(re.findall(r"recusou a conexao", texto))
             + len(re.findall(r"WATCHDOG|TRAVADO", texto))
             + len(re.findall(r"nao respondeu em 90s", texto)))
    if infra >= 3 or re.search(r"WATCHDOG|TRAVADO", texto):
        sinais.append(f"INFRA: {infra} ocorrencia(s) de agente recusado/"
                      "travado -- o retry automatico pode nao ter coberto "
                      "todos os passes")
    if "estagio 3.5 cortado" in texto:
        sinais.append("GEOMETRIA_CORTADA: Estagio 3.5 cortado pelo teto -> "
                      "geometria de OHLC mantida")

    # Sinais INFORMATIVOS (contexto conhecido, nao mudam o veredito nem pedem
    # revisao sozinhos): geometria cortada no XAUUSD e regra antiga sem camada 2.
    relevantes = [s for s in sinais
                  if not s.startswith(SINAIS_INFORMATIVOS)]
    if veredito == "INCOMPLETO":
        sugestao = "combo nao terminou (sem veredito no log)"
    elif relevantes:
        sugestao = "REVISAR (ha sinais)"
    else:
        sugestao = ("decisao consistente com os numeros (sem sinais)")
    return {"rotulo": rotulo, "veredito": veredito, "motivo": motivo,
            "numeros": numeros, "sinais": sinais, "sugestao": sugestao}


def blocos_campanha(texto: str) -> list[tuple[str, str]]:
    """[(rotulo 'SIM SISTEMA VARIANTE', texto do bloco)] so dos combos PRONTOS
    (com a linha final '-> ...')."""
    cabs = list(_CAB_CAMPANHA.finditer(texto))
    out = []
    for i, m in enumerate(cabs):
        fim = cabs[i + 1].start() if i + 1 < len(cabs) else len(texto)
        bloco = texto[m.start():fim]
        if re.search(r"^-> \S+", bloco, re.M):
            out.append((f"{m.group(3)} {m.group(4)} {m.group(5)}", bloco))
    return out


def rotulo_sweep(texto: str, nome: str) -> str:
    m = _CAB_SWEEP.search(texto)
    return f"{m.group(1)} {m.group(2)} {m.group(3)}" if m else nome


def formatar(a: dict) -> str:
    n = a["numeros"]
    linhas = [f"AVALIAR {a['rotulo']} -> {a['veredito']}"
              + (f" | {a['motivo']}" if a["motivo"] else "")]
    partes = []
    if n["retencao_oos_pct"] is not None:
        partes.append(f"ret {n['retencao_oos_pct']:.1f}%")
    if n["divergencia_pct"] is not None:
        partes.append(f"diverg {n['divergencia_pct']:.1f}%")
    if n["retencao_em_pct"] is not None:
        partes.append(f"ret% {n['retencao_em_pct']:.1f}%")
    if n["historico_3a"]:
        h = n["historico_3a"]
        partes.append(f"3a: lucro {h['lucro']} / {h['trades']} tr / "
                      f"exp {h['expectancy']}R / DD {h['dd']}%")
    if n["holdout_3a"]:
        partes.append(f"holdout3a {n['holdout_3a']['lucro']} "
                      f"({n['holdout_3a']['trades']} tr)")
    if n["periodo_anterior"]:
        partes.append(f"anterior: {n['periodo_anterior']}")
    if n["wfe_global_pct"] is not None:
        partes.append(f"WFA {n['wfa_ciclos']} WFE {n['wfe_global_pct']:.0f}%")
    if n["pf"] is not None:
        partes.append(f"PF {n['pf']:.2f}")
    if n["dd_pct"] is not None:
        partes.append(f"DD {n['dd_pct']:.1f}%")
    if partes:
        linhas.append("  numeros: " + " | ".join(partes))
    for s in a["sinais"]:
        linhas.append("  SINAL " + s)
    linhas.append("  => " + a["sugestao"])
    return "\n".join(linhas)


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) < 2:
        print(__doc__)
        return 2
    caminho = Path(argv[1])
    texto = caminho.read_text(encoding="utf-8", errors="replace")
    prontos = blocos_campanha(texto)
    if prontos:
        rot, bloco = prontos[-1]
        print(formatar(auditar(bloco, rot)))
    else:
        print(formatar(auditar(texto, rotulo_sweep(texto, caminho.stem))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
