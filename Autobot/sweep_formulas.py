# -*- coding: utf-8 -*-
"""Sweep de formulas para UM sistema, no circuito COMPLETO (com WFO), pra
comparar divergencia/geometria/sobrevivencia de verdade -- nao so lucro
bruto sem WFO (amostra_noite.py). Generaliza os scripts descartaveis usados
pra validar 03_TRAIL_ONLY em 2026-08-23 (_sweep_formulas_trail_xauusd.py /
_sweep_formulas_trail_confirmacao.py), agora reutilizavel pra qualquer
sistema/ativo por quem for rodar a proxima rodada.

O ATIVO importa: cada sistema tem um carater estrategico diferente (trail
persegue tendencia, grid/martingale/d'alembert apostam em reversao a media)
e testar tudo no mesmo par generico (ex.: EURUSD pra tudo) mede o sistema
no ativo ERRADO pro que ele faz. Ver PLANO_DIVISAO_TESTES_FORMULAS.md pro
mapeamento sistema -> ativo compativel e a divisao em 5 partes.

Uso:
    python sweep_formulas.py --sistema 05_BE_TRAIL --simbolo XAUUSD \
        --deposit 10000 --variante BUY_MULTI

    # so um subconjunto de formulas (fase de confirmacao em outro ativo):
    python sweep_formulas.py --sistema 05_BE_TRAIL --simbolo BTCUSD \
        --deposit 2500 --formulas 2,9,11
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_sets as base
from optimize_two_stage import formula_soma_r_compativel

TODAS_FORMULAS = {
    1: "GridSurvivalScore", 2: "Profit", 3: "ProfitWinTradeDD",
    4: "EfficiencyRelativeToDeposit", 5: "AdjustedEfficiencyForGrid",
    6: "ProfitRelativeToDDAndDeposit", 7: "ProfitPerTradeAdjustedByDD",
    8: "SharpeAdjustedByDD", 9: "PessimisticProfit", 10: "ResilienceToDrawdown",
    11: "ReturnUniformity", 12: "SystemRobustness", 13: "LevainCompositeScore",
    14: "SomaR",
    # Porte literal do composite_score() do gate.py do Zeus (2026-08-30) --
    # ver ZeusCompositeScore() no .mq5 e avaliar_gate_relativo() no
    # optimize_two_stage.py, que ja usa a mesma formula pra decidir
    # promocao. Testar ela tambem como criterio de BUSCA (nao so de gate
    # pos-hoc) responde se buscar direto pelo que o gate premia da
    # resultado melhor do que buscar por uma das 14 formulas nativas e so
    # checar composite_score no fim.
    15: "ZeusCompositeScore",
}

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--sistema", required=True)
parser.add_argument("--simbolo", required=True)
parser.add_argument("--deposit", type=int, required=True)
parser.add_argument("--variante", default="BUY_MULTI")
parser.add_argument("--from-data", dest="de", default="2026.05.22")
parser.add_argument("--to-data", dest="ate", default="2026.08.22")
parser.add_argument("--min-retencao", type=float, default=30.0)
parser.add_argument(
    "--min-trades-por-ano", type=float, default=33.0,
    help="taxa anual de trades pro piso derivado (ver optimize_two_stage."
         "piso_trades_da_janela); 33/ano espelha o piso1 ja aceito no "
         "Estagio 1 (max(30, 100//3)). Ponto de partida, nao numero "
         "definitivo -- calibrar por classe de sistema se necessario.")
parser.add_argument("--timeout", type=int, default=3600)
parser.add_argument(
    "--formulas", default="",
    help="lista separada por virgula (ex.: 2,9,11); vazio = todas as 14")
parser.add_argument(
    "--indicador-solo", action="store_true",
    help="liga o Estagio 1.5 (refino do indicador vencedor sozinho) em TODAS "
         "as formulas deste sweep. Ou nenhuma ou todas: metade do sweep com o "
         "estagio e metade sem nao compara formula, compara circuito.")
args = parser.parse_args()

if args.formulas.strip():
    ids = [int(x) for x in args.formulas.split(",")]
    formulas = {i: TODAS_FORMULAS[i] for i in ids}
else:
    formulas = TODAS_FORMULAS

origem = base.achar_set(args.simbolo, args.sistema, args.variante)
checkpoint = Path(
    f"campanha_checkpoints/{args.simbolo}__{args.sistema}__{args.variante}.json")

prefixo = f"sweep_{args.sistema}_{args.simbolo}"
master = Path(f"{prefixo}_master.log")

PADRAO_FORMULA = re.compile(r"selectedFormula=\d+\|\|\d+\|\|1\|\|\d+\|\|N")

# Valor de PRODUCAO do template, lido antes de qualquer reescrita. O sweep
# reescreve `origem` -- o template DA BIBLIOTECA, nao uma copia -- a cada
# formula, e ate 2026-09-03 nunca desfazia isso: os 11 sistemas ja varridos
# ficaram com o selectedFormula da ULTIMA formula testada gravado no template
# (auditado: 11 de 11 fora do FORMULA_POR_SISTEMA, um deles parado na 7 de um
# sweep interrompido). Isso nao e cosmetico -- campo_da_formula_ativa() le
# esse campo pra decidir o corte de elegibilidade, entao a proxima campanha
# de producao naquele ativo passaria a filtrar pela formula do sweep.
formula_original = None
_m = PADRAO_FORMULA.search(origem.read_text(encoding="utf-16"))
if _m:
    formula_original = int(re.search(r"\d+", _m.group(0)).group(0))
    print(f"selectedFormula de producao no template: {formula_original} "
          "(restaurado ao fim do sweep)", flush=True)
else:
    print("AVISO: selectedFormula nao casou o padrao no template -- o sweep "
          "nao vai conseguir trocar a formula nem restaurar o valor "
          "original.", flush=True)


def gravar_formula(indice: int) -> None:
    texto = origem.read_text(encoding="utf-16")
    texto = PADRAO_FORMULA.sub(
        f"selectedFormula={indice}||{indice}||1||{indice}||N", texto)
    origem.write_text(texto, encoding="utf-16")


# Formula 14 (SomaR) so calcula algo em PositionSizeMode Percentage(0) ou
# FixedR(3) -- ComputeRMetrics() no .mq5 devolve false em qualquer outro
# modo, e FormulaSomaR() devolve 0.0 SEMPRE nesse caso (comentario da propria
# EA: "Respeita o piso MinTradesOnTester; demais modos: 0"). Achado ao vivo,
# 2026-09-04 (dono reportou "ontester ta retornando 0" com 07_GRID_SEPARATE/
# AUDNZD, PositionSizeMode=2/FixedLot, testando a formula 14): sem esta
# checagem o sweep gasta um circuito INTEIRO (Estagio 1 sozinho ja ~15-20min)
# guiado por um criterio constante -- genetico sem nenhuma pressao de
# selecao, equivalente a busca aleatoria. PositionSizeMode nao muda entre
# formulas do mesmo sweep (so selectedFormula muda), entao basta ler uma vez.
_m_sizing = re.search(r"PositionSizeMode=(\d+)", origem.read_text(encoding="utf-16"))
POSITION_SIZE_MODE = _m_sizing.group(1) if _m_sizing else None
if not formula_soma_r_compativel(POSITION_SIZE_MODE) and 14 in formulas:
    print(f"AVISO: PositionSizeMode={POSITION_SIZE_MODE!r} (FixedLot/"
          "Monetary) -- a formula 14 (SomaR) sempre devolve 0.0 nesse modo, "
          "vai ser pulada sem gastar circuito.", flush=True)


try:
    with master.open("w", encoding="utf-8") as fm:
        for formula, nome in sorted(formulas.items()):
            titulo = f"===== [{formula}/{len(formulas)}] {nome} ====="
            print(f"\n{titulo}", flush=True)
            fm.write(f"\n{titulo}\n")

            if formula == 14 and not formula_soma_r_compativel(POSITION_SIZE_MODE):
                linha = (f"    pulada: PositionSizeMode={POSITION_SIZE_MODE!r} "
                        "incompativel com SomaR (nem Percentage nem FixedR) "
                        "-- ver aviso no topo do log.")
                print(linha, flush=True)
                fm.write(linha + "\n")
                continue

            gravar_formula(formula)
            checkpoint.unlink(missing_ok=True)

            comando = [
                sys.executable, "optimize_two_stage.py",
                "--symbol", args.simbolo, "--sistema", args.sistema,
                "--variante", args.variante, "--period", "M1",
                "--from", args.de, "--to", args.ate,
                "--deposit", str(args.deposit),
                "--min-retencao", str(args.min_retencao),
                "--min-trades-per-year", str(args.min_trades_por_ano),
                "--fechar-terminal", "--timeout", str(args.timeout)]
            if args.indicador_solo:
                comando.append("--indicador-solo")

            log = Path(f"{prefixo}_{formula:02d}_{nome}.log")
            with log.open("w", encoding="utf-8") as fh:
                subprocess.run(comando, stdout=fh, stderr=subprocess.STDOUT)
            linha = f"    log salvo em {log}"
            print(linha, flush=True)
            fm.write(linha + "\n")
finally:
    # finally, nao no fim do laco: um Ctrl+C ou uma queda no meio do sweep e
    # exatamente o caso que deixou 07_GRID_SEPARATE/AUDNZD parado na formula 7
    # e 03_TRAIL_ONLY/XAUUSD na 13.
    if formula_original is not None:
        gravar_formula(formula_original)
        print(f"\nselectedFormula do template restaurado para "
              f"{formula_original}.", flush=True)

print("\n===== SWEEP COMPLETO =====", flush=True)
