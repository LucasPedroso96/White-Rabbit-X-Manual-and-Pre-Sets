# -*- coding: utf-8 -*-
"""Motor de sugestao do AutoManagerLive -- ver PLANO_TREINAMENTO_100_A_MILHAO.md
secao 8 ("Deployment: AutoManagerLive") para o desenho completo.

Pega o pool que o painel "Certified sets" ja expoe (`/api/implantacao`) e
produz uma fila NUMERADA de sugestoes de combinacao: combos certificados que
cabem juntos por correlacao (reaproveitando portfolio_builder.py), ordenados
primeiro pela ordem de graduacao por risco (RESEARCH -> HEDGE_ACCOUNT_REQUIRED
-> HIGH_RISK -> HIGH_RISK_RESEARCH), e cada sugestao ja diz quantas contas
precisa e de que tipo.

Fora daqui, de proposito: promocao/rebaixamento por metrica ao vivo (EM_PROVA)
exige historico de trade ao vivo real, que este codebase ainda nao ingere --
ver secao 8 do plano, "Fora de escopo por enquanto".
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

import portfolio_builder as pb
from generate_system_sets import ASSETS, CLASSES, SYSTEMS

# Mesma ordem de graduacao pra capital ao vivo da secao 5 do plano.
TIER_ORDEM = ["RESEARCH", "HEDGE_ACCOUNT_REQUIRED", "HIGH_RISK",
             "HIGH_RISK_RESEARCH"]

SYSTEM_STATUS: dict[str, str] = {s.code: s.status for s in SYSTEMS}

ASSET_CLASS_OF: dict[str, str] = {
    ativo: classe for classe, ativos in ASSETS.items() for ativo in ativos
}


def _classe_do_simbolo(simbolo: str) -> str | None:
    """Resolve a classe de ativo do simbolo: exato primeiro, senao o radical
    antes do primeiro separador -- mesma logica de capital_minimo_classe,
    compartilhada aqui pra nunca perder um combo por causa de sufixo de
    corretora na hora de agrupar por classe em contas_necessarias()."""
    classe = ASSET_CLASS_OF.get(simbolo)
    if classe is None:
        radical = re.split(r"[.\-_]", simbolo)[0]
        classe = ASSET_CLASS_OF.get(radical)
    return classe


def capital_minimo_classe(simbolo: str) -> float | None:
    """Capital minimo da classe do ativo (generate_system_sets.CLASSES).

    Tenta o simbolo exato primeiro (cobre casos como "BRK.B", que tem ponto
    proprio, nao sufixo de corretora); so cai pro radical antes do primeiro
    separador quando o simbolo exato nao bate -- mesma ideia de
    ready_library.achar_ativo(), pra aceitar "EURUSD.HT"/"EURUSD-ECN" etc.

    Nao resolve um sufixo colado sem separador (ex: "EURUSDm") -- retorna None.
    Precisaria validar contra mt5.symbols_get() pra ser seguro (evita false
    positives em short tickers no ASSET_CLASS_OF).
    """
    classe = _classe_do_simbolo(simbolo)
    if classe is None:
        return None
    return CLASSES[classe].capital_base


def ordenar_candidatos(combos: list[dict]) -> list[dict]:
    """Ordem de graduacao por risco (secao 5 do plano) primeiro; dentro do
    mesmo tier, maior retencao_oos primeiro, depois menor mc_prob_ruina --
    mesmo desempate que a secao 6 ja usa pro ranking por ativo. Combo sem
    retencao/mc conhecido fica no fim do proprio tier, nunca no comeco."""
    def chave_ordenacao(c: dict) -> tuple:
        tier = SYSTEM_STATUS.get(c["sistema"], "HIGH_RISK_RESEARCH")
        indice_tier = (TIER_ORDEM.index(tier) if tier in TIER_ORDEM
                      else len(TIER_ORDEM))
        retencao = c.get("retencao")
        mc = c.get("mc_prob_ruina")
        return (
            indice_tier,
            -(retencao if retencao is not None else -1e18),
            mc if mc is not None else 1e18,
        )
    return sorted(combos, key=chave_ordenacao)


def selecionar_ordenado(series: dict[str, pd.Series], ordem: list[str],
                        maximo: int, teto: float,
                        recuperacao_minima: float) -> tuple[list[str], list[str]]:
    """Mesma elegibilidade e mesmo teto de correlacao POSITIVA de
    portfolio_builder.selecionar() (correlacao negativa nunca exclui -- e o
    melhor caso, ver a docstring de selecionar()), mas a ordem de escolha
    segue `ordem` (graduacao de risco, ja despatada por retencao/mc) em vez
    do maior fator de recuperacao. O resultado pode misturar tiers quando o
    teto de correlacao permite -- e exatamente esse caso que aciona a regra
    de "mistura de tier" de contas_necessarias().
    """
    quadro = pd.DataFrame(series).fillna(0.0)
    correl = quadro.corr().fillna(0.0)

    avaliacao = {nome: pb.metricas(serie) for nome, serie in series.items()}
    elegiveis: list[str] = []
    recusadas: list[str] = []
    for nome in ordem:
        m = avaliacao.get(nome)
        if m is None:
            continue
        if m["resultado"] <= 0:
            recusadas.append(f"{nome}: resultado negativo")
        elif m["recuperacao"] < recuperacao_minima:
            recusadas.append(
                f"{nome}: recuperacao {m['recuperacao']:.2f} "
                f"abaixo de {recuperacao_minima:g}")
        else:
            elegiveis.append(nome)

    escolhidas: list[str] = []
    for nome in elegiveis:
        if len(escolhidas) >= maximo:
            break
        if not escolhidas:
            escolhidas.append(nome)
            continue
        pior = max(correl.loc[nome, j] for j in escolhidas)
        if pior <= teto:
            escolhidas.append(nome)
    return escolhidas, recusadas


def contas_necessarias(combos: list[dict], saldo_conta: float) -> list[dict]:
    """Particiona os combos de uma sugestao em contas, so por restricao dura
    (secao 8 do plano -- nunca por preferencia de diversificacao):

      MISTURA DE TIER   combo HEDGE_ACCOUNT_REQUIRED (07/08) sempre isolado
                        numa conta de hedging separada dos demais tiers.
      CAPITAL MINIMO    soma dos capitais minimos das classes de ativo
                        presentes no resto excede `saldo_conta` -> particiona
                        por classe ate caber. saldo_conta<=0 (desconhecido)
                        nunca forca split -- assume que cabe.
    """
    hedge = [c for c in combos
            if SYSTEM_STATUS.get(c["sistema"]) == "HEDGE_ACCOUNT_REQUIRED"]
    normais = [c for c in combos if c not in hedge]

    contas: list[dict] = []
    if hedge:
        capital_hedge = max(
            (capital_minimo_classe(c["simbolo"]) or 0.0) for c in hedge)
        contas.append({
            "tipo": "hedging",
            "capital_minimo": capital_hedge,
            "combos": [c["chave"] for c in hedge],
        })

    if normais:
        por_classe: dict[str, list[dict]] = {}
        sem_classe: list[dict] = []
        for c in normais:
            classe = _classe_do_simbolo(c["simbolo"])
            if classe is None:
                sem_classe.append(c)
            else:
                por_classe.setdefault(classe, []).append(c)
        classes_presentes = sorted(por_classe)
        capital_total = sum(CLASSES[classe].capital_base
                            for classe in classes_presentes)
        if saldo_conta <= 0 or capital_total <= saldo_conta or not classes_presentes:
            contas.append({
                "tipo": "normal",
                "capital_minimo": capital_total,
                "combos": [c["chave"] for c in normais],
            })
        else:
            for classe in classes_presentes:
                contas.append({
                    "tipo": "normal",
                    "capital_minimo": CLASSES[classe].capital_base,
                    "combos": [c["chave"] for c in por_classe[classe]],
                })
            if sem_classe:
                contas.append({
                    "tipo": "normal",
                    "capital_minimo": 0.0,
                    "combos": [c["chave"] for c in sem_classe],
                })
    return contas
