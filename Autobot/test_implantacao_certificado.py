# -*- coding: utf-8 -*-
"""Testa a aba de implantacao e o contador do /api/status contra os dois
achados de 2026-09-25 (dono: "limpeza no dashboard se tiver campeao teste"):

  1. Um VALIDADO_ de SWEEP de formula (que nao escreve no ledger) aparecia
     "certificado" com as metricas da campanha oficial do mesmo combo --
     inclusive de uma REPROVADA. Certificado agora exige ledger aprovado +
     relatorio + arquivo IGUAL ao que o ledger registrou.
  2. O contador de aprovados somava linhas cruas do ledger (append-only):
     campeao rebaixado continuava contado como aprovado.

Tudo em pasta temporaria (ledger, relatorios, duas "instalacoes") -- nunca
os arquivos reais da campanha ao vivo.

    python test_implantacao_certificado.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import dashboard_campanha as painel
import wrx_paths

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


def gravar_set(pasta: Path, nome: str, valores: dict[str, str]) -> None:
    corpo = "\r\n".join(f"{k}={v}||0||0||0||N" for k, v in valores.items())
    (pasta / nome).write_text("; teste\r\n" + corpo + "\r\n", encoding="utf-16")


tmp = Path(tempfile.mkdtemp())
original, clone = tmp / "ORIG", tmp / "CLONE"
for pasta in (original, clone):
    (pasta / "MQL5" / "Profiles" / "Tester").mkdir(parents=True)
tester_o = original / "MQL5" / "Profiles" / "Tester"
tester_c = clone / "MQL5" / "Profiles" / "Tester"
relatorios = tmp / "relatorios"
ledger = tmp / "ledger.jsonl"
implantados = tmp / "implantados.json"

oficial = {"TimeFrame": "2", "EntryIndicator": "3", "Take": "7.25"}
sweep = {"TimeFrame": "4", "EntryIndicator": "6", "Take": "5.50"}
linhas = [
    # campeao oficial aprovado (arquivo no CLONE)
    {"simbolo": "XAUUSD", "sistema": "04_SLTP_TRAIL", "variante": "BUY_MULTI",
     "aprovado": True, "relatorio_dir": "XAUUSD__04_SLTP_TRAIL__BUY_MULTI",
     "parametros": oficial, "quando": "2026-09-21T13:53:00"},
    # combo reprovado na oficial, com VALIDADO_ de sweep no ORIGINAL
    {"simbolo": "XAUUSD", "sistema": "11_SIGNAL_ONLY", "variante": "BUY_MULTI",
     "aprovado": False, "relatorio_dir": "XAUUSD__11_SIGNAL_ONLY__BUY_MULTI",
     "parametros": oficial, "quando": "2026-09-21T17:52:00"},
    # aprovado e depois rebaixado (duas linhas, a ultima vence)
    {"simbolo": "GBPUSD", "sistema": "03_TRAIL_ONLY", "variante": "BOTH_MULTI",
     "aprovado": True, "relatorio_dir": "GBPUSD__03_TRAIL_ONLY__BOTH_MULTI",
     "parametros": {}, "quando": "2026-09-19T06:57:00"},
    {"simbolo": "GBPUSD", "sistema": "03_TRAIL_ONLY", "variante": "BOTH_MULTI",
     "aprovado": False, "rebaixado": True, "motivo_rebaixamento": "teste",
     "relatorio_dir": "GBPUSD__03_TRAIL_ONLY__BOTH_MULTI",
     "parametros": {}, "quando": "2026-09-21T19:35:00"},
]
ledger.write_text("\n".join(json.dumps(r) for r in linhas) + "\n",
                  encoding="utf-8")
for r in linhas:
    (relatorios / r["relatorio_dir"]).mkdir(parents=True, exist_ok=True)

# XAUUSD/04: sobra de SWEEP no original + oficial no clone (mesmo nome)
gravar_set(tester_o, "VALIDADO_XAUUSD_04_SLTP_TRAIL_BUY_MULTI.set", sweep)
gravar_set(tester_c, "VALIDADO_XAUUSD_04_SLTP_TRAIL_BUY_MULTI.set", oficial)
# XAUUSD/11: sweep no original, oficial REPROVADA no ledger
gravar_set(tester_o, "VALIDADO_XAUUSD_11_SIGNAL_ONLY_BUY_MULTI.set", oficial)
# GBPUSD/03: arquivo ainda com nome VALIDADO_, ledger ja rebaixou
gravar_set(tester_c, "VALIDADO_GBPUSD_03_TRAIL_ONLY_BOTH_MULTI.set", {})

salvos = (painel.LEDGER, painel.RELATORIOS_DIR, painel.SETS_IMPLANTADOS,
          painel.ready_library.LEDGER, wrx_paths.pastas_de_dados_do_projeto)
painel.LEDGER = ledger
painel.ready_library.LEDGER = ledger
painel.RELATORIOS_DIR = relatorios
painel.SETS_IMPLANTADOS = implantados
wrx_paths.pastas_de_dados_do_projeto = lambda: [("original", original),
                                                ("clone", clone)]
try:
    pares = painel._sets_com_origem()
    por_chave = {linha["chave"]: (linha, origem) for linha, origem in pares}

    checar("um por combo (sem duplicar XAUUSD/04)", len(pares), 3)
    l04, o04 = por_chave["XAUUSD__04_SLTP_TRAIL__BUY_MULTI"]
    checar("XAUUSD/04: o certificado e o do clone", l04["instalacao"], "clone")
    checar("XAUUSD/04: certificado", l04["certificado"], True)
    checar("XAUUSD/04: export/delete apontam pro arquivo do clone",
           o04.parent, tester_c)

    l11, _ = por_chave["XAUUSD__11_SIGNAL_ONLY__BUY_MULTI"]
    checar("XAUUSD/11: reprovado no ledger NAO e certificado",
           l11["certificado"], False)
    checar("XAUUSD/11: motivo", l11["motivo_sem_certificado"]["codigo"],
           "reprovado")

    l03, _ = por_chave["GBPUSD__03_TRAIL_ONLY__BOTH_MULTI"]
    checar("GBPUSD/03 rebaixado: NAO e certificado", l03["certificado"], False)
    checar("GBPUSD/03: motivo", l03["motivo_sem_certificado"]["codigo"],
           "rebaixado")

    # So o sweep, sem o oficial: aprovado no ledger mas arquivo diferente
    (tester_c / "VALIDADO_XAUUSD_04_SLTP_TRAIL_BUY_MULTI.set").unlink()
    so_sweep = {l["chave"]: l for l, _ in painel._sets_com_origem()}
    l04s = so_sweep["XAUUSD__04_SLTP_TRAIL__BUY_MULTI"]
    checar("sweep com ledger aprovado de OUTRA corrida: NAO certificado",
           l04s["certificado"], False)
    checar("sweep: motivo arquivo_diverge",
           l04s["motivo_sem_certificado"]["codigo"], "arquivo_diverge")

    status = json.loads(painel.status("MULTI").body)
    checar("status: uma linha por combo", status["total_feitos"], 3)
    checar("status: rebaixado nao conta como aprovado", status["aprovados"], 1)
    checar("status: 03_TRAIL_ONLY 1 combo, 0 aprovados",
           status["por_sistema"]["03_TRAIL_ONLY"], {"total": 1, "aprovados": 0})
    checar("status: recentes = mais recente primeiro",
           status["recentes"][0]["sistema"], "03_TRAIL_ONLY")
finally:
    (painel.LEDGER, painel.RELATORIOS_DIR, painel.SETS_IMPLANTADOS,
     painel.ready_library.LEDGER, wrx_paths.pastas_de_dados_do_projeto) = salvos
    shutil.rmtree(tmp, ignore_errors=True)

# ===================================== sweep (--calibracao) x relatorio oficial
# O sweep nao pode sobrescrever campanha_relatorios/<combo> -- e a evidencia
# que a aba mostra do campeao oficial.
import optimize_two_stage as ots

tmp2 = Path(tempfile.mkdtemp())
salvos2 = (ots.RELATORIOS_DIR, ots.base.DADOS, ots.MODO_CALIBRACAO)
ots.RELATORIOS_DIR = tmp2 / "relatorios"
ots.base.DADOS = tmp2
(tmp2 / "conf_wrx.htm").write_text("relatorio", encoding="utf-8")
try:
    ots.MODO_CALIBRACAO = False
    checar("campanha: relatorio na pasta do combo",
           ots.arquivar_relatorio("XAUUSD", "04_SLTP_TRAIL", "BUY_MULTI"),
           "XAUUSD__04_SLTP_TRAIL__BUY_MULTI")
    ots.MODO_CALIBRACAO = True
    pasta = ots.arquivar_relatorio("XAUUSD", "04_SLTP_TRAIL", "BUY_MULTI")
    checar("calibracao: relatorio em pasta PROPRIA", pasta,
           "CALIBRACAO__XAUUSD__04_SLTP_TRAIL__BUY_MULTI")
    checar("calibracao: pasta sem barra (endpoint de resumo recusa '/')",
           "/" in (pasta or "") or "\\" in (pasta or ""), False)
finally:
    ots.RELATORIOS_DIR, ots.base.DADOS, ots.MODO_CALIBRACAO = salvos2
    shutil.rmtree(tmp2, ignore_errors=True)

if FALHAS:
    print("implantacao_certificado: FALHOU")
    for f in FALHAS:
        print("  -", f)
    sys.exit(1)
print("implantacao_certificado: todos os casos passaram")
