# Espera o runner dos 6 sistemas (_runner_partes_1_a_3.py, PID passado por
# parametro) terminar de verdade, so entao roda o sweep completo das 14
# formulas do 03_TRAIL_ONLY -- ele foi validado em 22/08 (ReturnUniformity),
# mais de um dia ANTES dos 3 fixes do EA em 24/08 (lote minimo, gate do
# Pyramid, tolerancia de slippage), entao essa comparacao de formulas nunca
# rodou com o EA corrigido. Mesmo motivo/padrao ja visto no 04_SLTP_TRAIL
# (dono, 2026-08-25). Uso interno, apagar depois.
param([int]$PidRunner)

while (Get-Process -Id $PidRunner -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 30
}
Start-Sleep -Seconds 5

Set-Location "C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot"
$python = "C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python310\python.exe"
"########## CALIBRACAO DOS 6 SISTEMAS TERMINOU, RECALIBRANDO 03_TRAIL_ONLY (pos-fixes) ##########" |
    Out-File -FilePath recalibracao_trail_pos_fixes.log -Encoding utf8
& $python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo XAUUSD --deposit 10000 *>> recalibracao_trail_pos_fixes.log
"########## 03_TRAIL_ONLY RECALIBRADO ##########" | Out-File -FilePath recalibracao_trail_pos_fixes.log -Encoding utf8 -Append
