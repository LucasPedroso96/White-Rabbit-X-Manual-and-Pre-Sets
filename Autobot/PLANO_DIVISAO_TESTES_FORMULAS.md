# Divisao de testes de formula por sistema (2026-08-23)

## Contexto

`03_TRAIL_ONLY` acabou de passar pelo teste mais rigoroso que qualquer
sistema teve ate agora: sweep completo das 14 formulas em XAUUSD (circuito
inteiro, com WFO) + confirmacao das 3 melhores em mais dois ativos.
Resultado: `ReturnUniformity` (11) venceu, aplicado como novo default
(`generate_system_sets.py`, commit `270b7bb9`/`b2f51e1b`).

Os outros 10 sistemas ainda nao tiveram esse nivel de evidencia -- a
maioria so tem o resultado de um "fulltest" de lucro bruto SEM WFO
(2026-08-10), e dois (`07_GRID_SEPARATE`, `12_GRID_INVERSO`) tem um A/B
manual de 2 formulas num unico ativo, nunca o sweep completo das 14.

## O ativo importa -- nao testar tudo no mesmo par generico

Cada sistema tem um carater estrategico diferente. Testar todos no mesmo
ativo (ex.: EURUSD pra tudo) mede o sistema fora do regime em que ele foi
desenhado pra operar:

- **Persegue tendencia** (trailing puro/hibrido, piramide a favor do
  preco): precisa de ativo que TENDE. `XAUUSD` ja provou ser um bom
  candidato pra isso (foi o que revelou a divergencia OHLC-vs-tick-real de
  36-70% que motivou o Estagio 3.5, e foi o ativo do sweep vencedor do
  trail).
- **Aposta em reversao a media** (grid classico contra o preco, martingale,
  d'alembert -- todos aumentam exposicao depois de perda esperando o preco
  voltar): precisa de ativo que OSCILA sem tendencia sustentada.
  `AUDNZD` e o candidato citado no proprio historico do codigo
  (`generate_system_sets.py`, comentario do `07_GRID_SEPARATE`: "revisar
  com EURGBP/AUDNZD antes de tratar como definitivo").
- **Neutro** (SL/TP fixo classico, sem dependencia forte de regime):
  `EURUSD`, o par mais liquido, serve como piso de comparacao.
- **Signal-only** (sem rede de protecao, mede o sinal cru): precisa de
  ativo com movimento real pra ter o que medir -- um ativo choppy mede
  ruido, nao sinal. `XAUUSD` de novo.

## Mapeamento sistema -> ativo

| Sistema | Ativo | Deposito | Motivo |
|---|---|---|---|
| 04_SLTP_TRAIL | XAUUSD | 10000 | trailing atras do TP fixo -- precisa de tendencia sustentada pra valer a pena vs. so o TP |
| 05_BE_TRAIL | XAUUSD | 10000 | irmao do 03_TRAIL_ONLY (breakeven+trailing, sem TP fixo) -- mesmo regime |
| 09_MARTINGALE | AUDNZD | 1000 | aposta em reversao a media, sem SL nativo -- precisa de par que nao dispara numa direcao so |
| 10_DALEMBERT | AUDNZD | 1000 | mesma familia de reversao a media que martingale, incremento mais brando |
| 07_GRID_SEPARATE | AUDNZD | 1000 | grid classico contra o preco -- cross-check do resultado atual (so testado em EURUSD) num par genuinamente sem tendencia |
| 12_GRID_INVERSO | XAUUSD | 10000 | piramide A FAVOR da tendencia (anti-martingale) -- precisa do mesmo regime que trail, nao de reversao a media |
| 01_SLTP | EURUSD | 1000 | SL/TP classico, neutro a regime -- piso de comparacao no par mais liquido |
| 02_SLTP_ORGANIC | EURUSD | 1000 | mesma logica do 01_SLTP |
| 06_REVERSAL_EXIT | EURGBP | 1000 | sai no sinal contrario -- precisa de par que realmente inverte com frequencia, nao que tende sem parar |
| 11_SIGNAL_ONLY | XAUUSD | 10000 | sem SL/TP, mede sinal cru -- precisa de movimento real pra ter o que medir |

## Divisao em 5 partes (uma pessoa por parte)

Cada parte roda o sweep completo das 14 formulas (circuito inteiro, com
WFO) nos sistemas designados, usando o `sweep_formulas.py` novo (generaliza
os scripts descartaveis do teste do trail).

### Parte 1 -- familia trend (XAUUSD)
```
python sweep_formulas.py --sistema 04_SLTP_TRAIL --simbolo XAUUSD --deposit 10000
python sweep_formulas.py --sistema 05_BE_TRAIL    --simbolo XAUUSD --deposit 10000
```

### Parte 2 -- familia reversao a media, lote progressivo (AUDNZD)
```
python sweep_formulas.py --sistema 09_MARTINGALE --simbolo AUDNZD --deposit 1000
python sweep_formulas.py --sistema 10_DALEMBERT  --simbolo AUDNZD --deposit 1000
```

### Parte 3 -- familia grid (asset por regime)
```
python sweep_formulas.py --sistema 07_GRID_SEPARATE --simbolo AUDNZD --deposit 1000
python sweep_formulas.py --sistema 12_GRID_INVERSO  --simbolo XAUUSD --deposit 10000
```

### Parte 4 -- familia SL/TP classico (EURUSD)
```
python sweep_formulas.py --sistema 01_SLTP         --simbolo EURUSD --deposit 1000
python sweep_formulas.py --sistema 02_SLTP_ORGANIC --simbolo EURUSD --deposit 1000
```

### Parte 5 -- reversao de sinal + signal-only (mista)
```
python sweep_formulas.py --sistema 06_REVERSAL_EXIT --simbolo EURGBP --deposit 1000
python sweep_formulas.py --sistema 11_SIGNAL_ONLY   --simbolo XAUUSD --deposit 10000
```

## Isolamento de janela (opcional, recomendado)

O MT5 relanca uma vez por candidato do torneio de retencao -- um sweep de
14 formulas facilmente passa de uma centena de relancamentos, e cada um
pode flashear foco por um instante mesmo minimizado. `mt5_runner.py`
manda a janela pro desktop virtual isolado "WRX-MT5-Isolado" automaticamente
se o modulo `VirtualDesktop` (Markus Scholtes, PSGallery, MIT) estiver
instalado:

```
Install-Module -Name VirtualDesktop -Scope CurrentUser -Force
```

Sem o modulo instalado o sweep roda normalmente do mesmo jeito -- so volta
a flashear foco no desktop principal como antes. Nao e obrigatorio, so
evita a interrupcao.

## Depois do sweep

Cada `sweep_formulas.py` gera `sweep_<SISTEMA>_<SIMBOLO>_master.log` e um
log por formula (`sweep_<SISTEMA>_<SIMBOLO>_NN_Nome.log`). Ler o veredito
final de cada log (`APROVADO`/`REPROVADO`, retencao, divergencia) e
reportar os 2-3 melhores por sistema. Se sobrar tempo, repetir a formula
vencedora de cada sistema em um segundo ativo da mesma familia pra
confirmar (mesmo padrao usado no trail: XAUUSD -> BTCUSD/USDJPY).

Nao mexer em `FORMULA_POR_SISTEMA` (`generate_system_sets.py`) sem antes
compilar a tabela de resultados e confirmar com o dono -- mesmo processo
usado pro trail.
