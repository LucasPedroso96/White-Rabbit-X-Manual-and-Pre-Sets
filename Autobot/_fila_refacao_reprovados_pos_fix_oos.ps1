# Refacao dos 43 combos reprovados entre 13/09 e 26/09 02:05 cuja decisao
# (e a escolha dos parametros pelo torneio) usou a retencao medida com o bug
# da EA (entrada bloqueada no OOS em 'In Sample + Out Sample'). Fica de fora
# quem morreu no Estagio 1/2 (decisao so-IS, valida). Ordem: melhores
# candidatos primeiro (expectancy). Cada lado roda na instalacao que tem os
# templates: acoes/indices so existem no CLONE.
#   -Lado clone    : metais (teto 3.5 = 15 min) + acoes/indices  (24 combos)
#   -Lado original : forex unilateral + forex BOTH (modo economico) + BOLLINGER (19)
# Pausa a qualquer momento: o botao Pause do painel / campanha_pausa.json.
param([ValidateSet("clone", "original")][string]$Lado,
      [int]$EsperarPid = 0)

$ErrorActionPreference = "Continue"
$aqui = "C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot"
$py = "C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python310\python.exe"
$log = Join-Path $aqui "campanha_refacao_reprovados_$Lado.log"
$corte = "2026-09-26T02:06"

if ($EsperarPid -gt 0) {
    while (Get-Process -Id $EsperarPid -ErrorAction SilentlyContinue) {
        Start-Sleep -Seconds 60
    }
}

if ($Lado -eq "clone") {
    $env:WRX_MT5_DATA_DIR = "C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal\4A85BF7BB91E709E95066E8432253C88"
    $env:WRX_MT5_INSTALL_DIR = "C:\Users\Lucas Pedroso\Documents\White Rabbit X\MT5_Optimizer2"
    $etapas = @(
        @{rotulo = "metais"; extra = @("--timeout-geometria-min", "15");
          combos = "XAUUSD:05_BE_TRAIL:BUY_MULTI,XAUUSD:05_BE_TRAIL:SELL_MULTI,XAUUSD:04_SLTP_TRAIL:SELL_MULTI,XAUUSD:11_SIGNAL_ONLY:BUY_MULTI,XAGUSD:04_SLTP_TRAIL:BUY_MULTI,XAGUSD:04_SLTP_TRAIL:SELL_MULTI,XAUEUR:04_SLTP_TRAIL:BUY_MULTI,XAUEUR:04_SLTP_TRAIL:SELL_MULTI"},
        # teto 3.5 = 20 min: o MESMO das campanhas originais de acoes/indices
        # (campanha_foco_trail*.log). Sem ele o 3.5 herdaria 12 h por combo.
        @{rotulo = "acoes e indices"; extra = @("--timeout-geometria-min", "20");
          combos = ".US500Cash:04_SLTP_TRAIL:BUY_MULTI,.USTECHCash:04_SLTP_TRAIL:SELL_MULTI,.USTECHCash:04_SLTP_TRAIL:BUY_MULTI,.DE40Cash:04_SLTP_TRAIL:SELL_MULTI,NVDA:04_SLTP_TRAIL:SELL_MULTI,.US30Cash:04_SLTP_TRAIL:BUY_MULTI,.US30Cash:04_SLTP_TRAIL:SELL_MULTI,.JP225Cash:04_SLTP_TRAIL:BUY_MULTI,.JP225Cash:04_SLTP_TRAIL:SELL_MULTI,GOOGL:04_SLTP_TRAIL:SELL_MULTI,GOOGL:04_SLTP_TRAIL:BUY_MULTI,META:04_SLTP_TRAIL:BUY_MULTI,META:04_SLTP_TRAIL:SELL_MULTI,AMZN:04_SLTP_TRAIL:BUY_MULTI,AMZN:04_SLTP_TRAIL:SELL_MULTI,AAPL:04_SLTP_TRAIL:BUY_MULTI"}
    )
} else {
    Remove-Item Env:WRX_MT5_DATA_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:WRX_MT5_INSTALL_DIR -ErrorAction SilentlyContinue
    $etapas = @(
        @{rotulo = "forex unilateral"; extra = @();
          combos = "USDCAD:06_REVERSAL_EXIT:SELL_MULTI,USDCAD:06_REVERSAL_EXIT:BUY_MULTI,USDCAD:07_GRID_SEPARATE:BUY_MULTI,USDCAD:07_GRID_SEPARATE:SELL_MULTI,GBPUSD:06_REVERSAL_EXIT:BUY_MULTI,GBPUSD:07_GRID_SEPARATE:BUY_MULTI,GBPUSD:07_GRID_SEPARATE:SELL_MULTI,EURUSD:07_GRID_SEPARATE:BUY_MULTI"},
        @{rotulo = "forex BOTH (modo economico)"; extra = @("--modo-economico");
          combos = "USDJPY:03_TRAIL_ONLY:BOTH_MULTI,CHFJPY:03_TRAIL_ONLY:BOTH_MULTI,GBPUSD:12_GRID_INVERSO:BOTH_MULTI,GBPUSD:06_REVERSAL_EXIT:BOTH_MULTI,GBPUSD:04_SLTP_TRAIL:BOTH_MULTI,GBPUSD:01_SLTP:BOTH_MULTI,GBPUSD:05_BE_TRAIL:BOTH_MULTI,GBPUSD:07_GRID_SEPARATE:BOTH_MULTI,AUDUSD:03_TRAIL_ONLY:BOTH_MULTI,EURCHF:03_TRAIL_ONLY:BOTH_MULTI"},
        @{rotulo = "bollinger"; extra = @("--modo-economico", "--familia", "BOLLINGER");
          combos = "AUDCAD:04_SLTP_TRAIL:BOTH_BOLLINGER"}
    )
}

Set-Location $aqui
$env:PYTHONIOENCODING = "utf-8"
foreach ($e in $etapas) {
    if (Test-Path (Join-Path $aqui "campanha_pausa.json")) {
        "=== $(Get-Date -Format 'dd/MM HH:mm') pausa pedida -- fila parada antes de '$($e.rotulo)' ===" | Add-Content -Path $log -Encoding ASCII
        break
    }
    "=== $(Get-Date -Format 'dd/MM HH:mm') REFACAO pos-correcao da EA ($Lado): $($e.rotulo) ===" | Add-Content -Path $log -Encoding ASCII
    # cmd >> (nao o *>> do PowerShell 5.1, que grava UTF-16 e o vigia le lixo)
    $extra = ($e.extra -join " ")
    cmd /c "`"$py`" -u campanha.py --janela-dinamica --combos `"$($e.combos)`" --refazer-antes-de $corte $extra >> `"$log`" 2>&1"
}
"=== $(Get-Date -Format 'dd/MM HH:mm') FILA DE REFACAO ($Lado) TERMINOU ===" | Add-Content -Path $log -Encoding ASCII
