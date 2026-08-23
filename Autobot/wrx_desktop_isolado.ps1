<#
Move a janela de um processo (pelo PID) pro desktop virtual isolado
"WRX-MT5-Isolado", criando-o se ainda nao existir nesta sessao de login.

Existe porque o MT5 flasheia foco no proprio boot mesmo lancado minimizado
e sem ativar (SW_SHOWMINNOACTIVE) -- e o torneio de retencao relanca o
terminal uma vez POR CANDIDATO, entao um sweep de 14 formulas facilmente
passa de uma centena de relancamentos. Rodar isolado num desktop virtual
que o usuario nao esta olhando resolve sem reduzir o rigor do torneio.

Desktops virtuais do Windows nao persistem entre logoff/reboot -- por isso
a busca-ou-cria roda a cada chamada (idempotente, custo de milissegundos),
nunca assume que o desktop de uma chamada anterior ainda existe.

Modulo VirtualDesktop (Markus Scholtes, PSGallery, MIT) instalado em
escopo do usuario -- nao mexe no sistema, nada de admin.
#>
param(
    [switch]$Preparar,
    [int]$ProcessoPid = 0,
    [int]$EsperaSegundos = 8
)

Import-Module VirtualDesktop -ErrorAction Stop

$NOME = "WRX-MT5-Isolado"

function Obter-DesktopIsolado {
    $d = Get-Desktop -Index $NOME -ErrorAction SilentlyContinue
    if ($d) { return $d }
    $novo = New-Desktop
    Set-DesktopName -Desktop $novo -Name $NOME | Out-Null
    return $novo
}

if ($Preparar) {
    $d = Obter-DesktopIsolado
    Write-Output "desktop isolado pronto: $NOME (indice $(Get-DesktopIndex -Desktop $d))"
    exit 0
}

if ($ProcessoPid -le 0) {
    Write-Output "uso: -Preparar  OU  -ProcessoPid <numero>"
    exit 1
}

$desktop = Obter-DesktopIsolado
$limite = (Get-Date).AddSeconds($EsperaSegundos)
$hwnd = 0
while ((Get-Date) -lt $limite) {
    try {
        $proc = Get-Process -Id $ProcessoPid -ErrorAction Stop
    } catch {
        # processo ja morreu (self-close rapido demais) -- nada a mover
        exit 0
    }
    if ($proc.MainWindowHandle -ne 0) { $hwnd = $proc.MainWindowHandle; break }
    Start-Sleep -Milliseconds 300
}

if ($hwnd -ne 0) {
    Move-Window -Desktop $desktop -Hwnd $hwnd | Out-Null
    Write-Output "PID $ProcessoPid movido pro desktop isolado"
} else {
    Write-Output "PID $ProcessoPid sem janela principal ate o limite -- nada movido"
}
