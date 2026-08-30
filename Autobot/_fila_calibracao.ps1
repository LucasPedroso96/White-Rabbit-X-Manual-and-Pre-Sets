# Espera o PID da campanha de 03_TRAIL_ONLY (USDJPY/EURJPY/GBPJPY) morrer,
# roda um sweep CURTO e controlado (Profit x ReturnUniformity, 3 meses,
# igual o metodo ja usado pra XAUUSD/BTCUSD/USDJPY) em GBPUSD -- pedido do
# dono, 2026-08-24: checar se a lembranca de "Profit dava violento em
# GBPUSD" se confirma com dado real, antes de decidir se GBPUSD entra na
# campanha de producao (3 anos) e com qual formula. So DEPOIS disso lanca
# a calibracao dos 6 sistemas restantes. Get-Process (nao ps do Git-Bash --
# ja deu falso negativo, 2026-08-23). Uso interno.
param([int]$PidCampanha)

Set-Location "C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot"
$python = "C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python310\python.exe"

while (Get-Process -Id $PidCampanha -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 20
}
Start-Sleep -Seconds 5

"########## CAMPANHA USDJPY/EURJPY/GBPJPY TERMINOU, INICIANDO SWEEP GBPUSD (Profit x ReturnUniformity) ##########" |
    Out-File -FilePath sweep_trail_gbpusd.log -Encoding utf8
& $python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo GBPUSD --deposit 1000 --formulas 2,11 *>> sweep_trail_gbpusd.log

Start-Sleep -Seconds 5
"########## SWEEP GBPUSD TERMINOU, INICIANDO CALIBRACAO DOS 6 SISTEMAS RESTANTES ##########" |
    Out-File -FilePath calibracao_madrugada.log -Encoding utf8
& $python _runner_partes_1_a_3.py *>> calibracao_madrugada.log
