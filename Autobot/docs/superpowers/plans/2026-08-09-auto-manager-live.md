# AutoManagerLive (suggestion engine) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the AutoManagerLive suggestion engine described in `PLANO_TREINAMENTO_100_A_MILHAO.md` §8 — a numbered queue of certified-set combinations that fit together (low correlation), each stating how many live accounts it needs — and wire it into the existing "Certified sets" dashboard panel.

**Architecture:** A new pure-Python module (`auto_manager_live.py`) reuses `portfolio_builder.py`'s correlation/allocation math and `generate_system_sets.py`'s tier/class metadata to turn the dashboard's existing certified-sets pool into a tier-ordered, numbered suggestion queue with a hard-constraint account-splitting rule. One new read-only FastAPI endpoint exposes it; the existing "Certified sets" panel in `dashboard_static/` gets a new box that renders the queue and reuses the existing `/api/implantacao/marcar` endpoint to accept a suggestion.

**Tech Stack:** Python 3.13, FastAPI, pandas/numpy (already a dependency via `portfolio_builder.py`), vanilla JS (no framework, matches `dashboard_static/app.js`).

## Global Constraints

- Work happens on a **new branch off `main`**, e.g. `feat/auto-manager-live` — never on `feat/deposito-auto-sugestao` (that branch has an unrelated open PR #1).
- **Never restart, kill, or otherwise touch the dashboard process already running on port 8020** (PID varies — check with `netstat -ano | grep 8020` if unsure). It is mid-campaign. Manual verification in this plan uses a second instance on a spare port instead.
- No new third-party dependencies. Everything needed (`pandas`, `numpy`, `fastapi`) is already imported elsewhere in this codebase.
- This repo has **no pytest config and no `tests/` directory** — every `test_*.py` lives flat at the repo root and is a plain script using a `checar(rotulo, obtido, esperado)` / `FALHAS` list convention (see `test_ready_library.py`), run directly with the interpreter, not through pytest. Follow that convention exactly — do not introduce pytest-style `assert`/fixtures.
- Run tests with: `"C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python313\python.exe" test_auto_manager_live.py` from the repo root (`C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot`). A bare `python` is not on PATH in this shell; use the full path shown here.
- New Python modules live flat at the repo root (no subpackages anywhere in this codebase — `auto_set_manager.py`, `portfolio_builder.py`, `calc_capital_base.py` are all root-level).
- FastAPI endpoints in `dashboard_campanha.py` return `JSONResponse(...)`; follow the existing naming style (Portuguese function/variable names, English is only used in `dashboard_static/`'s user-facing strings for the Deployment tab, which is not localized like the rest of the UI — do not add i18n dictionary keys for this feature).
- **Explicitly out of scope for this plan:** live-trade-based promotion/demotion (the `EM_PROVA` probation status and tolerance-band comparison described in plan §8). That requires ingesting real MT5 live-account trade history, which does not exist in this codebase yet and was not designed — the plan document itself already defers the exact numbers ("os números exatos... ficam pra depois"). This plan implements everything that's buildable today from data that already exists: the certified-sets pool, archived Strategy Tester reports, and the tier/class metadata already in `generate_system_sets.py`. A follow-up brainstorm + plan is needed once real live trades exist.
- This plan implements against the **public repo checkout only** (`C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot`). Mirroring to the private repo (`Metatrader5EAS`) is a manual follow-up once this is reviewed — not part of this plan.

---

## File Structure

- **Create:** `auto_manager_live.py` — pure-logic suggestion engine (tier ordering, capital-per-class lookup, correlation-based greedy selection reusing `portfolio_builder.py`, account-splitting rule, report-to-daily-series loader, top-level queue builder). No FastAPI, no MT5 import — importable and testable standalone.
- **Create:** `test_auto_manager_live.py` — tests for every function above, following the existing `checar()`/`FALHAS` convention.
- **Modify:** `dashboard_campanha.py` — one new endpoint, `GET /api/implantacao/sugestoes`, that feeds the existing `_sets_certificados()` pool into `auto_manager_live` and returns the numbered queue as JSON. No changes to any existing endpoint or function.
- **Modify:** `dashboard_static/index.html` — new box inside the existing `#painel-implantacao` section: account-balance input, recalculate button, two bulk "mark as deployed" buttons, and a suggestion card with prev/next navigation.
- **Modify:** `dashboard_static/app.js` — new `carregarSugestoes()`/`renderizarSugestao()` functions and event wiring, called alongside the existing `carregarImplantacao()` when the Deployment tab opens.

---

### Task 1: Tier/class metadata and capital-per-class lookup

**Files:**
- Create: `auto_manager_live.py`
- Test: `test_auto_manager_live.py`

**Interfaces:**
- Produces: `TIER_ORDEM: list[str]`, `SYSTEM_STATUS: dict[str, str]`, `ASSET_CLASS_OF: dict[str, str]`, `capital_minimo_classe(simbolo: str) -> float | None`

- [ ] **Step 1: Create the branch and the test file with a failing test**

```bash
cd "C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot"
git checkout main
git pull origin main
git checkout -b feat/auto-manager-live
```

Create `test_auto_manager_live.py`:

```python
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
checar("classe direta: forex", aml.capital_minimo_classe("EURUSD"), 500)
checar("classe com ponto proprio (nao e sufixo)",
       aml.capital_minimo_classe("BRK.B"), 5000)
checar("sufixo de corretora/HT cai pro radical",
       aml.capital_minimo_classe("EURUSD.HT"), 500)
checar("simbolo desconhecido", aml.capital_minimo_classe("NAOEXISTE"), None)


if FALHAS:
    print(f"{len(FALHAS)} falha(s):")
    for f in FALHAS:
        print(f"  {f}")
    sys.exit(1)
print("ok")
```

- [ ] **Step 2: Run it to verify it fails (module doesn't exist yet)**

Run: `"C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python313\python.exe" test_auto_manager_live.py`
Expected: `ModuleNotFoundError: No module named 'auto_manager_live'`

- [ ] **Step 3: Create `auto_manager_live.py` with the metadata and the lookup function**

```python
# -*- coding: utf-8 -*-
"""Motor de sugestao do AutoManagerLive -- ver PLANO_TREINAMENTO_100_A_MILHAO.md
secao 8 ("Deployment: AutoManagerLive") para o desenho completo.

Pega o pool que o painel "Certified sets" ja expoe (`/api/implantacao`) e
produz uma fila NUMERADA de sugestoes de combinacao: combos certificados que
cabem juntos por correlacao (reaproveitando portfolio_builder.py), ordenados
primeiro pela ordem de graduacao por risco (RESEARCH -> HEDGE_ACCOUNT_REQUIRED
-> HIGH_RISK -> HIGH_RISK_RESEARCH), e cada sugestao ja diz quantas contas
precisa e de que tipo.

Fora daqui, de proposito: promocao/rebaixamento por metrica ao vivo (EM_PROVA)
exige historico de trade ao vivo real, que este codebase ainda nao ingere --
ver secao 8 do plano, "Fora de escopo por enquanto".
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

import portfolio_builder as pb
from generate_system_sets import ASSETS, CLASSES, SYSTEMS

# Mesma ordem de graduacao pra capital ao vivo da secao 5 do plano.
TIER_ORDEM = ["RESEARCH", "HEDGE_ACCOUNT_REQUIRED", "HIGH_RISK",
             "HIGH_RISK_RESEARCH"]

SYSTEM_STATUS: dict[str, str] = {s.code: s.status for s in SYSTEMS}

ASSET_CLASS_OF: dict[str, str] = {
    ativo: classe for classe, ativos in ASSETS.items() for ativo in ativos
}


def capital_minimo_classe(simbolo: str) -> float | None:
    """Capital minimo da classe do ativo (generate_system_sets.CLASSES).

    Tenta o simbolo exato primeiro (cobre casos como "BRK.B", que tem ponto
    proprio, nao sufixo de corretora); so cai pro radical antes do primeiro
    separador quando o simbolo exato nao bate -- mesma ideia de
    ready_library.achar_ativo(), pra aceitar "EURUSD.HT"/"EURUSDm" etc.
    """
    classe = ASSET_CLASS_OF.get(simbolo)
    if classe is None:
        radical = re.split(r"[.\-_]", simbolo)[0]
        classe = ASSET_CLASS_OF.get(radical)
    if classe is None:
        return None
    return CLASSES[classe].capital_base
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python313\python.exe" test_auto_manager_live.py`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add auto_manager_live.py test_auto_manager_live.py
git commit -m "feat(auto-manager-live): tier/class metadata and capital-per-class lookup"
```

---

### Task 2: Candidate ordering by risk tier

**Files:**
- Modify: `auto_manager_live.py`
- Test: `test_auto_manager_live.py`

**Interfaces:**
- Consumes: `TIER_ORDEM`, `SYSTEM_STATUS` (Task 1)
- Produces: `ordenar_candidatos(combos: list[dict]) -> list[dict]` — each combo dict has at least `"sistema"`, `"retencao"` (float or None), `"mc_prob_ruina"` (float or None); returns a new list sorted tier-first, tie-broken by higher `retencao` then lower `mc_prob_ruina`. This is the same dict shape `_sets_certificados()` in `dashboard_campanha.py` already produces.

- [ ] **Step 1: Add the failing test**

Append to `test_auto_manager_live.py` (before the `if FALHAS:` block):

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `"C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python313\python.exe" test_auto_manager_live.py`
Expected: `AttributeError: module 'auto_manager_live' has no attribute 'ordenar_candidatos'`

- [ ] **Step 3: Implement**

Append to `auto_manager_live.py`:

```python
def ordenar_candidatos(combos: list[dict]) -> list[dict]:
    """Ordem de graduacao por risco (secao 5 do plano) primeiro; dentro do
    mesmo tier, maior retencao_oos primeiro, depois menor mc_prob_ruina --
    mesmo desempate que a secao 6 ja usa pro ranking por ativo. Combo sem
    retencao/mc conhecido fica no fim do proprio tier, nunca no comeco."""
    def chave_ordenacao(c: dict) -> tuple:
        tier = SYSTEM_STATUS.get(c["sistema"], "HIGH_RISK_RESEARCH")
        indice_tier = (TIER_ORDEM.index(tier) if tier in TIER_ORDEM
                      else len(TIER_ORDEM))
        retencao = c.get("retencao")
        mc = c.get("mc_prob_ruina")
        return (
            indice_tier,
            -(retencao if retencao is not None else -1e18),
            mc if mc is not None else 1e18,
        )
    return sorted(combos, key=chave_ordenacao)
```

- [ ] **Step 4: Run to verify it passes**

Run: `"C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python313\python.exe" test_auto_manager_live.py`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add auto_manager_live.py test_auto_manager_live.py
git commit -m "feat(auto-manager-live): risk-tier candidate ordering"
```

---

### Task 3: Correlation-based greedy selection, tier-priority seeded

**Files:**
- Modify: `auto_manager_live.py`
- Test: `test_auto_manager_live.py`

**Interfaces:**
- Consumes: `portfolio_builder.metricas(curva: pd.Series) -> dict` (existing, has `resultado` and `recuperacao` keys)
- Produces: `selecionar_ordenado(series: dict[str, pd.Series], ordem: list[str], maximo: int, teto: float, recuperacao_minima: float) -> tuple[list[str], list[str]]` — returns `(escolhidas, recusadas)`, same shape as `portfolio_builder.selecionar()`'s return (list of names picked, list of human-readable rejection reasons for money-losing/low-recovery names).

- [ ] **Step 1: Add the failing test**

Append to `test_auto_manager_live.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `"C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python313\python.exe" test_auto_manager_live.py`
Expected: `AttributeError: module 'auto_manager_live' has no attribute 'selecionar_ordenado'`

- [ ] **Step 3: Implement**

Append to `auto_manager_live.py`:

```python
def selecionar_ordenado(series: dict[str, pd.Series], ordem: list[str],
                        maximo: int, teto: float,
                        recuperacao_minima: float) -> tuple[list[str], list[str]]:
    """Mesma elegibilidade e mesmo teto de correlacao POSITIVA de
    portfolio_builder.selecionar() (correlacao negativa nunca exclui -- e o
    melhor caso, ver a docstring de selecionar()), mas a ordem de escolha
    segue `ordem` (graduacao de risco, ja despatada por retencao/mc) em vez
    do maior fator de recuperacao. O resultado pode misturar tiers quando o
    teto de correlacao permite -- e exatamente esse caso que aciona a regra
    de "mistura de tier" de contas_necessarias().
    """
    quadro = pd.DataFrame(series).fillna(0.0)
    correl = quadro.corr().fillna(0.0)

    avaliacao = {nome: pb.metricas(serie) for nome, serie in series.items()}
    elegiveis: list[str] = []
    recusadas: list[str] = []
    for nome in ordem:
        m = avaliacao.get(nome)
        if m is None:
            continue
        if m["resultado"] <= 0:
            recusadas.append(f"{nome}: resultado negativo")
        elif m["recuperacao"] < recuperacao_minima:
            recusadas.append(
                f"{nome}: recuperacao {m['recuperacao']:.2f} "
                f"abaixo de {recuperacao_minima:g}")
        else:
            elegiveis.append(nome)

    escolhidas: list[str] = []
    for nome in elegiveis:
        if len(escolhidas) >= maximo:
            break
        if not escolhidas:
            escolhidas.append(nome)
            continue
        pior = max(correl.loc[nome, j] for j in escolhidas)
        if pior <= teto:
            escolhidas.append(nome)
    return escolhidas, recusadas
```

- [ ] **Step 4: Run to verify it passes**

Run: `"C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python313\python.exe" test_auto_manager_live.py`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add auto_manager_live.py test_auto_manager_live.py
git commit -m "feat(auto-manager-live): tier-priority correlation-capped selection"
```

---

### Task 4: Account-splitting rule (hard constraints only)

**Files:**
- Modify: `auto_manager_live.py`
- Test: `test_auto_manager_live.py`

**Interfaces:**
- Consumes: `SYSTEM_STATUS`, `ASSET_CLASS_OF`, `capital_minimo_classe()` (Task 1)
- Produces: `contas_necessarias(combos: list[dict], saldo_conta: float) -> list[dict]` — each combo dict needs `"chave"`, `"simbolo"`, `"sistema"`. Returns a list of `{"tipo": "hedging" | "normal", "capital_minimo": float, "combos": list[str]}`.

- [ ] **Step 1: Add the failing test**

Append to `test_auto_manager_live.py`:

```python
# --- contas_necessarias -------------------------------------------------------
forex_a = {"chave": "S1", "simbolo": "EURUSD", "sistema": "01_SLTP"}
forex_b = {"chave": "S2", "simbolo": "GBPUSD", "sistema": "02_SLTP_ORGANIC"}
metais_a = {"chave": "S4", "simbolo": "XAUUSD", "sistema": "01_SLTP"}
hedge_a = {"chave": "S3", "simbolo": "XAUUSD", "sistema": "07_GRID_SEPARATE"}

# Caso A: so RESEARCH, uma classe, saldo cobre -> 1 conta.
contas = aml.contas_necessarias([forex_a, forex_b], saldo_conta=1000)
checar("caso A: 1 conta so", len(contas), 1)
checar("caso A: tipo normal", contas[0]["tipo"], "normal")
checar("caso A: capital minimo = 500 (Forex)", contas[0]["capital_minimo"], 500)
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
checar("caso C: capitais 500 e 10000", capitais, [500, 10000])

# Caso D: saldo desconhecido (0) -> nao forca split.
contas = aml.contas_necessarias([forex_a, metais_a], saldo_conta=0)
checar("caso D: 1 conta so quando saldo e desconhecido", len(contas), 1)
```

- [ ] **Step 2: Run to verify it fails**

Run: `"C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python313\python.exe" test_auto_manager_live.py`
Expected: `AttributeError: module 'auto_manager_live' has no attribute 'contas_necessarias'`

- [ ] **Step 3: Implement**

Append to `auto_manager_live.py`:

```python
def contas_necessarias(combos: list[dict], saldo_conta: float) -> list[dict]:
    """Particiona os combos de uma sugestao em contas, so por restricao dura
    (secao 8 do plano -- nunca por preferencia de diversificacao):

      MISTURA DE TIER   combo HEDGE_ACCOUNT_REQUIRED (07/08) sempre isolado
                        numa conta de hedging separada dos demais tiers.
      CAPITAL MINIMO    soma dos capitais minimos das classes de ativo
                        presentes no resto excede `saldo_conta` -> particiona
                        por classe ate caber. saldo_conta<=0 (desconhecido)
                        nunca forca split -- assume que cabe.
    """
    hedge = [c for c in combos
            if SYSTEM_STATUS.get(c["sistema"]) == "HEDGE_ACCOUNT_REQUIRED"]
    normais = [c for c in combos if c not in hedge]

    contas: list[dict] = []
    if hedge:
        capital_hedge = max(
            (capital_minimo_classe(c["simbolo"]) or 0.0) for c in hedge)
        contas.append({
            "tipo": "hedging",
            "capital_minimo": capital_hedge,
            "combos": [c["chave"] for c in hedge],
        })

    if normais:
        classes_presentes = sorted({
            ASSET_CLASS_OF.get(c["simbolo"]) for c in normais
            if ASSET_CLASS_OF.get(c["simbolo"])})
        capital_total = sum(CLASSES[classe].capital_base
                            for classe in classes_presentes)
        if saldo_conta <= 0 or capital_total <= saldo_conta or not classes_presentes:
            contas.append({
                "tipo": "normal",
                "capital_minimo": capital_total,
                "combos": [c["chave"] for c in normais],
            })
        else:
            for classe in classes_presentes:
                membros = [c for c in normais
                          if ASSET_CLASS_OF.get(c["simbolo"]) == classe]
                contas.append({
                    "tipo": "normal",
                    "capital_minimo": CLASSES[classe].capital_base,
                    "combos": [c["chave"] for c in membros],
                })
    return contas
```

- [ ] **Step 4: Run to verify it passes**

Run: `"C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python313\python.exe" test_auto_manager_live.py`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add auto_manager_live.py test_auto_manager_live.py
git commit -m "feat(auto-manager-live): hard-constraint account-splitting rule"
```

---

### Task 5: Report-to-series loader and the numbered suggestion queue

**Files:**
- Modify: `auto_manager_live.py`
- Test: `test_auto_manager_live.py`

**Interfaces:**
- Consumes: `portfolio_builder.ler_html(path: Path) -> pd.DataFrame | None`, `portfolio_builder.serie_diaria(trades: pd.DataFrame) -> pd.Series`, `portfolio_builder.alocar(series, nomes) -> dict[str, float]` (all existing), plus `ordenar_candidatos`, `selecionar_ordenado`, `contas_necessarias` (Tasks 2-4)
- Produces:
  - `carregar_series_certificadas(sets_certificados: list[dict], relatorios_dir: Path) -> dict[str, pd.Series]` — combo dicts need `"chave"`, `"certificado"`, `"relatorio_dir"`.
  - `montar_sugestoes(sets_certificados: list[dict], series_por_chave: dict[str, pd.Series], saldo_conta: float, max_por_sugestao: int = 8, teto_correlacao: float = 0.5, recuperacao_minima: float = 1.0) -> list[dict]` — each item: `{"numero": int, "combos": [{"chave", "simbolo", "sistema", "variante", "peso"}, ...], "contas": [...]}` (contas shape from Task 4).

- [ ] **Step 1: Add the failing tests**

Append to `test_auto_manager_live.py`:

```python
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

relatorio_html = pd.DataFrame({
    "Order": [1, 2, 3, 4, 5, 6],
    "Symbol": ["EURUSD"] * 6,
    "Type": ["buy"] * 6,
    "Volume": [0.01] * 6,
    "Time": ["2026.01.01 00:00", "2026.01.01 01:00", "2026.01.02 00:00",
             "2026.01.02 01:00", "2026.01.03 00:00", "2026.01.03 01:00"],
    "Profit": [10.0, -2.0, 8.0, -1.0, 9.0, 3.0],
}).to_html(index=False)

with tempfile.TemporaryDirectory() as tmp:
    relatorios_dir = _Path(tmp)
    pasta_combo = relatorios_dir / "combo_1"
    pasta_combo.mkdir()
    (pasta_combo / "conf_wrx.htm").write_text(relatorio_html, encoding="utf-8")

    pool = [
        {"chave": "com_relatorio", "certificado": True, "relatorio_dir": "combo_1"},
        {"chave": "sem_relatorio_dir", "certificado": True, "relatorio_dir": None},
        {"chave": "nao_certificado", "certificado": False, "relatorio_dir": "combo_1"},
        {"chave": "arquivo_ausente", "certificado": True, "relatorio_dir": "combo_2"},
    ]
    series = aml.carregar_series_certificadas(pool, relatorios_dir)
    checar("so o combo com relatorio legivel entra", list(series.keys()),
           ["com_relatorio"])
    checar("serie tem 3 dias (resample diario)", len(series["com_relatorio"]), 3)
```

- [ ] **Step 2: Run to verify it fails**

Run: `"C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python313\python.exe" test_auto_manager_live.py`
Expected: `AttributeError: module 'auto_manager_live' has no attribute 'montar_sugestoes'`

- [ ] **Step 3: Implement**

Append to `auto_manager_live.py`:

```python
def carregar_series_certificadas(sets_certificados: list[dict],
                                 relatorios_dir: Path) -> dict[str, pd.Series]:
    """Serie diaria de lucro por combo certificado, extraida do relatorio de
    confirmacao arquivado (conf_wrx.htm) -- mesmo parser que
    portfolio_builder.py usa pra relatorio do Strategy Tester. Combo sem
    relatorio legivel simplesmente nao entra: sem serie, sem correlacao pra
    medir, nao da pra sugerir em combinacao."""
    series: dict[str, pd.Series] = {}
    for combo in sets_certificados:
        if not combo.get("certificado") or not combo.get("relatorio_dir"):
            continue
        caminho = relatorios_dir / combo["relatorio_dir"] / "conf_wrx.htm"
        if not caminho.is_file():
            continue
        trades = pb.ler_html(caminho)
        if trades is None or trades.empty:
            continue
        series[combo["chave"]] = pb.serie_diaria(trades)
    return series


def montar_sugestoes(sets_certificados: list[dict],
                     series_por_chave: dict[str, pd.Series],
                     saldo_conta: float, max_por_sugestao: int = 8,
                     teto_correlacao: float = 0.5,
                     recuperacao_minima: float = 1.0) -> list[dict]:
    """Fila numerada de sugestoes de combinacao pronta pra subir ao vivo.

    Espera receber so combos AINDA NAO implantados (quem chama filtra --
    mesmo escopo de _sets_certificados() do dashboard, sem os ja marcados).
    Cada rodada tira do pool os combos escolhidos e tenta montar a proxima
    sugestao com o que sobrou, ate esgotar os elegiveis."""
    por_chave = {c["chave"]: c for c in sets_certificados}
    pendentes = [c for c in sets_certificados if c["chave"] in series_por_chave]
    sugestoes: list[dict] = []
    numero = 1
    while pendentes:
        ordenados = ordenar_candidatos(pendentes)
        ordem = [c["chave"] for c in ordenados]
        series = {chave: series_por_chave[chave] for chave in ordem}
        escolhidas, _recusadas = selecionar_ordenado(
            series, ordem, max_por_sugestao, teto_correlacao,
            recuperacao_minima)
        if not escolhidas:
            break
        pesos = pb.alocar(series, escolhidas)
        sugestoes.append({
            "numero": numero,
            "combos": [
                {"chave": chave, "simbolo": por_chave[chave]["simbolo"],
                 "sistema": por_chave[chave]["sistema"],
                 "variante": por_chave[chave]["variante"],
                 "peso": pesos[chave]}
                for chave in escolhidas
            ],
            "contas": contas_necessarias(
                [por_chave[chave] for chave in escolhidas], saldo_conta),
        })
        pendentes = [c for c in pendentes if c["chave"] not in escolhidas]
        numero += 1
    return sugestoes
```

- [ ] **Step 4: Run to verify it passes**

Run: `"C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python313\python.exe" test_auto_manager_live.py`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add auto_manager_live.py test_auto_manager_live.py
git commit -m "feat(auto-manager-live): report loader and numbered suggestion queue"
```

---

### Task 6: `GET /api/implantacao/sugestoes` endpoint

**Files:**
- Modify: `dashboard_campanha.py`

**Interfaces:**
- Consumes: `_sets_certificados()` (existing, `dashboard_campanha.py`), `auto_manager_live.carregar_series_certificadas`, `auto_manager_live.montar_sugestoes` (Task 5)
- Produces: `GET /api/implantacao/sugestoes?saldo=<float>` → `{"sugestoes": [...]}` (same shape `montar_sugestoes` returns)

- [ ] **Step 1: Add the import**

In `dashboard_campanha.py`, next to the other local imports near the top (around line 63-67):

```python
import optimize_sets as base
import ready_library
import relatorio_resumo
import auto_manager_live
from generate_system_sets import ASSETS, CLASSES, SYSTEMS
from mt5_runner import fechar_terminal, terminal_aberto
```

- [ ] **Step 2: Add the endpoint**

Add directly after the existing `implantacao()` function (which ends right before `_NOMES_RELATORIO_VALIDOS = {"conf_wrx", "sobrevivencia"}`, i.e. right after the current `@app.get("/api/implantacao")` block):

```python
@app.get("/api/implantacao/sugestoes")
def implantacao_sugestoes(saldo: float = 0.0) -> JSONResponse:
    """Fila numerada de combinacoes sugeridas pra subir ao vivo -- so entre os
    certificados que ainda NAO estao marcados como implantados. Aceitar uma
    sugestao e o /api/implantacao/marcar de sempre, por chave -- este
    endpoint so calcula a fila, nunca escreve em sets_implantados.json."""
    disponiveis = [s for s in _sets_certificados()
                  if s["certificado"] and not s["implantado"]]
    series = auto_manager_live.carregar_series_certificadas(
        disponiveis, RELATORIOS_DIR)
    sugestoes = auto_manager_live.montar_sugestoes(disponiveis, series, saldo)
    return JSONResponse({"sugestoes": sugestoes})
```

- [ ] **Step 3: Manually verify against a secondary dashboard instance**

The dashboard on port 8020 is mid-campaign — do not touch it. Start a second, disposable instance instead:

```bash
cd "C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot"
"C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python313\python.exe" dashboard_campanha.py --port 8099
```

In another terminal:

```bash
curl "http://127.0.0.1:8099/api/implantacao/sugestoes?saldo=100"
```

Expected: valid JSON with a `"sugestoes"` key (an array — empty is fine if there are currently 0 certified-and-undeployed combos with a readable report; check `/api/implantacao` on the same instance first to see what's certified). Stop the instance (Ctrl+C) once confirmed — it was only for this check, it must not keep running alongside the real one on 8020.

- [ ] **Step 4: Commit**

```bash
git add dashboard_campanha.py
git commit -m "feat(auto-manager-live): expose suggestion queue via /api/implantacao/sugestoes"
```

---

### Task 7: Deployment-suggestions panel in the dashboard UI

**Files:**
- Modify: `dashboard_static/index.html`
- Modify: `dashboard_static/app.js`

**Interfaces:**
- Consumes: `GET /api/implantacao/sugestoes?saldo=<float>` (Task 6), existing `POST /api/implantacao/marcar` (unmodified), existing `api()`/`post()` helpers and `implantacaoSets`/`carregarImplantacao()` (`app.js`)
- Produces: two new module-level JS functions, `carregarSugestoes()` and `renderizarSugestao()`, plus a new box in the Deployment tab. No new backend surface beyond Task 6.

- [ ] **Step 1: Add the HTML**

In `dashboard_static/index.html`, inside `<section id="painel-implantacao" class="painel">`, right after the closing `</table>` of `#tbl-implantacao` and before the section's closing `</div></section>`:

```html
  <div class="box">
    <h2>Deployment suggestions</h2>
    <p class="status-msg">Combinations of certified, not-yet-deployed sets that fit
      together (low correlation), ordered by risk tier first (research systems
      before grid/martingale). Each suggestion states how many live accounts it
      needs — never assumes just one.</p>
    <div class="linha" style="margin:10px 0">
      <label>Account balance: $<input type="number" id="sugestoes-saldo" value="100" style="width:90px"></label>
      <button class="acao secundario" id="btn-sugestoes-recarregar">Recalculate</button>
      <button class="acao secundario" id="btn-implantacao-marcar-tudo">Mark all certified as deployed</button>
      <button class="acao secundario" id="btn-implantacao-desmarcar-tudo">Mark none as deployed</button>
    </div>
    <div id="caixa-sugestao"><span class="status-msg">no suggestion loaded yet — click Recalculate.</span></div>
    <div class="linha" style="margin-top:10px;align-items:center;gap:10px">
      <button class="acao secundario" id="btn-sugestao-anterior">&larr; Previous</button>
      <span id="sugestao-posicao" class="status-msg"></span>
      <button class="acao secundario" id="btn-sugestao-proxima">Next suggestion &rarr;</button>
    </div>
    <span class="status-msg" id="msg-sugestoes"></span>
  </div>
```

- [ ] **Step 2: Add the JS**

In `dashboard_static/app.js`, append after the existing implantacao section (after the `btn-implantacao-exportar` click handler at the end of the file):

```js
// -------------------------------------------------------- sugestoes (AutoManagerLive)

let sugestoesFila = [];
let sugestaoCursor = 0;

function renderizarSugestao() {
  const caixa = document.getElementById("caixa-sugestao");
  const posicao = document.getElementById("sugestao-posicao");
  if (!sugestoesFila.length) {
    caixa.innerHTML = `<span class="status-msg">no suggestion available -- every certified set is already deployed, or none has a readable report yet.</span>`;
    posicao.textContent = "";
    return;
  }
  if (sugestaoCursor >= sugestoesFila.length) sugestaoCursor = sugestoesFila.length - 1;
  const s = sugestoesFila[sugestaoCursor];
  const combosHtml = s.combos.map((c) =>
    `<li>${c.simbolo} / ${c.sistema} / ${c.variante} — weight ${(c.peso * 100).toFixed(1)}%</li>`
  ).join("");
  const contasHtml = s.contas.map((c) =>
    `<li>${c.tipo === "hedging" ? "Hedging account" : "Account"} (min. capital $${c.capital_minimo.toFixed(0)}): ${c.combos.length} combo(s)</li>`
  ).join("");
  caixa.innerHTML = `
    <h3>Suggestion #${s.numero}</h3>
    <p><b>${s.contas.length} account(s) needed:</b></p>
    <ul>${contasHtml}</ul>
    <p><b>Combos:</b></p>
    <ul>${combosHtml}</ul>
    <button class="acao" id="btn-sugestao-marcar">Mark this suggestion as deployed</button>`;
  posicao.textContent = `${sugestaoCursor + 1} / ${sugestoesFila.length}`;
  document.getElementById("btn-sugestao-marcar").addEventListener("click", async () => {
    const chaves = s.combos.map((c) => c.chave);
    await post("/api/implantacao/marcar", { chaves, implantado: true });
    await carregarImplantacao();
    await carregarSugestoes();
  });
}

async function carregarSugestoes() {
  const saldo = parseFloat(document.getElementById("sugestoes-saldo").value) || 0;
  const d = await api(`/api/implantacao/sugestoes?saldo=${saldo}`);
  sugestoesFila = d.sugestoes || [];
  sugestaoCursor = 0;
  renderizarSugestao();
}

document.getElementById("btn-sugestoes-recarregar").addEventListener("click", carregarSugestoes);
document.getElementById("btn-sugestao-proxima").addEventListener("click", () => {
  if (sugestaoCursor < sugestoesFila.length - 1) sugestaoCursor++;
  renderizarSugestao();
});
document.getElementById("btn-sugestao-anterior").addEventListener("click", () => {
  if (sugestaoCursor > 0) sugestaoCursor--;
  renderizarSugestao();
});
document.getElementById("btn-implantacao-marcar-tudo").addEventListener("click", async () => {
  const msg = document.getElementById("msg-sugestoes");
  const chaves = implantacaoSets.filter((s) => s.certificado).map((s) => s.chave);
  await post("/api/implantacao/marcar", { chaves, implantado: true });
  msg.textContent = `marked ${chaves.length} certified set(s) as deployed.`;
  msg.className = "status-msg ok";
  await carregarImplantacao();
  await carregarSugestoes();
});
document.getElementById("btn-implantacao-desmarcar-tudo").addEventListener("click", async () => {
  const msg = document.getElementById("msg-sugestoes");
  const chaves = implantacaoSets.filter((s) => s.certificado).map((s) => s.chave);
  await post("/api/implantacao/marcar", { chaves, implantado: false });
  msg.textContent = `cleared deployed flag on ${chaves.length} set(s).`;
  msg.className = "status-msg ok";
  await carregarImplantacao();
  await carregarSugestoes();
});
```

- [ ] **Step 3: Wire it into the tab-open handler**

In `dashboard_static/app.js`, find the tab-switch handler (`if (btn.dataset.tab === "implantacao") carregarImplantacao();`, around line 947) and change it to also load suggestions:

```js
    if (btn.dataset.tab === "implantacao") { carregarImplantacao(); carregarSugestoes(); }
```

- [ ] **Step 4: Manually verify in a browser, against the disposable instance**

```bash
cd "C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot"
"C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python313\python.exe" dashboard_campanha.py --port 8099
```

Open `http://127.0.0.1:8099/` in a browser, go to the Deployment tab, and confirm:
- The new "Deployment suggestions" box renders below the existing Certified sets table.
- Clicking Recalculate calls the endpoint and either shows a suggestion card or the "no suggestion available" message, without a JS console error.
- If there is at least one certified, undeployed combo with an archived report: the suggestion card shows account count/type and the combo list; clicking "Mark this suggestion as deployed" checks the corresponding row's Deployed checkbox in the table above.
- "Mark all certified as deployed" / "Mark none as deployed" toggle every row's Deployed checkbox in one click.
- Prev/Next buttons move between suggestions without any network call (pure client-side cursor).

Stop the instance (Ctrl+C) once confirmed.

- [ ] **Step 5: Commit**

```bash
git add dashboard_static/index.html dashboard_static/app.js
git commit -m "feat(auto-manager-live): deployment-suggestions panel in the dashboard UI"
```

---

## Self-Review Notes

- **Spec coverage:** suggestion engine (Tasks 3, 5) ✓; numbered queue (Task 5) ✓; hard-constraint account splitting, hedge-tier isolation and per-class capital (Task 4) ✓; sibling-account model — satisfied structurally: `contas_necessarias` never assumes one account, `montar_sugestoes`/the endpoint never reference a single fixed account, and pairing a suggestion's per-account combo list with `auto_set_manager.py`'s `PERFIL_MODELO` for a specific real account stays a manual step, same as export already is today ✓; UI mark-suggestion/mark-all/next-suggestion (Task 7) ✓. Live promotion/demotion is explicitly excluded (Global Constraints) with the reason stated.
- **Placeholder scan:** no TBD/TODO; every step has real code.
- **Type consistency:** `combos` dicts carry `chave`/`simbolo`/`sistema`/`variante` consistently from `_sets_certificados()` (Task 6) through `montar_sugestoes` (Task 5) to the frontend (Task 7); `contas` shape (`tipo`/`capital_minimo`/`combos`) is identical between Task 4's return value and Task 7's rendering.
