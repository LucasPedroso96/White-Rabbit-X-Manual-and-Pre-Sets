# -*- coding: utf-8 -*-
"""Testa o modo pause da campanha (dono, 2026-08-09): sinal em disco
(`optimize_sets.PAUSA`) que para a corrida no proximo ponto seguro, sem
perder trabalho nem marcar o combo interrompido como reprovado no ledger.

Sem MT5 real: `campanha.rodar_combo()` normalmente lanca um subprocesso de
verdade (`optimize_two_stage.py` via Strategy Tester) -- aqui o
`subprocess.Popen` e trocado por um dublê que devolve o returncode que a
gente quer testar, sem abrir o MT5. `dashboard_campanha.estado_campanha()`
e testada do mesmo jeito, trocando so as pecas que tocam SO/tasklist
(`_pid_vivo`, `terminal_aberto`) e apontando os arquivos de estado (LOCK/
PROGRESSO/PAUSA) pra uma pasta temporaria -- nunca os arquivos reais da
campanha ao vivo.

    python test_pausa_campanha.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import optimize_sets as base
import campanha
import dashboard_campanha as painel

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# ============================================================ pausa_solicitada
# PAUSA trocado por um caminho temporario -- nunca o sinal real, que
# pausaria a campanha ao vivo de verdade se ela estiver rodando.
_pausa_original = base.PAUSA
_tmp_pausa = Path(tempfile.mkdtemp()) / "pausa_teste.json"
base.PAUSA = _tmp_pausa
try:
    checar("sem sinal: pausa_solicitada() False", base.pausa_solicitada(), False)
    _tmp_pausa.touch()
    checar("com sinal: pausa_solicitada() True", base.pausa_solicitada(), True)
    # So a PRESENCA importa -- conteudo vazio ou lixo, tanto faz.
    _tmp_pausa.write_text("qualquer coisa", encoding="utf-8")
    checar("conteudo do sinal e irrelevante", base.pausa_solicitada(), True)
    _tmp_pausa.unlink()
    checar("apos remover: False de novo", base.pausa_solicitada(), False)
finally:
    base.PAUSA = _pausa_original
    shutil.rmtree(_tmp_pausa.parent, ignore_errors=True)

checar("CODIGO_PAUSA distinto de sucesso(0) e erro(1)",
       base.CODIGO_PAUSA not in (0, 1), True)


# ==================================================================== rodar_combo
class _ProcessoFalso:
    """Dublê de subprocess.Popen: sem stdout de verdade (nao ha nada pra
    ecoar), devolve o returncode escolhido na hora do wait()."""

    def __init__(self, returncode: int) -> None:
        self._returncode = returncode
        self.stdout = iter(())  # esgotado -- a thread leitora sai na hora

    def wait(self, timeout=None) -> int:
        return self._returncode

    def kill(self) -> None:
        pass


def _rodar_combo_com_returncode(returncode: int) -> dict:
    popen_original = campanha.subprocess.Popen
    campanha.subprocess.Popen = lambda *a, **k: _ProcessoFalso(returncode)
    try:
        args = SimpleNamespace(inicio="2023.01.01", fim="2026.01.01",
                               deposit=500, min_retencao=30.0, timeout=1)
        return campanha.rodar_combo("EURUSD", "07_GRID_SEPARATE", "BUY_MULTI", args)
    finally:
        campanha.subprocess.Popen = popen_original


reg_pausa = _rodar_combo_com_returncode(base.CODIGO_PAUSA)
checar("CODIGO_PAUSA -> so {'pausado': True}", reg_pausa, {"pausado": True})

reg_erro = _rodar_combo_com_returncode(1)
checar("returncode de erro real NAO diz pausado",
       reg_erro.get("pausado"), None)
checar("returncode de erro real cai no fallback 'sem JSON final'",
       reg_erro.get("erro"), "sem JSON final")


# ============================================================ estado_campanha
# LOCK/PROGRESSO/PAUSA trocados por arquivos temporarios -- nunca tocar no
# estado real da campanha ao vivo enquanto o teste roda.
_tmp_estado = Path(tempfile.mkdtemp())
_lock_original, _prog_original, _pausa2_original = (
    painel.LOCK, painel.PROGRESSO, base.PAUSA)
painel.LOCK = _tmp_estado / "lock.json"
painel.PROGRESSO = _tmp_estado / "progresso.json"
base.PAUSA = _tmp_estado / "pausa.json"
_pid_vivo_original = painel._pid_vivo
_terminal_aberto_original = painel.terminal_aberto
painel._pid_vivo = lambda pid: False  # processo sempre "morto" -- controla
                                       # so via _processo/LOCK no teste
painel.terminal_aberto = lambda: False

try:
    # --- nunca rodou: tudo parado, nada pausado -----------------------------
    e = painel.estado_campanha()
    checar("nunca rodou: rodando False", e["rodando"], False)
    checar("nunca rodou: pausado False", e["pausado"], False)
    checar("nunca rodou: pausando False", e["pausando"], False)

    # --- rodando (PID vivo simulado), sem pedido de pausa --------------------
    painel.LOCK.write_text(json.dumps({"pid": 999999, "modo": "auto"}),
                           encoding="utf-8")
    painel._pid_vivo = lambda pid: True
    e = painel.estado_campanha()
    checar("rodando: rodando True", e["rodando"], True)
    checar("rodando sem pedido: pausando False", e["pausando"], False)
    checar("rodando sem pedido: pausado False", e["pausado"], False)

    # --- pausa pedida, processo AINDA rodando (transicao) --------------------
    base.PAUSA.touch()
    e = painel.estado_campanha()
    checar("pedido feito, ainda rodando: pausando True", e["pausando"], True)
    checar("pedido feito, ainda rodando: pausado False (ainda nao saiu)",
           e["pausado"], False)

    # --- processo honrou a pausa e saiu: PROGRESSO marca estagio=pausado -----
    painel._pid_vivo = lambda pid: False
    painel.PROGRESSO.write_text(
        json.dumps({"symbol": "EURUSD", "sistema": "07_GRID_SEPARATE",
                   "variante": "BUY_MULTI", "estagio": "pausado"}),
        encoding="utf-8")
    e = painel.estado_campanha()
    checar("processo saiu apos pausa: rodando False", e["rodando"], False)
    checar("processo saiu apos pausa: pausado True", e["pausado"], True)
    checar("processo saiu apos pausa: pausando False (ja nao esta vivo)",
           e["pausando"], False)

    # --- ponto-chave do bug que este teste evita: campanha que termina   ----
    # --- SOZINHA (todos os combos feitos) tambem deixa LOCK com PID morto --
    # --- e PAUSA ausente -- so nao pode ser confundida com "pausado" porque
    # --- o ultimo progresso gravado NAO foi o marcador "estagio=pausado".
    base.PAUSA.unlink(missing_ok=True)
    painel.PROGRESSO.write_text(
        json.dumps({"symbol": "EURUSD", "sistema": "07_GRID_SEPARATE",
                   "variante": "BUY_MULTI", "estagio": "5/5 (sobrevivencia)"}),
        encoding="utf-8")
    e = painel.estado_campanha()
    checar("terminou sozinha (nao pausada): pausado False", e["pausado"], False)

finally:
    painel.LOCK, painel.PROGRESSO, base.PAUSA = (
        _lock_original, _prog_original, _pausa2_original)
    painel._pid_vivo = _pid_vivo_original
    painel.terminal_aberto = _terminal_aberto_original
    shutil.rmtree(_tmp_estado, ignore_errors=True)


if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("pausa_campanha: todos os casos passaram")
