# -*- coding: utf-8 -*-
"""Audita o painel do White Rabbit X sem precisar abrir o MetaTrader.

Le o corpo de UpdateChartDashboard e verifica o que o olho so pega depois de
anexar a EA no grafico. Desde 2026-08-01 o painel e UM OBJ_BITMAP so (CCanvas),
nao mais objetos OBJ_LABEL individuais -- as linhas viram DashPush/DashRow/
DashCycleLine em vez de DashboardSetLabel/DashboardRow/DashboardCycleLine, mas
o espacamento vertical continua a mesma grade fixa de sempre.

1. TEXTOS       duas linhas com o mesmo conteudo escritas no mesmo render.
2. SOBREPOSICAO duas linhas na mesma coordenada Y, ou espacamento menor que a
                altura da fonte -- que e como o texto acaba montado em cima do
                de baixo.
3. TIPOGRAFIA   quantos tamanhos e quantas familias de fonte estao em uso.
4. PALETA       cores fora da paleta declarada.
5. CICLOS       o painel cobre tudo o que o Comment do OnTrade mostrava?
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import wrx_paths

EA = (wrx_paths.data_dir() / "MQL5" / "Experts"
      / "White Rabbit X (Global Multi-Indicator).mq5")

# Altura aproximada de uma linha por tamanho de fonte, em pixels. Serve para
# decidir se duas linhas consecutivas se tocam.
def line_height(pt: int) -> int:
    return int(pt * 1.6) + 2


def body_of(src: str, name: str) -> str:
    match = re.search(rf"void\s+{name}\s*\([^)]*\)\s*\{{", src)
    assert match, f"{name} nao encontrada"
    start = src.index("{", match.start())
    depth = 0
    for pos in range(start, len(src)):
        if src[pos] == "{":
            depth += 1
        elif src[pos] == "}":
            depth -= 1
            if depth == 0:
                return src[start:pos + 1]
    raise AssertionError(f"{name}: chave nao fecha")


def main() -> int:
    src = EA.read_text(encoding="utf-8")
    body = body_of(src, "UpdateChartDashboard")
    problems: list[str] = []

    defines = dict(re.findall(r"#define\s+(DASH_PT_\w+)\s+(\d+)", src))
    # As cores migraram de #define para "color DASH_C_X = ...;" (input-like,
    # editavel sem recompilar layout) -- casar so a forma antiga fazia a
    # paleta "declarada" sempre dar 0, por mais cores que existissem.
    palette = set(re.findall(r"#define\s+(DASH_C_\w+)\s+", src))
    palette |= set(re.findall(r"\bcolor\s+(DASH_C_\w+)\s*=", src))

    # --- 1. linhas do painel --------------------------------------------
    # Desde 2026-08-01 o painel e UM OBJ_BITMAP so (CCanvas) -- nao ha mais
    # "nome de objeto duplicado" pra checar (so existe um nome: "...Canvas").
    # O que sobra e contar quantas chamadas DashPush/DashRow/DashCycleLine
    # existem, so como sinal de tamanho do painel.
    rows = len(re.findall(r'\bDash(?:Push|Row|CycleLine)\(', body))
    print(f"Linhas do painel (DashPush/DashRow/DashCycleLine): {rows} chamadas")

    # --- 2. textos repetidos -------------------------------------------
    literals = re.findall(r'"((?:[^"\\]|\\.){4,})"', body)
    counted: dict[str, int] = {}
    for lit in literals:
        # So interessa texto que o usuario le no grafico. Fragmentos de
        # concatenacao de codigo (" + InterfaceLabel(") nao sao conteudo.
        if re.search(r"[+(),;]|InterfaceLabel|IntegerToString|DoubleToString",
                     lit):
            continue
        if not re.search(r"[A-Za-z]{3}", lit):
            continue
        counted[lit] = counted.get(lit, 0) + 1
    for lit, count in counted.items():
        if count > 1 and len(lit) > 8:
            problems.append(f'texto "{lit[:40]}" aparece {count}x')

    # O titulo nao pode repetir o nome padrao da estrategia.
    default_name = re.search(r'input string NomedaEstrategia = "([^"]+)"', src)
    if default_name and 'DashPush("WHITE RABBIT X"' in body:
        guard = f'StringCompare(named, "{default_name.group(1)}", false) != 0'
        if guard not in body:
            problems.append(
                f'titulo pode duplicar NomedaEstrategia (padrao '
                f'"{default_name.group(1)}") -- falta o guard de comparacao')
        else:
            print(f'Guard contra duplicar "{default_name.group(1)}": presente')

    # --- 3. sobreposicao vertical --------------------------------------
    # Reconstroi a sequencia de y += N e o tamanho de fonte de cada linha.
    # As tres funcoes tem "y" em posicoes diferentes na assinatura:
    #   DashPush(texto, cor, fontSize, y)   -- y por ultimo, fontSize antes dele
    #   DashRow(rotulo, valor, y, cor)      -- y no meio, fonte sempre BODY
    #   DashCycleLine(y, valor, cor)        -- y primeiro (por referencia),
    #                                          avanca DASH_CYCLE_LINE por conta
    #                                          propria (nao aparece um "y +="
    #                                          separado no texto pra essas).
    steps = re.findall(
        r'(DashCycleLine\(\s*y\s*,[^;]*?\)\s*;|'
        r'DashPush\([^;]*?,\s*(DASH_PT_\w+)\s*,\s*y\s*\)\s*;|'
        r'DashRow\([^;]*?,\s*y\s*,[^;]*?\)\s*;|'
        r'y \+= ([A-Z_0-9]+(?:\s*\+\s*\d+)?|\d+);)',
        body, re.DOTALL)
    consts = {"DASH_LINE": None, "DASH_GAP": None, "DASH_CYCLE_LINE": None}
    for key in consts:
        m = re.search(rf"#define\s+{key}\s+(\d+)", src)
        consts[key] = int(m.group(1)) if m else 0

    pending_pt = None
    min_gap = None
    for whole, pt_token, step_token in steps:
        if whole.startswith("DashCycleLine"):
            # Cada chamada carrega seu proprio avanco implicito (DASH_CYCLE_LINE):
            # valida contra a linha PENDENTE (se houver) e ja deixa a proxima
            # pendente, sem esperar um "y +=" que nunca vai aparecer no texto.
            body_pt = int(defines.get("DASH_PT_BODY", 9))
            if pending_pt:
                gap = consts["DASH_CYCLE_LINE"]
                need = line_height(pending_pt)
                if gap < need:
                    problems.append(
                        f"linha de ciclo ({pending_pt}pt) seguida de avanco de "
                        f"{gap}px (precisa de {need}px) -- textos se tocam")
                min_gap = gap if min_gap is None else min(min_gap, gap)
            pending_pt = body_pt
        elif whole.startswith("DashRow"):
            pending_pt = int(defines.get("DASH_PT_BODY", 9))
        elif whole.startswith("DashPush"):
            pt = defines.get(pt_token)
            pending_pt = int(pt) if pt else int(defines.get("DASH_PT_BODY", 9))
        elif step_token:
            expr = step_token
            for key, val in consts.items():
                expr = expr.replace(key, str(val))
            # As expressoes sao sempre inteiros somados ("20", "26 + 2"), entao
            # somar os numeros basta -- e evita avaliar texto do arquivo.
            numbers = re.findall(r"\d+", expr)
            if not numbers:
                continue
            gap = sum(int(n) for n in numbers)
            if pending_pt:
                need = line_height(pending_pt)
                if gap < need:
                    problems.append(
                        f"linha de {pending_pt}pt seguida de avanco de {gap}px "
                        f"(precisa de {need}px) -- textos se tocam")
                min_gap = gap if min_gap is None else min(min_gap, gap)
            pending_pt = None
    print(f"Menor avanco vertical entre linhas: {min_gap}px")

    # --- 4. tipografia --------------------------------------------------
    sizes = {int(v) for _, v in defines.items()}
    # DashPush termina em "..., fontSize, y)" -- numero cru apareceria logo
    # antes do "y" de fechamento, ao contrario do formato antigo (que vinha
    # logo DEPOIS do "y").
    raw_sizes = set(re.findall(r",\s*(\d+)\s*,\s*y\s*\)", body))
    if raw_sizes:
        problems.append(
            f"tamanho de fonte fora da escala (numero cru): {sorted(raw_sizes)}")
    # Familia de fonte: etiquetas de deal/linhas de nivel ainda usam
    # ObjectSetString(OBJPROP_FONT,...); o painel (canvas) usa FontSet(nome,...).
    families = set(re.findall(r'OBJPROP_FONT,\s*([^)]+)\)', src))
    families |= set(re.findall(r'\.FontSet\(\s*([^,]+),', src))
    print(f"Tamanhos de fonte na escala: {sorted(sizes)}")
    print(f"Familias de fonte: {', '.join(sorted(families))}")
    if len(sizes) > 4:
        problems.append(f"{len(sizes)} tamanhos de fonte -- a escala deveria "
                        "ter no maximo 4")
    if len(families) > 1:
        problems.append(f"{len(families)} familias de fonte no painel")

    # --- 5. paleta ------------------------------------------------------
    stray = sorted(set(re.findall(r"\bclr[A-Z][A-Za-z]+", body)))
    print(f"Cores da paleta declaradas: {len(palette)}")
    if stray:
        problems.append(f"cores fora da paleta no painel: {', '.join(stray)}")

    # --- 6. cobertura dos ciclos ---------------------------------------
    ontrade = body_of(src, "OnTrade")
    ontrade_topics = {
        "Consecutive losses": "Consecutive losses",
        "Debt": "Debt",
        "Cycle P&L": "Cycle",
        "Target": "Target",
    }
    print("\nCobertura dos ciclos (o que o Comment do OnTrade mostrava):")
    for label, needle in ontrade_topics.items():
        in_ontrade = needle.lower() in ontrade.lower()
        in_panel = label.lower() in body.lower()
        mark = "ok" if in_panel else "FALTA"
        origem = "estava no OnTrade" if in_ontrade else "nao estava no OnTrade"
        print(f"  {label:<22} painel={mark:<6} ({origem})")
        if in_ontrade and not in_panel:
            problems.append(f"'{label}' saiu do Comment e nao entrou no painel")

    extras = [x for x in ("Recovered", "Legs", "Realized", "Anchor",
                          "ATR spacing", "Next lot", "Steps")
              if x.lower() in body.lower()]
    print(f"  Alem do OnTrade: {', '.join(extras)}")

    print()
    if problems:
        print(f"ACHADOS ({len(problems)}):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("Painel sem duplicacao, sem sobreposicao, tipografia e paleta "
          "consistentes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
