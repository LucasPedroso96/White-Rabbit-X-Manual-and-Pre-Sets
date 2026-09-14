# -*- coding: utf-8 -*-
"""Testa `campanha.resolver_janela()` -- Fase 1 da mudanca de direcao
(2026-09-13): a janela historica (--from) passa a poder ser dimensionada por
CONTAGEM DE TRADES necessaria em vez de sempre 3 anos fixos.

Sem MT5 real: o caminho de ledger usa um `campanha_resultados.jsonl`
fabricado numa pasta temporaria (mesmo principio de test_checkpoint_estagio1
e test_pausa_campanha -- nunca o ledger real da campanha ao vivo). O caminho
de sonda (`_taxa_anual_por_sonda`) e exercido com um combo que nao existe na
biblioteca de sets local -- `achar_set()` devolve None sem precisar abrir o
MT5, e a funcao cai no fallback de teto do mesmo jeito que cairia se o
terminal estivesse ocupado por outra campanha.

    python test_resolver_janela.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import campanha

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


def checar_que(rotulo: str, condicao: bool) -> None:
    if not condicao:
        FALHAS.append(rotulo)


tmp = Path(tempfile.mkdtemp())
ledger_original = campanha.LEDGER
lock_original = campanha._LEDGER_LOCK
try:
    campanha.LEDGER = tmp / "campanha_resultados.jsonl"
    campanha._LEDGER_LOCK = tmp / "campanha_resultados.jsonl.lock"

    # --- flag desligada: identico ao comportamento anterior a esta funcao --
    checar("flag desligada devolve anos_atras(3), sem tocar em nada",
          campanha.resolver_janela("EURUSD", "01_SLTP", "BUY_MULTI",
                                   None, "2026.09.13", dinamica=False),
          campanha.anos_atras(3))

    # --- --from explicito sempre vence, mesmo com a flag ligada ------------
    checar("--from explicito vence mesmo com --janela-dinamica",
          campanha.resolver_janela("EURUSD", "01_SLTP", "BUY_MULTI",
                                   "2020.01.01", "2026.09.13", dinamica=True),
          "2020.01.01")

    # --- ligada, sem dado no ledger e combo inexistente (sonda falha) ------
    # achar_set() nao encontra "SISTEMA_FAKE" na biblioteca -> sonda devolve
    # None -> cai no teto (janela_maxima_anos), igual ao status quo.
    checar(
        "sem ledger e sonda sem set: cai no teto (janela_maxima_anos)",
        campanha.resolver_janela("MOEDA_QUE_NAO_EXISTE", "SISTEMA_FAKE",
                                 "VARIANTE_FAKE", None, "2026.09.13",
                                 dinamica=True, janela_maxima_anos=2),
        campanha.anos_atras(2))

    # --- ligada, com dado no ledger: usa a taxa medida ----------------------
    # 200 trades em 730 dias (janela_dias) = 100 trades/ano exatos.
    campanha.LEDGER.write_text(
        json.dumps({"simbolo": "EURUSD", "sistema": "01_SLTP",
                   "variante": "BUY_MULTI", "trades_oos": 200,
                   "janela_dias": 730}) + "\n",
        encoding="utf-8")
    fim = "2026.09.13"
    obtido = campanha.resolver_janela("EURUSD", "01_SLTP", "BUY_MULTI",
                                      None, fim, dinamica=True,
                                      trades_alvo=100.0)
    checar_que(f"com dado de ledger (100/ano), janela nao cai no teto de 3 "
              f"anos (obtido {obtido})",
              obtido != campanha.anos_atras(3))
    # 100 trades/ano, alvo de 100 trades -> dias_para_trades_alvo(100, 100)
    # dias antes de `fim` (mesma conta que optimize_two_stage faz).
    import optimize_two_stage as ots
    from datetime import datetime, timedelta
    dias_esperados = ots.dias_para_trades_alvo(100.0, 100.0, maximo_dias=3*365)
    esperado = (datetime.strptime(fim, "%Y.%m.%d")
               - timedelta(days=dias_esperados)).strftime("%Y.%m.%d")
    checar("janela calculada bate com dias_para_trades_alvo da mesma taxa",
          obtido, esperado)

    # --- registro de OUTRO combo no ledger nao contamina este -------------
    # Sonda deliberadamente neutralizada (monkeypatch) pra isolar SO o
    # comportamento do ledger aqui -- desde que a sonda passou a rodar um
    # passe real de verdade (fix de 2026-09-13, ver campanha.py), usar um
    # combo REAL como EURUSD/01_SLTP/BUY_MULTI sem neutralizar a sonda
    # faria este teste abrir o MT5 de verdade, o que ele nunca deve fazer.
    sonda_original = campanha._taxa_anual_por_sonda
    campanha._taxa_anual_por_sonda = lambda *a, **k: None
    try:
        campanha.LEDGER.write_text(
            json.dumps({"simbolo": "GBPUSD", "sistema": "01_SLTP",
                       "variante": "BUY_MULTI", "trades_oos": 5000,
                       "janela_dias": 30}) + "\n",
            encoding="utf-8")
        checar(
            "combo sem dado proprio nao usa taxa de OUTRO simbolo/sistema/variante",
            campanha.resolver_janela("EURUSD", "01_SLTP", "BUY_MULTI",
                                     None, "2026.09.13", dinamica=True,
                                     janela_maxima_anos=2),
            campanha.anos_atras(2))

        # --- linha corrompida no ledger nao derruba a leitura ---------------
        campanha.LEDGER.write_text("isso nao e json valido {{{\n",
                                   encoding="utf-8")
        checar(
            "ledger corrompido: nao explode, cai no teto (sonda neutralizada)",
            campanha.resolver_janela("EURUSD", "01_SLTP", "BUY_MULTI",
                                     None, "2026.09.13", dinamica=True,
                                     janela_maxima_anos=2),
            campanha.anos_atras(2))
    finally:
        campanha._taxa_anual_por_sonda = sonda_original

    # --- sonda escalona a janela de referencia antes de desistir -----------
    # Achado do dono, 2026-09-14: "por que nao ofereceu 2? 2 e meio?" -- um
    # combo com parametros DEFAULT pouco ativos pode dar 0 trades numa sonda
    # de 180d sem ser inviavel de verdade; a sonda antiga desistia na
    # primeira tentativa e pulava direto pro teto cheio. Simula aqui achar_set
    # bem-sucedido mas passe_unico devolvendo 0 trades nas duas primeiras
    # janelas (180d, 360d) e so achando trade na terceira (720d) -- confere
    # que a sonda USA essa janela maior em vez de desistir cedo, e que ela
    # nunca ultrapassa o teto pedido.
    achar_set_original = ots.base.achar_set
    reescrever_original = ots.reescrever
    passe_unico_original = ots.passe_unico
    tentativas: list[int] = []
    try:
        ots.base.achar_set = lambda *a, **k: Path("fake_origem.set")
        ots.reescrever = lambda *a, **k: None

        def passe_unico_fake(caminho, symbol, periodo, inicio, fim, *a, **k):
            from datetime import datetime as _dt
            dias = (_dt.strptime(fim, "%Y.%m.%d")
                   - _dt.strptime(inicio, "%Y.%m.%d")).days
            tentativas.append(dias)
            # so a partir de ~720 dias de referencia este combo fake produz
            # trade (180 e 360 continuam em 0, como um sistema pouco ativo
            # com parametros DEFAULT desligados demais pra disparar rapido).
            trades = 50 if dias >= 700 else 0
            return {"trades": trades}

        ots.passe_unico = passe_unico_fake

        taxa = campanha._taxa_anual_por_sonda(
            "EURUSD", "01_SLTP", "BUY_MULTI", "2026.09.13", teto_dias=3 * 365)
        checar_que(
            "sonda escalonada tentou mais de uma janela antes de achar trade",
            len(tentativas) >= 3)
        checar_que(
            "sonda escalonada NUNCA excede o teto pedido (3 anos = 1095 dias)",
            all(d <= 1095 for d in tentativas))
        checar_que(
            "sonda escalonada achou taxa (nao desistiu) quando a janela maior "
            "tem trade", taxa is not None and taxa > 0)

        # --- nem no teto acha trade: desiste de verdade (None) -------------
        tentativas.clear()
        ots.passe_unico = lambda *a, **k: {"trades": 0}
        taxa_zero = campanha._taxa_anual_por_sonda(
            "EURUSD", "01_SLTP", "BUY_MULTI", "2026.09.13", teto_dias=3 * 365)
        checar("sonda sem trade nenhum ate o teto devolve None (desiste "
              "de verdade)", taxa_zero, None)
    finally:
        ots.base.achar_set = achar_set_original
        ots.reescrever = reescrever_original
        ots.passe_unico = passe_unico_original
finally:
    campanha.LEDGER = ledger_original
    campanha._LEDGER_LOCK = lock_original
    shutil.rmtree(tmp, ignore_errors=True)

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("resolver_janela: todos os casos passaram")
