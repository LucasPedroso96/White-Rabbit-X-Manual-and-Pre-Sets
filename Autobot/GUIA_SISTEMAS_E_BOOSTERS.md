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
5. **Ler o resultado:** reprovação só por divergência > 30%, sobrevivência/DD, dado não visto negativo com ≥ 10
   trades ou pior que o incumbente. Robustez, consistência e queda máxima são **alertas**, não reprovações.
6. **Ao vivo:** `validar_live.py` antes de implantar; a Limit do XAUUSD 04 mostrou vantagem pequena e sensível
   a atraso de execução — não confie nela sem forward-teste em demo.

## 6. Como testar mudanças (EA, gerador, pipeline) antes de gastar dias de terminal

| Camada | Comando | O que prova |
|---|---|---|
| Offline | `test_*.py` (38 arquivos) | regras, parsers, modelos, sem MT5 |
| Pendentes | `testar_pendentes.py --rodar` / `--verificar` | preço, SL/TP, lote, expiração, OCO, WFO de cada ordem pendente contra as barras do terminal |
| Sistemas e recuperação | `testar_sistemas.py --rodar` / `--verificar` | cada sistema sai como o nome diz; o lote de cada entrada bate com o modelo do `.mq5` |
| Lógica dos inputs | `bateria_logica.py --parte i/n --saida bateria_logica/AAAA-MM-DD/x.jsonl` | cada eixo do template muda o resultado e nada é recusado sem motivo (pasta nova sempre que a EA muda) |
| Pipeline | `optimize_two_stage.py … --calibracao` em janela curta | o circuito inteiro roda para o sistema, sem tocar o ledger |
| Antes de subir fila | `preflight.py` | nada velho, nada rodando, tudo com o build atual |

## 7. Armadilhas já medidas

* **Reabertura do mercado:** ordens no 1º segundo (ex.: ouro 01:00) falham com `[Market closed]` — também a
  mercado, não é da pendente.
* **OCO na rolagem da meia-noite:** com o spread aberto as duas pernas podem executar no mesmo instante; use
  `MaxSpread` e evite armar o bracket ali.
* **Pausa da campanha:** só vale entre combos; um combo que acha candidato na rodada 1 do Estágio 1 roda até o
  fim (4–6 h).
* **Um teste com EA velha não vale:** cada rodada de validação precisa ser posterior ao `.ex5` atual (o
  `preflight.py` compara as datas).
