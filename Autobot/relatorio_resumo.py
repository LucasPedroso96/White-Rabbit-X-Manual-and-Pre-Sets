# -*- coding: utf-8 -*-
"""Extrai as metricas-chave da secao "Resultados" de um relatorio .htm do
Strategy Tester (o mesmo arquivo ja arquivado por
`optimize_two_stage.arquivar_relatorio()` para todo combo testado).

O relatorio inteiro (Profit Factor, Sharpe, Recovery Factor, drawdowns,
sequencias de ganho/perda...) ja fica salvo em disco para cada combo, mas o
dashboard so mostrava um link cru pro `.htm` -- "um monte de relatorio, e
nao temos nada la" (dono, ver docstring de `arquivar_relatorio`). Este modulo
existe so pra reaproveitar o que ja esta arquivado, sem mudar o que e gerado.

Mesma tolerancia a idioma de `custo_nativo._celulas_deals`: a secao
"Resultados" e achada pela POSICAO estrutural do relatorio (sempre a
antepenultima das 6 secoes com titulo `colspan="13"` -- Relatorio, Corretora,
Configuracao, Resultados, Ordens, Transacoes -- nessa ordem fixa, qualquer
idioma do terminal), nao pelo texto do titulo. Dentro da secao, cada rotulo e
uma celula terminando em ':' e o valor e a proxima celula nao-vazia -- mesmo
formato em qualquer idioma.

Uso:
    python relatorio_resumo.py caminho/para/conf_wrx.htm
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

_TITULO = re.compile(r'colspan="13"[^>]*>\s*<div[^>]*>\s*<b>[^<]*</b>')
_CELULA = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_TAG = re.compile(r"<[^>]+>")


def _secao_resultados(texto: str) -> str:
    """Trecho da secao 'Resultados': sempre a antepenultima das secoes com
    titulo colspan=13 (as duas seguintes sao 'Ordens' e 'Transacoes', nessa
    ordem, em qualquer idioma do terminal MT5)."""
    titulos = list(_TITULO.finditer(texto))
    if len(titulos) < 3:
        return ""
    return texto[titulos[-3].end():titulos[-2].start()]


def extrair_pares(texto: str) -> dict[str, str]:
    """Todo par rotulo:valor da secao Resultados, na ordem do relatorio."""
    secao = _secao_resultados(texto)
    celulas = [html.unescape(_TAG.sub("", c)).strip()
               for c in _CELULA.findall(secao)]
    pares: dict[str, str] = {}
    i = 0
    while i < len(celulas):
        if celulas[i].endswith(":"):
            for j in range(i + 1, len(celulas)):
                if celulas[j]:
                    pares[celulas[i].rstrip(":").strip()] = celulas[j]
                    i = j
                    break
        i += 1
    return pares


# Substrings EN+PT, casadas sem diferenciar maiusc./minusc. -- cobre os dois
# idiomas mais comuns nos terminais deste projeto sem depender de acento
# exato (terminal pode variar codificacao/versao entre maquinas).
ALIASES: dict[str, tuple[str, ...]] = {
    "profit_factor": ("fator de lucro", "profit factor"),
    "recovery_factor": ("fator de recupera", "recovery factor"),
    "sharpe_ratio": ("sharpe",),
    "expected_payoff": ("retorno esperado", "expected payoff"),
    "z_score": ("pontua", "z-score"),
    "equity_dd_relative": ("rebaixamento relativo do capital",
                           "equity drawdown relative"),
    "balance_dd_relative": ("rebaixamento relativo do saldo",
                            "balance drawdown relative"),
    "max_consecutive_wins": ("ximo ganhos consecutivos",
                             "maximum consecutive wins"),
    "max_consecutive_losses": ("ximo perdas consecutivas",
                               "maximum consecutive losses"),
    "largest_profit_trade": ("maior lucro da negocia",
                             "largest profit trade"),
    "largest_loss_trade": ("maior perda na negocia", "largest loss trade"),
    "quality_of_history": ("qualidade do hist", "quality of history"),
}


def resumo_relatorio(caminho_htm: Path) -> dict[str, str | None]:
    """Metricas-chave da secao Resultados de UM relatorio .htm (UTF-16,
    'Salvar como Relatorio' do MT5). None para o que nao foi encontrado --
    nunca inventa valor (mesma regra de `custo_nativo.custo_cacheado`)."""
    if not caminho_htm.exists():
        return {k: None for k in ALIASES}
    texto = caminho_htm.read_text(encoding="utf-16", errors="replace")
    pares = extrair_pares(texto)
    pares_lower = {k.lower(): v for k, v in pares.items()}

    def achar(prefixos: tuple[str, ...]) -> str | None:
        for chave, valor in pares_lower.items():
            if any(p in chave for p in prefixos):
                return valor
        return None

    return {campo: achar(prefixos) for campo, prefixos in ALIASES.items()}


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: python relatorio_resumo.py caminho/conf_wrx.htm")
        return 1
    resumo = resumo_relatorio(Path(sys.argv[1]))
    for campo, valor in resumo.items():
        print(f"{campo}: {valor}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
