# -*- coding: utf-8 -*-
"""Mantem o espelho de sets PRONTOS ao lado da biblioteca de templates.

Os sets validados pelo circuito nascem soltos na raiz de Profiles/Tester
(`VALIDADO_*.set`), e a raiz nao responde a pergunta que importa na hora de
subir um set: "para ESTE ativo e ESTE sistema, existe algo pronto?". A
resposta certa mora na mesma geografia da biblioteca -- por isso o espelho:

    White_Rabbit_X_Sets_PRONTOS/<classe>/<ativo>/<sistema>/＊BUY_MULTI.set

A arvore e um clone 1:1 das pastas da biblioteca, entao o dialogo "Load" do
Strategy Tester navega nela do jeito que ja se navega nos templates. Pasta
vazia = nada pronto ali; arquivo com ＊ = set validado, ja com WFO desligado,
pronto para subir.

Sobre o marcador: o Windows proibe `*` literal em nome de arquivo, entao o
espelho usa o asterisco de largura total ＊ (U+FF0A) -- visualmente identico,
valido no NTFS, e ordena o arquivo no topo da pasta. No MAPA.md, que e texto,
o `*` e o verdadeiro.

Na raiz do espelho ficam ainda:

  MAPA.md                arvore compacta com * onde ha set pronto
  _PORTFOLIOS/<sistema>.md   o portfolio daquele algoritmo: membros validados
                         com retencao OOS, expectancy, trades e CapitalBaseR
                         somado -- o capital que o conjunto exige

A fonte da verdade e o NOME do arquivo de entrega (o prefixo carrega o
veredito -- decisao antiga do circuito) mais o ledger da campanha, quando
existe, para as metricas. O sync e idempotente: sumiu o VALIDADO_ de origem
(recorrida, rebaixamento), o marcador sai do espelho na proxima passada.

Uso:
    python ready_library.py            # sincroniza e imprime o resumo
    python ready_library.py --listar   # so mostra o que esta pronto
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import wrx_paths

AQUI = Path(__file__).resolve().parent
DADOS = wrx_paths.TERMINAL
TESTER = DADOS / "MQL5" / "Profiles" / "Tester"
BIBLIOTECA = TESTER / "White_Rabbit_X_Sets_templates"
PRONTOS = TESTER / "White_Rabbit_X_Sets_Autobot"
LEDGER = AQUI / "campanha_resultados.jsonl"

MARCA = "\uff0a"          # ＊ -- ver docstring
PASTA_PORTFOLIOS = "_PORTFOLIOS"

# O sistema comeca com dois digitos e a variante e um conjunto fechado; e isso
# que torna o parse do nome nao-ambiguo mesmo com underscores no simbolo
# (EURUSD.HT vira EURUSD_HT na gravacao).
NOME_ENTREGA = re.compile(
    r"^VALIDADO_(?P<simbolo>.+?)_(?P<sistema>\d{2}_[A-Z_]+?)_"
    r"(?P<variante>(?:BUY|SELL|BOTH)_(?:MULTI|ICHIMOKU))\.set$")


def analisar_nome(nome: str) -> dict[str, str] | None:
    """Extrai (simbolo, sistema, variante) do nome do set de entrega."""
    m = NOME_ENTREGA.match(nome)
    if not m:
        return None
    d = m.groupdict()
    # A gravacao trocou '.' por '_' (EURUSD.HT -> EURUSD_HT); para exibir e
    # casar com o ledger, desfaz-se a troca. Um simbolo com underscore proprio
    # sairia com ponto no lugar -- tolerado: o casamento com o ledger e a busca
    # na biblioteca normalizam de volta.
    d["simbolo_exibicao"] = d["simbolo"].replace("_", ".")
    return d


def metricas_do_ledger(ledger: Path) -> dict[tuple[str, str, str], dict]:
    """Ultimo registro de cada combo. Linha truncada nao derruba as demais."""
    saida: dict[tuple[str, str, str], dict] = {}
    if not ledger.exists():
        return saida
    for linha in ledger.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        try:
            r = json.loads(linha)
        except json.JSONDecodeError:
            continue
        chave = (str(r.get("simbolo", "")).replace(".", "_"),
                 r.get("sistema", ""), r.get("variante", ""))
        saida[chave] = r
    return saida


def achar_ativo(biblioteca: Path, simbolo: str) -> Path | None:
    """Pasta do ativo na biblioteca, aceitando sufixo (EURUSD_HT -> EURUSD)."""
    candidatos = [simbolo, simbolo.replace("_", ".")]
    radical = re.split(r"[.\-_]", simbolo)[0]
    if radical not in candidatos:
        candidatos.append(radical)
    for classe in sorted(p for p in biblioteca.iterdir() if p.is_dir()):
        for nome in candidatos:
            alvo = classe / nome
            if alvo.is_dir():
                return alvo
    return None


def ler_param(caminho: Path, nome: str) -> str | None:
    """Primeiro campo de um parametro do .set (UTF-16, formato do MT5)."""
    try:
        texto = caminho.read_text(encoding="utf-16", errors="replace")
    except OSError:
        return None
    m = re.search(rf"^{re.escape(nome)}=([^|\r\n]*)", texto, re.M)
    return m.group(1).strip() if m else None


def _fmt(valor, sufixo: str = "", casas: int = 1) -> str:
    if valor is None:
        return "n/d"
    return f"{valor:.{casas}f}{sufixo}"


def sincronizar(biblioteca: Path = BIBLIOTECA, tester: Path = TESTER,
                destino: Path = PRONTOS, ledger: Path = LEDGER) -> dict:
    """Espelha pastas, posiciona os prontos com ＊ e regenera MAPA/portfolios.

    Devolve um resumo dict (usado pela campanha para logar sem re-varrer).
    """
    if not biblioteca.is_dir():
        raise FileNotFoundError(f"biblioteca nao encontrada: {biblioteca}")

    # 1. Clone das pastas. So pastas: arquivo no espelho significa "pronto",
    #    entao copiar templates para ca destruiria justamente essa semantica.
    relativos = [p.relative_to(biblioteca) for p in biblioteca.rglob("*")
                 if p.is_dir()]
    destino.mkdir(parents=True, exist_ok=True)
    for rel in relativos:
        (destino / rel).mkdir(parents=True, exist_ok=True)

    # 2. O que DEVERIA estar no espelho, a partir dos VALIDADO_ da raiz.
    metricas = metricas_do_ledger(ledger)
    esperados: dict[Path, Path] = {}
    prontos: list[dict] = []
    avisos: list[str] = []
    for origem in sorted(tester.glob("VALIDADO_*.set")):
        info = analisar_nome(origem.name)
        if info is None:
            avisos.append(f"nome fora do padrao, ignorado: {origem.name}")
            continue
        ativo = achar_ativo(biblioteca, info["simbolo"])
        if ativo is None:
            avisos.append(f"ativo sem pasta na biblioteca: {origem.name}")
            continue
        no = destino / ativo.parent.name / ativo.name / info["sistema"]
        no.mkdir(parents=True, exist_ok=True)
        alvo = no / f"{MARCA}{info['variante']}.set"
        esperados[alvo] = origem
        reg = metricas.get((info["simbolo"], info["sistema"],
                            info["variante"]), {})
        prontos.append({
            "classe": ativo.parent.name, "ativo": ativo.name,
            "sistema": info["sistema"], "variante": info["variante"],
            "simbolo": info["simbolo_exibicao"], "alvo": alvo,
            "retencao": reg.get("retencao_oos"),
            "expectancy": reg.get("expectancy_r"),
            "trades": reg.get("trades_oos"),
            "mc_prob_ruina": reg.get("mc_prob_ruina"),
            "capital": ler_param(origem, "CapitalBaseR"),
        })

    # 3. Marcador orfao sai: um VALIDADO_ removido da raiz (recorrida que
    #    rebaixou, limpeza manual) nao pode continuar afirmando "pronto" aqui.
    removidos = 0
    for marcado in destino.rglob(f"{MARCA}*.set"):
        if marcado not in esperados:
            marcado.unlink()
            removidos += 1

    # 4. Copia o que falta ou mudou. copy2 preserva o mtime, entao a comparacao
    #    de mtime+tamanho detecta re-entregas do mesmo combo.
    copiados = 0
    for alvo, origem in esperados.items():
        st_o = origem.stat()
        if alvo.exists():
            st_a = alvo.stat()
            if (st_a.st_size == st_o.st_size
                    and abs(st_a.st_mtime - st_o.st_mtime) < 2):
                continue
        shutil.copy2(origem, alvo)
        copiados += 1

    total_templates = sum(1 for _ in biblioteca.rglob("*.set"))
    _gerar_mapa(destino, biblioteca, prontos, total_templates)
    _gerar_portfolios(destino, prontos)

    return {"prontos": len(prontos), "copiados": copiados,
            "removidos": removidos, "avisos": avisos,
            "templates": total_templates, "itens": prontos}


def _gerar_mapa(destino: Path, biblioteca: Path, prontos: list[dict],
                total_templates: int) -> None:
    """MAPA.md: a visao de cima. So os ativos COM algo pronto ganham linha --
    um mapa com 89 linhas vazias esconderia as poucas que interessam."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    linhas = [
        "# Mapa de sets prontos",
        "",
        f"Atualizado: {agora} | prontos: **{len(prontos)}** de "
        f"{total_templates} templates.",
        "",
        "`*` = set validado pelo circuito (WFO desligado, pronto para subir).",
        "No disco o marcador e `＊` (U+FF0A): o Windows proibe `*` em nomes.",
        "",
    ]
    por_classe: dict[str, dict[str, list[dict]]] = {}
    for p in prontos:
        por_classe.setdefault(p["classe"], {}).setdefault(p["ativo"], []).append(p)

    for classe in sorted(c.name for c in biblioteca.iterdir() if c.is_dir()):
        ativos = por_classe.get(classe, {})
        total_ativos = sum(1 for p in (biblioteca / classe).iterdir()
                           if p.is_dir())
        linhas.append(f"## {classe}")
        for ativo in sorted(ativos):
            marcas = "  ".join(
                f"*{p['sistema']}/{p['variante']}"
                for p in sorted(ativos[ativo],
                                key=lambda x: (x["sistema"], x["variante"])))
            linhas.append(f"- **{ativo}**: {marcas}")
        sem_nada = total_ativos - len(ativos)
        if sem_nada > 0:
            linhas.append(f"- ({sem_nada} ativos sem set pronto)")
        linhas.append("")
    (destino / "MAPA.md").write_text("\n".join(linhas), encoding="utf-8")


def _gerar_portfolios(destino: Path, prontos: list[dict]) -> None:
    """Um arquivo por ALGORITMO (sistema): e assim que o dono monta e sobe.

    O portfolio de um algoritmo atravessa os ativos, entao ele nao cabe dentro
    de <ativo>/<sistema>/ -- mora em _PORTFOLIOS/, na raiz do espelho. Arquivo
    de sistema sem nenhum validado e apagado, nao mantido vazio: portfolio
    vazio parece configuracao, e ausencia e a informacao certa.
    """
    pasta = destino / PASTA_PORTFOLIOS
    pasta.mkdir(exist_ok=True)
    por_sistema: dict[str, list[dict]] = {}
    for p in prontos:
        por_sistema.setdefault(p["sistema"], []).append(p)

    for velho in pasta.glob("*.md"):
        if velho.stem not in por_sistema:
            velho.unlink()

    for sistema, membros in por_sistema.items():
        # Retencao decrescente, sem-medida por ultimo. Nao usar `or`: ele
        # jogaria retencao 0.0 (medida, e ruim) no mesmo balde de None.
        membros.sort(key=lambda m: -(m["retencao"]
                                     if m["retencao"] is not None else -9e9))
        capitais = [float(m["capital"]) for m in membros
                    if m["capital"] not in (None, "")]
        linhas = [
            f"# Portfolio — {sistema}",
            "",
            f"Membros validados: {len(membros)} | capital base somado: "
            f"{sum(capitais):,.0f}" if capitais else
            f"Membros validados: {len(membros)} | capital base: n/d",
            "",
            "| Simbolo | Variante | Retencao OOS | Expectancy | Trades OOS "
            "| Prob. Ruina (MC) | CapitalBaseR | Set |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for m in membros:
            exp = m["expectancy"]
            ruina = m.get("mc_prob_ruina")
            linhas.append(
                f"| {m['simbolo']} | {m['variante']} "
                f"| {_fmt(m['retencao'], '%')} "
                f"| {'n/d' if exp is None else f'{exp:+.3f}R'} "
                f"| {m['trades'] if m['trades'] is not None else 'n/d'} "
                f"| {'n/d' if ruina is None else f'{ruina*100:.1f}%'} "
                f"| {m['capital'] or 'n/d'} "
                f"| {m['classe']}/{m['ativo']}/{m['sistema']}/"
                f"{MARCA}{m['variante']}.set |")
        linhas += [
            "",
            "Metricas do ledger da campanha; 'n/d' = corrida feita fora dela.",
            "Pesos por correlacao: rode portfolio_builder.py com os",
            "relatorios HTML dos membros -- correlacao pede a serie diaria,",
            "que o ledger nao guarda.",
        ]
        (pasta / f"{sistema}.md").write_text("\n".join(linhas),
                                             encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listar", action="store_true",
                    help="so mostra o que esta pronto, sem mexer no disco")
    args = ap.parse_args()

    if args.listar:
        r = sincronizar()  # sync e listagem sao a mesma varredura
        for p in r["itens"]:
            print(f"  * {p['classe']}/{p['ativo']}/{p['sistema']}/"
                  f"{p['variante']}  retencao={_fmt(p['retencao'], '%')}")
        print(f"{r['prontos']} prontos de {r['templates']} templates.")
        return 0

    r = sincronizar()
    for aviso in r["avisos"]:
        print(f"  AVISO: {aviso}")
    print(f"espelho: {r['prontos']} prontos | {r['copiados']} copiados | "
          f"{r['removidos']} marcadores removidos | MAPA.md e "
          f"{PASTA_PORTFOLIOS}/ atualizados em {PRONTOS.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
