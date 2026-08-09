# Autobot — Sugestão automática de Deposit por classe de ativo no dashboard

Data: 2026-08-08. Pedido do dono (condensado ao longo da conversa): "o
campo Deposit deveria virar uma caixa que recomenda o melhor saldo de
acordo com a classe de ativo marcada — se desmarcar, libera pra digitar
o valor manualmente (500 por padrão). Fica marcada por padrão. No Modo
Automático sempre vai ser automático nesse sentido também."

## Contexto

Na mesma sessão, a campanha de grid ativa (`08_GRID_UNIFIED`) foi
recomposta para tirar XAUUSD e manter só os 9 majors/cruzamentos forex,
porque sistemas de lote fixo (07-11) não escalam com o saldo ao vivo e
`calc_capital_base.py` mostra que cada classe de ativo precisa de um
capital mínimo bem diferente para o lote mínimo da corretora não
distorcer o risco pretendido (Forex ~500, Cripto/Índices-Energia ~2.500,
Ações ~5.000, Metais ~10.000 — `generate_system_sets.py:249-255`,
`CLASSES`).

O dashboard já expõe esse número por classe (`/api/config` retorna
`classes: {codigo: {capital_base, ativos}}`, consumido em
`app.js:1152-1153` só para exibir "(capital base X)" no título de cada
grupo de ativos no Modo Manual) mas o campo **Deposit**
(`index.html:120`, `campo-deposito`) continua sendo um número solto,
sem ligação com o que foi marcado — hoje quem escolhe o valor certo por
classe é o próprio dono, de cabeça.

## Decisão

Adicionar uma caixa de seleção "Sugerir automaticamente" ao lado do
campo Deposit. O campo permanece o mesmo (`campo-deposito`); a caixa só
passa a controlar se o valor é calculado ou digitado.

| | Modo Manual | Modo Automático |
|---|---|---|
| Estado da caixa | Marcada por padrão; usuário pode desmarcar | Sempre marcada; **sem opção de desmarcar** (checkbox disabled) |
| Base do cálculo | Maior `capital_base` entre as classes com ≥1 ativo marcado em `.chk-ativo` | Maior `capital_base` entre **todas** as classes do catálogo (hoje 10.000, Metais) |
| Campo Deposit | `disabled` enquanto a caixa estiver marcada, mostrando o valor calculado | Sempre `disabled`, mostrando o valor calculado |
| Se desmarcar (só Manual) | Campo volta a `disabled=false` e o valor reseta para 500 (mesmo default de hoje) | N/A |
| Nenhuma classe marcada ainda (Manual) | Cai no fallback 500 | N/A |

Justificativa do "maior valor" quando várias classes estão marcadas: o
Deposit é um parâmetro único por campanha (`--deposit`), não por
símbolo — usar o maior garante que o valor sugerido respeita a classe
mais exigente da seleção, em vez de subestimar risco para ela.

Justificativa do travamento total no Modo Automático: esse modo já
esconde toda a seleção manual de ativo/sistema (`bloco-manual`
com `display:none`) porque testa o catálogo inteiro sozinho — não faz
sentido oferecer um override que não tem uma seleção específica por
trás. A base do cálculo vira "pior caso entre todas as classes", já que
o Automático eventualmente passa por todas.

**Onde recalcular** (sem mudança de backend — `capital_base` por classe
já está em `CONFIG.classes` desde `carregarConfig()`):
- ao marcar/desmarcar a própria caixa "Sugerir automaticamente";
- ao marcar/desmarcar qualquer `.chk-ativo` (inclui os atalhos
  `btn-ativos-todos`, `btn-ativos-nenhum`, `btn-classe-todos`,
  `btn-classe-nenhum` e o fluxo de `btn-detectar`, que hoje setam
  `.checked` direto via JS sem disparar evento `change` — cada um desses
  pontos precisa chamar o recálculo explicitamente, não só um listener
  delegado);
- ao trocar de modo (`setModo`), já que a base do cálculo muda entre
  Manual e Automático;
- uma vez no carregamento inicial (`carregarConfig()`), porque
  `modoAtual` já começa como `"auto"` e a caixa já nasce marcada — o
  campo precisa mostrar o valor calculado (10.000 hoje) desde o
  primeiro paint, não o 500 antigo.

Os números usados (500/2.500/5.000/10.000) são os reais de
`CLASSES` no código — nenhuma classe hoje vale exatamente 2.000; o
cálculo lê o valor real de cada classe, não uma tabela redonda separada.

## Fora de escopo

- Mudar os valores de `capital_base`/`CapitalBaseR` em
  `generate_system_sets.py` — isso afeta a normalização de risco da
  pesquisa (Fixed-R) e é uma decisão separada, não parte desta UI.
- Qualquer mudança em `campanha.py`, `dashboard_campanha.py` ou outro
  endpoint — a feature é inteiramente client-side (`index.html` +
  `app.js`).
- Persistir a preferência (marcado/desmarcado) entre sessões — cada
  carregamento da página volta ao padrão descrito acima.
- Tradução das novas strings de UI para os 9 idiomas já suportados em
  `app.js` — acompanha o texto em inglês/português na implementação,
  chaves `data-i18n` completas ficam para a execução do plano.
