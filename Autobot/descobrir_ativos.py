# -*- coding: utf-8 -*-
"""Descobre quais ativos ESTE terminal pode testar -- nunca uma lista fixa.

Uma lista de simbolos cravada no codigo (como os 9 `.HT` do dono original)
so funciona na maquina de quem a escreveu. Em qualquer outro terminal os
simbolos nao existem, o `/config:` do Strategy Tester falha em silencio, e
o combo sai com "sem JSON final" -- foi exatamente o que aconteceu com um
usuario externo rodando o Autobot publicado (2026-08-02).

Prioridade por ativo: prefere o NATIVO da corretora (dono, 2026-08-08 --
medido que o dado diverge entre as duas fontes, e o nativo saiu melhor);
cai pro INJETADO (sufixo `.HT` do Historical Tool Manager) so quando o
nativo nao existe no terminal. Nativo tambem e o que qualquer cliente ja
tem sem instalar nada extra -- um set validado em `.HT` nao carrega numa
conta sem Historical Tool Manager, porque o simbolo gravado no arquivo e
literalmente "SIMBOLO.HT". O Historical Tool Manager continua OPCIONAL,
so como fallback agora, nao mais preferencia.

Saldo NUNCA bloqueia backtest -- regra do projeto (saldo governa so a
EXECUCAO ao vivo, nunca pesquisa/treino/promocao). Descobrimos isso na
propria pele: a conta do dono tem ~$114, abaixo do capital_base ate da
classe mais barata (Forex, 500) -- um filtro por saldo teria zerado a
NOSSA campanha tambem. Por isso `capital_base` aqui e so PRIORIDADE de
ordem (classes ja acessiveis primeiro), nunca portao de exclusao.

Elegibilidade real e so: o simbolo existe no terminal, e tem historico
minimo (`MIN_DIAS_HISTORICO`) pra sustentar um WFO de verdade.

Uso:
    python descobrir_ativos.py                 # lista o que seria usado, em ordem
    python descobrir_ativos.py --gravar        # fixa a lista detectada
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from generate_system_sets import ASSETS, CLASSES  # noqa: E402
from mt5_runner import fechar_terminal, garantir_terminal_livre  # noqa: E402
from optimize_sets import TERMINAL  # noqa: E402

MIN_DIAS_HISTORICO = 180
# mesmo piso do resto do projeto (historico curto demais nao sustenta WFO
# com ciclos IS/OOS reais)
CONFIG = Path(__file__).resolve().parent / "campanha_ativos.json"


def _historico_suficiente(mt5, simbolo: str, dias: int = MIN_DIAS_HISTORICO) -> bool:
    """Barras D1 nos ultimos `dias` -- tolera fins de semana/feriados (60%)."""
    fim = datetime.now()
    inicio = fim - timedelta(days=dias)
    barras = mt5.copy_rates_range(simbolo, mt5.TIMEFRAME_D1, inicio, fim)
    return barras is not None and len(barras) >= dias * 0.6


def descobrir() -> list[str]:
    """Varre ASSETS, devolve os simbolos jogaveis NESTE terminal.

    Ordem: classes cujo capital_base ja cabe no saldo atual vem primeiro
    (prioridade, nao exclusao) -- as demais entram depois, na mesma corrida.
    Pesquisa nunca fica menor por causa do saldo; so a ORDEM muda.
    """
    import MetaTrader5 as mt5

    garantir_terminal_livre(fechar=True, terminal=TERMINAL)
    if not mt5.initialize(path=str(TERMINAL)):
        raise SystemExit(f"Nao consegui conectar ao MT5: {mt5.last_error()}")
    try:
        conta = mt5.account_info()
        saldo = conta.balance if conta else 0.0
        todos = {s.name for s in mt5.symbols_get()}

        classes_ordenadas = sorted(
            ASSETS.items(),
            key=lambda item: (CLASSES[item[0]].capital_base > saldo,
                              CLASSES[item[0]].capital_base))

        resultado = []
        for classe_codigo, ativos in classes_ordenadas:
            capital = CLASSES[classe_codigo].capital_base
            acessivel = "acessivel agora" if saldo >= capital else "so pesquisa por ora"
            print(f"  {classe_codigo}: capital_base={capital:.0f} "
                  f"| saldo={saldo:.2f} -> {acessivel}", flush=True)
            for ativo in ativos:
                for candidato in (ativo, f"{ativo}.HT"):
                    if candidato not in todos:
                        continue
                    if not mt5.symbol_select(candidato, True):
                        continue
                    if _historico_suficiente(mt5, candidato):
                        resultado.append(candidato)
                        break
        return resultado
    finally:
        fechar_terminal(terminal=TERMINAL)


def carregar_ou_descobrir() -> list[str]:
    """Config gravada manualmente (usuario escolheu) tem prioridade sobre a
    auto-deteccao -- "o cara escolhe a lista de assets" (dono, 2026-08-02)."""
    if CONFIG.exists():
        lista = json.loads(CONFIG.read_text(encoding="utf-8"))
        print(f"Ativos definidos manualmente em {CONFIG.name}: "
              f"{len(lista)} simbolos", flush=True)
        return lista
    lista = descobrir()
    if lista:
        print(f"Ativos auto-detectados neste terminal: {len(lista)} simbolos "
              f"({', '.join(lista)})", flush=True)
    else:
        print("NENHUM ativo elegivel neste terminal -- confira simbolos "
              "disponiveis no Market Watch (nativos ou injetados via "
              "Historical Tool Manager) e o historico minimo de "
              f"{MIN_DIAS_HISTORICO} dias.", flush=True)
    return lista


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gravar", action="store_true",
                    help=f"grava a lista detectada em {CONFIG.name} (fixa a "
                         f"escolha ate voce apagar o arquivo)")
    args = ap.parse_args()

    lista = descobrir()
    print()
    for s in lista:
        print(f"  {s}")
    print(f"\n{len(lista)} simbolos jogaveis.")
    if args.gravar:
        CONFIG.write_text(json.dumps(lista, indent=2, ensure_ascii=False),
                          encoding="utf-8")
        print(f"Gravado em {CONFIG.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
