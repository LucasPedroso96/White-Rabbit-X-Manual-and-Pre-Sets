# Checklist — rodar Parte 4/5 da calibração (01_SLTP, 02_SLTP_ORGANIC, 06_REVERSAL_EXIT, 11_SIGNAL_ONLY)

## 1. Clonar/atualizar os dois repos (branch `main`, já com os fixes de hoje)

```
git clone -b main https://github.com/LucasPedroso96/White-Rabbit-X-Manual-and-Pre-Sets.git
git clone -b main https://github.com/LucasPedroso96/Metatrader5EAS.git
```

Se já tiver clonado antes:
```
git checkout main && git pull origin main
```
(rodar dentro de cada um dos dois repos)

## 2. Compilar o EA

Abrir `Metatrader5EAS/White Rabbit/EA/White Rabbit X (Global Multi-Indicator).mq5`
no MetaEditor do MT5 dele e compilar (F7). Confirmar "0 errors, 0 warnings".
Precisa estar no `MQL5\Experts\` do terminal dele (copiar o `.mq5` compilado
pra lá, ou compilar direto de lá).

## 3. Preparar o ambiente Python (dentro da pasta do Autobot)

```
pip install -r requirements.txt
python generate_system_sets.py
python atualizar_conta_real.py
```

## 4. Rodar os 4 sistemas que faltam

```
python sweep_formulas.py --sistema 01_SLTP         --simbolo EURUSD --deposit 1000
python sweep_formulas.py --sistema 02_SLTP_ORGANIC --simbolo EURUSD --deposit 1000
python sweep_formulas.py --sistema 06_REVERSAL_EXIT --simbolo EURGBP --deposit 1000
python sweep_formulas.py --sistema 11_SIGNAL_ONLY   --simbolo XAUUSD --deposit 10000
```

Cada um roda as 14 fórmulas sozinho (demora horas, pode deixar rodando sem
supervisão). Gera `sweep_<SISTEMA>_<SIMBOLO>_master.log` e um log por
fórmula — mandar esses arquivos de volta quando terminar.

## Atenção

- **Passo 1 é o que mais importa**: sem os fixes de hoje (lote mínimo, gate
  do Pyramid, tolerância de slippage, MaxRiscoTradeR, 11_SIGNAL_ONLY em
  Monetary) o resultado sai contaminado, igual o que já teve que ser
  refeito aqui.
- As datas padrão de `--from-data`/`--to-data` do `sweep_formulas.py`
  partem do calendário deste ambiente aqui — ele deve ajustar pra uma
  janela de ~3 meses terminando "hoje" no broker dele, se o histórico
  disponível for diferente.
- Números absolutos não vão bater com os nossos (broker/conta diferente) —
  o que importa é o *ranking* das 14 fórmulas dentro de cada sistema.
