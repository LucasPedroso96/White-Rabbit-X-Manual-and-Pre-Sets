# -*- coding: utf-8 -*-
"""Testa as conferencias de testar_pendentes.py SEM MT5: relatorio e barras
sinteticos com resposta conhecida -- inclusive ordens ERRADAS de proposito, pra
provar que o conferidor reprova o que tem que reprovar.

    python test_testar_pendentes.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta

import pandas as pd

import testar_pendentes as tp

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- relatorio real (trecho do XAUUSD 04 BUY com Limit) ----------------------
HTML = """<table>
<tr><th colspan="11">Ordens</th></tr>
<tr><th>Horário da Abertura</th><th>Ordem</th><th>Ativo</th><th>Tipo</th><th>Volume</th>
<th>Preço</th><th>S / L</th><th>T / P</th><th>Horário</th><th>Estado</th><th>Comentário</th></tr>
<tr><td>2025.07.03 01:15:00</td><td>2</td><td>XAUUSD</td><td>buy limit</td><td>0.16 / 0.16</td>
<td>3360.54</td><td>3354.54</td><td>3369.56</td><td>2025.07.03 01:15:00</td><td>filled</td>
<td>04-MUL Buy/RFixo/Pend</td></tr>
<tr><td>2025.09.03 17:15:00</td><td>46</td><td>XAUUSD</td><td>buy limit</td><td>0.05 / 0</td>
<td>3553.52</td><td>3533.68</td><td>3584.42</td><td>2025.09.03 17:30:00</td><td>canceled</td>
<td>04-MUL Buy/RFixo/Pend</td></tr>
<tr><th colspan="1">Transações</th></tr>
<tr><td>2025.07.03 00:00:00</td><td>1</td><td></td><td>balance</td><td></td><td></td><td></td><td></td>
<td>0.00</td><td>0.00</td><td>10 000.00</td><td>10 000.00</td><td></td></tr>
<tr><td>2025.07.03 01:15:00</td><td>2</td><td>XAUUSD</td><td>buy</td><td>in</td><td>0.16</td><td>3360.49</td>
<td>2</td><td>-1.08</td><td>0.00</td><td>0.00</td><td>9 998.92</td><td>04-MUL Buy/RFixo/Pend</td></tr>
</table>"""
ordens, deals = tp.parse_html(HTML)
checar("parse: 2 ordens", len(ordens), 2)
checar("parse: 2 deals (balance incluso)", len(deals), 2)
checar("parse: tipo/preco", (ordens[0]["tipo"], ordens[0]["preco"]), ("buy limit", 3360.54))
checar("parse: SL/TP", (ordens[0]["sl"], ordens[0]["tp"]), (3354.54, 3369.56))
checar("parse: volume pedido/executado", (ordens[1]["vol"], ordens[1]["vol_exec"]), (0.05, 0.0))
checar("parse: estado e fim", (ordens[1]["estado"], ordens[1]["fim"]),
       ("canceled", datetime(2025, 9, 3, 17, 30)))
checar("parse: deal de entrada liga na ordem",
       (deals[1]["direcao"], deals[1]["ordem"], deals[1]["preco"]), ("in", 2, 3360.49))
checar("parse: saldo com separador de milhar", deals[0]["saldo"], 10000.0)

# --- barras sinteticas: M15 com ATR constante = 2 ----------------------------
T0 = datetime(2026, 8, 3, 0, 0)                      # segunda-feira
N15 = 60
m15 = pd.DataFrame({
    "time": [T0 + timedelta(minutes=15 * i) for i in range(N15)],
    "open": [100.0 + i for i in range(N15)],
    "high": [101.0 + i for i in range(N15)],
    "low": [99.0 + i for i in range(N15)],
    "close": [100.5 + i for i in range(N15)]}).set_index("time")
m1_rows = []
for i in range(N15):
    for j in range(15):
        m1_rows.append({"time": T0 + timedelta(minutes=15 * i + j),
                        "open": 100.0 + i, "high": 101.0 + i, "low": 99.0 + i,
                        "close": 100.0 + i})
m1 = pd.DataFrame(m1_rows).set_index("time")
barras = tp.Barras({"M15": m15, "M1": m1})
INFO = {"tick": 0.01, "vol_step": 0.01, "vol_min": 0.01, "contrato": 100.0}
PARAMS = {"EntryOrderType": "2", "PendingReferencia": "0", "PendingDistanciaATR": "0.5",
          "PendingExpiracaoBarras": "3", "TimeFrame": "2", "ATR_TimeFrame": "2",
          "PeriodoATR": "14", "MaxLongTrades": "1", "MaxShortTrades": "0",
          "PositionSizeMode": "3", "PositionSizeValue": "1", "CapitalBaseR": "10000",
          "AtivarStop": "true", "Stop": "2", "VelaStop": "1", "AtivarTake": "true",
          "Take": "3", "VelaTake": "1"}

# ATR fechado = 2; da barra em formacao fica entre (2*13+0.5)/14 e 2
checar("atr fechado", round(barras.atr_fechado("M15", 14, 30), 6), 2.0)
t_ordem = T0 + timedelta(minutes=15 * 30)           # abertura da barra 30
lo, hi = barras.atr_intervalo("M15", 14, t_ordem, 0)
checar("atr em formacao: intervalo", (round(lo, 4), round(hi, 4)), (round((26 + 0.5) / 14, 4), 2.0))
checar("atr shift 1 exato", barras.atr_intervalo("M15", 14, t_ordem, 1), (2.0, 2.0))


def ordem(tipo, preco, sl, tp, t=t_ordem, fim=None, estado="filled", vol=0.0, n=1,
          coment="04-MUL Buy/RFixo/Pend"):
    return {"abertura": t, "ordem": n, "simbolo": "XAUUSD", "tipo": tipo, "vol": vol,
            "vol_exec": vol, "preco": preco, "sl": sl, "tp": tp,
            "fim": fim or t + timedelta(seconds=30), "estado": estado, "comentario": coment}


# fechamento da barra 29 = 129.5; buy limit a 0.5 ATR abaixo => ~128.5
def rodar(checagem, *a):
    r = tp.Resultado()
    checagem(*a, r)
    return r


boa = ordem("buy limit", 128.5, 124.5, 134.5)          # SL = 2*ATR, TP = 3*ATR
ruim_preco = ordem("buy limit", 129.5, 125.5, 135.5)   # esqueceu o k x ATR
r = rodar(tp.checar_preco, [boa], PARAMS, barras, 0.01)
checar("preco certo passa", r.falhas, [])
r = rodar(tp.checar_preco, [ruim_preco], PARAMS, barras, 0.01)
checar("preco sem o k x ATR reprova", len(r.falhas), 1)
# extremo: buy limit usa a MINIMA da barra 29 (128) - 0.5*2 = 127
extremo = dict(PARAMS, PendingReferencia="1")
r = rodar(tp.checar_preco, [ordem("buy limit", 127.0, 123.0, 133.0)], extremo, barras, 0.01)
checar("limit no extremo (minima) passa", r.falhas, [])
r = rodar(tp.checar_preco, [ordem("buy limit", 129.0, 125.0, 135.0)], extremo, barras, 0.01)
checar("limit no extremo com a MAXIMA reprova", len(r.falhas), 1)
# buy stop acima: maxima da barra 29 (130) + 1.0
stop = dict(PARAMS, EntryOrderType="1", PendingReferencia="1")
r = rodar(tp.checar_preco, [ordem("buy stop", 131.0, 127.0, 137.0)], stop, barras, 0.01)
checar("stop no extremo (maxima + k ATR) passa", r.falhas, [])
# sell stop abaixo: minima (128) - 1.0
sell = dict(stop, MaxLongTrades="0", MaxShortTrades="1")
r = rodar(tp.checar_preco, [ordem("sell stop", 127.0, 131.0, 121.0)], sell, barras, 0.01)
checar("sell stop no extremo (minima - k ATR) passa", r.falhas, [])
r = rodar(tp.checar_preco, [ordem("sell stop", 131.0, 135.0, 125.0)], sell, barras, 0.01)
checar("sell stop acima do mercado reprova", len(r.falhas), 1)


# --- sem M1 (janelas antigas: o terminal so guarda ~100 mil barras de M1) ---------
barras_sem_m1 = tp.Barras({"M15": m15})
r = rodar(tp.checar_preco, [boa], PARAMS, barras_sem_m1, 0.01)
checar("sem M1: preco certo (k>0) passa", r.falhas, [])
r = rodar(tp.checar_preco, [ruim_preco], PARAMS, barras_sem_m1, 0.01)
checar("sem M1: preco errado reprova", len(r.falhas), 1)

# --- SL/TP relativos ao preco DA ORDEM ---------------------------------------
r = rodar(tp.checar_sl_tp, [boa], PARAMS, barras, 0.01)
checar("SL/TP relativos ao preco da ordem passam", r.falhas, [])
do_mercado = ordem("buy limit", 128.5, 127.0, 131.0)   # SL/TP colados no mercado
r = rodar(tp.checar_sl_tp, [do_mercado], PARAMS, barras, 0.01)
checar("SL/TP medidos do mercado (nao da ordem) reprovam", len(r.falhas), 1)
r = rodar(tp.checar_sl_tp, [ordem("buy limit", 128.5, 131.0, 134.5)], PARAMS, barras, 0.01)
checar("SL acima do preco numa compra reprova", len(r.falhas), 1)

# --- tipos --------------------------------------------------------------------
r = rodar(tp.checar_tipos, [boa], PARAMS)
checar("tipos: limit em set limit-compra passa", r.falhas, [])
r = rodar(tp.checar_tipos, [ordem("buy stop", 128.5, 124.5, 134.5)], PARAMS)
checar("tipos: stop num set limit reprova", len(r.falhas), 1)
r = rodar(tp.checar_tipos, [ordem("sell limit", 128.5, 132.5, 122.5)], PARAMS)
checar("tipos: venda num set so-compra reprova", len(r.falhas) >= 1, True)
r = rodar(tp.checar_tipos, [ordem("buy", 128.5, 124.5, 134.5, coment="04-MUL Buy/RFixo")],
          dict(PARAMS, EntryOrderType="0"))
checar("tipos: mercado sem pendente passa", r.falhas, [])
r = rodar(tp.checar_tipos, [boa], dict(PARAMS, EntryOrderType="0"))
checar("tipos: pendente com EntryOrderType=0 reprova", len(r.falhas), 1)
r = rodar(tp.checar_tipos, [ordem("buy limit", 128.5, 124.5, 134.5, coment="07-MUL Buy/Grid")], PARAMS)
checar("tipos: perna de grade virando pendente reprova", len(r.falhas), 1)

# --- lote ---------------------------------------------------------------------
# R = 10000 * 1% = 100; SL a 4.0 => 100 / (4.0 * 100) = 0.25 lote
r = rodar(tp.checar_lote, [ordem("buy limit", 128.5, 124.5, 134.5, vol=0.25)], PARAMS, INFO)
checar("lote Fixed-R certo passa", r.falhas, [])
r = rodar(tp.checar_lote, [ordem("buy limit", 128.5, 124.5, 134.5, vol=0.5)], PARAMS, INFO)
checar("lote Fixed-R dobrado reprova", len(r.falhas), 1)
fixo = dict(PARAMS, PositionSizeMode="2", PositionSizeValue="0.05")
r = rodar(tp.checar_lote, [ordem("buy limit", 128.5, 124.5, 134.5, vol=0.05)], fixo, INFO)
checar("FixedLot exato passa", r.falhas, [])
r = rodar(tp.checar_lote, [ordem("buy limit", 128.5, 124.5, 134.5, vol=0.07)], fixo, INFO)
checar("FixedLot diferente reprova", len(r.falhas), 1)

# --- expiracao ----------------------------------------------------------------
ini = t_ordem
no_prazo = ordem("buy limit", 128.5, 124.5, 134.5, fim=ini + timedelta(minutes=45, seconds=20),
                 estado="canceled")
r = rodar(tp.checar_expiracao, [no_prazo], PARAMS, barras)
checar("cancela com 3 barras (45 min) passa", (r.falhas, r.metricas["cancel_no_prazo"]), ([], 1))
tarde = ordem("buy limit", 128.5, 124.5, 134.5, fim=ini + timedelta(minutes=75), estado="canceled")
r = rodar(tp.checar_expiracao, [tarde], PARAMS, barras)
checar("viva 75 min com prazo de 45 reprova", len(r.falhas), 1)
cedo = ordem("buy limit", 128.5, 124.5, 134.5, fim=ini + timedelta(minutes=15), estado="canceled")
r = rodar(tp.checar_expiracao, [cedo], PARAMS, barras)
checar("cancelada antes do prazo so e contada", (r.falhas, r.metricas["cancel_antes_do_prazo"]), ([], 1))
r = rodar(tp.checar_expiracao, [ordem("buy limit", 128.5, 124.5, 134.5,
                                      fim=ini + timedelta(minutes=60), estado="expired")], PARAMS, barras)
checar("expirada pelo broker reprova (a EA deveria ter cancelado)", len(r.falhas) >= 1, True)

# fim de semana / mercado fechado: a EA conta barras EXISTENTES (iBarShift), entao o
# prazo de 3 barras cai na 3a barra depois do buraco, nao 45 min de relogio
lacuna = m15.drop(m15.index[32:36])                       # some 1h de barras (32..35)
barras_lacuna = tp.Barras({"M15": lacuna, "M1": m1})
p_ord = tp.Barras({"M15": lacuna}).pos("M15", t_ordem)
prazo_real = lacuna.index[p_ord + 3].to_pydatetime()      # 3a barra existente depois da ordem
apos_lacuna = ordem("buy limit", 128.5, 124.5, 134.5, fim=prazo_real + timedelta(seconds=20),
                    estado="canceled")
r = rodar(tp.checar_expiracao, [apos_lacuna], PARAMS, barras_lacuna)
checar("prazo contado em barras existentes (buraco de mercado) passa",
       (r.falhas, r.metricas["cancel_no_prazo"]), ([], 1))


# pausa diaria do mercado: ordem colocada na ultima barra antes do buraco expira pelo
# broker na reabertura (a EA nao acumula barras) -- nao e falha; e o comentario vira "expired [...]"
apos_pausa = ordem("buy limit", 128.5, 124.5, 134.5, fim=lacuna.index[p_ord + 1].to_pydatetime(),
                   estado="expired", coment="expired [2026.08.03 09:15]")
r = rodar(tp.checar_expiracao, [apos_pausa], PARAMS, barras_lacuna)
checar("expirada pelo broker na pausa do mercado passa",
       (r.falhas, r.metricas["expirada_na_pausa_do_mercado"]), ([], 1))
r = rodar(tp.checar_tipos, [apos_pausa], PARAMS)
checar("comentario 'expired [...]' nao conta como perna sem marca", r.falhas, [])
tarde_exp = ordem("buy limit", 128.5, 124.5, 134.5, fim=lacuna.index[p_ord + 4].to_pydatetime(),
                  estado="expired", coment="expired [2026.08.03 12:00]")
r = rodar(tp.checar_expiracao, [tarde_exp], PARAMS, barras_lacuna)
checar("expirada pelo broker DEPOIS de N barras existentes reprova", len(r.falhas), 1)

# --- sobreposicao -------------------------------------------------------------
a = ordem("buy limit", 128.5, 124.5, 134.5, t=T0, fim=T0 + timedelta(minutes=45), estado="canceled", n=1)
b = ordem("buy limit", 128.5, 124.5, 134.5, t=T0 + timedelta(minutes=15), fim=T0 + timedelta(minutes=60),
          estado="canceled", n=2)
r = rodar(tp.checar_sobreposicao, [a, b], PARAMS)
checar("duas pendentes de compra vivas juntas reprovam", len(r.falhas), 1)
c2 = ordem("buy limit", 128.5, 124.5, 134.5, t=T0 + timedelta(minutes=45), fim=T0 + timedelta(minutes=60),
           estado="canceled", n=3)
r = rodar(tp.checar_sobreposicao, [a, c2], PARAMS)
checar("uma depois da outra passa", r.falhas, [])
v = ordem("sell limit", 129.5, 133.5, 123.5, t=T0 + timedelta(minutes=15), fim=T0 + timedelta(minutes=30),
          estado="canceled", n=4)
r = rodar(tp.checar_sobreposicao, [a, v], PARAMS)
checar("lados diferentes juntos passam", r.falhas, [])

# --- execucao -----------------------------------------------------------------
deal = {"t": t_ordem + timedelta(seconds=5), "deal": 9, "simbolo": "XAUUSD", "tipo": "buy",
        "direcao": "in", "vol": 0.25, "preco": 128.4, "ordem": 1, "comissao": 0, "swap": 0,
        "lucro": 0, "saldo": 10000, "comentario": ""}
r = rodar(tp.checar_execucao, [boa], [deal], 0.01)
checar("limit executando melhor passa", r.falhas, [])
r = rodar(tp.checar_execucao, [boa], [dict(deal, preco=128.9)], 0.01)
checar("limit executando PIOR que o pedido reprova", len(r.falhas), 1)
st = ordem("buy stop", 131.0, 127.0, 137.0)
r = rodar(tp.checar_execucao, [st], [dict(deal, preco=131.2)], 0.01)
checar("stop com derrapagem contra passa", r.falhas, [])
r = rodar(tp.checar_execucao, [st], [dict(deal, preco=130.0)], 0.01)
checar("stop executando a favor do gatilho reprova", len(r.falhas), 1)

# --- OCO ----------------------------------------------------------------------
oco = dict(PARAMS, EntryOrderType="3", MaxShortTrades="1")
compra = ordem("buy stop", 131.0, 127.0, 137.0, n=10, fim=t_ordem + timedelta(minutes=5),
               coment="04-MUL Buy/OCO")
venda = ordem("sell stop", 127.0, 131.0, 121.0, n=11, fim=t_ordem + timedelta(minutes=5, seconds=1),
              estado="canceled", coment="04-MUL Buy/OCO")
d_compra = dict(deal, ordem=10, t=t_ordem + timedelta(minutes=5), preco=131.0)
r = rodar(tp.checar_oco, [compra, venda], [d_compra], oco)
checar("bracket com irma cancelada em 1 s passa", r.falhas, [])
venda_viva = dict(venda, estado="expired")
r = rodar(tp.checar_oco, [compra, venda_viva], [d_compra], oco)
checar("irma nao cancelada reprova", len(r.falhas), 1)
# duas pernas no MESMO instante = spread que abriu (rolagem) passou a largura do bracket:
# a EA nao tem como cancelar antes -> aviso; com segundos de diferenca o cancelamento falhou
r = rodar(tp.checar_oco, [compra, dict(venda, ordem=11)], [d_compra, dict(d_compra, ordem=11, deal=10)], oco)
checar("as duas pernas no mesmo instante: aviso, nao falha",
       (r.falhas, len(r.avisos), r.metricas["oco_duas_pernas_simultaneas"]), ([], 1, 1))
r = rodar(tp.checar_oco, [compra, dict(venda, ordem=11)],
          [d_compra, dict(d_compra, ordem=11, deal=10, t=d_compra["t"] + timedelta(seconds=30))], oco)
checar("as duas pernas executadas com 30 s de diferenca reprova", len(r.falhas), 1)
r = rodar(tp.checar_oco, [compra], [], oco)
checar("bracket sem a outra perna reprova", len(r.falhas), 1)
venda_lenta = dict(venda, fim=t_ordem + timedelta(minutes=5, seconds=30))
r = rodar(tp.checar_oco, [compra, venda_lenta], [d_compra], oco)
checar("irma cancelada 30 s depois reprova", len(r.falhas), 1)
r = rodar(tp.checar_oco, [ordem("buy stop", 126.0, 122.0, 132.0, n=12, coment="04-MUL Buy/OCO"),
                          ordem("sell stop", 131.0, 135.0, 125.0, n=13, coment="04-MUL Buy/OCO")], [], oco)
checar("bracket com compra abaixo da venda reprova", len(r.falhas), 1)

# --- sessao -------------------------------------------------------------------
sess = dict(oco, PendingGatilho="1", PendingHoraSessao="8")
h8 = datetime(2026, 8, 3, 8, 0, 5)
r = rodar(tp.checar_sessao, [ordem("buy stop", 1, 1, 1, t=h8), ordem("sell stop", 1, 1, 1, t=h8, n=2)], sess)
checar("bracket na hora da sessao passa", r.falhas, [])
r = rodar(tp.checar_sessao, [ordem("buy stop", 1, 1, 1, t=h8.replace(hour=9))], sess)
checar("bracket fora da hora reprova", len(r.falhas), 1)

# --- janela -------------------------------------------------------------------
jan = dict(PARAMS, TOD_From_Hour="10", TOD_To_Hour="12", TradeMonday="true", TradeTuesday="true",
           TradeWednesday="true", TradeThursday="true", TradeFriday="true")
r = rodar(tp.checar_janela, [ordem("buy limit", 1, 1, 1, t=datetime(2026, 8, 3, 11, 0))], jan)
checar("dentro do pregao passa", r.falhas, [])
r = rodar(tp.checar_janela, [ordem("buy limit", 1, 1, 1, t=datetime(2026, 8, 3, 12, 30))], jan)
checar("fora do pregao reprova", len(r.falhas), 1)


# --- WFO In-Sample: a pendente nao nasce nem executa no OOS ----------------------------
LOG_WFO = "\n".join([
    "Step 1:", "  In-Sample (IS): 2026.08.03 - 2026.08.12",
    "  Out-Sample (OOS): 2026.08.13 - 2026.08.16",
    "Step 2:", "  In-Sample (IS): 2026.08.17 - 2026.08.26",
    "  Out-Sample (OOS): 2026.08.27 - 2026.08.30",
    "  Out-Sample (OOS): 2026.08.13 - 2026.08.16"])          # repetida (outro agente)
checar("wfo: parse das janelas OOS (sem repetir)", len(tp.parse_janelas_wfo(LOG_WFO)), 2)
checar("wfo: OOS termina as 23:59:59 do ultimo dia",
       tp.parse_janelas_wfo(LOG_WFO)[0], (datetime(2026, 8, 13), datetime(2026, 8, 16, 23, 59, 59)))
wfo_p = dict(PARAMS, AtivarWFO="true", MetodoDeEntradawfo="0")
no_is = ordem("buy limit", 1, 1, 1, t=datetime(2026, 8, 11, 10, 0), fim=datetime(2026, 8, 11, 10, 45), estado="canceled", n=1)
r = rodar(tp.checar_wfo, [no_is], [], LOG_WFO, wfo_p)
checar("wfo: pendente que vive e morre no IS passa", r.falhas, [])
nasceu_no_oos = ordem("buy limit", 1, 1, 1, t=datetime(2026, 8, 14, 10, 0), fim=datetime(2026, 8, 14, 10, 45), estado="canceled", n=2)
r = rodar(tp.checar_wfo, [nasceu_no_oos], [], LOG_WFO, wfo_p)
checar("wfo: pendente colocada no OOS reprova", len(r.falhas), 1)
executou_no_oos = ordem("buy limit", 1, 1, 1, t=datetime(2026, 8, 13, 23, 0), fim=datetime(2026, 8, 14, 5, 0), n=3)
d_oos = dict(deal, ordem=3, t=datetime(2026, 8, 14, 5, 0))
r = rodar(tp.checar_wfo, [executou_no_oos], [d_oos], LOG_WFO, wfo_p)
checar("wfo: pendente que executa no OOS reprova", len(r.falhas), 1)
# a EA numera as janelas a partir da 1a barra do teste (ex.: 23:00): as datas impressas tem
# ~1 dia de folga -- a ultima hora do 'dia' de inicio do OOS ainda e IS de fato
borda_do_dia = ordem("buy limit", 1, 1, 1, t=datetime(2026, 8, 13, 10, 0), fim=datetime(2026, 8, 13, 10, 45),
                     estado="canceled", n=4)
r = rodar(tp.checar_wfo, [borda_do_dia], [], LOG_WFO, wfo_p)
checar("wfo: ordem no dia da borda impressa nao e violacao (so o interior vale)", r.falhas, [])
r = rodar(tp.checar_wfo, [nasceu_no_oos], [], "", wfo_p)
checar("wfo: ligado sem nenhuma janela impressa reprova", len(r.falhas), 1)
r = rodar(tp.checar_wfo, [nasceu_no_oos], [], LOG_WFO, dict(PARAMS, AtivarWFO="false"))
checar("wfo desligado: nada a conferir", r.falhas, [])


# --- marca de pendente com o comentario cortado em 31 caracteres (grade/piramide) -----
for coment, esperado_marca in (("07-MUL Buy / Grid / FixedLot/Pe", True),
                               ("12-MUL Buy / Pyramid / FixedR/P", True),
                               ("04-MUL Buy/RFixo/Pend", True), ("04-MUL Buy/OCO", True),
                               ("07-MUL Buy / Grid / FixedLot", False), ("04-MUL Buy/RFixo", False)):
    checar(f"marca de pendente em {coment!r}", bool(tp.RE_MARCA_PEND.search(coment)), esperado_marca)

# --- G7: diferenca semanal Limit - mercado ------------------------------------------
def _saida(t, lucro):
    return {"direcao": "out", "t": t, "lucro": lucro, "comissao": -1.0, "swap": 0.0}


sa = [_saida(datetime(2026, 8, 3, 10), 100), _saida(datetime(2026, 8, 10, 10), 50),
      _saida(datetime(2026, 8, 17, 10), -20), _saida(datetime(2026, 8, 24, 10), 80)]
sb = [_saida(datetime(2026, 8, 3, 10), 90), _saida(datetime(2026, 8, 10, 10), 60),
      _saida(datetime(2026, 8, 17, 10), -30), _saida(datetime(2026, 8, 24, 10), 70)]
c = tp.comparar_semanal(sa, sb)
checar("g7: media/EP/t da diferenca semanal", (c["semanas"], c["media"], c["ep"], c["t"]), (4, 5.0, 5.0, 1.0))
checar("g7: semana so com um dos lados conta zero no outro",
       tp.comparar_semanal(sa, sb[:2])["semanas"], 4)

# --- log ----------------------------------------------------------------------
r = tp.Resultado()
tp.checar_log("ok tudo", r)
checar("log limpo", (r.falhas, r.avisos), ([], []))
r = tp.Resultado()
tp.checar_log("Invalid pending entry: PendingExpiracaoBarras=0", r)
checar("log com configuracao recusada reprova", len(r.falhas), 1)
r = tp.Resultado()
tp.checar_log("myOrderSend failed: type=2 retcode=10016", r)
checar("falha de envio vira aviso com o retcode", ("10016" in r.avisos[0], r.falhas), (True, []))

# --- catalogo -----------------------------------------------------------------
cat = tp.catalogo()
nomes = [c.nome for c in cat]
checar("catalogo: nomes unicos", len(nomes), len(set(nomes)))
checar("catalogo: controle existe", all(c.controle in nomes for c in cat if c.controle), True)
checar("catalogo: cobre Stop/Limit/OCO/sessao",
       {int(c.sobrepor.get("EntryOrderType", 9)) for c in cat if "EntryOrderType" in c.sobrepor}
       >= {0, 1, 2, 3}, True)
checar("catalogo: cobre as 3 EAs",
       {c.variante.split("_")[-1] for c in cat} >= {"MULTI", "BOLLINGER", "CANDLES"}, True)

if FALHAS:
    print(f"{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  -", f)
    sys.exit(1)
print("testar_pendentes: todos os casos passaram")
