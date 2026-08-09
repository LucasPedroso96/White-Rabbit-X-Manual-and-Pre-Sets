# Deposit Auto-suggest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a checkbox next to the dashboard's Deposit field that auto-fills it with the recommended capital for the asset classes in play, instead of always requiring a hand-typed number.

**Architecture:** Pure client-side change in the Autobot dashboard's static frontend (`Autobot/dashboard_static/index.html` + `app.js`). A single function reads which asset classes are "in play" (checked assets in Modo Manual, or the whole catalog in Modo Automático) and writes the highest `capital_base` among them into the existing `campo-deposito` input, locking it while the checkbox is on. No backend or API changes — `/api/config` already returns `capital_base` per class.

**Tech Stack:** Vanilla JS/DOM (no framework), served as static files by `dashboard_campanha.py`. There is no JS test runner in this project (no `package.json`, no Jest/Playwright — confirmed by search) and no browser-automation harness. Every task's "test" step is therefore manual: run `python dashboard_campanha.py` (or use the instance already running on this machine, port 8020), open `http://127.0.0.1:8020/`, and check concrete, observable states (element attributes/values), listed step by step below. Where useful, a one-line browser-console snippet is given to make the check exact instead of eyeballed.

## Global Constraints

- No backend/API changes — everything lives in `index.html` and `app.js` (from spec `docs/superpowers/specs/2026-08-08-deposit-auto-suggest-design.md`).
- Checkbox defaults to **checked** in both modes.
- **Modo Manual**: checkbox is togglable. Checked → `campo-deposito` is `disabled` and shows the highest `capital_base` among classes with ≥1 checked asset (fallback `500` if none checked). Unchecked → `campo-deposito` is enabled and resets to `500`.
- **Modo Automático**: checkbox is always checked and `disabled` (no user override) — value is the highest `capital_base` across **all** classes in the catalog.
- Real class values come from `CLASSES` in `generate_system_sets.py`, surfaced via `/api/config` → `classes[codigo].capital_base`. Today: Forex 500, Cryptocurrencies 2500, Indices/Energies 2500, US Stocks CFD 5000, Metals 10000. No hardcoded duplicate table — always read from what `/api/config` already provides.
- New UI string gets a `data-i18n` key translated across all **11** languages already supported in `app.js` (`en, pt, es, de, fr, it, ru, zh, ja, ko, tr` — confirmed by grep, matches `<select id="lang-picker">` in `index.html:20-30`), matching the existing full-coverage convention (every other `setup.*` key has all 11).
- No new dependencies, build step, or CSS files — follow the existing inline-`style=` convention already used in this HTML for one-off spacing (e.g. `index.html:97`, `:107`) instead of adding CSS classes.

---

### Task 1: Checkbox markup + i18n label (11 languages)

**Files:**

- Modify: `Autobot/dashboard_static/index.html:120`
- Modify: `Autobot/dashboard_static/app.js` (11 single-line insertions, one per language block: lines 44, 121, 198, 275, 352, 429, 506, 583, 660, 737, 814)

**Interfaces:**

- Consumes: existing `data-i18n` translation mechanism (`applyTranslations()`, already wired elsewhere in `app.js`).
- Produces: `#chk-deposito-auto` (checkbox, `checked` by default), `#campo-deposito` now carries a static `disabled` attribute by default, i18n key `'setup.deposit-auto'` available in all 11 language tables for later tasks/labels.

- [ ] **Step 1: Add the checkbox to the Parameters row**

In `Autobot/dashboard_static/index.html`, replace line 120:

```html
        <div><label class="campo" data-i18n="setup.deposit">Deposit</label><input type="number" id="campo-deposito" value="500"></div>
```

with:

```html
        <div><label class="campo" data-i18n="setup.deposit">Deposit</label><input type="number" id="campo-deposito" value="500" disabled>
          <label style="display:inline-block; margin-left:8px; font-weight:normal"><input type="checkbox" id="chk-deposito-auto" checked> <span data-i18n="setup.deposit-auto">Auto-suggest</span></label>
        </div>
```

- [ ] **Step 2: Add the translated label to all 11 language blocks in app.js**

In `Autobot/dashboard_static/app.js`, each language block has a `'setup.deposit': '...'` line. Insert one new line immediately after **each** of the 11 occurrences, exactly as listed. Every inserted line gets the same 4-space indent as the `'setup.deposit'` line above it (not shown in the table below to keep the code spans clean):

| Language | Insert after | New line to insert (indent 4 spaces) |
| --- | --- | --- |
| en | line 44 | `'setup.deposit-auto': 'Auto-suggest',` |
| pt | line 121 | `'setup.deposit-auto': 'Sugerir automaticamente',` |
| es | line 198 | `'setup.deposit-auto': 'Sugerir automáticamente',` |
| de | line 275 | `'setup.deposit-auto': 'Automatisch vorschlagen',` |
| fr | line 352 | `'setup.deposit-auto': 'Suggestion automatique',` |
| it | line 429 | `'setup.deposit-auto': 'Suggerisci automaticamente',` |
| ru | line 506 | `'setup.deposit-auto': 'Предлагать автоматически',` |
| zh | line 583 | `'setup.deposit-auto': '自动建议',` |
| ja | line 660 | `'setup.deposit-auto': '自動提案',` |
| ko | line 737 | `'setup.deposit-auto': '자동 제안',` |
| tr | line 814 | `'setup.deposit-auto': 'Otomatik öner',` |

Each row is independent (same key, 11 language blocks) — e.g. for `en`, line 44 currently reads `    'setup.deposit': 'Deposit',`; insert the new `en` row's line directly below it, inside the same `en: { ... }` object literal. Repeat for each of the other 10 rows in their own language block.

- [ ] **Step 3: Manual verification**

Start the dashboard if it isn't already running: `python dashboard_campanha.py` from `Autobot/` (or reuse the instance already running on this machine — check with a browser at `http://127.0.0.1:8020/`). Open the "Run setup" tab.

Confirm:

1. A checked checkbox labeled "Auto-suggest" appears immediately to the right of the Deposit field.
2. The Deposit field looks disabled (greyed out, not editable).
3. Switch the language picker (top right) through a few languages (e.g. `pt`, `de`, `ja`) — the new checkbox's label text changes each time, matching the translations above.

- [ ] **Step 4: Commit**

```bash
git add Autobot/dashboard_static/index.html Autobot/dashboard_static/app.js
git commit -m "feat: add auto-suggest checkbox markup and i18n label for Deposit field"
```

---

### Task 2: Suggestion engine + mode integration

**Files:**

- Modify: `Autobot/dashboard_static/app.js:1135-1160` (`setModo`, `carregarConfig`)

**Interfaces:**

- Consumes: `#chk-deposito-auto`, `#campo-deposito`, `#grupos-ativos` (from Task 1 and existing markup), global `modoAtual` (existing).
- Produces: global function `atualizarDepositoSugerido()` — no args, no return, reads DOM state and mutates `#campo-deposito`/`#chk-deposito-auto`. Task 3 calls this function from the asset-picking interaction points. Also produces a `data-capital-base` attribute on every `#grupos-ativos fieldset`, which `atualizarDepositoSugerido()` depends on.

- [ ] **Step 1: Tag each class fieldset with its capital_base, add the engine, and recompute at the end of carregarConfig**

In `Autobot/dashboard_static/app.js`, replace:

```js
  const grupos = document.getElementById("grupos-ativos");
  grupos.innerHTML = Object.entries(CONFIG.classes).map(([classe, info]) => `
    <fieldset><legend>${classe} (capital base ${info.capital_base})
      <button type="button" class="btn-classe-todos">all</button>
      <button type="button" class="btn-classe-nenhum">none</button>
    </legend>
    <div class="grid-check">${info.ativos.map((a) =>
      `<label><input type="checkbox" class="chk-ativo" value="${a}"> ${a}</label>`).join("")}</div>
    </fieldset>`).join("");
}
carregarConfig();
```

with:

```js
  const grupos = document.getElementById("grupos-ativos");
  grupos.innerHTML = Object.entries(CONFIG.classes).map(([classe, info]) => `
    <fieldset data-capital-base="${info.capital_base}"><legend>${classe} (capital base ${info.capital_base})
      <button type="button" class="btn-classe-todos">all</button>
      <button type="button" class="btn-classe-nenhum">none</button>
    </legend>
    <div class="grid-check">${info.ativos.map((a) =>
      `<label><input type="checkbox" class="chk-ativo" value="${a}"> ${a}</label>`).join("")}</div>
    </fieldset>`).join("");
  atualizarDepositoSugerido();
}

function maiorCapitalBase(somenteMarcados) {
  let maior = null;
  document.querySelectorAll("#grupos-ativos fieldset").forEach((fs) => {
    if (somenteMarcados && !fs.querySelector(".chk-ativo:checked")) return;
    const base = Number(fs.dataset.capitalBase);
    if (maior === null || base > maior) maior = base;
  });
  return maior;
}

function atualizarDepositoSugerido() {
  const chk = document.getElementById("chk-deposito-auto");
  const campo = document.getElementById("campo-deposito");
  if (modoAtual === "auto") {
    chk.checked = true;
    chk.disabled = true;
    campo.disabled = true;
    const maior = maiorCapitalBase(false);
    if (maior !== null) campo.value = maior;
    return;
  }
  chk.disabled = false;
  if (chk.checked) {
    campo.disabled = true;
    const maior = maiorCapitalBase(true);
    campo.value = maior !== null ? maior : 500;
  } else {
    campo.disabled = false;
  }
}
carregarConfig();
document.getElementById("chk-deposito-auto").addEventListener("change", (ev) => {
  if (!ev.target.checked) document.getElementById("campo-deposito").value = 500;
  atualizarDepositoSugerido();
});
```

(the `atualizarDepositoSugerido();` call at the end of `carregarConfig()` itself is new — it makes the field correct from first paint, since `modoAtual` already defaults to `"auto"` before the user touches anything; function declarations are hoisted, so `atualizarDepositoSugerido`/`maiorCapitalBase` are callable from inside `carregarConfig()` even though they're defined textually after it)

- [ ] **Step 2: Wire mode switching**

Replace `setModo` (currently):

```js
function setModo(m) {
  modoAtual = m;
  document.getElementById("btn-modo-auto").classList.toggle("ativo", m === "auto");
  document.getElementById("btn-modo-manual").classList.toggle("ativo", m === "manual");
  document.getElementById("bloco-manual").style.display = m === "manual" ? "block" : "none";
}
```

with:

```js
function setModo(m) {
  modoAtual = m;
  document.getElementById("btn-modo-auto").classList.toggle("ativo", m === "auto");
  document.getElementById("btn-modo-manual").classList.toggle("ativo", m === "manual");
  document.getElementById("bloco-manual").style.display = m === "manual" ? "block" : "none";
  atualizarDepositoSugerido();
}
```

- [ ] **Step 3: Manual verification**

Reload `http://127.0.0.1:8020/` (Run setup tab).

1. On first load (default mode is Automático): open the browser console and run `document.getElementById("campo-deposito").value` — expect `"10000"` (today's highest `capital_base`, Metals) and `document.getElementById("campo-deposito").disabled` — expect `true`. `document.getElementById("chk-deposito-auto").disabled` — expect `true` (locked, matches spec's "always automatic" rule for this mode).
2. Click "Manual" mode. The checkbox is now togglable (`chk-deposito-auto.disabled === false`). With no asset checked yet, `campo-deposito.value` should read `"500"` (fallback).
3. Manually check one `EURUSD`-class asset via devtools: `document.querySelector('.chk-ativo').checked = true` does NOT trigger the listener (this specific manual step doesn't fire `change` — that's expected, Task 3 wires this). Instead, toggle the auto-suggest checkbox off then on again — `campo-deposito.value` should recompute and still show `"500"` if the class you touched is Forex, or the correct number if you checked an asset in a pricier class.
4. Uncheck "Auto-suggest" — field becomes editable (`disabled === false`) and resets to `"500"`.
5. Switch back to "Automático" mode — checkbox re-locks checked, field goes back to `"10000"` and `disabled`.

- [ ] **Step 4: Commit**

```bash
git add Autobot/dashboard_static/app.js
git commit -m "feat: compute suggested Deposit from selected asset classes"
```

---

### Task 3: Live wiring for asset-selection interactions

**Files:**

- Modify: `Autobot/dashboard_static/app.js:1163-1177` (bulk select/clear buttons)
- Modify: `Autobot/dashboard_static/app.js` (`btn-detectar` handler, inside the `pollJob` callback)

**Interfaces:**

- Consumes: `atualizarDepositoSugerido()` from Task 2.
- Produces: nothing new for later tasks — this is the terminal task, it makes the Manual-mode suggestion live as the user actually picks assets (today, checking `.chk-ativo` only updates on the next checkbox toggle or mode switch, per Task 2's Step 3.3 workaround).

- [ ] **Step 1: React to individual asset checkboxes**

Immediately after the existing `grupos-ativos` click listener (the one handling `.btn-classe-todos`/`.btn-classe-nenhum`), add a second, `change`-based listener on the same container — checkbox `change` events bubble, so this catches every direct click on a `.chk-ativo` without touching each checkbox individually:

```js
document.getElementById("grupos-ativos").addEventListener("change", (ev) => {
  if (ev.target.classList.contains("chk-ativo")) atualizarDepositoSugerido();
});
```

- [ ] **Step 2: React to the bulk select-all/clear-all buttons**

These currently mutate `.checked` via `forEach`, which does not fire `change` — each handler needs an explicit call. Replace:

```js
document.getElementById("btn-ativos-todos").addEventListener("click", () =>
  document.querySelectorAll(".chk-ativo").forEach((c) => { c.checked = true; }));
document.getElementById("btn-ativos-nenhum").addEventListener("click", () =>
  document.querySelectorAll(".chk-ativo").forEach((c) => { c.checked = false; }));
document.getElementById("grupos-ativos").addEventListener("click", (ev) => {
  const todos = ev.target.closest(".btn-classe-todos");
  const nenhum = ev.target.closest(".btn-classe-nenhum");
  if (!todos && !nenhum) return;
  ev.target.closest("fieldset").querySelectorAll(".chk-ativo")
    .forEach((c) => { c.checked = !!todos; });
});
```

with:

```js
document.getElementById("btn-ativos-todos").addEventListener("click", () => {
  document.querySelectorAll(".chk-ativo").forEach((c) => { c.checked = true; });
  atualizarDepositoSugerido();
});
document.getElementById("btn-ativos-nenhum").addEventListener("click", () => {
  document.querySelectorAll(".chk-ativo").forEach((c) => { c.checked = false; });
  atualizarDepositoSugerido();
});
document.getElementById("grupos-ativos").addEventListener("click", (ev) => {
  const todos = ev.target.closest(".btn-classe-todos");
  const nenhum = ev.target.closest(".btn-classe-nenhum");
  if (!todos && !nenhum) return;
  ev.target.closest("fieldset").querySelectorAll(".chk-ativo")
    .forEach((c) => { c.checked = !!todos; });
  atualizarDepositoSugerido();
});
```

(leave the earlier-added `.addEventListener("change", ...)` from Step 1 as a separate listener on the same element — `click` and `change` are different event types and don't conflict)

- [ ] **Step 3: React to "Detect available now" auto-checking assets**

In the `btn-detectar` click handler, inside the `pollJob` callback, find:

```js
    document.querySelectorAll(".chk-ativo").forEach((c) => {
      // O nome real pode vir com sufixo (EURUSD.HT, EURUSDm...) -- usar esse
      // nome exato, nao o generico da biblioteca, ou o /config: do terminal
      // falha em silencio pra um simbolo que essa conta nao tem (achado
      // 2026-08-06: EURUSD puro em vez de EURUSD.HT -- "sem JSON final" em
      // 12s, nenhum passe rodou de verdade).
      const real = nomes.find((n) => n === c.value || n.startsWith(c.value + "."));
      if (real) {
        c.checked = true;
        c.dataset.real = real;
        const label = c.closest("label");
        if (label && real !== c.value) {
          label.title = `usa ${real} nesta conta`;
          label.classList.add("ativo-resolvido");
        }
      }
    });
  });
});
```

and replace the closing of that `forEach` block with:

```js
    document.querySelectorAll(".chk-ativo").forEach((c) => {
      // O nome real pode vir com sufixo (EURUSD.HT, EURUSDm...) -- usar esse
      // nome exato, nao o generico da biblioteca, ou o /config: do terminal
      // falha em silencio pra um simbolo que essa conta nao tem (achado
      // 2026-08-06: EURUSD puro em vez de EURUSD.HT -- "sem JSON final" em
      // 12s, nenhum passe rodou de verdade).
      const real = nomes.find((n) => n === c.value || n.startsWith(c.value + "."));
      if (real) {
        c.checked = true;
        c.dataset.real = real;
        const label = c.closest("label");
        if (label && real !== c.value) {
          label.title = `usa ${real} nesta conta`;
          label.classList.add("ativo-resolvido");
        }
      }
    });
    atualizarDepositoSugerido();
  });
});
```

- [ ] **Step 4: Manual verification**

Reload `http://127.0.0.1:8020/`, switch to "Manual" mode, keep "Auto-suggest" checked.

1. Click a single asset checkbox in the Forex class (e.g. `EURUSD`) — `campo-deposito.value` immediately becomes `"500"` without touching anything else.
2. Also check one asset in the Metals class (e.g. `XAUUSD`) — value immediately jumps to `"10000"` (the max of the two selected classes).
3. Click "none" on the Metals fieldset's own clear button — value drops back to `"500"` (only Forex left selected).
4. Click "Clear selection" (the global `btn-ativos-nenhum`) — value falls back to `"500"` (nothing selected).
5. Click "Select all assets" (`btn-ativos-todos`) — value becomes `"10000"` (Metals, the priciest class, is now included).
6. If MT5/the dashboard's asset detection is available in this environment, click "Detect available now" and confirm the value updates once detection finishes and checks its matching assets. If detection isn't practical to run here (needs a live MT5 terminal), skip the live run and instead re-read the edited handler to confirm `atualizarDepositoSugerido()` sits inside the `pollJob` callback, after the `forEach`, so it fires once real detection completes.

- [ ] **Step 5: Commit**

```bash
git add Autobot/dashboard_static/app.js
git commit -m "feat: recompute suggested Deposit live as assets are picked"
```
