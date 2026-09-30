# Sistemas × Boosters — o que é o quê e a melhor forma de trabalhar

Escrito em 29/09/2026 a pedido do dono ("verifique o que é booster, o que é sistema, as melhores formas de
trabalhar com tudo"). Tudo aqui foi conferido no código (`generate_system_sets.py`, `optimize_two_stage.py`,
os `.mq5`) e nos testes do tester — onde há número, ele saiu de uma rodada, não de suposição.

## 1. Três coisas diferentes (não misturar)

| O quê | Pergunta que responde | Exemplos |
|---|---|---|
| **Sistema** | O que acontece com a posição *depois* da entrada? | SL+TP, trailing, grade, pirâmide, bracket OCO |
| **Família de entrada** | De onde vem o sinal? | MULTI (11 indicadores) e ICHIMOKU, BOLLINGER, CANDLES |
| **Booster** | Existe uma camada *opcional* que melhora um sistema que já tem edge? | Recuperação, entrada pendente, filtros de execução, filtro de volatilidade |

Regra do dono (08/09): *"não são sistemas, são extras de todos os outros"* — por isso `09_MARTINGALE` e
`10_DALEMBERT` deixaram de existir como sistema; viraram o booster de recuperação. Um booster **nunca cria
edge sozinho**: se o sistema não passa nos portões sem ele, o booster não salva.

## 2. Os 10 sistemas

| Sistema | O que faz | SL | TP | Sizing na busca | Recuperação | Conta hedge | Arquivos |
|---|---|:-:|:-:|---|:-:|:-:|---|
| `01_SLTP` | SL e TP em múltiplos de ATR; breakeven opcional | sim | sim | Fixed-R | sim | não | BUY/SELL/BOTH × 4 famílias |
| `02_SLTP_ORGANIC` | SL + TP "orgânico" (ancorado no último trade) | sim | orgânico | Fixed-R | sim | não | idem |
| `03_TRAIL_ONLY` | SL + trailing, sem TP, breakeven fora | sim | não | Fixed-R | sim | não | idem |
| `04_SLTP_TRAIL` | SL + TP + trailing atrás; breakeven opcional | sim | sim | Fixed-R | sim | não | idem |
| `05_BE_TRAIL` | Breakeven obrigatório + trailing, sem TP | sim | não | Fixed-R | sim | não | idem |
| `06_REVERSAL_EXIT` | Sai quando o indicador vira (BOTH: ou por ordem oposta) | sim (rede) | não | Fixed-R | sim | só no modo "ordem oposta" | idem |
| `07_GRID_SEPARATE` | Grade, alvo por lado, **sem SL** (a cesta é a gestão) | não | cesta | Lote fixo | **não** | **sim** | idem |
| `11_SIGNAL_ONLY` | Sem SL nem TP; mede o sinal cru | não | não | Lote fixo | sim | não | idem |
| `12_GRID_INVERSO` | Pirâmide a favor do preço + trailing da cesta | sim (por perna) | não | Fixed-R | **não** | **sim** | idem |
| `13_OCO_ROMPIMENTO` | Bracket buy stop + sell stop armado 1×/dia numa hora fixa; uma perna cancela a outra; saída do 04 | sim | sim | Fixed-R | não previsto | não | só `BOTH_MULTI` |

Fixed-R = o lote sai do orçamento de risco (1R = 1% do capital base), então o mesmo set serve para qualquer
conta. **Lote fixo (07 e 11) não tem essa proteção**: o risco é o que o lote mínimo custa no ativo.

Histórico no ledger (registros aprovados, contando reavaliações do mesmo set): `04` 7 (XAUUSD, NVDA, US500,
DE40), `07` 3 (USDCAD), `02` 2 (GBPUSD), `03` 1 (GBPUSD); `01`, `05`, `06`, `11`, `12` nunca aprovaram e o
`13` ainda não rodou. O `04` é o cavalo de batalha.

## 3. Os boosters

| Booster | Estágio | Como liga | Adoção | Vale em | Risco / cuidado |
|---|---|---|---|---|---|
| Filtros secundários (MA, ADX, MTF) e filtro de volatilidade ATR | 1–2 (fazem parte da busca) | flags do template | entram se o torneio de retenção os escolher | todos | mais filtro = menos trades (piso de trades por TF protege) |
| **Recuperação** (Martingale / D'Alembert) | 2.5 | `--recuperacao martingale\|dalembert` (painel: *Camada de Recuperação*) | **aplicada quando pedida** — não compete com a versão sem ela; os portões finais julgam. O log mostra o efeito na retenção | 01–06 e 11 (a EA recusa com grade) | lote cresce com a sequência de perdas. Fixed-R: recupera a dívida no TP (ou no SL se não há TP), teto de 3R por trade. D'Alembert **exige lote fixo** — o estágio troca o sizing e perde a medida em R |
| **Entrada pendente** (Stop / Limit / OCO por sinal) | 2.7 | automático (`--sem-entrada-pendente` desliga) | só se a retenção subir ≥ 5 pontos sobre a entrada a mercado | todos (na grade/pirâmide só a semente) | latência (a vantagem da Limit é frágil), rejeição `[Market closed]` no 1º segundo da reabertura, OCO com spread aberto na rolagem |
| **Filtros de execução** (hora, dia, spread) | 3 | automático | só se a retenção subir ≥ 5 pontos (otimiza em IS+OOS por decisão do dono) | todos | vazamento de OOS aceito nesses eixos de higiene |

Fora do circuito de propósito: filtro de notícias (o tester não tem histórico de notícias) e travas de risco
de conta (configuração da conta ao vivo, não estratégia).

## 4. O que a EA aceita junto (OnInit)

| Combinação | Aceita? |
|---|:-:|
| Fixed-R + Martingale | sim |
| Fixed-R + D'Alembert | **não** (passo absoluto quebra a independência de saldo do R) |
| D'Alembert | precisa de lote fixo, sem grade, `DAlembertStep` > 0 |
| Grade (07) ou pirâmide (12) + recuperação | **não** |
| Fixed-R + grade clássica (07) | **não** (sem stop para medir o R) |
| Percentual | precisa de stop loss |
| Grade / `Hedging=true` / saída por ordem oposta (`ReversalExitMode=1`) | conta hedging real |
| Pendente / OCO | vale em conta netting também (duas pernas juntas se anulam) |

Efeito colateral conhecido: no `06 BOTH`, `Hedging` e `ReversalExitMode` são eixos independentes, mas o modo 1
exige `Hedging=true`; cerca de um quarto das combinações possíveis desse combo (modo 1 com hedge desligado) é
recusado no OnInit — orçamento do genético perdido, não resultado errado (a bateria de lógica confirmou a
mensagem: *exit requires bilateral trading on a real hedging account with Grid disabled*).

## 5. Como trabalhar (receita)

1. **Antes de qualquer campanha:** `python preflight.py`. Ele diz, em segundos, se a EA está igual nas duas
   instalações e mais nova que o fonte, se os templates têm os 10 sistemas e são mais novos que os geradores,
   se há fila rodando, se a pausa está armada e se as validações foram feitas com o build atual.
2. **Escolha do sistema:** comece pelo `04` (mais evidência). `02`/`03` são complementos em forex. Grade (`07`)
   só com capital que aguente a queda — o gate de 40% de drawdown só mede sets em R, então o alerta de *queda
   máxima* (capital ≈ queda em $ ÷ 0,40) é a leitura que vale. `11` é pesquisa, nunca para operar. `12` e `13`
   ainda não têm campeão.
3. **Campanha normal:** deixe os boosters automáticos (2.7 e 3) ligados; eles só entram se provarem ganho.
4. **Recuperação:** só depois de existir um campeão sem ela, e como decisão sua. Compare o campeão com e sem,
   olhe o alerta de queda e o holdout lacrado; em conta pequena, evite.
5. **Ler o resultado:** depois dos pisos de cada estágio (retenção, trades), o veredito final
   (`decidir_trader`) reprova só por: divergência OHLC × tick real > 30%; não sobreviver ao período completo;
   queda máxima > 40% em 3 anos (medida só em sets em R — grade em lote fixo escapa); prejuízo no dado nunca
   visto (período anterior ao treino + holdout lacrado) com ≥ 10 trades; ou ser pior que o campeão
   implantado. Robustez (vizinhos ±10%), consistência (trimestres) e queda máxima em $ são **alertas**, não
   reprovações.
6. **Ao vivo:** `validar_live.py` antes de implantar; a Limit do XAUUSD 04 mostrou vantagem pequena e sensível
   a atraso de execução — não confie nela sem forward-teste em demo.

### Painel × fila × linha de comando (o que cada um liga)

| Opção | Painel (Start) | Fila `_fila_*.ps1` | `campanha.py` / `optimize_two_stage.py` |
|---|:-:|:-:|---|
| Camada de recuperação | sim (*Camada de Recuperação*) | não | `--recuperacao martingale\|dalembert` |
| Modo econômico (BOTH) e família | sim | sim | `--modo-economico`, `--familia` |
| Janela dinâmica (por taxa de trades, teto 2 anos) | **não** (janela fixa de 3 anos, cortada em 2) | **sim** | `--janela-dinamica` |
| Teto do Estágio 3.5 (tick real) | **não** | **sim** (15–20 min) | `--timeout-geometria-min` |
| Desligar a entrada pendente / triagem de sensibilidade | não | não | `--sem-entrada-pendente`, `--triagem-sensibilidade` |
| Combos exatos e refazer o que é anterior a um corte | não | **sim** | `--combos`, `--refazer-antes-de` |

Ou seja: o circuito completo da metodologia atual (janela por trades, holdout lacrado, 3.5 com teto) sai pela
**fila**; o botão Start do painel é o caminho curto e usa os padrões, sem a janela dinâmica.

## 6. Como testar mudanças (EA, gerador, pipeline) antes de gastar dias de terminal

| Camada | Comando | O que prova |
|---|---|---|
| Offline | `test_*.py` (39 arquivos) | regras, parsers, modelos, sem MT5 |
| Pendentes | `testar_pendentes.py --rodar` / `--verificar` | preço, SL/TP, lote, expiração, OCO, WFO de cada ordem pendente contra as barras do terminal |
| Sistemas e recuperação | `testar_sistemas.py --rodar` / `--verificar` | cada sistema sai como o nome diz; o lote de cada entrada bate com o modelo do `.mq5` |
| Lógica dos inputs | `bateria_logica.py --parte i/n --saida bateria_logica/AAAA-MM-DD/x.jsonl` | cada eixo do template muda o resultado e nada é recusado sem motivo (pasta nova sempre que a EA muda) |
| Pipeline | `optimize_two_stage.py … --calibracao` em janela curta | o circuito inteiro roda para o sistema, sem tocar o ledger |
| Antes de subir fila | `preflight.py` | nada velho, nada rodando, tudo com o build atual |

## 7. Armadilhas já medidas

* **Reabertura do mercado:** ordens no 1º segundo (ex.: ouro 01:00) falham com `[Market closed]` — também a
  mercado, não é da pendente.
* **OCO na rolagem da meia-noite:** com o spread aberto (≈ 23:56–00:05 neste servidor) as duas pernas podem
  executar no mesmo instante (medido no GBPUSD). Duas proteções que a EA já tem: `MaxSpread` e a janela de
  horário com `Fecharordensforadohorario=true` (cancela a pendente fora da janela — verificado no cenário
  `g6_pregao_10_12`). Para um bracket ao vivo, termine a janela antes da rolagem (ex.: `TOD_To_Hour` ≤ 23) e
  não arme na hora 0.
* **Pausa da campanha:** só vale entre combos; um combo que acha candidato na rodada 1 do Estágio 1 roda até o
  fim (4–6 h).
* **Um teste com EA velha não vale:** cada rodada de validação precisa ser posterior ao `.ex5` atual (o
  `preflight.py` compara as datas).

## 8. Evidência da rodada de 29/09/2026 (build EA `0c0d23b8` / `b5c674de` / `d756d1da`)

| Teste | Escopo | Resultado |
|---|---|---|
| Ordens pendentes (`testar_pendentes`) | 113 cenários, 3 EAs, 7.348 ordens, tick real, 4 semanas cada | 0 falhas; preço exato em 7.159, empurrado à distância mínima do corretor em 189, nenhum fora |
| Assinatura dos sistemas (S1) | 10 sistemas × 12 arquivos (XAUUSD) + os 10 em `BOTH_MULTI` no EURUSD, 8 semanas, 20.037 posições | 0 falhas, 0 avisos: SL/TP nas ordens, classes de saída, lado do arquivo, grade com 2–5 pernas, saídas por SL classificadas em inicial (1.502) / breakeven (2.381) / arrastada (2.214) e coerentes com `AtivarBreakeven` / `AtivarTrailATR` |
| Recuperação (S2) | Martingale e D'Alembert em 01–06 e 11, 3 EAs, XAUUSD e EURUSD, 27 cenários | 3.992 lotes de entrada recalculados com o modelo do `.mq5` (dívida por lado, passos, teto de 3R): **0 divergências**; 3.102 com dívida/passo ativo, 2.128 acima do lote base |
| Travas de risco (S3) | perda diária do magic, proteção global diária e total, com e sem fechamento, Limit, Bollinger e Candles — 9 cenários | 0 entradas depois do estouro em todos (o controle sem trava teria 13 entradas depois do estouro diário e 88 depois do total); com `Protecao_Fecha_Posicoes=false` nenhum fechamento de emergência |
| Filtros de execução (S4) | janela de horário (inclusive noturna), dias da semana e spread máximo, a mercado e com Limit — 8 cenários | 0 ordens de entrada fora da janela, em dia desligado ou com spread da barra acima do teto (semântica conferida antes contra 109 relatórios reais sem filtro: 0 violação) |
| Pipeline completo, sistema 13 (smoke) | `optimize_two_stage --calibracao`, XAUUSD, treino de 109 dias | os 5 estágios, holdout, WFA e decisão rodaram sem erro; o candidato foi REPROVADO (queda de 99% em 3 anos), como o esperado de um treino tão curto — o teste é do encanamento, não da vantagem |
| Pipeline com recuperação (smoke) | idem, 04 BUY com `--recuperacao martingale` | Estágio 2.5 rodou de ponta a ponta e imprimiu o efeito (retenção 45,7% → 60,1%); os 4 valores de `MaxMartingaleSteps` deram o mesmo resultado (a sequência de perdas nunca passou do limite); reprovado por queda de 75% em 3 anos |
| Ablação de boosters (S5) | 5 sets já otimizados × 83 variantes × 2 janelas de 90 dias = 166 cenários | ver seção 9 |
| Bateria de lógica | 1.032 passes, 262 eixos, 4 famílias | de 32 achados (14/09) para 12: o filtro ATR deixou de zerar as entradas; os que restam são eixos condicionais por desenho (Bollinger: modo Reversal/Squeeze/filtro MTF). Os eixos inertes do Ichimoku (`InpAppliedPrice`, Stochastic) foram corrigidos depois, em 29/09 (ver abaixo); a contagem de 12 é anterior a essa correção e a bateria não foi refeita |
| Biblioteca × OnInit (`validate_system_sets`) | 10.246 sets, 93 milhões de combinações de canto, esquema de cada família contra a própria EA | nenhum set alcança combinação recusada, exceto o acoplamento conhecido do 06 BOTH |

O que a rodada **mudou no código**: Candles com `InpAppliedPrice` cravado em CLOSE (a EA recusa OPEN/HIGH/LOW; 43% do
eixo eram passes recusados); Ichimoku com `InpAppliedPrice` e os três parâmetros do Stochastic cravados (eram eixos
inertes no Ichimoku — a bateria acusou que variar o valor não muda nenhuma entrada — e o genético gastava passes
neles), com a biblioteca inteira regenerada nas duas
instalações e conferida arquivo a arquivo contra o backup (só o Ichimoku mudou; 27 cenários do S1 deram resultado
idêntico antes e depois); a prova em % do Estágio 5 não roda mais com D'Alembert (a EA exige lote fixo); o
Estágio 2.5 imprime o efeito da recuperação na retenção; `bateria_logica`, `validate_system_sets` e
`testar_pendentes` ganharam as conferências acima.

## 9. Que combinações rendem: o que o circuito extraiu e o que a ablação mostra

**O que o circuito já extraiu** (ledger, metodologia final de 26/09) — os dois aprovados são *pilhas* de boosters sobre
um sistema, escolhidas juntas pela otimização para aquele ativo:

| Combo | Base (sistema + entrada) | Boosters empilhados pelo circuito | Dado nunca visto (período anterior ao treino + holdout lacrado de 90 dias) |
|---|---|---|---|
| XAUUSD 04 BUY | CCI M15 (método "qualquer gatilho"), SL 4,0 / TP 6,0 / trailing 3,0 ATR só no lucro, sem breakeven | Limit no fechamento (k = 0, 1 barra) + filtros MA, ADX e MTF + janela 12:00–08:55 + teto de spread 100 pts | **+359 em 281 trades** (anterior +570/257; holdout lacrado **−211/24**); queda em 3 anos 18,5% no pipeline (10,1% no passe contínuo do `validar_live`) |
| USDCAD 07 BUY | OsMA M15, ATR M30 (7), alvo 9,0 ATR, breakeven 0,35, distância mínima 2,5 (grade, lote fixo, hedge) | só a janela 06:00–04:55 | **+1.420 em 690 trades** (anterior +1.275/596; holdout +145/94); queda de 71% em 3 anos na validação pré-live (a regra não mede lote fixo: alerta de capital) |

Quase-aprovado sob a mesma regra: XAUUSD 04 BUY **a mercado** — nunca visto **+928 em 134 trades**, queda em 3 anos **6,0%**
(holdout −213/11) — foi barrado só pelo gate relativo contra o campeão implantado, que tem a Limit. Em dado não visto e em
queda ele está melhor que o campeão; os dois perderam nos últimos 90 dias. Os demais reprovaram: 04 SELL (nunca visto
−2.089), 05 BUY (queda de 58% em 3 anos), 11 (sobrevivência), 06 (queda). A recuperação nunca foi escolhida.

**O que a ablação (S5) mostra** — `testar_sistemas.py --rodar --so s5` e `--ablacao`; cinco sets já otimizados
(XAUUSD 04, USDCAD 07, NVDA 04, GBPUSD 03 e 02), OHLC, duas janelas de 90 dias (a: nunca vista pelo treino; b: a anterior),
ligando *um* booster por vez sobre a versão a mercado e tirando *um* por vez do que o campeão já carregava. Leitura
conservadora: só vale linha com ≥ 10 trades dos dois lados e diferença ≥ 1% do depósito; o resumo é um placar de sinais
entre bases e janelas (teste dos sinais), não o *t* de uma linha.

* **Nenhum booster ajuda de forma consistente em todas as bases** (o melhor placar tem p ≈ 0,2). Não existe receita
  genérica: o booster só vale quando escolhido para aquele ativo e provado em dado não visto — que é o que o circuito faz.
* **Tendem a atrapalhar:** entrada **Stop** (1 melhora contra 5 pioras nos pares válidos), janelas de horário aplicadas
  às cegas (7–20h: 3 × 6; 13–20h: 1 × 5), **OCO por sinal** (1 × 3) e o **filtro ATR "alta volatilidade" com o
  multiplicador padrão**, que esvaziou a estratégia (< 30% dos trades) nos 10 pares. No USDCAD 07 (grade) o filtro ATR levou a
  queda a 86%.
* **Neutros/inconclusivos:** Limit no fechamento (2 × 3, mediana −1,2% do depósito — **não confirma** vantagem sobre o mercado,
  o mesmo que a comparação semanal do XAUUSD já indicava), Martingale (raramente exercitado: 4 de 7 pares sem efeito),
  D'Alembert contra o lote fixo (3 × 2).
* **Tirar do campeão do XAUUSD piora nas duas janelas, sem chegar a ser significativo (amostras de 6 a 24 trades):**
  sem MA (−228 / −495), sem MTF (−131 / −236), sem a janela (−43 / −86); sem o ADX é misto. Tirar **tudo** (o sistema pelado) faz a queda ir de 0,6% para 39% na janela b — a pilha de
  filtros funciona principalmente como **filtro de risco**: reduz de ~280 para 6–24 trades por 90 dias.
* **O próprio campeão do XAUUSD perdeu na janela a** (−300, PF 0,76, 24 trades, em OHLC), coerente com o achado anterior de
  que a vantagem dele é fina e negativa fora da amostra. A base de USDCAD 07 foi a única claramente boa (+247, PF 3,0, queda
  3,5%), e nenhum booster a melhorou de forma relevante.

**Melhor forma de trabalhar, então:** (1) deixar o circuito escolher a pilha de cada ativo (Estágios 1–3) e não ligar
booster na mão em set validado; (2) tratar entrada Stop, filtro ATR e OCO por sinal como candidatos de baixa prioridade;
(3) recuperação só como experimento seu, com o efeito na retenção lido no log e os portões finais decidindo; (4) exigir do
booster que ele *reduza risco* ou *prove ganho em dado não visto*, não só que aumente o lucro do treino.

Limites: OHLC (não tick real), 90 dias, poucas dezenas de trades por linha, cinco bases. É indício para priorizar o que testar
em tick real, não prova.
