# Espera o watcher da recalibracao do 03_TRAIL_ONLY (_fila_trail_apos_calibracao.ps1)
# terminar de verdade -- marcador "03_TRAIL_ONLY RECALIBRADO" no log --
# so entao dispara o estagio 3: confirmacao de 1 ano das formulas aprovadas
# de cada sistema (_confirmacao_longa.py). Uso interno, apagar depois.
$logAlvo = "recalibracao_trail_pos_fixes.log"

while ($true) {
    if (Test-Path $logAlvo) {
        $conteudo = Get-Content $logAlvo -Raw -ErrorAction SilentlyContinue
        if ($conteudo -match "03_TRAIL_ONLY RECALIBRADO") {
            break
        }
    }
    Start-Sleep -Seconds 30
}
Start-Sleep -Seconds 5

Set-Location "C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot"
$python = "C:\Users\Lucas Pedroso\AppData\Local\Programs\Python\Python310\python.exe"
& $python _confirmacao_longa.py *>> confirmacao_longa_driver.log
