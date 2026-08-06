# -*- coding: utf-8 -*-
"""Propaga a contagem real de sets para manuais, docs e descricoes de venda.

O numero de sets aparece em mais de 100 arquivos, em 11 idiomas. Toda vez que a
biblioteca muda -- e ela muda quando um sistema ganha ou perde eixos -- esses
arquivos passam a mentir, e o comprador conta os arquivos que baixou e ve outro
numero.

O `align_manuals.py` fez UMA migracao especifica; e um migrador, nao serve para
manutencao. Este script existe para a manutencao: le a contagem verdadeira do
disco e escreve nos arquivos.

DETALHE QUE IMPORTA: o separador de milhar muda por idioma -- ponto em portugues
e aleman, virgula em ingles e chines, espaco em frances e russo. Substituir sem
olhar o separador deixaria o estilo errado no meio de uma frase. Aqui cada
ocorrencia e reescrita no MESMO estilo em que estava.

Nao mexe em .pdf/.docx: aquilo e gerado a partir do .md por render_manuals.py.
Rode este script primeiro, o render depois.

CUIDADO: este arquivo mora num dos DESTINOS, entao ele se reescreve tambem. Por
isso a documentacao aqui NAO cita numero de contagem literal -- se citasse, cada
execucao a substituiria e o exemplo viraria absurdo (ja aconteceu: o texto
passou a dizer que trocava um numero por ele mesmo).

Uso:
    python sync_set_count.py --de <contagem_antiga>
    python sync_set_count.py --de <contagem_antiga> --so-listar
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BIBLIOTECA = Path(r"C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal"
                  r"\D2A36B4A61A508797F5C460B1F34DC5D\MQL5\Profiles\Tester"
                  r"\White_Rabbit_X_Sets_templates")

DESTINOS = [
    Path(r"C:\Users\Lucas Pedroso\OneDrive\SantoGral\Santo Gral\venda mql5"
         r"\Pacote_Completo_White_Rabbit_X\Languages"),
    Path(r"C:\Users\Lucas Pedroso\Desktop\Metatrader5EAS\White Rabbit"),
    Path(r"C:\Users\Lucas Pedroso\Desktop\Levain 2.0 (Em Andamento)"
         r"\Levain-2.0\white_rabbit_x_optimization_tools"),
    Path(r"C:\Users\Lucas Pedroso\Desktop\Levain 2.0 (Em Andamento)"
         r"\Levain-2.0\AutoBotSetup"),
]

TEXTO = {".md", ".txt", ".py", ".csv", ".json", ".html"}
# Versao arquivada guarda o numero que valia na epoca. Reescrever ali nao
# corrige nada -- falsifica o historico.
NAO_TOCAR = ("archive", "arquivo_morto", "_old", ".bak", ".backup")
# Separadores que os 11 idiomas usam, incluindo o espaco estreito do frances.
SEPARADORES = ["", ".", ",", " ", "\u00a0", "\u202f"]


def contar_sets() -> int:
    if not BIBLIOTECA.is_dir():
        raise SystemExit(f"Biblioteca nao encontrada: {BIBLIOTECA}")
    return sum(1 for _ in BIBLIOTECA.rglob("*.set"))


def variantes(n: int) -> list[tuple[str, str]]:
    """(padrao, rotulo) para cada estilo de separador de um numero de 4 digitos."""
    txt = str(n)
    if len(txt) != 4:
        return [(re.escape(txt), "puro")]
    saida = []
    for sep in SEPARADORES:
        saida.append((re.escape(f"{txt[0]}{sep}{txt[1:]}"), sep or "puro"))
    return saida


def reescrever(velho: int, novo: int, arquivo: Path) -> int:
    try:
        original = arquivo.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return 0
    texto = original
    for sep in SEPARADORES:
        de = f"{str(velho)[0]}{sep}{str(velho)[1:]}"
        para = f"{str(novo)[0]}{sep}{str(novo)[1:]}"
        texto = texto.replace(de, para)
    if texto == original:
        return 0
    trocas = sum(1 for a, b in zip(original.split(), texto.split()) if a != b) or 1
    arquivo.write_text(texto, encoding="utf-8")
    return trocas


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--de", type=int, required=True,
                    help="contagem antiga, a que esta escrita nos arquivos")
    ap.add_argument("--para", type=int,
                    help="contagem nova (padrao: conta os .set do disco)")
    ap.add_argument("--so-listar", action="store_true",
                    help="mostra o que mudaria, sem gravar")
    args = ap.parse_args()

    novo = args.para if args.para else contar_sets()
    if novo == args.de:
        print(f"A contagem nos arquivos ({args.de}) ja e a do disco. Nada a fazer.")
        return 0

    print(f"biblioteca no disco: {novo} sets")
    print(f"trocando {args.de} -> {novo}"
          f"{'  (simulacao)' if args.so_listar else ''}\n")

    padroes = [p for p, _ in variantes(args.de)]
    regex = re.compile("|".join(padroes))

    total_arquivos = 0
    nao_texto: list[Path] = []
    naming: list[Path] = []
    for raiz in DESTINOS:
        if not raiz.is_dir():
            print(f"  (ausente, ignorado) {raiz}")
            continue
        atingidos = 0
        for arquivo in sorted(raiz.rglob("*")):
            if not arquivo.is_file():
                continue
            baixo = arquivo.as_posix().lower()
            if any(marca in baixo for marca in NAO_TOCAR):
                continue
            if arquivo.suffix.lower() not in TEXTO:
                try:
                    if regex.search(arquivo.read_bytes().decode("latin-1")):
                        nao_texto.append(arquivo)
                except OSError:
                    pass
                continue
            try:
                conteudo = arquivo.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if not regex.search(conteudo):
                continue
            atingidos += 1
            # Sinaliza quem descreve o padrao de nome dos arquivos: com o
            # 08_GRID_UNIFIED bilateral, "BUY/SELL" deixou de cobrir todos.
            if re.search(r"BUY_|SELL_|<LADO>|_MULTI\.set", conteudo):
                naming.append(arquivo)
            if not args.so_listar:
                reescrever(args.de, novo, arquivo)
        if atingidos:
            print(f"  {atingidos:>4} arquivos em {raiz.name}")
        total_arquivos += atingidos

    print(f"\n{total_arquivos} arquivos de texto "
          f"{'seriam alterados' if args.so_listar else 'alterados'}.")

    if nao_texto:
        print(f"\n{len(nao_texto)} arquivos NAO-texto ainda citam {args.de} "
              "(pdf/docx sao gerados, nao editados):")
        for p in nao_texto[:8]:
            print(f"   {p.name}")
        print("   Regenere com render_manuals.py depois deste script.")

    if naming:
        print(f"\n{len(naming)} arquivos descrevem o padrao de nome dos sets.")
        print("   Reveja a mao: o 08_GRID_UNIFIED agora e BOTH_*.set, porque")
        print("   abre compra e venda juntas. 'BUY ou SELL' deixou de cobrir")
        print("   todos os sistemas, e isso e prosa, nao um numero -- trocar")
        print("   automaticamente em 11 idiomas daria frase errada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
