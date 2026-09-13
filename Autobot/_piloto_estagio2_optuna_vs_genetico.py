# -*- coding: utf-8 -*-
"""Piloto A/B: Estagio 2 via genetico nativo vs. Optuna/TPE, no mesmo
combo, mesmo travados/WFO -- Fase 3 da mudanca de direcao (2026-09-13).

Roda standalone (fora do circuito completo de 5 estagios) pra isolar so a
BUSCA numerica: fixa a entrada no que o .set de origem ja traz (sem rodar
Estagio 1 -- escopo reduzido pra caber numa janela autonoma), monta os
MESMOS `numeros`/`travados` pros dois backends, e compara:
  - tempo de parede de cada busca
  - melhor nota (campo da formula ativa) que cada uma achou

NAO substitui o piloto A/B completo do plano (que compara POS-torneio de
retencao, com repeticoes pra medir variancia) -- e um piloto ENXUTO (n=1
por backend por combo) pra caber numa janela noturna, deixado explicito
no relatorio final. Log tudo em texto simples pra acompanhar depois.

    python _piloto_estagio2_optuna_vs_genetico.py
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import optimize_sets as base
import optimize_two_stage as ots

# Bypass deliberado da guarda de colisao entre instancias MT5 (dono,
# 2026-09-13: "essas otimizacoes de agora vao se perder, servem so de
# comparacao... nao tem por que se preocupar com elas" -- autorizacao
# explicita pras campanhas descartaveis rodando esta noite). SO pra este
# piloto noturno; a guarda real (_outra_instancia_mt5_ativa) continua
# protegendo o circuito de producao normalmente.
ots._outra_instancia_mt5_ativa = lambda: False

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI / "_piloto_estagio2_optuna_vs_genetico_resultado.jsonl"
LOG = AQUI / "_piloto_estagio2_optuna_vs_genetico.log"

COMBOS = [
    ("EURUSD", "01_SLTP", "BUY_MULTI"),
    ("XAUUSD", "12_GRID_INVERSO", "BUY_MULTI"),
]
INICIO, FIM = "2026.06.01", "2026.09.01"
DEPOSITO = 1000
N_TRIALS_OPTUNA = 60
TIMEOUT_GENETICO = 2700  # 45 min de teto de seguranca por rodada genetica


def log(msg: str) -> None:
    linha = f"{datetime.now().isoformat(timespec='seconds')} | {msg}"
    print(linha, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(linha + "\n")


def gravar(registro: dict) -> None:
    with SAIDA.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(registro, ensure_ascii=False) + "\n")


def rodar_combo(symbol: str, sistema: str, variante: str) -> None:
    caminho = base.achar_set(symbol, sistema, variante)
    if caminho is None:
        log(f"{symbol}/{sistema}/{variante}: set nao encontrado, pulando")
        return
    if ots._outra_instancia_mt5_ativa():
        log(f"{symbol}/{sistema}/{variante}: outra instalacao MT5 ativa "
           "agora -- pulando este combo por seguranca (arquivo de "
           "formulas compartilhado).")
        return

    trabalho = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_ETAPA_PILOTO.set"
    travados = ots.janelas_wfo(INICIO, FIM)
    travados["InterfaceLanguage"] = "1"
    numeros = ots.eixos_reotimizaveis(sistema, None)
    campo = ots.campo_da_formula_ativa(sistema, caminho)
    log(f"=== {symbol}/{sistema}/{variante} | {len(numeros)} eixos | "
       f"campo da formula: {campo} ===")

    # --- backend genetico (baseline) ---------------------------------------
    if ots._outra_instancia_mt5_ativa():
        log("  outra instancia ficou ativa entre combos -- abortando o "
           "restante deste combo.")
        return
    t0 = time.time()
    ots.reescrever(caminho, trabalho, numeros, travados)
    ots.limpar_todas_formulas()
    cab_g, linhas_g = ots.rodar(trabalho, symbol, "M1", INICIO, FIM,
                               DEPOSITO, 1, TIMEOUT_GENETICO,
                               variante=variante)
    dt_g = time.time() - t0
    melhor_g = None
    if linhas_g and campo:
        formulas = ots.carregar_todas_formulas()
        casados = ots.casar_formula_com_relatorio(cab_g, linhas_g, formulas)
        notas = [d.get(campo) for d in casados.values() if d.get(campo) is not None]
        melhor_g = max(notas) if notas else None
    log(f"  genetico: {dt_g/60:.1f} min | {len(linhas_g)} passes | "
       f"melhor {campo}={melhor_g}")
    gravar({"symbol": symbol, "sistema": sistema, "variante": variante,
           "backend": "genetico", "minutos": round(dt_g / 60, 1),
           "passes": len(linhas_g), "melhor_nota": melhor_g,
           "quando": datetime.now().isoformat(timespec="seconds")})

    # --- backend optuna ------------------------------------------------------
    if ots._outra_instancia_mt5_ativa():
        log("  outra instancia ficou ativa antes do optuna -- abortando "
           "a metade optuna deste combo.")
        return
    t0 = time.time()
    cab_o, linhas_o = ots.otimizar_estagio2_optuna(
        caminho, trabalho, numeros, travados,
        type("Args", (), {"symbol": symbol, "sistema": sistema,
                          "variante": variante, "period": "M1",
                          "inicio": INICIO, "fim": FIM,
                          "deposit": DEPOSITO,
                          "estagio2_optuna_trials": N_TRIALS_OPTUNA})(),
        n_trials=N_TRIALS_OPTUNA, timeout_trial=90)
    dt_o = time.time() - t0
    melhor_o = None
    if linhas_o and "Profit" in cab_o:
        i_lucro = cab_o.index("Profit")
        melhor_o = max(float(l[i_lucro]) for l in linhas_o)
    log(f"  optuna:   {dt_o/60:.1f} min | {len(linhas_o)} trials | "
       f"melhor Profit={melhor_o}")
    gravar({"symbol": symbol, "sistema": sistema, "variante": variante,
           "backend": "optuna", "minutos": round(dt_o / 60, 1),
           "passes": len(linhas_o), "melhor_nota_profit": melhor_o,
           "quando": datetime.now().isoformat(timespec="seconds")})


def main() -> None:
    log("piloto iniciado")
    for symbol, sistema, variante in COMBOS:
        try:
            rodar_combo(symbol, sistema, variante)
        except Exception as exc:  # nunca derruba o piloto inteiro por 1 combo
            log(f"{symbol}/{sistema}/{variante}: ERRO -- {exc!r}")
    log("piloto concluido")


if __name__ == "__main__":
    main()
