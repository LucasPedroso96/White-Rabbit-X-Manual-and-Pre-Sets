# -*- coding: utf-8 -*-
"""Testa a aritmetica de `_cortar_por_efeito()` e o leitor `parametros_do_set()`
-- Fase 2 da mudanca de direcao (2026-09-13): triagem de sensibilidade tipo
Morris/OAT antes do genetico do Estagio 1, pra nao gastar orcamento em eixos
que isolados quase nao mudam a nota da EA.

Os dois rodam em milissegundos, sem MT5 -- o proprio `triagem_sensibilidade()`
(que RODA passes reais) so e validavel num piloto ao vivo, deliberadamente
fora deste arquivo.

    python test_triagem_sensibilidade.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from optimize_two_stage import _cortar_por_efeito, parametros_do_set

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


def checar_que(rotulo: str, condicao: bool) -> None:
    if not condicao:
        FALHAS.append(rotulo)


# --- _cortar_por_efeito: corta o percentil inferior -------------------------
efeitos = {"a": 100.0, "b": 1.0, "c": 50.0, "d": 0.5}
checar("corta 25% (1 de 4) -- o de menor efeito",
      _cortar_por_efeito(efeitos, 0.25), {"d"})
checar("corta 50% (2 de 4) -- os dois de menor efeito",
      _cortar_por_efeito(efeitos, 0.5), {"d", "b"})
checar("corte 0: nao corta nada", _cortar_por_efeito(efeitos, 0.0), set())
checar("sem efeitos: nao corta nada", _cortar_por_efeito({}, 0.25), set())

# --- efeitos empatados: corte por contagem truncada (int(n*corte_pct)) ----
empatados = {"x": 1.0, "y": 1.0, "z": 1.0}
checar("corte 1/3 (int(3*0.34)=1) de 3 empatados corta exatamente 1",
      len(_cortar_por_efeito(empatados, 0.34)), 1)
checar("corte 0.33 de 3 (int(3*0.33)=0) nao corta nada -- truncamento, nao "
      "arredondamento",
      len(_cortar_por_efeito(empatados, 0.33)), 0)

# --- eixo ausente de `efeitos` nunca e cortado (contrato do chamador) ------
# triagem_sensibilidade() so inclui em `efeitos` o que MEDIU -- um eixo cujo
# passe falhou fica de fora do dict, e portanto de fora do corte tambem.
so_alguns = {"medido_baixo": 0.1}
checar("so o que foi medido entra no corte -- nada mais a verificar aqui "
      "alem do dict de entrada ja vir filtrado",
      _cortar_por_efeito(so_alguns, 1.0), {"medido_baixo"})


# --- parametros_do_set: le start/step/stop de um .set fixture --------------
tmp = Path(tempfile.mkdtemp())
try:
    fixture = tmp / "fixture.set"
    # UTF-16 com \r\n, igual aos .set reais da biblioteca.
    conteudo = (
        "ComEixo=5||1||1||10||Y\r\n"
        "SemEixo=false\r\n"
        "Cravado=2||2||0||2||N\r\n"
    )
    fixture.write_text(conteudo, encoding="utf-16")

    parametros = parametros_do_set(fixture)
    checar("ComEixo tem 5 campos (valor,start,step,stop,flag)",
          parametros["ComEixo"], ["5", "1", "1", "10", "Y"])
    checar("Cravado (start==stop) ainda aparece -- quem decide se e' eixo "
          "de verdade e o chamador (eixos_da_fase1 compara partes[1] != "
          "partes[3])",
          parametros["Cravado"], ["2", "2", "0", "2", "N"])
    checar_que("SemEixo (sem \"||\") NAO aparece -- so formato de 5 campos",
              "SemEixo" not in parametros)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# --- triagem com o terminal VIZINHO escrevendo no arquivo comum (2026-09-26)
# Antes a triagem pulava inteira com outra instalacao ativa (= sempre, com os
# 2 terminais em paralelo) e, quando rodava, lia formulas[-1] -- a linha do
# vizinho. Agora: nota da linha DESTE passe e sem limpar o arquivo comum.
import optimize_two_stage as ots

EFEITO = {"A": 100.0, "B": 50.0, "C": 10.0, "D": 1.0}
estado = {"travar": {}, "limpezas": 0, "arquivo": []}
salvos = {n: getattr(ots, n) for n in (
    "_outra_instancia_mt5_ativa", "parametros_do_set", "campo_da_formula_ativa",
    "reescrever", "passe_unico", "carregar_todas_formulas",
    "limpar_todas_formulas")}
tmp2 = Path(tempfile.mkdtemp())
salvo_dados = ots.base.DADOS


def _passe(*_a, **_k):
    nota = sum(EFEITO[e] for e, v in estado["travar"].items() if v == "alto")
    saldo, trades = 1000.0 + nota + 0.37, 40 + len(estado["arquivo"])
    estado["arquivo"].append({"trades": trades, "profit": saldo - 1000.0,
                              "ProfitFormula": nota})
    # o vizinho escreve DEPOIS do nosso passe terminar
    estado["arquivo"].append({"trades": 999, "profit": 12345.0,
                              "ProfitFormula": 1e9})
    return {"saldo": saldo, "trades": trades}


try:
    ots.base.DADOS = tmp2
    ots._outra_instancia_mt5_ativa = lambda: True
    ots.parametros_do_set = lambda _o: {e: ["x", "baixo", "1", "alto", "Y"]
                                        for e in EFEITO}
    ots.campo_da_formula_ativa = lambda *_a: "ProfitFormula"
    ots.reescrever = lambda _o, _t, _e, travar: estado.update(travar=dict(travar))
    ots.passe_unico = _passe
    ots.carregar_todas_formulas = lambda: list(estado["arquivo"])
    ots.limpar_todas_formulas = lambda: estado.update(
        limpezas=estado["limpezas"] + 1)
    sobra = ots.triagem_sensibilidade(Path("origem.set"), list(EFEITO), {},
                                      "04_SLTP_TRAIL", "XAUUSD", "M1",
                                      "2025.01.01", "2025.12.31", 1000)
    checar("vizinho ativo: corta so o eixo de menor efeito proprio (D)",
           sobra, ["A", "B", "C"])
    checar("vizinho ativo: nunca limpa o arquivo comum", estado["limpezas"], 0)
finally:
    for nome, f in salvos.items():
        setattr(ots, nome, f)
    ots.base.DADOS = salvo_dados
    shutil.rmtree(tmp2, ignore_errors=True)

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("triagem_sensibilidade (aritmetica + parametros_do_set): todos os "
     "casos passaram")
