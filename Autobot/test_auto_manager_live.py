# -*- coding: utf-8 -*-
"""Testa o motor de sugestao do AutoManagerLive sem precisar do MT5 nem do
dashboard -- puro Python sobre dados sinteticos, mesmo espirito de
test_ready_library.py.

    python test_auto_manager_live.py
"""
from __future__ import annotations

import sys

import pandas as pd

import auto_manager_live as aml

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- capital_minimo_classe ---------------------------------------------------
checar("classe direta: metais", aml.capital_minimo_classe("XAUUSD"), 10000)
checar("classe direta: forex", aml.capital_minimo_classe("EURUSD"), 1000)
checar("classe com ponto proprio (nao e sufixo)",
       aml.capital_minimo_classe("BRK.B"), 5000)
checar("sufixo de corretora/HT cai pro radical",
       aml.capital_minimo_classe("EURUSD.HT"), 1000)
checar("sufixo bare de broker (sem separador) -- nao resolvido (limitacao conhecida)",
       aml.capital_minimo_classe("EURUSDm"), None)
checar("simbolo desconhecido", aml.capital_minimo_classe("NAOEXISTE"), None)
checar("regressao: simbolo real nao misclassificado por short ticker (V = Visa stock)",
       aml.capital_minimo_classe("VETUSD"), None)


# --- ordenar_candidatos -------------------------------------------------------
combos = [
    {"chave": "hedge_alta", "sistema": "07_GRID_SEPARATE", "retencao": 90.0, "mc_prob_ruina": 0.01},
    {"chave": "research_baixa", "sistema": "01_SLTP", "retencao": 10.0, "mc_prob_ruina": 0.04},
    {"chave": "research_alta", "sistema": "02_SLTP_ORGANIC", "retencao": 80.0, "mc_prob_ruina": 0.02},
    {"chave": "research_sem_retencao", "sistema": "03_TRAIL_ONLY", "retencao": None, "mc_prob_ruina": None},
]
ordenados = [c["chave"] for c in aml.ordenar_candidatos(combos)]
checar("tier RESEARCH antes de HEDGE, e dentro do tier maior retencao primeiro",
       ordenados,
       ["research_alta", "research_baixa", "research_sem_retencao", "hedge_alta"])


# --- selecionar_ordenado ------------------------------------------------------
# s1 e s2 sobem em linha reta (s2 = 2*s1): correlacao exatamente +1.0.
# s3 desce em linha reta com a mesma soma de s1 (s3 = 6 - s1): correlacao
# exatamente -1.0 com s1 -- negativa e bem-vinda, so a positiva incomoda.
s1 = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
s2 = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])
s3 = pd.Series([5.0, 4.0, 3.0, 2.0, 1.0])
s4_perdedora = pd.Series([-1.0, -2.0, -3.0, -4.0, -5.0])

series = {"s1": s1, "s2": s2, "s3": s3, "s4_perdedora": s4_perdedora}
escolhidas, recusadas = aml.selecionar_ordenado(
    series, ["s1", "s2", "s3", "s4_perdedora"], maximo=4, teto=0.5,
    recuperacao_minima=1.0)
checar("s1 entra (primeiro da ordem)", "s1" in escolhidas, True)
checar("s2 fora (correlacao +1.0 com s1, acima do teto)",
       "s2" in escolhidas, False)
checar("s3 entra (correlacao -1.0 com s1 -- negativa protege)",
       "s3" in escolhidas, True)
checar("s4 nunca entra (resultado negativo)",
       "s4_perdedora" in escolhidas, False)
checar("s4 aparece nas recusadas", any("s4_perdedora" in r for r in recusadas), True)
checar("ordem final respeita a prioridade (s1 antes de s3)",
       escolhidas, ["s1", "s3"])

# maximo limita o tamanho da sugestao mesmo com mais candidatos elegiveis.
escolhidas_lim, _ = aml.selecionar_ordenado(
    series, ["s1", "s2", "s3", "s4_perdedora"], maximo=1, teto=0.5,
    recuperacao_minima=1.0)
checar("maximo=1 devolve so o primeiro", escolhidas_lim, ["s1"])

# --- eligibilidade: recuperacao abaixo do minimo (branch elif nunca testada) ---
s5_baixa_recuperacao = pd.Series([10.0, -8.0, 10.0, -8.0, 1.0])
# resultado = soma = 5.0 (positivo, passa no primeiro filtro)
# acumulado = [10,2,12,4,5], pico = [10,10,12,12,12], dd = min(acumulado-pico) = -8
# recuperacao = 5/8 = 0.625, abaixo do recuperacao_minima=1.0padrão -> rejeitada no segundo filtro
series_b = {"s5_baixa_recuperacao": s5_baixa_recuperacao}
_, recusadas_b = aml.selecionar_ordenado(
    series_b, ["s5_baixa_recuperacao"], maximo=1, teto=0.5, recuperacao_minima=1.0)
checar("recuperacao abaixo do minimo tambem rejeita (resultado positivo, recuperacao baixa)",
       any("recuperacao" in r for r in recusadas_b), True)

# --- correlacao exatamente igual ao teto e aceita (limite inclusivo, <=) ---
sA = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
sB = pd.Series([3.0, 1.0, 5.0, 2.0, 9.0, 4.0, 8.0])
# ambas so tem valores diarios positivos -> cumulativo monotonico -> dd=0 -> recuperacao=inf
# em ambas, elegibilidade trivial garantida independente da correlacao entre elas.
teto_exato = float(pd.DataFrame({"a": sA, "b": sB}).corr().loc["a", "b"])
series_c = {"a": sA, "b": sB}
escolhidas_c, _ = aml.selecionar_ordenado(
    series_c, ["a", "b"], maximo=2, teto=teto_exato, recuperacao_minima=1.0)
checar("correlacao exatamente igual ao teto e aceita (limite inclusivo, <=)",
       escolhidas_c, ["a", "b"])


# --- contas_necessarias -------------------------------------------------------
forex_a = {"chave": "S1", "simbolo": "EURUSD", "sistema": "01_SLTP"}
forex_b = {"chave": "S2", "simbolo": "GBPUSD", "sistema": "02_SLTP_ORGANIC"}
metais_a = {"chave": "S4", "simbolo": "XAUUSD", "sistema": "01_SLTP"}
hedge_a = {"chave": "S3", "simbolo": "XAUUSD", "sistema": "07_GRID_SEPARATE"}

# Caso A: so RESEARCH, uma classe, saldo cobre -> 1 conta.
contas = aml.contas_necessarias([forex_a, forex_b], saldo_conta=1000)
checar("caso A: 1 conta so", len(contas), 1)
checar("caso A: tipo normal", contas[0]["tipo"], "normal")
checar("caso A: capital minimo = 1000 (Forex)", contas[0]["capital_minimo"], 1000)
checar("caso A: os 2 combos na mesma conta",
       sorted(contas[0]["combos"]), ["S1", "S2"])

# Caso B: mistura de tier (HEDGE_ACCOUNT_REQUIRED junto com RESEARCH) -> 2 contas.
contas = aml.contas_necessarias([forex_a, forex_b, hedge_a], saldo_conta=1000)
checar("caso B: 2 contas (hedge isolado)", len(contas), 2)
tipos = sorted(c["tipo"] for c in contas)
checar("caso B: uma hedging, uma normal", tipos, ["hedging", "normal"])
hedge_conta = next(c for c in contas if c["tipo"] == "hedging")
checar("caso B: hedge sozinho na conta de hedging", hedge_conta["combos"], ["S3"])
checar("caso B: capital minimo da hedge = 10000 (Metais)",
       hedge_conta["capital_minimo"], 10000)

# Caso C: capital minimo combinado estoura o saldo -> particiona por classe.
contas = aml.contas_necessarias([forex_a, metais_a], saldo_conta=1000)
checar("caso C: 2 contas normais (uma por classe)", len(contas), 2)
checar("caso C: nenhuma e hedging",
       all(c["tipo"] == "normal" for c in contas), True)
capitais = sorted(c["capital_minimo"] for c in contas)
checar("caso C: capitais 1000 e 10000", capitais, [1000, 10000])

# Caso D: saldo desconhecido (0) -> nao forca split.
contas = aml.contas_necessarias([forex_a, metais_a], saldo_conta=0)
checar("caso D: 1 conta so quando saldo e desconhecido", len(contas), 1)

# Caso E: sufixo de corretora em simbolo (EURUSD.HT) nunca e ignorado.
forex_ht = {"chave": "S9", "simbolo": "EURUSD.HT", "sistema": "01_SLTP"}
contas = aml.contas_necessarias([forex_ht, metais_a], saldo_conta=1000)
checar("caso E: 2 contas por capital insuficiente", len(contas), 2)
todos_combos = sorted([c for conta in contas for c in conta["combos"]])
checar("caso E: nenhum combo desaparece (S9 e S4 presentes)", todos_combos, ["S4", "S9"])
forex_ht_conta = next(c for c in contas if "S9" in c["combos"])
checar("caso E: EURUSD.HT em conta Forex (capital_minimo 1000)", forex_ht_conta["capital_minimo"], 1000)

# Caso F: simbolo genuinamente desconhecido nao desaparece, vai pra uma conta separada.
fake = {"chave": "S10", "simbolo": "ZZZFAKE_NAO_EXISTE", "sistema": "01_SLTP"}
contas = aml.contas_necessarias([fake, metais_a], saldo_conta=1000)
checar("caso F: 2 contas (classe desconhecida + metais)", len(contas), 2)
todos_combos_f = sorted([c for conta in contas for c in conta["combos"]])
checar("caso F: nenhum combo desaparece (S10 e S4 presentes)", todos_combos_f, ["S10", "S4"])
fake_conta = next(c for c in contas if "S10" in c["combos"])
checar("caso F: combo desconhecido em conta separada com capital_minimo None (nao 0.0, que pareceria 'gratis')",
       fake_conta["capital_minimo"], None)

combo_desconhecido_isolado = {"chave": "S11", "simbolo": "ZZZ_NAO_EXISTE_NENHUMA_CLASSE", "sistema": "07_GRID_SEPARATE"}
contas = aml.contas_necessarias([combo_desconhecido_isolado], saldo_conta=1000)
checar("hedge totalmente sem classe resolvivel -> capital_minimo None (nao 0.0, que pareceria 'gratis')",
       contas[0]["capital_minimo"], None)

# Caso G: conta de hedging com DUAS classes (achado 2026-08-09 -- antes usava
# max() e reportava so 10000; capital real pra sustentar as duas posicoes ao
# mesmo tempo e a SOMA, 1000 + 10000).
hedge_forex = {"chave": "S12", "simbolo": "AUDCAD", "sistema": "07_GRID_SEPARATE"}
hedge_metais = {"chave": "S13", "simbolo": "XAUUSD", "sistema": "07_GRID_SEPARATE"}
contas = aml.contas_necessarias([hedge_forex, hedge_metais], saldo_conta=1000)
checar("caso G: 1 conta de hedging so (tier nao particiona por classe)", len(contas), 1)
checar("caso G: capital minimo = soma das 2 classes (1000 + 10000)",
       contas[0]["capital_minimo"], 11000)
checar("caso G: os 2 combos na mesma conta de hedging",
       sorted(contas[0]["combos"]), ["S12", "S13"])

# Caso H: 2 combos de hedging da MESMA classe nao duplicam o capital minimo.
hedge_forex_b = {"chave": "S14", "simbolo": "EURUSD", "sistema": "07_GRID_SEPARATE"}
contas = aml.contas_necessarias([hedge_forex, hedge_forex_b], saldo_conta=1000)
checar("caso H: mesma classe nao soma duas vezes (1000, nao 2000)",
       contas[0]["capital_minimo"], 1000)


# --- montar_sugestoes (usa as mesmas series deterministicas do Task 3) -------
combos_certificados = [
    {"chave": "s1", "simbolo": "EURUSD", "sistema": "01_SLTP",
     "variante": "BUY_MULTI", "retencao": 80.0, "mc_prob_ruina": 0.01},
    {"chave": "s2", "simbolo": "GBPUSD", "sistema": "01_SLTP",
     "variante": "BUY_MULTI", "retencao": 75.0, "mc_prob_ruina": 0.01},
    {"chave": "s3", "simbolo": "USDJPY", "sistema": "02_SLTP_ORGANIC",
     "variante": "BUY_MULTI", "retencao": 70.0, "mc_prob_ruina": 0.01},
]
series_por_chave = {"s1": s1, "s2": s2, "s3": s3}
sugestoes = aml.montar_sugestoes(combos_certificados, series_por_chave,
                                 saldo_conta=1000, teto_correlacao=0.5)
checar("2 sugestoes (s2 fica pra segunda rodada)", len(sugestoes), 2)
checar("numeracao sequencial", [s["numero"] for s in sugestoes], [1, 2])
chaves_sug1 = sorted(c["chave"] for c in sugestoes[0]["combos"])
checar("sugestao 1: s1 + s3 (s2 correlaciona +1.0 com s1)",
       chaves_sug1, ["s1", "s3"])
checar("sugestao 2: so s2, sozinho",
       [c["chave"] for c in sugestoes[1]["combos"]], ["s2"])
checar("toda sugestao tem contas calculadas",
       all("contas" in s and s["contas"] for s in sugestoes), True)
pesos_sug1 = {c["chave"]: c["peso"] for c in sugestoes[0]["combos"]}
checar("pesos da sugestao 1 somam 1.0",
       round(sum(pesos_sug1.values()), 6), 1.0)

# --- carregar_series_certificadas --------------------------------------------
import tempfile
from pathlib import Path as _Path


def _relatorio_sintetico_mt5(pares_tempo_lucro: list[tuple[str, str]]) -> str:
    """Relatorio .htm minimo, mas estruturalmente identico ao formato real
    do MT5 (6 secoes com titulo colspan=13, tabela de Transacoes com 13
    colunas) -- ao contrario do fixture antigo (pd.DataFrame.to_html(), que
    nao reproduzia o formato real e por isso nao pegou o bug do leitor
    anterior)."""
    linhas_trade = "".join(
        f'<tr><td>{tempo}</td><td>{i}</td><td>EURUSD</td><td>buy</td>'
        f'<td>in</td><td>0.01</td><td>1.10000</td><td>{i}</td>'
        f'<td>0.00</td><td>0.00</td><td>{lucro}</td><td>0.00</td><td></td></tr>'
        for i, (tempo, lucro) in enumerate(pares_tempo_lucro, start=1))
    secoes = "".join(
        f'<tr><td colspan="13"><div><b>{nome}</b></div></td></tr>'
        for nome in ("Relatorio", "Corretora", "Configuracao", "Resultados", "Ordens"))
    return (
        f'<html><body><table>{secoes}'
        f'<tr><td colspan="13"><div><b>Transacoes</b></div></td></tr>'
        f'<tr><td>Horario</td><td>Oferta</td><td>Ativo</td><td>Tipo</td>'
        f'<td>Direcao</td><td>Volume</td><td>Preco</td><td>Ordem</td>'
        f'<td>Comissao</td><td>Swap</td><td>Lucro</td><td>Saldo</td>'
        f'<td>Comentario</td></tr>'
        f'{linhas_trade}</table></body></html>')


# --- _trades_do_relatorio isolado -----------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    caminho = _Path(tmp) / "conf_wrx.htm"
    caminho.write_text(_relatorio_sintetico_mt5([
        ("2026.01.01 00:00:00", "5.00"), ("2026.01.01 01:00:00", "5.00"),
        ("2026.01.02 00:00:00", "5.00"), ("2026.01.02 01:00:00", "5.00"),
        ("2026.01.03 00:00:00", "5.00"),
    ]), encoding="utf-16")
    trades = aml._trades_do_relatorio(caminho)
    checar("_trades_do_relatorio: numero de trades extraidos", len(trades), 5)
    checar("_trades_do_relatorio: soma do lucro", float(trades["lucro"].sum()), 25.0)

    caminho_vazio = _Path(tmp) / "vazio.htm"
    caminho_vazio.write_text("<html><body>nada aqui</body></html>", encoding="utf-16")
    checar("_trades_do_relatorio: sem secoes colspan=13 -> None",
           aml._trades_do_relatorio(caminho_vazio), None)


# --- _trades_do_relatorio / carregar_series_certificadas (formato real MT5) --
relatorio_html = _relatorio_sintetico_mt5([
    ("2026.01.01 00:00:00", "10.00"), ("2026.01.01 01:00:00", "-2.00"),
    ("2026.01.02 00:00:00", "8.00"), ("2026.01.02 01:00:00", "-1.00"),
    ("2026.01.03 00:00:00", "9.00"), ("2026.01.03 01:00:00", "3.00"),
])

with tempfile.TemporaryDirectory() as tmp:
    relatorios_dir = _Path(tmp)
    pasta_combo = relatorios_dir / "combo_1"
    pasta_combo.mkdir()
    (pasta_combo / "conf_wrx.htm").write_text(relatorio_html, encoding="utf-16")

    pool = [
        {"chave": "com_relatorio", "certificado": True, "relatorio_dir": "combo_1"},
        {"chave": "sem_relatorio_dir", "certificado": True, "relatorio_dir": None},
        {"chave": "nao_certificado", "certificado": False, "relatorio_dir": "combo_1"},
        {"chave": "arquivo_ausente", "certificado": True, "relatorio_dir": "combo_2"},
    ]
    series = aml.carregar_series_certificadas(pool, relatorios_dir)
    checar("so o combo com relatorio legivel entra (formato real MT5, UTF-16)",
           list(series.keys()), ["com_relatorio"])
    checar("serie tem 3 dias (resample diario)", len(series["com_relatorio"]), 3)
    checar("soma da serie bate com os lucros do fixture (10-2+8-1+9+3)",
           round(float(series["com_relatorio"].sum()), 2), 27.0)


if FALHAS:
    print(f"{len(FALHAS)} falha(s):")
    for f in FALHAS:
        print(f"  {f}")
    sys.exit(1)
print("ok")
