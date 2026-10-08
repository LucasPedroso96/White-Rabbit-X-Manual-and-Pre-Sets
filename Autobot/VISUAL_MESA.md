# Visual Mesa no Autobot

Em 2026-10-08 o dashboard do Autobot (`dashboard_static/`) e o relatório de portfólio
(`portfolio_html.py`) passaram para o sistema **Mesa**, o mesmo dos outros dashboards do
dono (Mesa de Controle, Claude Trader, Zeus, Big Guys, Levain). Nenhuma rota, id, regra
de campanha ou texto de i18n existente mudou. O que mudou é cor, forma de estado, tipografia
mínima e acessibilidade.

## O que mudou no dashboard (`index.html`)

- **Identidade por família (restaurada em 2026-10-08).** A primeira passada deixou as quatro famílias
  no mesmo grafite. Agora cada família volta a repintar a página inteira, como no painel original:
  Multi-Indicator verde-petróleo, Bollinger verde-floresta, Ichimoku azul-oceano, Candle Entry
  marrom-cobre, com o halo radial no fundo, cartões em gradiente suave e botões com o gradiente da
  família. Por cima ficam as regras da Mesa: ok/atenção/crítico com fundo próprio, texto/fundo ≥ 7:1,
  secundário e destaques ≥ 4,5:1, borda de controle ≥ 3:1 e texto dos botões ≥ 4,5:1 (valores da
  família ajustados só em luminosidade onde falhavam; `btnA`/`btnB` guardam o gradiente do botão).
  Nos temas Dia e Daltônico a família também vale (Daltônico = Noite da família com status em
  azul/amarelo/laranja).
- **Três temas**, escolhidos no cabeçalho e lembrados (`wrx_tema`): Noite (padrão), Dia e
  Daltônico (Noite com ok/atenção/crítico em azul, amarelo e laranja). O tema Dia já existia
  nas paletas, mas não tinha botão.
- **Estado = forma + palavra.** Selos do cabeçalho, KPIs, veredito (`✓ approved`, `✕ rejected`,
  `▲ demoted`), certificado, implantação, auditoria e as mensagens de retorno carregam um glifo
  (`✓ ▲ ✕ ○ ◆ ●`). "Não implantado" deixou de ser vermelho: é `○`, neutro.
- **Mapa de ativos** com glifo dentro da célula (✓ retenção ≥ 70%, ▲ aprovado com retenção
  menor, ✕ reprovado, vazio = não testado), legenda e `aria-label` por célula. Antes era só cor.
- **Sem gradiente, sem sombra de cartão, sem faixa lateral colorida** ("rodando agora", linhas
  de combo, linhas expandidas); a borda dá a elevação.
- **Acessibilidade e celular:** foco visível, `prefers-reduced-motion`, campos de 16px e alvos
  de 44px abaixo de 560px, `viewport-fit=cover`, safe-area, texto nunca abaixo de 11px, bordas
  de controle com 3:1 (`pal.border`), abas de 44px, tabelas largas rolam em vez de espremer a pílula.
- **Idioma persistido** (`wrx_locale`) e `<html lang>` acompanha. Os rótulos novos do tema
  existem em `en` e `pt`; os outros nove idiomas caem no inglês pelo fallback de `t()`.

## PWA (`manifest.webmanifest`)

- Cores `#05080b` (as do painel original).
- `orientation: any` (era `portrait-primary`, que travava tablet e celular deitado).
- `display_override` sem `window-controls-overlay`: o cabeçalho não trata a área da barra de
  título, então o recurso sobrepunha os botões da janela no desktop.
- O `sw.js` continua sem cache de propósito (dados ao vivo).

## Relatório de portfólio (`portfolio_html.py`)

- Tokens Mesa embutidos (arquivo continua autocontido, abre offline): Noite por padrão, Dia
  segue o aparelho, impressão em fundo branco.
- Séries em paleta Okabe–Ito; da 6ª série em diante a linha sai **tracejada**, porque cor sozinha
  não separa mais de cinco linhas. Traço de espessura constante (`vector-effect`), já que
  `preserveAspectRatio="none"` distorcia a linha.
- Correlação em divergente **laranja (andam juntas) × azul (opostas)** em vez de vermelho × verde;
  o número continua dentro da célula.
- Tabela de composição com rolagem horizontal no celular.

## Decisões e limites

- Textos de interface que já eram fixos em inglês no `index.html` continuaram assim; só o
  que é novo passou por `i18n.js`.
- `support.js` (runtime `x-dc`) não foi tocado.
- O `<head>` ainda carrega React/Babel do unpkg (já era assim); não foi alterado.

## Como conferir

1. `python dashboard_campanha.py` e abra `http://localhost:8020/?demo` (o `?demo` usa o
   `mock-data.js`): troque família, tema e idioma e recarregue; as três escolhas ficam.
2. 390px e 1440px: sem rolagem horizontal da página.
3. `python portfolio_builder.py ... --html saida.html` e abra o arquivo no modo escuro e claro.
