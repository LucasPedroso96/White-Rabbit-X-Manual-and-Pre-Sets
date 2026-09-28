# -*- coding: utf-8 -*-
"""Testa as regras da revisao de metodologia de 2026-09-26 sem o MT5.

  - holdout lacrado: poucos trades = inconclusivo, nunca reprova (TF alto)
  - periodo anterior: piso -5% do deposito
  - retencao com poucas entradas no OOS = inconclusiva (nem aprova nem reprova)
  - cobertura de tick real lida do log do tester
  - MT5 que nao executou teste = erro de infraestrutura, nunca veredito

    python test_metodologia.py
"""
from __future__ import annotations

import sys

import optimize_two_stage as ots

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- holdout lacrado --------------------------------------------------------
h = ots.avaliar_holdout_lacrado
checar("lacrado sem medida", h(None, None, 1000)["veredito"], "sem_medida")
checar("lacrado D1 com 2 trades e prejuizo: inconclusivo, nao reprova",
       h(-80.0, 2, 1000)["veredito"], "inconclusivo")
checar("lacrado sem trade nenhum: inconclusivo", h(0.0, 0, 1000)["veredito"],
       "inconclusivo")
checar("lacrado com amostra e prejuizo: reprova",
       h(-15.0, ots.MIN_TRADES_LACRADO, 1000)["veredito"], "reprovado")
checar("lacrado com amostra e lucro: aprova", h(40.0, 30, 1000)["veredito"],
       "aprovado")
checar("lacrado zero a zero com amostra: nao e prejuizo",
       h(0.0, 12, 1000)["veredito"], "aprovado")

# --- periodo anterior: -5% --------------------------------------------------
pa = ots.avaliar_periodo_anterior
checar("PA -10% (US500 SELL): reprova agora", pa(-1000.0, 40, 10000)[0], False)
checar("PA -4%: passa", pa(-400.0, 40, 10000)[0], True)
checar("PA amostra pequena: nao avalia", pa(-5000.0, 3, 10000)[0], True)
checar("PA sem medida: nao avalia", pa(None, None, 10000)[0], True)

# --- retencao inconclusiva --------------------------------------------------
ok, mot = ots.veredito(5.0, -40.0, 30, entradas_oos=4)
checar("poucas entradas OOS + retencao ruim: nao reprova", ok, True)
checar("poucas entradas OOS: motivo diz inconclusiva",
       any("INCONCLUSIVA" in m for m in mot), True)
ok, _ = ots.veredito(5.0, -40.0, 30, entradas_oos=ots.MIN_ENTRADAS_OOS_RETENCAO)
checar("amostra suficiente + retencao ruim: reprova", ok, False)
ok, _ = ots.veredito(5.0, None, 30, entradas_oos=3,
                     motivo_retencao="In-Sample quase sem lucro (2.63)")
checar("IS quase sem lucro continua reprovando mesmo com pouca entrada", ok, False)
ok, _ = ots.veredito(45.0, 80.0, 30, entradas_oos=2)
checar("inconclusiva nao salva divergencia reprovada", ok, False)
ok, _ = ots.veredito(5.0, 80.0, 30, entradas_oos=None)
checar("sem contagem de entradas (.ex5 antigo): regra antiga", ok, True)

# --- cobertura de tick real --------------------------------------------------
LOG = ("Tester\tXAUUSD: ticks data begins from 2025.03.01 00:00\n"
       "Tester\tXAUUSD,M1 (RoboForex-ECN): testing of Experts\\X.ex5 from "
       "2024.09.01 00:00 to 2025.09.01 00:00\n")
checar("cobertura: metade do ano com tick real",
       ots.cobertura_tick_real(LOG), 50.4)
checar("cobertura: tick desde antes do teste = 100%",
       ots.cobertura_tick_real(LOG.replace("2025.03.01", "2020.01.01")), 100.0)
checar("cobertura: tick so depois do fim = 0%",
       ots.cobertura_tick_real(LOG.replace("2025.03.01", "2026.01.01")), 0.0)
checar("cobertura: log sem as linhas -> None",
       ots.cobertura_tick_real("final balance 100"), None)

# --- terminal que nao executou ----------------------------------------------
LIVEUPDATE = ("LiveUpdate\tfailed to create copy of terminal64.exe [32]\n"
              "Terminal\tcannot load config otim.ini\n")
try:
    ots.conferir_execucao(LIVEUPDATE, "a otimizacao")
    FALHAS.append("LiveUpdate sem teste: deveria levantar TerminalNaoExecutou")
except ots.TerminalNaoExecutou:
    pass
try:
    ots.conferir_execucao(LOG + "Core 01\tautomatical testing finished\n",
                          "o passe unico")
except ots.TerminalNaoExecutou:
    FALHAS.append("log com teste iniciado nao pode levantar erro")

# --- piso de trades por TF (mapa do Levain) -----------------------------------
p = ots.piso_trades_tf
SLTP = {"AtivarStop": "true", "AtivarTake": "true", "AtivarTrailATR": "false",
        "GridMode": "0", "TimeFrame": "4", "ATR_TimeFrame": "5"}
checar("ATR declarado: vale o TF do ATR (H4=20), nao o do indicador (H1)",
       p(SLTP)[0], 20)
SINAL = dict(SLTP, AtivarStop="false", AtivarTake="false")
checar("sem ATR (11_SIGNAL_ONLY): vale o TF do indicador (H1=35)", p(SINAL)[0], 35)
checar("grade ligada conta como ATR declarado",
       p(dict(SINAL, GridMode="1"))[0], 20)
checar("filtro de volatilidade ATR conta como declarado",
       p(dict(SINAL, EntradaATR="true"))[0], 20)
checar("ATR mais rapido que a entrada: vale a entrada (M15 + ATR M5 -> 80)",
       p(dict(SLTP, TimeFrame="2", ATR_TimeFrame="1"))[0], 80)
checar("ATR mais lento que a entrada: vale o ATR (M5 + ATR H1 -> 35)",
       p(dict(SLTP, TimeFrame="1", ATR_TimeFrame="4"))[0], 35)
M1 = dict(SLTP, TimeFrame="0", ATR_TimeFrame="0")
checar("M1 continua exigente (200)", p(M1)[0], 200)
checar("D1 = 12, W1 = 8", (p(dict(SLTP, ATR_TimeFrame="6"))[0],
                          p(dict(SLTP, ATR_TimeFrame="7"))[0]), (12, 8))
CANDLES = {"AtivarStop": "false", "AtivarTake": "false", "CandleTF1": "1",
           "CandleTF2": "4", "CandleTF3": "2"}
checar("Candles sem ATR: maior slot (H1=35)", p(CANDLES)[0], 35)
checar("sem TF nenhum: 30 (default do Levain)", p({})[0], 30)
checar("estagio 1 (1/3, chao 8): M1 -> 66, H4 -> 8",
       (p(M1, 3)[0], p(SLTP, 3)[0]), (66, 8))

# escolher_com_piso_tf: o piso e da LINHA (cada passe tem o seu TF)
CAB = ["Pass", "Profit", "Profit Factor", "Trades", "Equity DD %",
       "ATR_TimeFrame"]
LINHAS = [["1", "500", "1.5", "40", "10", "0"],   # M1 com 40 trades: fora
          ["2", "400", "1.5", "40", "10", "5"],   # H4 com 40 trades: dentro
          ["3", "300", "1.5", "210", "10", "0"]]  # M1 com 210: dentro
ok = ots.escolher_com_piso_tf(CAB, LINHAS, M1, 1.2)
checar("piso por linha: M1 com 40 fora, H4 com 40 e M1 com 210 dentro",
       sorted(x[0] for x in ok), ["2", "3"])
checar("piso fixo explicito mantem o comportamento antigo",
       sorted(x[0] for x in ots.escolher_com_piso_tf(CAB, LINHAS, M1, 1.2,
                                                     piso_fixo=100)), ["3"])

# --- cobertura (2026-09-26): eixos resgatados, pendente, inertes do 11 --------
for eixo in ("TrailSoLucro", "PyramidTrailSoLucro", "PyramidLevelOnlyInProfit",
             "ReversalExitMode"):
    checar(f"{eixo} travado pelo vencedor do Estagio 1 (ESCRITA)",
           eixo in ots.ESCRITA, True)
for eixo in ("PeriodoBaselineATR", "MultiplicadorATR"):
    checar(f"{eixo} refinado no Estagio 2 (NUMEROS)", eixo in ots.NUMEROS, True)
checar("TrailSoLucro fecha atras de trailing cravado off",
       ots.GATES.get("TrailSoLucro"), "AtivarTrailATR")
reot = ots.eixos_reotimizaveis("04_SLTP_TRAIL", None)
checar("pendente nunca reabre no Estagio 2",
       [e for e in ots.EIXOS_PENDENTE if e in reot], [])
checar("baseline do filtro ATR reabre no Estagio 2", "MultiplicadorATR" in reot,
       True)
reot11 = ots.eixos_reotimizaveis("11_SIGNAL_ONLY", None)
checar("11: Multiplicador e PeriodoATR inertes no Estagio 2",
       ("Multiplicador" in reot11, "PeriodoATR" in reot11), (False, False))
checar("04: Multiplicador continua reotimizavel",
       "Multiplicador" in reot, True)

# --- regra de trader solo (2026-09-27): 4 criterios, o resto informa --------
d = ots.decidir_trader
# grid USDCAD 07 BUY de 27/09: so a WFA reprovava -- agora aprova
g = d(7.0, True, None, 1274.65, 596, 144.90, 94, None, 1000)
checar("grid USDCAD 07: realista, sobrevive, lucra no nunca visto -> aprova",
       (g["aprovado"], g["nunca_visto"]["veredito"]), (True, "aprovado"))
# XAUUSD 05 BE_TRAIL: DD 57.8% nos 3 anos
x5 = d(2.5, None, 57.8, -622.90, 272, 186.68, 40, None, 10000)
checar("DD 57.8% > 40%: reprova no drawdown", x5["reprovado_em"], "drawdown")
checar("... e o nunca visto somado (-436) tambem falha",
       "nunca_visto" in x5["falhas"], True)
# lacrado pequeno negativo compensado pelo anterior: aprova
checar("anterior +500 e 90 dias -210 somados: aprova",
       d(16.6, None, 18.5, 500.0, 200, -210.97, 24, None, 10000)["aprovado"], True)
checar("divergencia acima de 30% reprova",
       d(31.0, None, 10.0, 100.0, 50, 10.0, 10, None, 1000)["reprovado_em"],
       "divergencia")
checar("divergencia nao medida reprova",
       d(None, None, None, None, None, None, None, None, 1000)["reprovado_em"],
       "divergencia")
checar("nunca visto com poucos trades: inconclusivo, nao reprova",
       d(5.0, None, 10.0, -50.0, 3, -20.0, 2, None, 1000)["aprovado"], True)
checar("sem nenhuma medida do nunca visto: nao reprova",
       d(5.0, None, 10.0, None, None, None, None, None, 1000)["aprovado"], True)
checar("sobrevivencia falhou: reprova",
       d(5.0, False, None, 100.0, 50, 10.0, 10, None, 1000)["reprovado_em"],
       "sobrevivencia")
checar("pior que o campeao: reprova",
       d(5.0, None, 10.0, 100.0, 50, 10.0, 10, False, 1000)["reprovado_em"],
       "gate_relativo")

# --- 13_OCO_ROMPIMENTO (2026-09-28): a pendente e o proprio sistema --------
r13 = ots.eixos_reotimizaveis("13_OCO_ROMPIMENTO", None)
checar("13: distancia, expiracao e faixa refinadas no Estagio 2",
       [e for e in ("PendingDistanciaATR", "PendingExpiracaoBarras",
                    "PendingFaixaBarras") if e in r13],
       ["PendingDistanciaATR", "PendingExpiracaoBarras", "PendingFaixaBarras"])
checar("demais sistemas continuam sem a pendente no Estagio 2",
       "PendingFaixaBarras" in ots.eixos_reotimizaveis("04_SLTP_TRAIL", None),
       False)
checar("13: hora da sessao decidida no Estagio 1 (ESCRITA)",
       "PendingHoraSessao" in ots.ESCRITA, True)
import campanha  # noqa: E402
checar("13: so o arquivo BOTH, com ou sem modo economico",
       (campanha.variantes("13_OCO_ROMPIMENTO"),
        campanha.variantes("04_SLTP_TRAIL")),
       (["BOTH_MULTI"], ["BUY_MULTI", "SELL_MULTI"]))

# --- alertas de trader (2026-09-28): robustez e consistencia, nao reprovam --
checar("vizinhos de inteiro: +-1 no minimo", ots.vizinhos_parametro("14"),
       ["13", "15"])
checar("vizinhos de decimal: +-10%", ots.vizinhos_parametro("3.5"),
       ["3.15", "3.85"])
checar("zero/None/texto nao tem vizinho",
       (ots.vizinhos_parametro("0"), ots.vizinhos_parametro(None),
        ots.vizinhos_parametro("abc")), ([], [], []))
checar("robustez: 1 de 4 vizinhos lucrando = pico isolado",
       ots.resumir_robustez([{"lucro": 5}, {"lucro": -1}, {"lucro": -2},
                             {"lucro": -3}])["alerta"], True)
checar("robustez: 3 de 4 lucrando = plato",
       ots.resumir_robustez([{"lucro": 5}, {"lucro": 1}, {"lucro": -2},
                             {"lucro": 3}])["alerta"], False)
checar("consistencia: lucro espalhado = ok",
       ots.resumir_consistencia([{"lucro": 100}, {"lucro": -20},
                                 {"lucro": 50}, {"lucro": 60}])["alerta"], False)
checar("consistencia: um trimestre com 99% do lucro = concentrado",
       ots.resumir_consistencia([{"lucro": 1000}, {"lucro": -20},
                                 {"lucro": -5}, {"lucro": 10}])["alerta"], True)

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("metodologia: todos os casos passaram")
