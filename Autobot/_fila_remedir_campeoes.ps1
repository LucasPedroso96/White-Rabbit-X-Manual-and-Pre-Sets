# Remedicao dos campeoes (o PROPRIO VALIDADO_) com a EA corrigida, no CLONE,
# depois que a refacao dos campeoes pela campanha terminar e antes da fila
# dos reprovados. Ver remedir_campeoes.py.
param([int]$EsperarPid = 0)

$aqui = "C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot"
$py = "C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python310\python.exe"
$log = Join-Path $aqui "campanha_remedicao_campeoes.log"

if ($EsperarPid -gt 0) {
    while (Get-Process -Id $EsperarPid -ErrorAction SilentlyContinue) {
        Start-Sleep -Seconds 60
    }
}
$env:WRX_MT5_DATA_DIR = "C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal\4A85BF7BB91E709E95066E8432253C88"
$env:WRX_MT5_INSTALL_DIR = "C:\Users\Lucas Pedroso\Documents\White Rabbit X\MT5_Optimizer2"
$env:PYTHONIOENCODING = "utf-8"
Set-Location $aqui
"=== $(Get-Date -Format 'dd/MM HH:mm') REMEDICAO DOS CAMPEOES com a EA corrigida ===" | Add-Content -Path $log -Encoding ASCII
cmd /c "`"$py`" -u remedir_campeoes.py >> `"$log`" 2>&1"
"=== $(Get-Date -Format 'dd/MM HH:mm') REMEDICAO TERMINOU ===" | Add-Content -Path $log -Encoding ASCII
