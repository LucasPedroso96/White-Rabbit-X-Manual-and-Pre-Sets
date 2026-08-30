# Espera o runner da calibracao dos 6 sistemas (_runner_partes_1_a_3.py)
# terminar de verdade, so entao regenera a biblioteca inteira de sets --
# rodar generate_system_sets.py com algum sweep/campanha ainda lendo os
# mesmos .set templates sobrescreveria o arquivo que o sweep esta
# reescrevendo por formula, corrompendo o teste em andamento (mesma
# licao de colisao de processo ja aprendida nesta sessao). Uso interno.
param([int]$PidRunner)

while (Get-Process -Id $PidRunner -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 30
}
Start-Sleep -Seconds 5

Set-Location "C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot"
$python = "C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python310\python.exe"
"########## CALIBRACAO DOS 6 SISTEMAS TERMINOU, REGENERANDO BIBLIOTECA (MaxRiscoTradeR fix) ##########" |
    Out-File -FilePath regenerar_sets.log -Encoding utf8
& $python generate_system_sets.py *>> regenerar_sets.log
"########## BIBLIOTECA REGENERADA ##########" | Out-File -FilePath regenerar_sets.log -Encoding utf8 -Append
