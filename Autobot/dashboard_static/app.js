// ---------------------------------------------------------------- utilidades

async function api(path, opts) {
  const r = await fetch(path, opts);
  return r.json();
}
async function post(path, body) {
  return api(path, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
}

async function pollJob(jobId, msgEl, onDone) {
  msgEl.textContent = "rodando...";
  msgEl.className = "status-msg";
  const tick = async () => {
    const j = await api(`/api/jobs/${jobId}`);
    if (j.status === "rodando" || j.status === "iniciado") {
      setTimeout(tick, 2000);
      return;
    }
    if (j.status === "feito") {
      msgEl.textContent = "concluído.";
      msgEl.className = "status-msg ok";
    } else {
      msgEl.textContent = "erro: " + (j.saida || "").slice(-300);
      msgEl.className = "status-msg no";
    }
    onDone && onDone(j);
  };
  tick();
}

// ------------------------------------------------------------------- abas

document.querySelectorAll("nav button[data-tab]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("nav button[data-tab]").forEach((b) => b.classList.remove("ativo"));
    document.querySelectorAll(".painel").forEach((p) => p.classList.remove("ativo"));
    btn.classList.add("ativo");
    document.getElementById("painel-" + btn.dataset.tab).classList.add("ativo");
    if (btn.dataset.tab === "biblioteca") carregarBiblioteca();
    if (btn.dataset.tab === "portfolios") carregarPortfolios();
    if (btn.dataset.tab === "custo") carregarCusto();
  });
});

// ---------------------------------------------------------- campanha ao vivo

async function carregarStatus() {
  const d = await api("/api/status");
  const emAndamento = d.atual ? 1 : 0;
  document.getElementById("cards").innerHTML = `
    <div class="card">Feitos<b>${d.total_feitos}</b></div>
    <div class="card">Aprovados<b class="ok">${d.aprovados}</b></div>
    <div class="card">Reprovados<b class="no">${d.reprovados}</b></div>
    <div class="card">Em andamento<b class="live">${emAndamento}</b></div>`;
  const a = d.atual;
  document.getElementById("atual").innerHTML = a
    ? `<b class="live">RODANDO AGORA</b> [${a.posicao}] ${a.simbolo} ${a.sistema} ${a.variante}<br>
       <span style="color:#9aa">${a.estagio || "..."}</span>`
    : `<span style="color:#9aa">Sem combo em andamento.</span>`;
  document.querySelector("#tbl-sistemas tbody").innerHTML =
    Object.entries(d.por_sistema).map(([s, v]) =>
      `<tr><td>${s}</td><td>${v.total}</td><td>${v.aprovados}</td></tr>`).join("");
  document.getElementById("sistema-bars").innerHTML = Object.entries(d.por_sistema).map(([s, v]) => {
    const pct = v.total ? Math.round((v.aprovados / v.total) * 100) : 0;
    return `<div class="bar-item"><div class="bar-label"><span>${s}</span><span>${v.aprovados}/${v.total}</span></div>
      <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
      <div class="bar-note">${pct}% aprovados</div></div>`;
  }).join("") || `<span class="status-msg">sem sistema validado ainda</span>`;
  document.querySelector("#tbl-recentes tbody").innerHTML = d.recentes.map((r) => {
    const ok = r.aprovado;
    return `<tr class="${ok ? "ok" : "no"}"><td>${r.simbolo}</td><td>${r.sistema}</td>
      <td>${r.variante}</td><td><span class="pill ${ok ? "ok" : "no"}">${ok ? "aprovado" : "reprovado"}</span></td>
      <td>${r.retencao_oos ?? "-"}</td><td>${r.minutos ?? "-"}</td></tr>`;
  }).join("");
}

async function carregarEstado() {
  const e = await api("/api/campanha/estado");
  const badgeMt5 = document.getElementById("badge-mt5");
  badgeMt5.textContent = "MT5: " + (e.terminal_aberto ? "ocupado" : "livre");
  badgeMt5.style.background = e.terminal_aberto ? "#3a1b1b" : "#14532d";
  const badgeC = document.getElementById("badge-campanha");
  badgeC.textContent = "Campanha: " + (e.rodando ? "rodando (" + (e.modo || "?") + ")" : "parada");
  badgeC.style.background = e.rodando ? "#14532d" : "#243047";
  document.getElementById("btn-stop").disabled = !e.rodando;
  document.getElementById("btn-iniciar").disabled = e.rodando;
}

document.getElementById("btn-stop").addEventListener("click", async () => {
  const msg = document.getElementById("msg-stop");
  msg.textContent = "parando...";
  const r = await post("/api/campanha/stop");
  msg.textContent = r.ok
    ? `parado. terminal fechado: ${r.terminal_fechado}. entradas incompletas removidas: ${r.entradas_incompletas_removidas}`
    : "erro ao parar";
  msg.className = "status-msg " + (r.ok ? "ok" : "no");
  carregarEstado();
});

setInterval(() => { carregarStatus(); carregarEstado(); }, 8000);
carregarStatus();
carregarEstado();

// ------------------------------------------------------------ configurar corrida

let modoAtual = "auto";
let CONFIG = null;

document.getElementById("btn-modo-auto").addEventListener("click", () => setModo("auto"));
document.getElementById("btn-modo-manual").addEventListener("click", () => setModo("manual"));
function setModo(m) {
  modoAtual = m;
  document.getElementById("btn-modo-auto").classList.toggle("ativo", m === "auto");
  document.getElementById("btn-modo-manual").classList.toggle("ativo", m === "manual");
  document.getElementById("bloco-manual").style.display = m === "manual" ? "block" : "none";
}

async function carregarConfig() {
  CONFIG = await api("/api/config");
  document.getElementById("check-sistemas").innerHTML = CONFIG.sistemas.map((s, i) =>
    `<label><input type="checkbox" value="${s.code}" ${i < 2 ? "checked" : ""}> ${s.code} — ${s.label}</label>`
  ).join("");
  const grupos = document.getElementById("grupos-ativos");
  grupos.innerHTML = Object.entries(CONFIG.classes).map(([classe, info]) => `
    <fieldset><legend>${classe} (capital base ${info.capital_base})</legend>
    <div class="grid-check">${info.ativos.map((a) =>
      `<label><input type="checkbox" class="chk-ativo" value="${a}"> ${a}</label>`).join("")}</div>
    </fieldset>`).join("");
  const chipGrid = document.getElementById("ativos-map");
  chipGrid.innerHTML = Object.entries(CONFIG.classes).map(([classe, info]) => `
    <div class="class-chip">
      <div class="chip-title">${classe}</div>
      <div class="chip-meta">${info.ativos.length} ativos</div>
      <div class="chip-meta">capital base ${info.capital_base}</div>
    </div>`).join("");
}
carregarConfig();

document.getElementById("btn-detectar").addEventListener("click", async () => {
  const msg = document.getElementById("msg-detectar");
  const r = await post("/api/ativos/detectar");
  if (!r.ok) { msg.textContent = r.erro; msg.className = "status-msg no"; return; }
  pollJob(r.job_id, msg, (j) => {
    if (j.status !== "feito") return;
    const linha = (j.saida || "").split("\n").find((l) => l.includes("simbolos"));
    if (!linha) return;
    const nomes = (linha.match(/\(([^)]*)\)/) || [, ""])[1].split(",").map((s) => s.trim());
    document.querySelectorAll(".chk-ativo").forEach((c) => {
      if (nomes.includes(c.value) || nomes.includes(c.value + ".HT")) c.checked = true;
    });
  });
});

document.getElementById("btn-iniciar").addEventListener("click", async () => {
  const msg = document.getElementById("msg-iniciar");
  const body = {
    modo: modoAtual,
    inicio: document.getElementById("campo-inicio").value,
    fim: document.getElementById("campo-fim").value,
    deposit: Number(document.getElementById("campo-deposito").value),
    min_retencao: Number(document.getElementById("campo-retencao").value),
  };
  if (modoAtual === "manual") {
    body.sistemas = [...document.querySelectorAll("#check-sistemas input:checked")].map((c) => c.value);
    body.simbolos = [...document.querySelectorAll(".chk-ativo:checked")].map((c) => c.value);
  }
  const r = await post("/api/campanha/start", body);
  msg.textContent = r.ok ? `iniciado (pid ${r.pid})` : r.erro;
  msg.className = "status-msg " + (r.ok ? "ok" : "no");
  carregarEstado();
});

// -------------------------------------------------------------- biblioteca

async function carregarBiblioteca() {
  const d = await api("/api/biblioteca");
  const el = document.getElementById("info-biblioteca");
  el.textContent = d.manifesto
    ? `${d.manifesto.total_sets} sets | gerado em ${d.manifesto.gerado_em}`
    : "sem biblioteca gerada ainda";
}
document.getElementById("btn-regenerar").addEventListener("click", async () => {
  const msg = document.getElementById("msg-regenerar");
  const r = await post("/api/biblioteca/regenerar");
  if (!r.ok) { msg.textContent = r.erro; msg.className = "status-msg no"; return; }
  pollJob(r.job_id, msg, () => carregarBiblioteca());
});

// -------------------------------------------------------------- portfolios

let portfolioSistemas = {};
let portfolioSelecionado = null;

async function carregarPortfolios() {
  const d = await api("/api/portfolios");
  document.getElementById("mapa-html").innerHTML = d.mapa_html || "sem MAPA.md ainda";
  portfolioSistemas = d.sistemas || {};
  const tabs = document.getElementById("tabs-sistemas-portfolio");
  const nomes = Object.keys(portfolioSistemas);
  tabs.innerHTML = nomes.map((n) => `<button data-sis="${n}">${n}</button>`).join("");
  tabs.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => selecionarPortfolio(b.dataset.sis)));
  if (nomes.length) selecionarPortfolio(nomes[0]);
}
function selecionarPortfolio(nome) {
  portfolioSelecionado = nome;
  document.querySelectorAll("#tabs-sistemas-portfolio button").forEach((b) =>
    b.classList.toggle("ativo", b.dataset.sis === nome));
  document.getElementById("portfolio-sistema-html").innerHTML = portfolioSistemas[nome] || "";
}
document.getElementById("btn-gerar-portfolio").addEventListener("click", async () => {
  const msg = document.getElementById("msg-portfolio");
  const pasta = document.getElementById("portfolio-pasta").value.trim();
  if (!pasta) { msg.textContent = "informe a pasta com os relatórios"; msg.className = "status-msg no"; return; }
  const r = await post("/api/portfolios/gerar", { pasta, nome: portfolioSelecionado || "geral" });
  if (!r.ok) { msg.textContent = r.erro; msg.className = "status-msg no"; return; }
  pollJob(r.job_id, msg, (j) => {
    if (j.status === "feito") msg.textContent = `concluído: ${r.arquivo}`;
  });
});

// ------------------------------------------------------------------ perfil

async function carregarPerfil() {
  document.getElementById("perfil-sistemas").innerHTML = (CONFIG ? CONFIG.sistemas : []).map((s) =>
    `<label><input type="checkbox" class="chk-perfil-sistema" value="${s.code}"> ${s.code}</label>`).join("");
  const d = await api("/api/perfil");
  document.getElementById("ultima-sync").textContent =
    d.ultima_sincronizacao ? JSON.stringify(d.ultima_sincronizacao, null, 2) : "nenhuma ainda";
}
carregarConfig().then(carregarPerfil);

function montarPerfil() {
  const ativos = document.getElementById("perfil-ativos").value
    .split(",").map((s) => s.trim()).filter(Boolean);
  const sistemas = [...document.querySelectorAll(".chk-perfil-sistema:checked")].map((c) => c.value);
  return {
    interesses: { ativos, sistemas, lados: ["BUY", "SELL"], variantes: ["MULTI", "ICHIMOKU"] },
    risco: {
      risco_por_trade_pct: Number(document.getElementById("perfil-risco").value),
      lote_fixo: Number(document.getElementById("perfil-lote").value),
      usar_lote_minimo_do_broker: true,
    },
    walk_forward: { ligar: false, data_final: document.getElementById("perfil-wfo-fim").value },
    arquivar_fora_do_escopo: false,
  };
}
async function sincronizarPerfil(dryRun) {
  const msg = document.getElementById("msg-perfil");
  const r = await post("/api/perfil/sincronizar", { perfil: montarPerfil(), dry_run: dryRun });
  if (!r.ok) { msg.textContent = r.erro; msg.className = "status-msg no"; return; }
  pollJob(r.job_id, msg, (j) => {
    document.getElementById("saida-perfil").textContent = j.saida || "";
    carregarPerfil();
  });
}
document.getElementById("btn-perfil-dry").addEventListener("click", () => sincronizarPerfil(true));
document.getElementById("btn-perfil-aplicar").addEventListener("click", () => sincronizarPerfil(false));

// -------------------------------------------------------------- custo nativo

async function carregarCusto() {
  const d = await api("/api/custo-nativo");
  document.querySelector("#tbl-custo tbody").innerHTML = Object.entries(d).map(([sym, c]) =>
    `<tr><td>${sym}</td><td>${c.comissao_por_lote.toFixed(4)}</td>
     <td>${c.swap_por_lote.toFixed(4)}</td><td>${c.quando}</td></tr>`).join("");
}
document.getElementById("btn-medir-custo").addEventListener("click", async () => {
  const msg = document.getElementById("msg-custo");
  const simbolo = document.getElementById("custo-simbolo").value.trim();
  if (!simbolo) { msg.textContent = "informe o símbolo"; msg.className = "status-msg no"; return; }
  const r = await post("/api/custo-nativo/medir", { symbol: simbolo });
  if (!r.ok) { msg.textContent = r.erro; msg.className = "status-msg no"; return; }
  pollJob(r.job_id, msg, () => carregarCusto());
});
