# -*- coding: utf-8 -*-
"""Mantem o espelho de sets PRONTOS ao lado da biblioteca de templates.

Os sets validados pelo circuito nascem soltos na raiz de Profiles/Tester
(`VALIDADO_*.set`), e a raiz nao responde a pergunta que importa na hora de
subir um set: "para ESTE ativo e ESTE sistema, existe algo pronto?". A
resposta certa mora na mesma geografia da biblioteca -- por isso o espelho:

    White_Rabbit_X_Sets_Autobot/＊<classe>/＊<ativo>/＊<sistema>/＊BUY_MULTI.set

A arvore e um clone 1:1 das pastas da biblioteca, entao o dialogo "Load" do
Strategy Tester navega nela do jeito que ja se navega nos templates. Pasta
vazia = nada pronto ali; arquivo com ＊ = set validado, ja com WFO desligado,
pronto para subir. Toda pasta ancestral (classe/ativo/sistema) que tem algum
set pronto em QUALQUER lugar abaixo dela tambem ganha o prefixo ＊ -- a arvore
inteira e ~1000 pastas, quase todas vazias; sem marcar os niveis
intermediarios, achar a unica pasta com conteudo exige abrir uma por uma
(achado do dono, 2026-08-03).

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
DADOS = wrx_paths.data_dir()
TESTER = DADOS / "MQL5" / "Profiles" / "Tester"
BIBLIOTECA = TESTER / "White_Rabbit_X_Sets_templates"
PRONTOS = TESTER / "White_Rabbit_X_Sets_Autobot"
LEDGER = AQUI / "campanha_resultados.jsonl"

MARCA = "\uff0a"          # ＊ -- ver docstring
PASTA_PORTFOLIOS = "_PORTFOLIOS"

# Espelha optimize_two_stage.py/generate_system_sets.py: sistemas com SL
# validam em R (Fixed-R). Fora daqui: lote fixo/monetario -- CapitalBaseR,
# expectancy em R e MC nunca se aplicam, e "0"/"n/d" nao e ausencia de
# medida, e "essa metrica nao existe pra esse sizing" (achado do dono,
# 2026-08-04: portfolio mostrava 0/n/d sem dizer qual dos dois era).
SISTEMAS_R_CAPAZES = {"01_SLTP", "02_SLTP_ORGANIC", "03_TRAIL_ONLY",
                      "04_SLTP_TRAIL", "05_BE_TRAIL", "06_REVERSAL_EXIT"}

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


def _normalizar_pastas(destino: Path) -> None:
    """Desfaz qualquer MARCA em nome de pasta antes do resto da sincronizacao.

    Sem isso, uma pasta marcada numa rodada anterior (`＊AUDCHF`) vira uma
    pasta NOVA e destrancada (`AUDCHF`) na proxima -- os passos 1-4 usam
    nomes puros da biblioteca para achar/criar cada no, e um nome ja marcado
    no disco nao bate com esse calculo, gerando duas pastas irmas para o
    mesmo ativo em vez de reconhecer as duas como o mesmo no.
    """
    pastas = sorted((p for p in destino.rglob("*") if p.is_dir()),
                    key=lambda p: len(p.parts), reverse=True)
    for pasta in pastas:
        if pasta.name.startswith(MARCA):
            pasta.rename(pasta.parent / pasta.name[len(MARCA):])


def _marcar_ancestrais(destino: Path, esperados: dict[Path, Path]) -> int:
    """Prefixa com MARCA toda pasta (classe/ativo/sistema) com algo pronto
    embaixo -- a arvore inteira e ~1000 pastas, quase todas vazias; sem
    marcar os niveis intermediarios, achar a UNICA pasta com conteudo exige
    abrir uma por uma no explorador (achado do dono, 2026-08-03).

    Roda DEPOIS de posicionar os arquivos-folha (passo 4): so entao se sabe,
    para cada pasta, se ha algo pronto em algum descendente dela.
    """
    marcar: set[tuple[str, ...]] = set()
    for alvo in esperados:
        partes = alvo.relative_to(destino).parts[:-1]   # sem o nome do .set
        for i in range(1, len(partes) + 1):
            marcar.add(partes[:i])

    pastas = sorted((p for p in destino.rglob("*") if p.is_dir()),
                    key=lambda p: len(p.parts), reverse=True)
    marcados = 0
    for pasta in pastas:
        partes = pasta.relative_to(destino).parts
        if partes in marcar:
            pasta.rename(pasta.parent / f"{MARCA}{pasta.name}")
            marcados += 1
    return marcados


def sincronizar(biblioteca: Path = BIBLIOTECA, tester: Path = TESTER,
                destino: Path = PRONTOS, ledger: Path = LEDGER) -> dict:
    """Espelha pastas, posiciona os prontos com ＊ e regenera MAPA/portfolios.

    Devolve um resumo dict (usado pela campanha para logar sem re-varrer).
    """
    if not biblioteca.is_dir():
        raise FileNotFoundError(f"biblioteca nao encontrada: {biblioteca}")

    destino.mkdir(parents=True, exist_ok=True)
    _normalizar_pastas(destino)

    # 1. Clone das pastas. So pastas: arquivo no espelho significa "pronto",
    #    entao copiar templates para ca destruiria justamente essa semantica.
    relativos = [p.relative_to(biblioteca) for p in biblioteca.rglob("*")
                 if p.is_dir()]
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
            "trades_is": reg.get("trades_is"),
            "mc_prob_ruina": reg.get("mc_prob_ruina"),
            "mc_medido": reg.get("mc_medido", False),
            "capital": ler_param(origem, "CapitalBaseR"),
            "sizing_fixed_r": info["sistema"] in SISTEMAS_R_CAPAZES,
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

    # 5. Propaga a MARCA para classe/ativo/sistema: so agora se sabe, para
    #    cada pasta, se ha algo pronto em algum descendente dela.
    pastas_marcadas = _marcar_ancestrais(destino, esperados)

    total_templates = sum(1 for _ in biblioteca.rglob("*.set"))
    _gerar_mapa(destino, biblioteca, prontos, total_templates)
    _gerar_portfolios(destino, prontos)

    return {"prontos": len(prontos), "copiados": copiados,
            "removidos": removidos, "avisos": avisos,
            "templates": total_templates, "itens": prontos,
            "pastas_marcadas": pastas_marcadas}


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
        # So soma capital de membro R-capaz: CapitalBaseR=0 em lote fixo/
        # monetario nao e "capital zero", e "essa metrica nao existe aqui" --
        # somar junto subestimaria o capital real de um portfolio misto.
        capitais = [float(m["capital"]) for m in membros
                    if m["sizing_fixed_r"] and m["capital"] not in (None, "")]
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
            r_capaz = m["sizing_fixed_r"]
            trades_txt = (str(m["trades"]) if m["trades"] is not None
                         else (f"~{m['trades_is']} (IS)"
                               if m.get("trades_is") is not None
                               else "n/d"))
            # MC e CapitalBaseR nao existem fora de Fixed-R -- "nao se aplica"
            # e um fato do sizing, nao ausencia de medida (mesma distincao
            # que mc_medido ja faz no dashboard principal).
            ruina_txt = ("n/a (fora de Fixed-R)" if not r_capaz
                        else "n/d" if not m.get("mc_medido")
                        else f"{ruina*100:.1f}%" if ruina is not None
                        else "n/d")
            capital_txt = ("n/a (lote fixo)" if not r_capaz
                          else (m["capital"] or "n/d"))
            linhas.append(
                f"| {m['simbolo']} | {m['variante']} "
                f"| {_fmt(m['retencao'], '%')} "
                f"| {'n/d' if exp is None else f'{exp:+.3f}R'} "
                f"| {trades_txt} "
                f"| {ruina_txt} "
                f"| {capital_txt} "
                # classe/ativo/sistema sempre carregam a MARCA aqui: um
                # membro so entra em `prontos` porque ele PROPRIO fez essas
                # tres pastas serem marcadas (ver _marcar_ancestrais).
                f"| {MARCA}{m['classe']}/{MARCA}{m['ativo']}/"
                f"{MARCA}{m['sistema']}/{MARCA}{m['variante']}.set |")
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
          f"{r['removidos']} marcadores removidos | {r['pastas_marcadas']} "
          f"pastas com * | MAPA.md e {PASTA_PORTFOLIOS}/ atualizados "
          f"em {PRONTOS.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
