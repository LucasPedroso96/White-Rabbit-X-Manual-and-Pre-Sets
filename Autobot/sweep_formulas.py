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
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_sets as base
from generate_system_sets import FORMULA_POR_SISTEMA
from mt5_watchdog import rodar_com_watchdog
from optimize_two_stage import formula_soma_r_compativel, limpar_checkpoint_estagio1

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
parser.add_argument("--from-data", dest="de", default=None,
                    help="default: hoje menos 90 dias -- mesmo espirito de "
                         "campanha.anos_atras(), nunca uma data cravada que "
                         "fica mais defasada a cada dia (achado 2026-08-06)")
parser.add_argument("--to-data", dest="ate", default=None,
                    help="default: hoje")
parser.add_argument("--min-retencao", type=float, default=30.0)
parser.add_argument(
    "--min-trades-por-ano", type=float, default=33.0,
    help="taxa anual de trades pro piso derivado (ver optimize_two_stage."
         "piso_trades_da_janela); 33/ano espelha o piso1 ja aceito no "
         "Estagio 1 (max(30, 100//3)). Ponto de partida, nao numero "
         "definitivo -- calibrar por classe de sistema se necessario.")
parser.add_argument("--timeout", type=int, default=3600)
parser.add_argument(
    "--timeout-geometria-min", type=float, default=10.0,
    help="teto do Estagio 3.5 (geometria em tick real) por formula. Achado "
         "2026-09-20: em XAUUSD ele levaria ~6h e era morto em 60 min com "
         "zero resultado em 8 de 8 formulas do 04_SLTP_TRAIL; 10 min da o "
         "mesmo resultado (geometria de OHLC mantida) sem gastar 1h por "
         "formula. Onde o 3.5 termina de verdade (EURUSD/BTCUSD: 4-18 min) "
         "suba este valor.")
parser.add_argument(
    "--formulas", default="",
    help="lista separada por virgula (ex.: 2,9,11); vazio = todas as 14")
parser.add_argument(
    "--indicador-solo", action="store_true",
    help="liga o Estagio 1.5 (refino do indicador vencedor sozinho) em TODAS "
         "as formulas deste sweep. Ou nenhuma ou todas: metade do sweep com o "
         "estagio e metade sem nao compara formula, compara circuito.")
parser.add_argument(
    # Achado ao vivo, 2026-09-19 (dono: "veja se nao e log ou print"): 15 min
    # dava falso positivo -- cada rodada do genetico no Estagio 1 e UMA
    # chamada bloqueante so, sem print nenhum ate ela terminar, e o proprio
    # optimize_two_stage.py ja documentava "pode ser 45min+ em grid" antes
    # de eu mexer em qualquer coisa. 15 min matava rodada legitima no meio
    # achando que travou -- foi isso que fez 04_SLTP_TRAIL/07_GRID_SEPARATE
    # perderem quase toda formula sem travamento real nenhum. 75 min cobre
    # o pior caso documentado (45min) com folga (contencao de CPU externa
    # pode alongar isso ainda mais) sem deixar de pegar travamento de
    # verdade (custa so 75min de espera, nao dias).
    "--watchdog-minutos", type=float, default=75.0,
    help="mata e considera travado um circuito cujo log ficar esse tanto "
         "de minutos SEM CRESCER (ver mt5_watchdog.py). 0 desliga o "
         "watchdog (comportamento antigo, subprocess.run sem teto). Uma "
         "rodada do Estagio 1 e uma chamada bloqueante sem print ate "
         "terminar -- 45min+ e documentado como normal em grid, entao o "
         "teto tem que ficar bem acima disso pra nao matar rodada legitima "
         "achando que travou.")
args = parser.parse_args()
if args.de is None:
    args.de = (datetime.now() - timedelta(days=90)).strftime("%Y.%m.%d")
if args.ate is None:
    args.ate = datetime.now().strftime("%Y.%m.%d")

if args.formulas.strip():
    ids = [int(x) for x in args.formulas.split(",")]
    formulas = {i: TODAS_FORMULAS[i] for i in ids}
else:
    formulas = TODAS_FORMULAS

origem = base.achar_set(args.simbolo, args.sistema, args.variante)

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
esperado = FORMULA_POR_SISTEMA.get(args.sistema)
if _m:
    formula_original = int(re.search(r"\d+", _m.group(0)).group(0))
    if esperado is not None and formula_original != esperado:
        # Achado ao vivo, 2026-09-14: o `finally` que restaura o valor la
        # embaixo NAO roda se o processo for morto a forca (Stop-Process
        # -Force, TaskStop no processo pai) -- o kill nao e uma excecao
        # Python, e o template fica preso na ULTIMA formula testada antes
        # do kill. Um relancamento sem este cross-check leria esse valor
        # sujo como se fosse "producao" e prometeria restaurar o numero
        # ERRADO ao fim -- corrompeu 04_SLTP_TRAIL (leu 1, era 5) e
        # 12_GRID_INVERSO (leu 1, era 2) de verdade nesta sessao antes de
        # eu notar e corrigir a mao. FORMULA_POR_SISTEMA e a fonte de
        # verdade; vence quando os dois discordam.
        print(f"AVISO: selectedFormula no template ({formula_original}) "
              f"diverge de FORMULA_POR_SISTEMA[{args.sistema!r}] "
              f"({esperado}) -- template provavelmente sujo por um sweep "
              f"anterior morto a forca. Usando {esperado} (FORMULA_POR_"
              "SISTEMA) como o valor de producao.", flush=True)
        formula_original = esperado
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
                # Escreve o proprio log da formula (nao so o master) --
                # achado 2026-09-04: sem isso, uma formula pulada nao deixa
                # NENHUM arquivo, e sweep_*_14_SomaR.log de uma corrida
                # ANTIGA (de antes desta checagem existir, com um REPROVADO
                # por busca as cegas) fica parecendo o resultado atual pra
                # quem le os logs depois -- exatamente o que confundiu a
                # auditoria original. Sobrescreve com o motivo real.
                log = Path(f"{prefixo}_{formula:02d}_{nome}.log")
                log.write_text(
                    f"    PULADA: PositionSizeMode={POSITION_SIZE_MODE!r} "
                    "(FixedLot/Monetary) incompativel com a formula 14 "
                    "(SomaR) -- ComputeRMetrics() no .mq5 exige "
                    "RiscoRFixo(3) ou Porcentagem(0), devolve false em "
                    "qualquer outro modo, e FormulaSomaR() sai sempre 0.0 "
                    "nesse caso. Nao ha sinal pra buscar; nao gasto "
                    "circuito. Achado ao vivo 2026-09-04 -- ver "
                    "formula_soma_r_compativel() em optimize_two_stage.py.\n",
                    encoding="utf-8")
                continue

            gravar_formula(formula)
            # Limpa pela funcao real (nao um caminho fixo montado a mao):
            # o checkpoint do Estagio 1 mudou de um .json solto para uma
            # pasta (campanha_checkpoints/<combo>/rodada_N.parquet +
            # meta.json) em 2026-09-12 -- um unlink() no caminho antigo
            # virava no-op e deixava o checkpoint da FORMULA ANTERIOR
            # vazar pra proxima, contaminando o sweep entre formulas.
            limpar_checkpoint_estagio1(args.simbolo, args.sistema, args.variante)

            comando = [
                # -u: sem isso o stdout do filho fica bufferizado e o
                # watchdog (que mede progresso pelo CRESCIMENTO do arquivo
                # de log) veria o arquivo parado mesmo com o circuito
                # avancando normal -- falso-positivo de travamento.
                sys.executable, "-u", "optimize_two_stage.py",
                "--symbol", args.simbolo, "--sistema", args.sistema,
                "--variante", args.variante, "--period", "M1",
                "--from", args.de, "--to", args.ate,
                "--deposit", str(args.deposit),
                "--min-retencao", str(args.min_retencao),
                "--min-trades-per-year", str(args.min_trades_por_ano),
                "--fechar-terminal", "--timeout", str(args.timeout),
                "--timeout-geometria", str(int(args.timeout_geometria_min * 60)),
                # Pesquisa, nao entrega: CALIBRACAO_ em vez de VALIDADO_ e
                # relatorio proprio -- nunca sobrescreve o campeao real nem
                # a evidencia dele (achado 2026-09-25, "campeao teste" no
                # dashboard).
                "--calibracao"]
            if args.indicador_solo:
                comando.append("--indicador-solo")

            log = Path(f"{prefixo}_{formula:02d}_{nome}.log")
            if args.watchdog_minutos > 0:
                # Ate 2 tentativas: travamento pode ser transitorio (achado
                # ja visto com o agente do tester, ver passe_unico()). Na
                # segunda vez, desiste da formula (nao do sistema inteiro)
                # e segue pra proxima -- mesmo padrao do pulo da formula 14.
                status = rodar_com_watchdog(
                    comando, log, sem_progresso_max=args.watchdog_minutos * 60)
                if status == "travado":
                    aviso = (f"    TRAVADO ({args.watchdog_minutos:.0f} min "
                            "sem o log crescer) -- repetindo uma vez")
                    print(aviso, flush=True)
                    fm.write(aviso + "\n")
                    status = rodar_com_watchdog(
                        comando, log,
                        sem_progresso_max=args.watchdog_minutos * 60)
                if status == "travado":
                    linha = (f"    PULADA: travou 2x seguidas (>="
                            f"{2 * args.watchdog_minutos:.0f} min sem "
                            "progresso no log) -- log em " + str(log) +
                            ". Se isto se repetir em VARIAS formulas deste "
                            "sistema, o problema provavelmente e o ativo "
                            f"({args.simbolo}), nao a formula: considere "
                            "relancar este sistema com --simbolo num par "
                            "mais leve (ex.: EURUSD).")
                    print(linha, flush=True)
                    fm.write(linha + "\n")
                    continue
            else:
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
