# -*- coding: utf-8 -*-
"""Reality Check adaptado (White 2000 / Hansen SPA, na medida do custo real):
o sweep de 14 formulas escolhe a que passou nos gates SEM corrigir por
multiplas comparacoes -- testar 14 e aceitar quem passou infla falso-positivo
vs um teste unico pre-registrado.

Um Reality Check de livro re-roda TODOS os candidatos em cada historico
reamostrado -- inviavel aqui (cada formula ja custa ~20-90min de busca
genetica). O truque: reusa os parametros JA TRAVADOS de cada formula (sem
re-otimizar), quebra o periodo em blocos calendario contiguos, roda
passe_unico() UMA VEZ por (formula x bloco) -- cacheado em disco, resume-safe
--, e faz o bootstrap de verdade em Python puro (gratis) reamostrando QUAL
CONJUNTO DE BLOCOS compoe a corrida sintetica de cada formula, usando o
MESMO indice sorteado pras 14 formulas em cada rodada. Esse detalhe -- indice
compartilhado -- e o que faz isto ser um reality check e nao 14 bootstraps
independentes: preserva a correlacao entre formulas (todas expostas ao MESMO
regime de mercado no mesmo bloco).

NAO e um Reality Check/SPA de livro-texto (que recentra contra um benchmark
externo) -- e uma adaptacao honesta pra uma pergunta mais estreita: "o
melhor-de-N observado e explicavel pela variabilidade bloco-a-bloco que a
gente realmente mediu?". Bootstrap com reposicao sobre os mesmos N blocos
preserva a media de cada formula mas infla a variancia em relacao ao
observado (cada bloco uma vez so) -- entao o nulo do MAXIMO e um teto
conservador de "quao grande o melhor-de-N fica so por sorte de composicao
de blocos", nao uma prova formal.

Escopo v1: so sistemas Fixed-R (PositionSizeMode=3) -- mesma limitacao que
monte_carlo_wrx.py ja tinha. Grid/martingale/d'Alembert (lote fixo/
monetario, sem unidade R comparavel) ficam para depois.

Uso:
    python reality_check_wrx.py --sistema 05_BE_TRAIL --simbolo XAUUSD \
        --deposit 10000
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_sets as base
import optimize_two_stage as ots
from mt5_runner import garantir_terminal_livre

AQUI = Path(__file__).resolve().parent
CACHE_DIR = AQUI / "reality_check_cache"

# Copia estatica de sweep_formulas.TODAS_FORMULAS -- NAO importar
# sweep_formulas.py: ele chama parser.parse_args() no escopo do modulo e
# sequestraria nosso proprio sys.argv.
FORMULAS = {
    1: "GridSurvivalScore", 2: "Profit", 3: "ProfitWinTradeDD",
    4: "EfficiencyRelativeToDeposit", 5: "AdjustedEfficiencyForGrid",
    6: "ProfitRelativeToDDAndDeposit", 7: "ProfitPerTradeAdjustedByDD",
    8: "SharpeAdjustedByDD", 9: "PessimisticProfit", 10: "ResilienceToDrawdown",
    11: "ReturnUniformity", 12: "SystemRobustness", 13: "LevainCompositeScore",
    14: "SomaR",
}


def parse_log_formula(sistema: str, simbolo: str, formula: int, nome: str,
                      pasta: Path = AQUI) -> dict | None:
    """Le sweep_{sistema}_{simbolo}_{formula:02d}_{nome}.log e devolve o
    ultimo blob JSON + veredito.

    'aprovado' vem do TEXTO do log, nao de uma chave do dict -- o JSON nao
    tem campo 'aprovado' (so mc_aprovado etc.). Mesma deteccao que
    _confirmacao_longa.py ja usa em producao: procura a linha "APROVADO:"
    impressa em optimize_two_stage.py (REPROVADO nao bate por construcao,
    comeca com R).
    """
    caminho = pasta / f"sweep_{sistema}_{simbolo}_{formula:02d}_{nome}.log"
    if not caminho.is_file():
        return None
    texto = caminho.read_text(encoding="utf-8", errors="ignore")
    ultimo_json = None
    for linha in texto.splitlines():
        linha = linha.strip()
        if linha.startswith("{") and linha.endswith("}"):
            try:
                json.loads(linha)
            except json.JSONDecodeError:
                continue
            ultimo_json = linha
    if ultimo_json is None:
        return None
    blob = json.loads(ultimo_json)
    return {
        "formula": formula, "nome": nome,
        "aprovado": bool(re.search(r"^\s*APROVADO", texto, re.MULTILINE)),
        "parametros": blob.get("parametros") or {},
        "motivo_reprovacao_precoce": blob.get("motivo_reprovacao_precoce"),
    }


def carregar_candidatos(sistema: str, simbolo: str,
                        pasta: Path = AQUI) -> dict[int, dict]:
    """Pool para o teste conjunto = TODA formula que o circuito completo
    avaliou (parametros != {}), NAO so as APROVADAS. Corrigir so o
    subconjunto que ja passou pelo proprio filtro reintroduziria o mesmo
    vies de selecao por outra porta -- White/Hansen corrigem pelo conjunto
    INTEIRO de modelos testados, nao pelos sobreviventes."""
    candidatos = {}
    for formula, nome in FORMULAS.items():
        info = parse_log_formula(sistema, simbolo, formula, nome, pasta)
        if info is None:
            print(f"  [{formula:02d}] {nome}: log ausente")
            continue
        if not info["parametros"]:
            print(f"  [{formula:02d}] {nome}: SEM_CANDIDATO "
                 f"({info['motivo_reprovacao_precoce'] or 'sem parametros'}), fora do pool")
            continue
        candidatos[formula] = info
    return candidatos


def reconstruir_set(origem: Path, destino: Path, parametros: dict) -> Path:
    """Reescreve o .set vencedor a partir dos parametros travados do JSON --
    MESMO mecanismo que grava o set de entrega (optimize_two_stage.reescrever,
    origem, destino, [], entrega).

    Duas diferencas deliberadas do 'entrega' original:
      1. AtivarWFO=false explicito (necessario pro passe_unico rodar uma
         janela arbitraria sem o WFO interno recortar o periodo).
      2. NAO fixamos PositionSizeMode/selectedFormula: o template de origem
         ja vem em PositionSizeMode=3 (Fixed-R) por padrao -- entao o
         reconstruido fica Fixed-R mesmo se a formula tiver sido ENTREGUE em
         Percentage no estagio 5. De proposito: mantem as N formulas na
         MESMA unidade escalonavel, sem juros compostos, comparavel entre si.
    """
    travar = dict(parametros)
    travar["AtivarWFO"] = "false"
    ots.reescrever(origem, destino, [], travar)
    faltando = ots.conferir_set(destino, travar)
    if faltando:
        raise RuntimeError(f"set reconstruido incompleto: {faltando}")
    return destino


def dividir_em_blocos(inicio: str, fim: str, n_blocos: int) -> list[tuple[str, str]]:
    """[inicio, fim] em n_blocos janelas contiguas, nao sobrepostas -- cada
    uma um passe_unico() independente (AtivarWFO=false ja garante isso).
    Ultimo bloco absorve o resto da divisao inteira."""
    d0 = datetime.strptime(inicio, "%Y.%m.%d")
    d1 = datetime.strptime(fim, "%Y.%m.%d")
    passo = (d1 - d0).days // n_blocos
    blocos, cursor = [], d0
    for i in range(n_blocos):
        fim_i = d1 if i == n_blocos - 1 else cursor + timedelta(days=passo)
        blocos.append((cursor.strftime("%Y.%m.%d"), fim_i.strftime("%Y.%m.%d")))
        cursor = fim_i
    return blocos


def obter_ou_criar_blocos(cache_dir: Path, inicio: str, fim: str,
                          n_blocos: int) -> list[tuple[str, str]]:
    """Grava o esquema de blocos UMA vez -- um resume depois de uma
    interrupcao precisa usar as MESMAS fronteiras, senao o cache por bloco
    fica orfao (mesmo cuidado que ja valeu a pena com o desligamento real
    que interrompeu 07_GRID_SEPARATE em 27/08)."""
    marcador = cache_dir / "blocos.json"
    if marcador.is_file():
        return [tuple(b) for b in json.loads(marcador.read_text(encoding="utf-8"))]
    cache_dir.mkdir(parents=True, exist_ok=True)
    blocos = dividir_em_blocos(inicio, fim, n_blocos)
    marcador.write_text(json.dumps(blocos), encoding="utf-8")
    return blocos


def rodar_bloco(caminho_set: Path, symbol: str, bloco: tuple[str, str],
                deposito: int, cache_dir: Path, formula: int,
                indice_bloco: int, timeout: int | None) -> dict:
    """1 passe_unico (modelo=4, tick real, ~35s) para 1 (formula, bloco),
    cacheado em disco -- resume-safe. Le cache se existe; senao roda e grava
    ATOMICO (tmp + os.replace) antes de devolver, pra nunca deixar um
    arquivo de cache pela metade no disco."""
    inicio, fim = bloco
    arq = cache_dir / f"{formula:02d}_{indice_bloco:02d}_{inicio}_{fim}.json"
    if arq.is_file():
        return json.loads(arq.read_text(encoding="utf-8"))
    t0 = time.time()
    r = ots.passe_unico(caminho_set, symbol, "M1", inicio, fim, deposito,
                        modelo=4, timeout=timeout)
    resultado = {"formula": formula, "indice_bloco": indice_bloco,
                "inicio": inicio, "fim": fim, "trades": r["trades"],
                "total_r": r["total_r"], "expectancy": r["expectancy"],
                "saldo": r["saldo"], "abortos": r["abortos"],
                "elapsed_s": round(time.time() - t0, 1)}
    tmp = arq.with_suffix(".tmp")
    tmp.write_text(json.dumps(resultado, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, arq)
    return resultado


def coletar_matriz(candidatos: dict, blocos: list, origem: Path,
                   cache_root: Path, args) -> dict[int, list[dict]]:
    """Reconstroi 1 .set por formula (barato, uma vez) e roda passe_unico em
    CADA bloco -- ate len(candidatos)*len(blocos) passes, cacheados um a
    um. .set fica sob a arvore Tester/ (passe_unico exige relative_to()
    dali); resultados JSON ficam no repo, em CACHE_DIR."""
    sets_dir = (base.DADOS / "MQL5" / "Profiles" / "Tester" /
               "_reality_check_sets" / f"{args.sistema}__{args.simbolo}__{args.variante}")
    sets_dir.mkdir(parents=True, exist_ok=True)
    resultados_dir = cache_root / "resultados"
    resultados_dir.mkdir(parents=True, exist_ok=True)

    matriz = {}
    for formula, info in sorted(candidatos.items()):
        destino = sets_dir / f"{formula:02d}_{info['nome']}.set"
        reconstruir_set(origem, destino, info["parametros"])
        linha = []
        for i, bloco in enumerate(blocos):
            print(f"  [{formula:02d}/{info['nome']}] bloco {i+1}/{len(blocos)} "
                 f"{bloco[0]}..{bloco[1]}", end=" ", flush=True)
            res = rodar_bloco(destino, args.simbolo, bloco, args.deposit,
                              resultados_dir, formula, i, args.timeout)
            print(f"-> {res['trades']} trades, {res['total_r']:+.2f}R "
                 f"({res['elapsed_s']}s)", flush=True)
            linha.append(res)
        matriz[formula] = linha
    return matriz


def bootstrap_por_blocos(matriz: dict[int, list[dict]], n_bootstrap: int,
                         seed: int | None) -> dict:
    """Estatistica: Total R somado nos blocos (mesma unidade escalonavel que
    Formula_SomaR/total_r ja usa em todo o resto do circuito). Real = ordem
    cronologica observada. Nulo = sortear o MESMO indice de blocos (com
    reposicao) pras N formulas em cada rodada -- e o que preserva a
    correlacao entre formulas (todas expostas ao mesmo regime no mesmo
    bloco), o detalhe que diferencia isto de so rodar N bootstraps
    independentes."""
    formulas = sorted(matriz.keys())
    n_blocos = len(next(iter(matriz.values())))
    r_por_formula = {f: np.array([b["total_r"] or 0.0 for b in matriz[f]])
                     for f in formulas}
    s_obs = {f: float(r_por_formula[f].sum()) for f in formulas}
    melhor_formula = max(s_obs, key=s_obs.get)
    melhor_obs = s_obs[melhor_formula]

    rng = np.random.default_rng(seed)
    melhor_nulo = np.empty(n_bootstrap)
    s_estrela = {f: np.empty(n_bootstrap) for f in formulas}
    for d in range(n_bootstrap):
        idx = rng.integers(0, n_blocos, size=n_blocos)   # MESMO idx p/ todas as formulas
        pior = -np.inf
        for f in formulas:
            s = float(r_por_formula[f][idx].sum())
            s_estrela[f][d] = s
            pior = max(pior, s)
        melhor_nulo[d] = pior

    p_conjunto = (1 + int((melhor_nulo >= melhor_obs).sum())) / (n_bootstrap + 1)
    return {
        "melhor_formula_observada": melhor_formula, "melhor_s_obs": melhor_obs,
        "p_valor_reality_check": p_conjunto,
        "nulo_percentis": {p: float(np.percentile(melhor_nulo, p)) for p in (50, 90, 95, 99)},
        "nulo_media": float(melhor_nulo.mean()), "nulo_desvio": float(melhor_nulo.std()),
        "diagnostico_por_formula": {
            f: {"s_obs": s_obs[f],
               "p_individual": (1 + int((s_estrela[f] >= s_obs[f]).sum())) / (n_bootstrap + 1)}
            for f in formulas},
        "n_bootstrap": n_bootstrap, "n_blocos": n_blocos,
    }


def relatorio(sistema, simbolo, variante, candidatos, resultado, alpha: float) -> None:
    aprovado_rc = resultado["p_valor_reality_check"] <= alpha
    linhas = [f"=== Reality Check (block bootstrap) {simbolo} {sistema} {variante} ===",
             f"blocos: {resultado['n_blocos']} | bootstrap: {resultado['n_bootstrap']} draws | alpha: {alpha}", ""]
    for f, info in sorted(candidatos.items()):
        d = resultado["diagnostico_por_formula"][f]
        linhas.append(f"[{f:02d}] {info['nome']:<26} original={'APROVADO' if info['aprovado'] else 'reprovado':<10} "
                      f"S_obs={d['s_obs']:+8.2f}R  p_individual={d['p_individual']:.3f}")
    linhas += ["",
        f"Melhor-de-{len(candidatos)} observado: formula {resultado['melhor_formula_observada']:02d} "
        f"({candidatos[resultado['melhor_formula_observada']]['nome']}), {resultado['melhor_s_obs']:+.2f}R",
        f"Nulo (reamostragem por blocos): media {resultado['nulo_media']:+.2f}R | "
        f"p95 {resultado['nulo_percentis'][95]:+.2f}R",
        f"p-valor (reality check): {resultado['p_valor_reality_check']:.4f}", "",
        ("SOBREVIVE ao Reality Check." if aprovado_rc else
         "NAO SOBREVIVE ao Reality Check: um conjunto de blocos reamostrado produz um "
         f"melhor-de-N tao bom ou melhor em mais de {alpha*100:.0f}% das vezes.")]
    texto = "\n".join(linhas)
    print(texto, flush=True)
    Path(f"reality_check_{sistema}_{simbolo}.log").write_text(texto, encoding="utf-8")
    Path(f"reality_check_{sistema}_{simbolo}.json").write_text(
        json.dumps({"sistema": sistema, "simbolo": simbolo, "variante": variante,
                    "alpha": alpha, "aprovado_reality_check": aprovado_rc, **resultado,
                    "candidatos": {f: {"nome": c["nome"], "aprovado_original": c["aprovado"]}
                                  for f, c in candidatos.items()}},
                   ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sistema", required=True)
    ap.add_argument("--simbolo", required=True)
    ap.add_argument("--variante", default="BUY_MULTI")
    ap.add_argument("--deposit", type=int, required=True)
    ap.add_argument("--from-data", dest="de", default="2025.08.25")
    ap.add_argument("--to-data", dest="ate", default="2026.08.25")
    ap.add_argument("--n-blocos", type=int, default=12)
    ap.add_argument("--n-bootstrap", type=int, default=10000)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--timeout", type=int, default=None)
    ap.add_argument("--fechar-terminal", action="store_true")
    ap.add_argument("--logs-dir", default=str(AQUI))
    args = ap.parse_args()

    origem = base.achar_set(args.simbolo, args.sistema, args.variante)
    if origem is None:
        print(f"Set de origem nao encontrado: {args.simbolo}/{args.sistema}/{args.variante}")
        return 1
    if ots.modo_de_sizing(origem) != "3":
        print("FORA DE ESCOPO (v1): reality_check_wrx.py so cobre Fixed-R "
             "(PositionSizeMode=3) -- grid/martingale/d'Alembert ficam para depois.")
        return 1

    candidatos = carregar_candidatos(args.sistema, args.simbolo, Path(args.logs_dir))
    if len(candidatos) < 2:
        print(f"Menos de 2 candidatos com parametros reais ({len(candidatos)}) -- "
             "nada para comparar.")
        return 1

    garantir_terminal_livre(fechar=args.fechar_terminal, terminal=base.TERMINAL)
    cache_root = CACHE_DIR / f"{args.sistema}__{args.simbolo}__{args.variante}"
    blocos = obter_ou_criar_blocos(cache_root, args.de, args.ate, args.n_blocos)
    matriz = coletar_matriz(candidatos, blocos, origem, cache_root, args)
    resultado = bootstrap_por_blocos(matriz, args.n_bootstrap, args.seed)
    relatorio(args.sistema, args.simbolo, args.variante, candidatos, resultado, args.alpha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
