// Dados de exemplo usados apenas quando o backend real (/api/...) não responde --
// mantém o painel demonstrável offline. Determinístico (hash simples) para não
// "piscar" números diferentes a cada poll de 8s.
function h(str) {
  let x = 2166136261;
  for (let i = 0; i < str.length; i++) { x ^= str.charCodeAt(i); x = Math.imul(x, 16777619); }
  return (x >>> 0);
}
function frac(str) { return (h(str) % 10000) / 10000; }

export const SISTEMAS = [
  { code: 'RSI_REV', label: 'RSI Reversal', tier: 'pesquisa', capital_aplica: false, fixedR: true },
  { code: 'MA_CROSS', label: 'MA Crossover', tier: 'pesquisa', capital_aplica: false, fixedR: true },
  { code: 'BREAKOUT', label: 'Volatility Breakout', tier: 'pesquisa', capital_aplica: false, fixedR: true },
  { code: 'ICHIMOKU_TK', label: 'Ichimoku TK Cross', tier: 'pesquisa', capital_aplica: false, fixedR: true },
  { code: 'BOLL_SQZ', label: 'Bollinger Squeeze', tier: 'pesquisa', capital_aplica: false, fixedR: true },
  { code: 'TREND_FLW', label: 'Trend Follower ATR', tier: 'pesquisa', capital_aplica: false, fixedR: true },
  { code: 'MEAN_REV', label: 'Mean Reversion Z-Score', tier: 'pesquisa', capital_aplica: false, fixedR: true },
  { code: 'SCALP_M5', label: 'Scalper M5', tier: 'pesquisa', capital_aplica: false, fixedR: true },
  { code: 'GRID_HEDGE', label: 'Hedge Grid', tier: 'grid', capital_aplica: true, fixedR: false },
  { code: 'MARTINGALE', label: 'Classic Martingale', tier: 'recuperacao', capital_aplica: true, fixedR: false },
  { code: 'DALEMBERT', label: "D'Alembert Recovery", tier: 'recuperacao', capital_aplica: true, fixedR: false },
];

export const CLASSES = {
  'Forex Majors': { capital_base: 500, ativos: ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD'] },
  'Forex Minors': { capital_base: 1000, ativos: ['EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'NZDUSD'] },
  'Metais': { capital_base: 3000, ativos: ['XAUUSD', 'XAGUSD'] },
  'Índices': { capital_base: 5000, ativos: ['US500', 'NAS100', 'GER40'] },
  'Cripto': { capital_base: 2000, ativos: ['BTCUSD', 'ETHUSD'] },
};
const TODOS_ATIVOS = Object.values(CLASSES).flatMap((c) => c.ativos);

function comboStatus(sym, sisCode) {
  const f = frac(sym + '|' + sisCode);
  if (f < 0.18) return 'sem_teste';
  if (f < 0.45) return 'reprovado';
  return 'aprovado';
}

export function mockStatus(familia) {
  const variante = familia === 'BOLLINGER' ? 'BOLLINGER' : familia === 'ICHIMOKU' ? 'ICHIMOKU' : 'MULTI';
  let total_feitos = 0, aprovados = 0, reprovados = 0;
  const por_sistema = {};
  const recentes = [];
  SISTEMAS.forEach((s) => {
    let total = 0, ap = 0;
    TODOS_ATIVOS.forEach((sym) => {
      const st = comboStatus(sym + variante, s.code);
      if (st === 'sem_teste') return;
      total++; total_feitos++;
      if (st === 'aprovado') { ap++; aprovados++; } else reprovados++;
    });
    por_sistema[s.code] = { total, aprovados: ap };
  });
  TODOS_ATIVOS.slice(0, 9).forEach((sym, i) => {
    const s = SISTEMAS[i % SISTEMAS.length];
    const f = frac(sym + s.code + 'r');
    const ok = f > 0.35;
    const minutosAtras = i * 11 + 4;
    recentes.push({
      simbolo: sym, sistema: s.code, variante,
      quando: new Date(Date.now() - minutosAtras * 60000).toISOString(),
      aprovado: ok,
      retencao_oos: ok ? Math.round(45 + f * 55) : Math.round(f * 40),
      expectancy_r: (f - 0.3) * 0.6,
      trades_oos: Math.round(30 + f * 220),
      minutos: Math.round(8 + f * 40),
      relatorio_dir: null,
      lucro_ohlc: Math.round((f - 0.3) * 4000),
      lucro_tick_real: Math.round((f - 0.32) * 3800),
      lucro_ajustado_custo_nativo: Math.round((f - 0.34) * 3600),
      retencao_pct: ok ? Math.round(45 + f * 55) : Math.round(f * 40),
      sizing_entrega: 'fixed-R',
      mc_dd_p95: s.fixedR ? Math.round(8 + f * 20) : null,
      mc_dd_observado: s.fixedR ? Math.round(6 + f * 15) : null,
      mc_prob_ruina: s.fixedR ? Math.max(0, (0.25 - f) * 0.4) : null,
    });
  });
  const mcMedidos = Math.round(total_feitos * 0.62);
  return {
    total_feitos, aprovados, reprovados,
    atual: {
      posicao: `${total_feitos + 1}/${TODOS_ATIVOS.length * SISTEMAS.length}`,
      simbolo: TODOS_ATIVOS[Math.floor((Date.now() / 9000) % TODOS_ATIVOS.length)],
      sistema: SISTEMAS[Math.floor((Date.now() / 13000) % SISTEMAS.length)].code,
      variante,
      estagio: 'walk-forward · janela 4/6',
    },
    por_sistema,
    qualidade: {
      mc_pass_rate: 71, mc_medidos: mcMedidos, mc_cobertura_pct: Math.round((mcMedidos / Math.max(1, total_feitos)) * 100),
      retencao_media: 58, lucro_medio_tick_real: 612,
      mc_status: `${mcMedidos} combos com Monte Carlo medido`, wfe_status: 'walk-forward em dia',
    },
    recentes,
  };
}

export function mockEstado() {
  return {
    terminal_aberto: false, rodando: false, pausando: false, pausado: false,
    modo: null, familia: null, terminal_fechado: false, progresso: null,
  };
}

export function mockConfig(familia) {
  return {
    sistemas: SISTEMAS.map((s) => ({
      code: s.code, label: s.label, capital_aplica: s.capital_aplica,
      capital_agregado: s.capital_aplica ? Math.round(500 + frac(s.code) * 4000) : 0,
    })),
    classes: CLASSES,
  };
}

export function mockHeatmap() {
  const sistemas = SISTEMAS.map((s) => s.code);
  const classes = {};
  Object.entries(CLASSES).forEach(([classe, info]) => {
    classes[classe] = {
      ativos: info.ativos.map((simbolo) => {
        const celulas = {};
        sistemas.forEach((sc) => {
          const st = comboStatus(simbolo, sc);
          if (st === 'sem_teste') { celulas[sc] = { status: 'sem_teste' }; return; }
          const f = frac(simbolo + sc + 'h');
          const testados = Math.round(20 + f * 80);
          const aprovados = st === 'aprovado' ? Math.round(testados * (0.5 + f * 0.4)) : Math.round(testados * f * 0.2);
          celulas[sc] = { status: st, testados, aprovados, melhor_retencao: st === 'aprovado' ? Math.round(40 + f * 60) : Math.round(f * 35) };
        });
        return { simbolo, celulas };
      }),
    };
  });
  return { classes, sistemas };
}

export function mockBiblioteca(familia) {
  return { manifesto: { total_sets: 128 + (familia === 'BOLLINGER' ? 12 : familia === 'ICHIMOKU' ? 34 : 82), gerado_em: new Date(Date.now() - 86400000).toLocaleString() } };
}

export function mockPortfolios() {
  const classes = {};
  Object.entries(CLASSES).forEach(([classe, info]) => {
    classes[classe] = {};
    info.ativos.forEach((ativo) => {
      const porSistema = {};
      SISTEMAS.forEach((s) => {
        if (frac(ativo + s.code + 'pf') > 0.55) porSistema[s.code] = ['MULTI'];
      });
      classes[classe][ativo] = porSistema;
    });
  });
  const sistemas = {};
  const capital_por_sistema = {};
  SISTEMAS.slice(0, 6).forEach((s) => {
    capital_por_sistema[s.code] = Math.round(800 + frac(s.code + 'cap') * 6000);
    sistemas[s.code] = `<table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead><tr><th style="text-align:left;padding:4px 8px">Símbolo</th><th style="text-align:left;padding:4px 8px">Retenção</th></tr></thead>
      <tbody>${TODOS_ATIVOS.slice(0, 5).map((a) => `<tr><td style="padding:4px 8px">${a}</td><td style="padding:4px 8px">${Math.round(40 + frac(a + s.code) * 55)}%</td></tr>`).join('')}</tbody>
    </table>`;
  });
  return {
    mapa: { atualizado_em: new Date(Date.now() - 3 * 3600000).toLocaleString(), prontos: 46, templates: 90, classes },
    sistemas, capital_por_sistema, gerados: [],
  };
}

export function mockPerfil() { return { ultima_sincronizacao: null }; }

export function mockCustoNativo() {
  const out = {};
  ['EURUSD', 'XAUUSD', 'GBPUSD'].forEach((sym) => {
    out[sym] = {
      comissao_por_lote: 2 + frac(sym + 'c') * 3, swap_por_lote: -(1 + frac(sym + 's') * 4),
      entradas: Math.round(80 + frac(sym) * 300), volume_lotes: 4 + frac(sym + 'v') * 20,
      periodo: '30d', quando: new Date(Date.now() - 5 * 86400000).toLocaleDateString(),
    };
  });
  return out;
}

export function mockImplantacao() {
  return {
    sets: TODOS_ATIVOS.slice(0, 8).map((simbolo, i) => {
      const s = SISTEMAS[(i * 2) % SISTEMAS.length];
      const f = frac(simbolo + s.code + 'impl');
      const certificado = f > 0.3;
      return {
        chave: `${simbolo}__${s.code}__MULTI`, simbolo, sistema: s.code, variante: 'MULTI',
        retencao: certificado ? Math.round(45 + f * 50) : null,
        sobrevivencia_medida: !s.fixedR, sobrevivencia_saldo_final: !s.fixedR ? Math.round(900 + f * 4000) : null,
        lucro_oos: certificado ? Math.round((f - 0.2) * 3000) : null,
        certificado, implantado: certificado && f > 0.6,
        relatorio_dir: certificado ? `${simbolo}_${s.code}_MULTI` : null,
        sobrevivencia_grafico: !s.fixedR,
      };
    }),
  };
}

export function mockEmProva(chaves) {
  const status = ['SEM_BASELINE', 'EM_PROVA', 'DENTRO_DA_FAIXA', 'REBAIXAR', 'PROMOVER'];
  return { ok: true, combos: chaves.map((chave) => ({ chave, status: status[h(chave) % status.length], trades_vividos: Math.round(frac(chave + 'tv') * 60) })) };
}

export function mockSugestoes(saldo) {
  const certificados = mockImplantacao().sets.filter((s) => s.certificado && !s.implantado);
  if (!certificados.length) return { sugestoes: [], pool: 0, com_serie: 0 };
  const combos = certificados.slice(0, 3).map((s) => ({ simbolo: s.simbolo, sistema: s.sistema, variante: s.variante, peso: 1 / 3, chave: s.chave }));
  return {
    sugestoes: [{
      numero: 1,
      contas: [
        { tipo: 'padrao', capital_minimo: Math.max(500, saldo * 0.8), combos: combos.slice(0, 2) },
        { tipo: 'hedging', capital_minimo: Math.max(1000, saldo), combos: combos.slice(2) },
      ],
      combos,
    }],
    pool: certificados.length, com_serie: certificados.length,
  };
}

export function mockRelatorioResumo() {
  return {
    ok: true,
    resumo: {
      profit_factor: 1.42, recovery_factor: 2.1, sharpe_ratio: 1.08,
      balance_dd_relative: '11.4%', max_consecutive_wins: 9, max_consecutive_losses: 4,
    },
  };
}
