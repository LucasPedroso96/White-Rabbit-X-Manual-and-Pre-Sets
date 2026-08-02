# -*- coding: utf-8 -*-
"""Audita o pacote de manuais multi-idioma do White Rabbit X.

Confere, para os 11 idiomas:

1. COBERTURA   - todo idioma tem os mesmos 8 documentos?
2. ESTRUTURA   - mesma quantidade e hierarquia de secoes que o ingles?
3. TRADUCAO    - algum trecho ficou identico ao ingles (nao traduzido)?
4. VOLUME      - contagem de palavras fora da faixa esperada indica conteudo
                 truncado ou perdido na traducao.
5. CONTATO     - o documento aponta o grupo do Telegram?
6. SINCRONIA   - o manual descreve a versao atual da EA (127 inputs)?

Idiomas com escrita logografica (chines, japones, coreano) contam poucas
"palavras" separadas por espaco; para eles a comparacao usa caracteres.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lucas Pedroso\OneDrive\SantoGral\Santo Gral"
            r"\venda mql5\Pacote_Completo_White_Rabbit_X\Languages")

# Cada idioma nomeia os arquivos a sua maneira; o vinculo e o prefixo numerico.
DOC_SLOTS = ["01", "02", "03", "04", "05", "06", "07", "08"]
DOC_NAMES = {
    "01": "Manual do usuario",
    "02": "Descricao de venda MQL5",
    "03": "Guia de otimizacao / WFO",
    "04": "FAQ e suporte",
    "05": "Texto puro da descricao",
    "06": "Referencia de inputs (CSV)",
    "07": "Tutorial do ecossistema de sets",
    "08": "Compatibilidade tecnica",
}
CJK_LANGS = {"03_Chinese", "05_Japanese", "07_Korean"}
REFERENCE = "01_English"


def read(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return path.read_bytes().decode("utf-8", errors="replace")


def units(textual: str, lang: str) -> int:
    """Palavras, ou caracteres nas linguas sem separador de palavra."""
    if lang in CJK_LANGS:
        return len(re.sub(r"\s+", "", textual))
    return len(textual.split())


def headings(markdown: str) -> list[int]:
    return [len(m.group(1))
            for m in re.finditer(r"^(#{1,6})\s+\S", markdown, re.MULTILINE)]


def main() -> int:
    langs = sorted(d.name for d in ROOT.iterdir()
                   if d.is_dir() and re.match(r"^\d\d_", d.name))
    if REFERENCE not in langs:
        print(f"Idioma de referencia ausente: {REFERENCE}")
        return 1

    docs: dict[str, dict[str, Path]] = {}
    for lang in langs:
        found: dict[str, Path] = {}
        for path in sorted((ROOT / lang).glob("*")):
            if path.is_dir():
                continue
            m = re.match(r"^(\d\d)_", path.name)
            if m and path.suffix.lower() in (".md", ".txt", ".csv"):
                found.setdefault(m.group(1), path)
        docs[lang] = found

    problems: list[str] = []
    report: dict[str, dict] = {}

    ref_docs = docs[REFERENCE]
    ref_text = {slot: read(p) for slot, p in ref_docs.items()}
    ref_units = {slot: units(ref_text[slot], REFERENCE) for slot in ref_text}

    print(f"{'Idioma':<22} {'Docs':>5} {'Secoes':>7} {'Volume vs EN':>14} "
          f"{'Telegram':>9}")
    print("-" * 62)

    for lang in langs:
        found = docs[lang]
        missing = [s for s in DOC_SLOTS if s not in found]
        if missing:
            problems.append(
                f"{lang}: faltam documentos "
                + ", ".join(f"{s} ({DOC_NAMES[s]})" for s in missing))

        telegram = any("t.me" in read(p).lower() or "telegram" in read(p).lower()
                       for p in found.values())

        section_issues = 0
        untranslated: list[str] = []
        ratios: list[float] = []

        for slot, path in sorted(found.items()):
            body = read(path)
            if path.suffix.lower() == ".md" and slot in ref_text:
                mine, theirs = headings(body), headings(ref_text[slot])
                if len(mine) != len(theirs):
                    section_issues += 1
                    problems.append(
                        f"{lang}/{path.name}: {len(mine)} secoes contra "
                        f"{len(theirs)} no ingles")
            if lang != REFERENCE and slot in ref_text:
                if body.strip() == ref_text[slot].strip():
                    untranslated.append(path.name)
                n = units(body, lang)
                base = ref_units.get(slot, 0)
                if base:
                    ratios.append(n / base)

        avg = sum(ratios) / len(ratios) if ratios else 1.0
        flag = ""
        if lang != REFERENCE and lang not in CJK_LANGS:
            if avg < 0.75:
                flag = "  <-- CURTO"
                problems.append(
                    f"{lang}: volume medio {avg:.0%} do ingles -- "
                    "conteudo possivelmente truncado")
            elif avg > 1.6:
                flag = "  <-- LONGO"
        if untranslated:
            problems.append(
                f"{lang}: identico ao ingles (nao traduzido): "
                + ", ".join(untranslated))

        print(f"{lang:<22} {len(found):>5} {len(found) - section_issues:>7} "
              f"{avg:>13.0%} {'sim' if telegram else 'NAO':>9}{flag}")
        report[lang] = {
            "documentos": len(found),
            "faltando": missing,
            "secoes_divergentes": section_issues,
            "volume_vs_ingles": round(avg, 3),
            "nao_traduzidos": untranslated,
            "telegram": telegram,
        }

    # Sincronia com a EA: o manual precisa refletir os 127 inputs atuais.
    ea = Path(r"C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal"
              r"\59EECBFD4A9CCD98CCBC61E96D5DED8E\MQL5\Experts"
              r"\White Rabbit X (Global Multi-Indicator).mq5")
    if ea.exists():
        ea_inputs = re.findall(
            r"^\s*input\s+(?!group\b)[A-Za-z_][A-Za-z0-9_]*\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*=",
            read(ea), re.MULTILINE)
        csv_ref = docs[REFERENCE].get("06")
        if csv_ref:
            # O nome do parametro e a 4a coluna do CSV, nao a 1a.
            listed = set()
            for row in read(csv_ref).splitlines()[1:]:
                cols = row.split(";")
                if len(cols) > 3:
                    listed.add(cols[3].strip())
            faltam = [i for i in ea_inputs if i not in listed]
            print(f"\nInputs na EA: {len(ea_inputs)} | "
                  f"na referencia CSV: {len(listed)}")
            if faltam:
                problems.append(
                    f"Referencia de inputs desatualizada, ausentes: "
                    + ", ".join(faltam[:8])
                    + (f" (+{len(faltam) - 8})" if len(faltam) > 8 else ""))

    print()
    if problems:
        print(f"ACHADOS ({len(problems)}):")
        for p in problems:
            print(f"  - {p}")
    else:
        print("Nenhum problema estrutural encontrado.")

    out = ROOT / "AUDITORIA_MANUAIS.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    print(f"\nRelatorio: {out}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
