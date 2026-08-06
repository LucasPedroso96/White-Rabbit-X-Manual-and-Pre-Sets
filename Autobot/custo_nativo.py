# -*- coding: utf-8 -*-
"""Mede comissao e swap REAIS por lote, direto no simbolo NATIVO da corretora,
e cacheia por simbolo -- para corrigir backtests rodados no simbolo `.HT`
(Historical Tool Manager), que saem com comissao ZERO por construcao.

O simbolo customizado (`.HT`) e clonado do nativo via CustomSymbolCreate, mas
comissao em MT5 vem do GRUPO da conta no SERVIDOR do broker, nao de uma
propriedade de simbolo -- um simbolo sintetico client-side nunca participa
disso. Confirmado empiricamente (2026-08-02): GBPUSD nativo cobrou -66,85 de
comissao em 1630 deals; GBPUSD.HT, rodando o MESMO set, cobrou 0,00 em 2587
deals. Isso nao e sobre PRIORIZAR nativo sobre Dukascopy na hora de baixar
historico -- e estrutural do mecanismo de Custom Symbol, e so se corrige
medindo o custo real e aplicando como correcao no relatorio.

"a comissao tem que ser preenchida pelos dados do historico da corretora"
(dono, 2026-08-02): a fonte da verdade e um passe de referencia no simbolo
NATIVO, nunca um numero digitado -- mesma filosofia de `atualizar_conta_real.py`
para leverage.

Uso:
    python custo_nativo.py --symbol GBPUSD --sistema 07_GRID_SEPARATE --variante BUY_MULTI
    python custo_nativo.py --symbol GBPUSD --inicio 2024.01.01 --fim 2024.04.01  # janela mais curta, mais rapido
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import optimize_sets as base  # noqa: E402

CACHE = Path(__file__).resolve().parent / "_custo_nativo.json"


def _celulas_deals(html: str) -> list[list[str]]:
    """Extrai as linhas de DEAL da tabela do relatorio, colunas ja limpas.

    Mesma tolerancia a idioma de `portfolio_builder._achar_coluna`: aqui a
    linha e reconhecida pelo FORMATO (data no inicio, >= 10 colunas), nao pelo
    texto do cabecalho -- o relatorio muda de idioma conforme o terminal.
    """
    linhas = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
    deals = []
    for linha in linhas:
        celulas = re.findall(r"<td[^>]*>(.*?)</td>", linha, re.S)
        celulas = [re.sub(r"<[^>]+>", "", c).strip() for c in celulas]
        if len(celulas) >= 10 and re.match(r"^\d{4}\.\d{2}\.\d{2}", celulas[0]):
            deals.append(celulas)
    return deals


def medir_custo_por_lote(caminho_htm: Path) -> dict | None:
    """(Comissao, swap) por lote de ENTRADA, a partir de UM relatorio.

    Comissao e swap contam de TODOS os deals (entrada e saida podem cobrar as
    duas); volume conta so das entradas ("in"), porque e o lote que abriu
    a posicao -- contar entrada+saida duplicaria o denominador.
    """
    html = caminho_htm.read_text(encoding="utf-16", errors="replace")
    deals = _celulas_deals(html)
    if not deals:
        return None
    total_com = total_swap = total_vol = 0.0
    n_in = 0
    for c in deals:
        try:
            direcao, vol, com, swap = c[4], float(c[5]), float(c[8]), float(c[9])
        except (IndexError, ValueError):
            continue
        total_com += com
        total_swap += swap
        if direcao.lower() == "in":
            total_vol += vol
            n_in += 1
    if total_vol <= 0:
        return None
    return {
        "comissao_por_lote": total_com / total_vol,
        "swap_por_lote": total_swap / total_vol,
        "deals": len(deals), "entradas": n_in, "volume_lotes": total_vol,
    }


def volume_negociado(caminho_htm: Path) -> float | None:
    """Total de lotes NEGOCIADOS (entradas) num relatorio -- para aplicar a
    taxa de custo nativo cacheada num relatorio de simbolo `.HT` (que nao tem
    comissao/swap proprios pra medir, so precisa do volume pra escalar)."""
    if not caminho_htm.exists():
        return None
    deals = _celulas_deals(caminho_htm.read_text(encoding="utf-16", errors="replace"))
    total = 0.0
    achou = False
    for c in deals:
        try:
            if c[4].lower() == "in":
                total += float(c[5])
                achou = True
        except (IndexError, ValueError):
            continue
    return total if achou else None


def ajustar_lucro(lucro_bruto: float, volume_lotes: float,
                  custo: dict) -> float:
    """Lucro do `.HT` (comissao/swap zerados) menos o custo REAL medido no
    simbolo nativo, escalado pelo volume desta corrida."""
    return (lucro_bruto
            + volume_lotes * custo["comissao_por_lote"]
            + volume_lotes * custo["swap_por_lote"])


def carregar_cache() -> dict:
    if not CACHE.exists():
        return {}
    return json.loads(CACHE.read_text(encoding="utf-8"))


def custo_cacheado(simbolo_nativo: str) -> dict | None:
    """Custo por lote ja medido para este simbolo, ou None se nunca medido.

    NUNCA inventa um numero: quem chama decide o que fazer na ausencia (nao
    corrigir, ou medir agora) -- mesma regra de `optimize_sets.leverage_conta`.
    """
    return carregar_cache().get(simbolo_nativo)


def medir_e_cachear(simbolo_nativo: str, caminho_set: Path, inicio: str, fim: str,
                    deposito: int = 500, timeout: int = 1800) -> dict:
    # Import tardio: optimize_two_stage tambem importa este modulo, e
    # importar passe_unico no topo do arquivo criaria um ciclo.
    from optimize_two_stage import passe_unico
    r = passe_unico(caminho_set, simbolo_nativo, "M1", inicio, fim, deposito,
                    4, timeout=timeout)
    relatorio = base.DADOS / "conf_wrx.htm"
    if not relatorio.exists():
        raise SystemExit(f"sem relatorio apos o passe em {simbolo_nativo}")
    custo = medir_custo_por_lote(relatorio)
    if custo is None:
        raise SystemExit(f"relatorio sem deals de entrada em {simbolo_nativo} "
                         f"(saldo medido: {r.get('saldo')}) -- periodo curto "
                         f"demais ou simbolo sem trades no range?")
    custo["quando"] = datetime.now().isoformat(timespec="seconds")
    custo["periodo"] = f"{inicio}..{fim}"
    cache = carregar_cache()
    cache[simbolo_nativo] = custo
    CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False),
                     encoding="utf-8")
    return custo


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", required=True,
                    help="simbolo NATIVO (sem sufixo .HT)")
    ap.add_argument("--sistema", default="07_GRID_SEPARATE")
    ap.add_argument("--variante", default="BUY_MULTI")
    ap.add_argument("--inicio", default="2023.08.01")
    ap.add_argument("--fim", default=datetime.now().strftime("%Y.%m.%d"))
    ap.add_argument("--deposit", type=int, default=500)
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    caminho_set = (base.DADOS / "MQL5" / "Profiles" / "Tester"
                   / "White_Rabbit_X_Sets_templates" / "01_Forex"
                   / args.symbol / args.sistema
                   / f"{args.variante}.set")
    if not caminho_set.exists():
        print(f"sem template em {caminho_set}", flush=True)
        return 1

    custo = medir_e_cachear(args.symbol, caminho_set, args.inicio, args.fim,
                            args.deposit, args.timeout)
    print(f"{args.symbol}: comissao_por_lote={custo['comissao_por_lote']:.4f} "
          f"swap_por_lote={custo['swap_por_lote']:.4f} "
          f"({custo['entradas']} entradas, {custo['volume_lotes']:.2f} lotes)",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
