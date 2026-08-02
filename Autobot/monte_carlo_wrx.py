# -*- coding: utf-8 -*-
"""Monte Carlo de robustez sobre o vencedor tick-real do estagio 4.

O estagio 4 ja responde "o lucro do OHLC se sustentou em tick real?" (retencao
+ divergencia). Isto responde uma pergunta diferente: o quanto essa sequencia
de trades dependeu da ORDEM em que aconteceu? Reamostrar (bootstrap, com
reposicao) a mesma lista de trades centenas de vezes e olhar o pior drawdown
das reamostras expoe uma estrategia que so nao quebrou porque as perdas vieram
espacadas -- na proxima corrida, na vida real, elas podem vir juntas.

Fonte dos trades: o relatorio .htm que o passe IS+OOS de `torneio_retencao`
(modelo=4, estagio 4) ja gera como efeito colateral e que hoje ninguem le --
`passe_unico` extrai metricas do LOG da EA, nunca do .htm. Reusa o parser de
`portfolio_builder.ler_html()`, que ja resolve o problema do relatorio sair no
idioma do terminal.

Medido em R, nao em dinheiro -- mesma convencao Fixed-R do resto do circuito
(scale-invariant, comparavel entre ativos e capital de partida). Sistemas sem
Fixed-R (grid/martingale/d'alembert, lote fixo) nao tem `CapitalBaseR`
significativo e `trades_em_r()` devolve None -- o Monte Carlo nao se aplica a
eles, mesma excecao que a prova em percentual do estagio 5 ja abre.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from portfolio_builder import ler_html, drawdown_maximo

import optimize_sets as base


def achar_relatorio(nome: str) -> Path | None:
    """Mesmo padrao de optimize_sets.py: relatorio sai solto na pasta DADOS,
    preferindo .htm quando existir (e o que passe_unico/torneio_retencao
    geram -- um backtest so, nao uma tabela de passes)."""
    candidatos = sorted(base.DADOS.glob(f"{nome}*"),
                        key=lambda p: (p.suffix.lower() != ".htm", p.name))
    return candidatos[0] if candidatos else None


def _ler_param(caminho: Path, nome: str) -> str | None:
    """Copia minima de ready_library.ler_param -- evita import cruzado entre
    os dois modulos (ready_library nao precisa saber de Monte Carlo)."""
    alvo = f"{nome}="
    for linha in caminho.read_text(encoding="utf-16").splitlines():
        if linha.strip().startswith(alvo):
            return linha.split("=", 1)[1].strip()
    return None


def trades_em_r(relatorio_htm: Path, caminho_set: Path) -> pd.Series | None:
    """Le o relatorio e converte lucro (dinheiro) em R usando o 1R do proprio
    set: RiscoPorTradePct% de CapitalBaseR -- o mesmo g_valorR que a EA usa
    para dimensionar (ver PrintFormat "Fixed-R mode enabled" no .mq5).

    None quando o sistema nao roda em Fixed-R (RiscoRFixo=false: grid,
    martingale, d'alembert) ou quando o relatorio nao tem trades legiveis.
    """
    if _ler_param(caminho_set, "RiscoRFixo") != "true":
        return None
    trades = ler_html(relatorio_htm)
    if trades is None or trades.empty:
        return None
    # Deal de ABERTURA sai com lucro exatamente 0 no relatorio do MT5; so o
    # FECHAMENTO carrega o resultado -- filtrar por != 0 isola um valor por
    # trade em vez de contar cada posicao duas vezes.
    fechados: pd.Series = trades.loc[trades["lucro"] != 0, "lucro"]
    if len(fechados) == 0:
        return None
    capital_base = _ler_param(caminho_set, "CapitalBaseR")
    risco_pct = _ler_param(caminho_set, "RiscoPorTradePct")
    if capital_base is None or risco_pct is None:
        return None
    try:
        um_r = float(capital_base) * float(risco_pct) / 100.0
    except ValueError:
        return None
    if um_r <= 0:
        return None
    return fechados / um_r


def simular(trades_r: pd.Series, n: int = 1000, seed: int | None = None) -> dict:
    """Bootstrap com reposicao sobre a sequencia de trades em R.

    mc_dd_p95: dos N embaralhamentos, o pior drawdown que so 5% deles supera --
    "95% das vezes o drawdown nao passa disto". Sempre em magnitude (positivo),
    para comparar direto com o drawdown observado sem confundir sinal.
    mc_prob_ruina: fracao dos embaralhamentos que fecha no vermelho.
    """
    valores = trades_r.to_numpy(dtype=float)
    if len(valores) < 5:
        return {"mc_dd_p95": None, "mc_dd_observado": None,
                "mc_prob_ruina": None, "mc_n_trades": int(len(valores))}
    rng = np.random.default_rng(seed)
    dd_observado = abs(drawdown_maximo(pd.Series(valores)))
    piores_dd = np.empty(n)
    terminais = np.empty(n)
    for i in range(n):
        amostra = rng.choice(valores, size=len(valores), replace=True)
        curva = np.cumsum(amostra)
        pico = np.maximum.accumulate(curva)
        piores_dd[i] = float((curva - pico).min())
        terminais[i] = float(curva[-1])
    return {
        "mc_dd_p95": float(np.percentile(np.abs(piores_dd), 95)),
        "mc_dd_observado": dd_observado,
        "mc_prob_ruina": float((terminais < 0).mean()),
        "mc_n_trades": int(len(valores)),
    }


def rodar_mc(relatorio_htm: Path, caminho_set: Path, n: int = 1000,
             seed: int | None = None) -> dict | None:
    """Wrapper: le o relatorio -> converte pra R -> simula.

    None quando nao ha o que medir (sistema sem Fixed-R, relatorio ausente ou
    ilegivel) -- ausencia de medida nao deve reprovar, so nao contribui pro
    gate (ver `mc_aprovado` em optimize_two_stage.py).
    """
    trades_r = trades_em_r(relatorio_htm, caminho_set)
    if trades_r is None:
        return None
    return simular(trades_r, n=n, seed=seed)
