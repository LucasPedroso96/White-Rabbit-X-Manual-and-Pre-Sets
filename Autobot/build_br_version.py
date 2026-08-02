# -*- coding: utf-8 -*-
"""Gera a versao brasileira a partir da global, traduzindo so os inputs.

Portar feature a feature deixou a brasileira 1.831 linhas atras da global e com
os mesmos bugs que ja tinham sido corrigidos la. Reconstruir do zero a cada
mudanca e mais barato e nao acumula divida: as duas versoes diferem APENAS nos
comentarios de exibicao dos inputs (o texto depois de //, que e o que o MT5
mostra na aba Inputs) e nos rotulos de input group. Os identificadores sao os
mesmos, e o painel do grafico ja e bilingue na global via InterfaceText.

As traducoes existentes sao reaproveitadas casando por IDENTIFICADOR, nao por
posicao: input que mudou de lugar continua achando sua traducao, e input novo
aparece na lista de pendentes em vez de sair em ingles sem aviso.

Uso:
    python build_br_version.py            # relatorio, nao grava
    python build_br_version.py --gravar
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXPERTS = Path(r"C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal"
               r"\59EECBFD4A9CCD98CCBC61E96D5DED8E\MQL5\Experts")
GLOBAL = EXPERTS / "White Rabbit X (Global Multi-Indicator).mq5"
BRASIL = EXPERTS / "White Rabbit X (Versão Brasileira PT).mq5"
GLOSSARIO = Path(__file__).parent / "glossario_br.json"

# Linha de input com comentario:  input <tipo> <nome> = <valor>; // <texto>
RE_INPUT = re.compile(r"^(input\s+[\w\s]+?\s+(\w+)\s*=[^;]*;\s*)//\s*(.*)$")
# Rotulo de grupo:  input group "<texto>"
RE_GRUPO = re.compile(r'^(input\s+group\s+)"(.*)"\s*$')


def extrair(caminho: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Devolve (comentarios por identificador, rotulos de grupo por texto)."""
    comentarios, grupos = {}, {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        m = RE_INPUT.match(linha)
        if m:
            comentarios[m.group(2)] = m.group(3).strip()
            continue
        g = RE_GRUPO.match(linha)
        if g:
            grupos[g.group(2)] = g.group(2)
    return comentarios, grupos


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gravar", action="store_true",
                    help="escreve a versao brasileira (sem isto, so relata)")
    args = ap.parse_args()

    if not GLOBAL.is_file():
        print(f"Global nao encontrada: {GLOBAL}")
        return 1

    # Traducoes ja existentes: da versao brasileira atual e do glossario
    # acumulado. O glossario sobrevive a reconstrucoes; a versao antiga, nao.
    conhecidas: dict[str, str] = {}
    grupos_conhecidos: dict[str, str] = {}
    if GLOSSARIO.is_file():
        salvo = json.loads(GLOSSARIO.read_text(encoding="utf-8"))
        conhecidas.update(salvo.get("inputs", {}))
        grupos_conhecidos.update(salvo.get("grupos", {}))
    if BRASIL.is_file():
        com_br, _ = extrair(BRASIL)
        com_en, _ = extrair(GLOBAL)
        for ident, texto in com_br.items():
            # So aproveita se o texto realmente difere do ingles: input que
            # nunca foi traduzido carrega o texto original e nao serve de fonte.
            if texto and texto != com_en.get(ident):
                conhecidas.setdefault(ident, texto)
        for linha in BRASIL.read_text(encoding="utf-8").splitlines():
            g = RE_GRUPO.match(linha)
            if g:
                grupos_conhecidos.setdefault(g.group(2), g.group(2))

    com_en, grupos_en = extrair(GLOBAL)
    pendentes = [i for i in com_en if i not in conhecidas]

    print(f"inputs na global:        {len(com_en)}")
    print(f"com traducao conhecida:  {len(com_en) - len(pendentes)}")
    print(f"PENDENTES de traducao:   {len(pendentes)}")
    if pendentes:
        print("\nSem traducao (sairiam em ingles):")
        for ident in pendentes:
            print(f"  {ident:<28} {com_en[ident][:70]}")

    if not args.gravar:
        print("\n(relatorio apenas; use --gravar para escrever)")
        return 0

    saida = []
    for linha in GLOBAL.read_text(encoding="utf-8").splitlines():
        m = RE_INPUT.match(linha)
        if m and m.group(2) in conhecidas:
            saida.append(f"{m.group(1)}// {conhecidas[m.group(2)]}")
            continue
        g = RE_GRUPO.match(linha)
        if g and g.group(2) in grupos_conhecidos:
            saida.append(f'{g.group(1)}"{grupos_conhecidos[g.group(2)]}"')
            continue
        saida.append(linha)

    BRASIL.write_text("\n".join(saida) + "\n", encoding="utf-8")
    print(f"\ngravada: {BRASIL.name}")

    # O glossario acumula o que foi traduzido, para a proxima reconstrucao nao
    # depender do arquivo que acabou de ser sobrescrito.
    GLOSSARIO.write_text(
        json.dumps({"inputs": conhecidas, "grupos": grupos_conhecidos},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"glossario: {len(conhecidas)} inputs, {len(grupos_conhecidos)} grupos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
