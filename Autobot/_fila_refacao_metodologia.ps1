# Refacao com a METODOLOGIA NOVA (2026-09-26, commit bad1b47f, dono: "segue
# com sugerido"): holdout lacrado de 90 dias, treino max 2 anos, periodo
# anterior -5%, amostra pequena = inconclusivo. Tudo que rodou antes do corte
# foi decidido pela metodologia antiga (e 18 linhas de 13:49-13:57 sao
# reprovacoes FALSAS do LiveUpdate do build 6230) -- refaz os 4 ex-campeoes e
# os 43 da refacao pos-correcao da EA. Ordem: ex-campeoes primeiro, depois os
# melhores candidatos (expectancy). Cada lado na instalacao com os templates:
#   -Lado clone    : metais (teto 3.5 = 15 min) + acoes/indices (20 min)  (28)
#   -Lado original : forex unilateral + forex BOTH (economico) + BOLLINGER (19)
# Para sozinha se a campanha sair com codigo 3 (MT5 nao executou 3x seguidas).
# Pausa a qualquer momento: botao Pause do painel / campanha_pausa.json.
param([ValidateSet("clone", "original")][string]$Lado,
      [int]$EsperarPid = 0)

$ErrorActionPreference = "Continue"
$aqui = "C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot"
$py = "C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python310\python.exe"
$log = Join-Path $aqui "campanha_refacao_metodologia_$Lado.log"
$corte = "2026-09-26T14:30"

if ($EsperarPid -gt 0) {
    while (Get-Process -Id $EsperarPid -ErrorAction SilentlyContinue) {
        Start-Sleep -Seconds 60
    }
}

# Build 6230 pendente nas duas instalacoes e o LiveUpdate reverte sozinho
# (ver mt5_runner.hash_pular_update): fica no 6182 -- o build de todo o
# historico -- com o hash de "pular" que o proprio updater usa em CADA
# instalacao, em mt5_pular_update.json (clone 14:27/14:34, original 14:41).
if ($Lado -eq "clone") {
    $env:WRX_MT5_DATA_DIR = "C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal\4A85BF7BB91E709E95066E8432253C88"
    $env:WRX_MT5_INSTALL_DIR = "C:\Users\Lucas Pedroso\Documents\White Rabbit X\MT5_Optimizer2"
    $etapas = @(
        @{rotulo = "metais"; extra = @("--timeout-geometria-min", "15");
          combos = "XAUUSD:04_SLTP_TRAIL:BUY_MULTI,XAUUSD:05_BE_TRAIL:BUY_MULTI,XAUUSD:05_BE_TRAIL:SELL_MULTI,XAUUSD:04_SLTP_TRAIL:SELL_MULTI,XAUUSD:11_SIGNAL_ONLY:BUY_MULTI,XAGUSD:04_SLTP_TRAIL:BUY_MULTI,XAGUSD:04_SLTP_TRAIL:SELL_MULTI,XAUEUR:04_SLTP_TRAIL:BUY_MULTI,XAUEUR:04_SLTP_TRAIL:SELL_MULTI"},
        @{rotulo = "acoes e indices"; extra = @("--timeout-geometria-min", "20");
          combos = "NVDA:04_SLTP_TRAIL:BUY_MULTI,.US500Cash:04_SLTP_TRAIL:SELL_MULTI,.DE40Cash:04_SLTP_TRAIL:BUY_MULTI,.US500Cash:04_SLTP_TRAIL:BUY_MULTI,.USTECHCash:04_SLTP_TRAIL:SELL_MULTI,.USTECHCash:04_SLTP_TRAIL:BUY_MULTI,.DE40Cash:04_SLTP_TRAIL:SELL_MULTI,NVDA:04_SLTP_TRAIL:SELL_MULTI,.US30Cash:04_SLTP_TRAIL:BUY_MULTI,.US30Cash:04_SLTP_TRAIL:SELL_MULTI,.JP225Cash:04_SLTP_TRAIL:BUY_MULTI,.JP225Cash:04_SLTP_TRAIL:SELL_MULTI,GOOGL:04_SLTP_TRAIL:SELL_MULTI,GOOGL:04_SLTP_TRAIL:BUY_MULTI,META:04_SLTP_TRAIL:BUY_MULTI,META:04_SLTP_TRAIL:SELL_MULTI,AMZN:04_SLTP_TRAIL:BUY_MULTI,AMZN:04_SLTP_TRAIL:SELL_MULTI,AAPL:04_SLTP_TRAIL:BUY_MULTI"}
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
    "=== $(Get-Date -Format 'dd/MM HH:mm') REFACAO metodologia nova ($Lado): $($e.rotulo) ===" | Add-Content -Path $log -Encoding ASCII
    # cmd >> (nao o *>> do PowerShell 5.1, que grava UTF-16 e o vigia le lixo)
    $extra = ($e.extra -join " ")
    cmd /c "`"$py`" -u campanha.py --janela-dinamica --combos `"$($e.combos)`" --refazer-antes-de $corte $extra >> `"$log`" 2>&1"
    if ($LASTEXITCODE -eq 3) {
        "=== $(Get-Date -Format 'dd/MM HH:mm') INFRA: o MT5 nao executou 3 combos seguidos -- fila PARADA (ver o log; terminal atualizando?) ===" | Add-Content -Path $log -Encoding ASCII
        break
    }
}
"=== $(Get-Date -Format 'dd/MM HH:mm') FILA DE REFACAO METODOLOGIA ($Lado) TERMINOU ===" | Add-Content -Path $log -Encoding ASCII
