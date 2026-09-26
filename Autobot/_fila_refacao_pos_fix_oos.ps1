# Refacao dos aprovados depois da correcao da EA (bloqueio de entrada no OOS
# vazando pro modo 'In Sample + Out Sample', 13/09 -> 26/09 02:05). Dono,
# 2026-09-26: "se tiver que refazer os aprovados refaca!".
# Espera a campanha GBPUSD (clone) terminar o ultimo combo e roda so os 4
# campeoes, na instalacao onde eles moram (CLONE). Resultado antigo fica no
# ledger; a corrida nova acrescenta linha.
param([int]$EsperarPid = 0)

$ErrorActionPreference = "Continue"
$aqui = "C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot"
$py = "C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python310\python.exe"
$log = Join-Path $aqui "campanha_refacao_campeoes.log"

if ($EsperarPid -gt 0) {
    while (Get-Process -Id $EsperarPid -ErrorAction SilentlyContinue) {
        Start-Sleep -Seconds 60
    }
}

$env:WRX_MT5_DATA_DIR = "C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal\4A85BF7BB91E709E95066E8432253C88"
$env:WRX_MT5_INSTALL_DIR = "C:\Users\Lucas Pedroso\Documents\White Rabbit X\MT5_Optimizer2"
Set-Location $aqui
"=== $(Get-Date -Format 'dd/MM HH:mm') REFACAO DOS CAMPEOES com a EA corrigida (OOS abre trade em IS+OOS): XAUUSD/NVDA/.DE40Cash BUY + .US500Cash SELL, 04_SLTP_TRAIL; teto 3.5 = 15 min ===" | Add-Content -Path $log -Encoding ASCII
# cmd >> (nao o *>> do PowerShell 5.1, que grava UTF-16 e o vigia le lixo)
$env:PYTHONIOENCODING = "utf-8"
$combos = "XAUUSD:04_SLTP_TRAIL:BUY_MULTI,NVDA:04_SLTP_TRAIL:BUY_MULTI,.US500Cash:04_SLTP_TRAIL:SELL_MULTI,.DE40Cash:04_SLTP_TRAIL:BUY_MULTI"
cmd /c "`"$py`" -u campanha.py --janela-dinamica --combos `"$combos`" --refazer-antes-de 2026-09-26T02:06 --timeout-geometria-min 15 >> `"$log`" 2>&1"
"=== $(Get-Date -Format 'dd/MM HH:mm') FILA DE REFACAO TERMINOU ===" | Add-Content -Path $log -Encoding ASCII
