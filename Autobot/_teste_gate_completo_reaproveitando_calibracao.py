# -*- coding: utf-8 -*-
"""Reaproveita a calibracao JA FEITA (formulas 7 e 13 do 12_GRID_INVERSO/
XAUUSD, achadas na confirmacao original de 27/08 -- parametros travados
reais, sem busca genetica nova) pra exercitar o pipeline de gate COMPLETO
de hoje: gate relativo na mesma janela (remedir_campeao_na_janela) + a
segunda trava no periodo padrao de 3 anos (confirmar_historico_completo).
Pedido do dono: nao refazer a busca do zero quando ja temos o resultado.
Uso interno, apagar depois."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_sets as base
import optimize_two_stage as ots
from mt5_runner import garantir_terminal_livre

garantir_terminal_livre(fechar=True, terminal=base.TERMINAL)

SISTEMA, SIMBOLO, VARIANTE = "12_GRID_INVERSO", "XAUUSD", "BUY_MULTI"
INICIO, FIM, DEPOSITO, PERIODO = "2025.08.25", "2026.08.25", 10000, "M1"

FORMULAS = {
    7: "sweep_12_GRID_INVERSO_XAUUSD_07_ProfitPerTradeAdjustedByDD.log",
    13: "sweep_12_GRID_INVERSO_XAUUSD_13_LevainCompositeScore.log",
}


def carregar_parametros(caminho_log: str) -> dict:
    texto = Path(caminho_log).read_text(encoding="utf-8", errors="replace")
    for linha in reversed(texto.splitlines()):
        if linha.startswith("{"):
            return json.loads(linha)["parametros"]
    raise RuntimeError(f"sem JSON final em {caminho_log}")


origem = base.achar_set(SIMBOLO, SISTEMA, VARIANTE)

print("===== Fase 1: gate relativo na MESMA janela (reusa calibracao real) =====")
params_formula7 = carregar_parametros(FORMULAS[7])
wfo = ots.janelas_wfo(INICIO, FIM)
passo_desafiante = dict(wfo, **params_formula7, MetodoDeEntradawfo="1",
                        InterfaceLanguage="1")
desafiante_mesma_janela = ots._medir_desempenho(
    origem, passo_desafiante, SIMBOLO, PERIODO, INICIO, FIM, DEPOSITO)
print("formula 7 (desafiante), mesma janela do campeao:", desafiante_mesma_janela)

campeao_mesma_janela = ots.remedir_campeao_na_janela(
    SISTEMA, SIMBOLO, VARIANTE, INICIO, FIM, DEPOSITO, PERIODO)
print("campeao (formula 13) re-medido, mesma janela:", campeao_mesma_janela)

ok1, motivos1 = ots.avaliar_gate_relativo(campeao_mesma_janela, desafiante_mesma_janela)
print("\ngate relativo (mesma janela):")
for m in motivos1:
    print(" ", m)
print("aprovado =", ok1)

print("\n===== Fase 2: segunda trava, periodo padrao de 3 anos =====")
ok2, motivos2 = ots.confirmar_historico_completo(
    SISTEMA, SIMBOLO, VARIANTE, origem, passo_desafiante, FIM, DEPOSITO, PERIODO)
print("gate no historico completo (3 anos):")
for m in motivos2:
    print(" ", m)
print("aprovado =", ok2)

print("\n===== VEREDITO FINAL (precisa passar nos dois gates) =====")
print("formula 7 seria promovida?", ok1 and ok2)
