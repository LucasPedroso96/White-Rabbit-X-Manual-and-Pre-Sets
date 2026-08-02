[CmdletBinding()]
param(
    [string]$LibraryRoot = 'C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal\59EECBFD4A9CCD98CCBC61E96D5DED8E\MQL5\Profiles\Tester\White_Rabbit_X_Asset_Library_Sets',
    [string]$TemplatePath = 'C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal\59EECBFD4A9CCD98CCBC61E96D5DED8E\MQL5\Profiles\Tester\exemplo arquivo set.set',
    [string]$EaSourcePath = 'C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal\59EECBFD4A9CCD98CCBC61E96D5DED8E\MQL5\Experts\White Rabbit X (Global Multi-Indicator).mq5',
    [string]$OutputRoot = '',
    [string]$WfoEndDate = '',
    [int]$MagicBase = 590000000,
    [int]$MaxCartesianPasses = 5000,
    [int]$MaxOptimizationFlags = 6,
    [switch]$RebuildExisting
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$setEncoding = [System.Text.UnicodeEncoding]::new($false, $true)
$utf8Bom = [System.Text.UTF8Encoding]::new($true)
$invariant = [Globalization.CultureInfo]::InvariantCulture
$markerText = 'WHITE_RABBIT_X_OPTIMIZATION_PROFILE_LIBRARY_V1'
$generatedAt = Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'

function Get-NormalizedFullPath {
    param([Parameter(Mandatory)][string]$Path)
    return [IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
}

function Assert-ChildPath {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$Candidate
    )
    $rootFull = Get-NormalizedFullPath $Root
    $candidateFull = Get-NormalizedFullPath $Candidate
    $prefix = $rootFull + [IO.Path]::DirectorySeparatorChar
    if (-not $candidateFull.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe path outside output root: $candidateFull"
    }
    return $candidateFull
}

function Write-Utf8BomFile {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Content
    )
    $directory = Split-Path -Parent $Path
    if ($directory) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }
    [IO.File]::WriteAllText($Path, $Content, $utf8Bom)
}

function Get-Sha256Text {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Text)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text)))).Replace('-', '')
    }
    finally {
        $sha.Dispose()
    }
}

function Copy-ValueMap {
    param([Parameter(Mandatory)][System.Collections.IDictionary]$Source)
    $copy = @{}
    foreach ($key in $Source.Keys) {
        $copy[[string]$key] = [string]$Source[$key]
    }
    return $copy
}

function Set-ProfileValue {
    param(
        [Parameter(Mandatory)][hashtable]$Map,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Value
    )
    if (-not $script:templateValues.Contains($Name)) {
        throw "Unknown template input: $Name"
    }
    $Map[$Name] = $Value
}

function Set-ProfileTuple {
    param(
        [Parameter(Mandatory)][hashtable]$Map,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Current,
        [Parameter(Mandatory)][string]$Start,
        [Parameter(Mandatory)][string]$Step,
        [Parameter(Mandatory)][string]$Stop,
        [ValidateSet('Y', 'N')][string]$Optimize = 'N'
    )
    Set-ProfileValue $Map $Name "$Current||$Start||$Step||$Stop||$Optimize"
}

function Set-FixedTuple {
    param(
        [Parameter(Mandatory)][hashtable]$Map,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Value
    )
    $step = if ($Value -match '^(true|false)$') { '0' } else { '1' }
    Set-ProfileTuple $Map $Name $Value $Value $step $Value 'N'
}

function Set-BooleanOptimization {
    param(
        [Parameter(Mandatory)][hashtable]$Map,
        [Parameter(Mandatory)][string]$Name,
        [ValidateSet('true', 'false')][string]$Current
    )
    Set-ProfileTuple $Map $Name $Current 'false' '0' 'true' 'Y'
}

function Get-TupleParts {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Value)
    if ([string]::IsNullOrEmpty($Value)) {
        return $null
    }
    $parts = [regex]::Split($Value, '\|\|')
    if ($parts.Count -ne 5) {
        return $null
    }
    return $parts
}

function Convert-ToInvariantDouble {
    param([Parameter(Mandatory)][string]$Value)
    $number = 0.0
    if (-not [double]::TryParse($Value, [Globalization.NumberStyles]::Float, $invariant, [ref]$number)) {
        throw "Not a numeric tuple value: $Value"
    }
    return $number
}

function Get-CandidateCount {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string[]]$Parts
    )
    $start = $Parts[1]
    $step = $Parts[2]
    $stop = $Parts[3]
    if ($start -match '^(true|false)$' -and $stop -match '^(true|false)$') {
        return $(if ($start -eq $stop) { 1L } else { 2L })
    }
    $startNumber = Convert-ToInvariantDouble $start
    $stepNumber = Convert-ToInvariantDouble $step
    $stopNumber = Convert-ToInvariantDouble $stop
    if ($stepNumber -le 0.0 -or $stopNumber -lt $startNumber) {
        throw "Invalid enabled optimization tuple for ${Name}: $($Parts -join '||')"
    }
    $raw = (($stopNumber - $startNumber) / $stepNumber)
    $rounded = [math]::Round($raw)
    if ([math]::Abs($raw - $rounded) -gt 1e-8) {
        throw "Enabled tuple endpoint is not aligned for ${Name}: $($Parts -join '||')"
    }
    return [long]$rounded + 1L
}

function Get-EnabledOptimization {
    param([Parameter(Mandatory)][hashtable]$Map)
    $enabled = [System.Collections.Generic.List[object]]::new()
    foreach ($name in $script:templateOrder) {
        $parts = Get-TupleParts ([string]$Map[$name])
        if ($null -ne $parts -and $parts[4] -eq 'Y') {
            $count = Get-CandidateCount $name $parts
            if ($count -lt 2) {
                throw "Optimization flag Y has fewer than two candidates: $name"
            }
            $current = if ($parts[0] -match '^(true|false)$') {
                $parts[0]
            }
            else {
                $currentNumber = Convert-ToInvariantDouble $parts[0]
                $startNumber = Convert-ToInvariantDouble $parts[1]
                $stopNumber = Convert-ToInvariantDouble $parts[3]
                if ($currentNumber -lt $startNumber - 1e-8 -or $currentNumber -gt $stopNumber + 1e-8) {
                    throw "Current value is outside enabled range for ${name}: $($parts -join '||')"
                }
                $currentNumber
            }
            $enabled.Add([pscustomobject]@{ Name = $name; Candidates = $count; Current = $current })
        }
    }
    return @($enabled)
}

function Set-Exposure {
    param(
        [Parameter(Mandatory)][hashtable]$Map,
        [ValidateSet('BUY', 'SELL', 'BOTH_HEDGE')][string]$Side,
        [int]$PerSideLimit = 1
    )
    switch ($Side) {
        'BUY' {
            Set-FixedTuple $Map 'MaxLongTrades' ([string]$PerSideLimit)
            Set-FixedTuple $Map 'MaxShortTrades' '0'
            Set-FixedTuple $Map 'Hedging' 'false'
        }
        'SELL' {
            Set-FixedTuple $Map 'MaxLongTrades' '0'
            Set-FixedTuple $Map 'MaxShortTrades' ([string]$PerSideLimit)
            Set-FixedTuple $Map 'Hedging' 'false'
        }
        'BOTH_HEDGE' {
            Set-FixedTuple $Map 'MaxLongTrades' ([string]$PerSideLimit)
            Set-FixedTuple $Map 'MaxShortTrades' ([string]$PerSideLimit)
            Set-FixedTuple $Map 'Hedging' 'true'
        }
    }
}

function Get-NewsCurrenciesForGroup {
    param([Parameter(Mandatory)][string]$GroupCode)
    switch ($GroupCode) {
        '01_Forex' { return '' }
        '02_Metals' { return 'USD,EUR' }
        '03_Cryptocurrencies' { return 'USD' }
        '04_Indices_Energies' { return 'USD,EUR,JPY' }
        '05_US_Stocks_CFD' { return 'USD' }
        default { throw "Unknown group: $GroupCode" }
    }
}

function Set-IndicatorFixed {
    param(
        [Parameter(Mandatory)][hashtable]$Map,
        [Parameter(Mandatory)][pscustomobject]$Indicator
    )
    Set-FixedTuple $Map 'EntryIndicator' ([string]$Indicator.Value)
    Set-FixedTuple $Map 'Fast_EMA' ([string]$Indicator.Fast)
    Set-FixedTuple $Map 'Slow_EMA' ([string]$Indicator.Slow)
    Set-FixedTuple $Map 'MACD_SMA' ([string]$Indicator.Signal)
    Set-FixedTuple $Map 'InpAppliedPrice' '1'
}

function Set-IndicatorTuning {
    param(
        [Parameter(Mandatory)][hashtable]$Map,
        [Parameter(Mandatory)][pscustomobject]$Indicator
    )
    Set-FixedTuple $Map 'EntryIndicator' ([string]$Indicator.Value)
    Set-ProfileTuple $Map 'Fast_EMA' ([string]$Indicator.TuneFast) ([string]$Indicator.FastStart) ([string]$Indicator.FastStep) ([string]$Indicator.FastStop) 'Y'
    if ($Indicator.UsesSlow) {
        Set-ProfileTuple $Map 'Slow_EMA' ([string]$Indicator.TuneSlow) ([string]$Indicator.SlowStart) ([string]$Indicator.SlowStep) ([string]$Indicator.SlowStop) 'Y'
    }
    else {
        Set-FixedTuple $Map 'Slow_EMA' ([string]$Indicator.Slow)
    }
    if ($Indicator.UsesSignal) {
        Set-ProfileTuple $Map 'MACD_SMA' ([string]$Indicator.TuneSignal) ([string]$Indicator.SignalStart) ([string]$Indicator.SignalStep) ([string]$Indicator.SignalStop) 'Y'
    }
    else {
        Set-FixedTuple $Map 'MACD_SMA' ([string]$Indicator.Signal)
    }
    if ($Indicator.UsesPrice) {
        Set-ProfileTuple $Map 'InpAppliedPrice' '1' '1' '1' '7' 'Y'
    }
    else {
        Set-FixedTuple $Map 'InpAppliedPrice' '1'
    }
}

function New-BaseMap {
    param(
        [Parameter(Mandatory)][pscustomobject]$Group,
        [ValidateSet('BUY', 'SELL', 'BOTH_HEDGE')][string]$Side,
        [Parameter(Mandatory)][int]$MagicNumber,
        [Parameter(Mandatory)][string]$StrategyName
    )
    $map = Copy-ValueMap $script:allOptimizationDisabled
    Set-ProfileValue $map 'NomedaEstrategia' $StrategyName
    Set-FixedTuple $map 'TimeFrame' ([string]$Group.TimeFrame)
    Set-IndicatorFixed $map $script:indicators[0]
    Set-FixedTuple $map 'EntryMethod' '1'
    Set-FixedTuple $map 'ATR_TimeFrame' ([string]$Group.TimeFrame)
    Set-FixedTuple $map 'PeriodoATR' '14'
    Set-FixedTuple $map 'AtivarStop' 'true'
    Set-FixedTuple $map 'VelaStop' '0'
    Set-FixedTuple $map 'Stop' ([string]$Group.Stop)
    Set-FixedTuple $map 'TakeOrganico' 'false'
    Set-FixedTuple $map 'AtivarTake' 'true'
    Set-FixedTuple $map 'VelaTake' '0'
    Set-FixedTuple $map 'Take' ([string]$Group.Take)

    Set-FixedTuple $map 'AtivarFiltroMTF' 'false'
    Set-FixedTuple $map 'MTF_RequererAmbos' 'false'
    Set-FixedTuple $map 'AtivarFiltroMA' 'false'
    Set-FixedTuple $map 'MA_TimeFrame' ([string]$Group.TimeFrame)
    Set-FixedTuple $map 'MA_Period' '200'
    Set-FixedTuple $map 'MA_Method' '1'
    Set-FixedTuple $map 'MA_AppliedPrice' '1'
    Set-FixedTuple $map 'MetodoMA' '2'
    Set-FixedTuple $map 'SentidoMA' '0'
    Set-FixedTuple $map 'MA_SlopeLookback' '3'
    Set-FixedTuple $map 'AtivarFiltroADX' 'false'
    Set-FixedTuple $map 'ADX_TimeFrame' ([string]$Group.TimeFrame)
    Set-FixedTuple $map 'ADX_Period' '14'
    Set-FixedTuple $map 'ADX_Limiar' '25'
    Set-FixedTuple $map 'MetodoADX' '0'
    Set-FixedTuple $map 'EntradaATR' 'false'
    Set-FixedTuple $map 'VolatilityFilter' '1'
    Set-FixedTuple $map 'AtivarFiltroNoticias' 'false'
    Set-FixedTuple $map 'NewsSomenteAltoImpacto' 'true'
    Set-FixedTuple $map 'NewsMinutosAntes' '15'
    Set-FixedTuple $map 'NewsMinutosDepois' '15'
    Set-ProfileValue $map 'NewsMoedasManual' (Get-NewsCurrenciesForGroup $Group.Code)

    Set-FixedTuple $map 'AtivarBreakeven' 'true'
    Set-FixedTuple $map 'BreakevenDistancia' '1.0'
    Set-FixedTuple $map 'AtivarTrailATR' 'false'
    Set-FixedTuple $map 'MetodoDeCalculo' '1'
    Set-FixedTuple $map 'TrailVela' '0'
    Set-FixedTuple $map 'Trail' ([string]$Group.Trail)
    Set-FixedTuple $map 'ReversalExitMode' '2'
    Set-FixedTuple $map 'ReversalExitUseEntryFilters' 'false'

    Set-FixedTuple $map 'TradeCapitalPercentage' '100'
    Set-FixedTuple $map 'PositionSizeMode' '2'
    Set-FixedTuple $map 'PositionSizeValue' '0.01'
    Set-FixedTuple $map 'CapitalBaseR' '0'
    Set-FixedTuple $map 'MaxRiscoTradeR' '0'
    Set-FixedTuple $map 'DailyLossLimitPercent' '0'
    Set-FixedTuple $map 'MaxEquityDrawdownPercent' '30'
    Set-FixedTuple $map 'MinFreeMarginPercent' '50'
    Set-FixedTuple $map 'RecoveryMode' '0'
    Set-FixedTuple $map 'Multiplicador' '1'
    Set-FixedTuple $map 'MaxMartingaleSteps' '0'
    Set-FixedTuple $map 'MaxMartingaleLot' '0'
    Set-FixedTuple $map 'DAlembertStep' '0.01'
    Set-FixedTuple $map 'GridMode' '0'
    Set-FixedTuple $map 'UsarsomenteATRGRID' 'false'
    Set-FixedTuple $map 'DistanciaMinima' '2'

    Set-FixedTuple $map 'Fecharordensforadohorario' 'false'
    Set-FixedTuple $map 'TOD_From_Hour' '0'
    Set-FixedTuple $map 'TOD_From_Min' '0'
    Set-FixedTuple $map 'TOD_To_Hour' '23'
    Set-FixedTuple $map 'TOD_To_Min' '55'
    foreach ($day in @('TradeMonday', 'TradeTuesday', 'TradeWednesday', 'TradeThursday', 'TradeFriday')) {
        Set-FixedTuple $map $day 'true'
    }
    $weekend = if ($Group.Code -eq '03_Cryptocurrencies') { 'true' } else { 'false' }
    Set-FixedTuple $map 'TradeSaturday' $weekend
    Set-FixedTuple $map 'TradeSunday' $weekend

    Set-FixedTuple $map 'MaxSpread' '0'
    Set-FixedTuple $map 'MaxSlippage' ([string]$Group.Slippage)
    Set-Exposure $map $Side 1
    Set-FixedTuple $map 'MagicNumber' ([string]$MagicNumber)
    Set-FixedTuple $map 'EnableChartDashboard' 'false'
    Set-FixedTuple $map 'ShowClosedDealLabels' 'false'
    Set-FixedTuple $map 'ApplyEmbeddedChartTheme' 'false'
    Set-FixedTuple $map 'AtivarWFO' 'false'
    Set-FixedTuple $map 'MetodoDeEntradawfo' '0'
    Set-ProfileValue $map 'input_end_date' $script:wfoEndDate
    Set-FixedTuple $map 'wfo_windowSize' '360'
    Set-FixedTuple $map 'wfo_customWindowSizeDays' '0'
    Set-FixedTuple $map 'wfo_stepSize' '180'
    Set-FixedTuple $map 'wfo_customStepSizePercent' '0'
    Set-FixedTuple $map 'selectedFormula' '7'
    return $map
}

function Configure-Profile {
    param(
        [Parameter(Mandatory)][hashtable]$Map,
        [Parameter(Mandatory)][pscustomobject]$Definition,
        [Parameter(Mandatory)][pscustomobject]$Group,
        [Parameter(Mandatory)][string]$Side
    )
    $v = $Definition.Variant
    switch ($Definition.Kind) {
        'ENTRY_SCREEN' {
            Set-IndicatorFixed $Map $v
            Set-ProfileTuple $Map 'TimeFrame' ([string]$Group.TimeFrame) '0' '1' '5' 'Y'
            Set-ProfileTuple $Map 'EntryMethod' '1' '0' '1' '6' 'Y'
        }
        'INDICATOR_TUNING' {
            Set-IndicatorTuning $Map $v
        }
        'FILTER_CORE_SCREEN' {
            foreach ($name in @('AtivarFiltroMTF', 'AtivarFiltroMA', 'AtivarFiltroADX', 'EntradaATR')) {
                Set-BooleanOptimization $Map $name 'false'
            }
        }
        'FILTER_NEWS_SCREEN' {
            Set-BooleanOptimization $Map 'AtivarFiltroNoticias' 'false'
            Set-FixedTuple $Map 'NewsSomenteAltoImpacto' 'true'
        }
        'FILTER_MA_SCREEN' {
            Set-FixedTuple $Map 'AtivarFiltroMA' 'true'
            Set-ProfileTuple $Map 'MA_Method' '1' '0' '1' '3' 'Y'
            Set-ProfileTuple $Map 'MetodoMA' '2' '0' '1' '3' 'Y'
            Set-ProfileTuple $Map 'SentidoMA' '0' '0' '1' '1' 'Y'
        }
        'FILTER_ADX_SCREEN' {
            Set-FixedTuple $Map 'AtivarFiltroADX' 'true'
            Set-ProfileTuple $Map 'MetodoADX' '0' '0' '1' '1' 'Y'
        }
        'FILTER_VOL_SCREEN' {
            Set-FixedTuple $Map 'EntradaATR' 'true'
            Set-ProfileTuple $Map 'VolatilityFilter' '1' '0' '1' '1' 'Y'
        }
        'FILTER_MTF_SCREEN' {
            Set-FixedTuple $Map 'AtivarFiltroMTF' 'true'
            Set-BooleanOptimization $Map 'MTF_RequererAmbos' 'false'
        }
        'FILTER_MA_TUNING' {
            Set-FixedTuple $Map 'AtivarFiltroMA' 'true'
            Set-ProfileTuple $Map 'MA_TimeFrame' ([string]$Group.TimeFrame) '0' '1' '5' 'Y'
            Set-ProfileTuple $Map 'MA_Period' '200' '50' '25' '250' 'Y'
            Set-ProfileTuple $Map 'MA_AppliedPrice' '1' '1' '1' '7' 'Y'
            Set-ProfileTuple $Map 'MA_SlopeLookback' '3' '1' '1' '7' 'Y'
        }
        'FILTER_ADX_TUNING' {
            Set-FixedTuple $Map 'AtivarFiltroADX' 'true'
            Set-ProfileTuple $Map 'ADX_TimeFrame' ([string]$Group.TimeFrame) '0' '1' '5' 'Y'
            Set-ProfileTuple $Map 'ADX_Period' '13' '7' '3' '28' 'Y'
            Set-ProfileTuple $Map 'ADX_Limiar' '25' '15' '5' '40' 'Y'
        }
        'FILTER_NEWS_TUNING' {
            Set-FixedTuple $Map 'AtivarFiltroNoticias' 'true'
            Set-BooleanOptimization $Map 'NewsSomenteAltoImpacto' 'true'
            Set-ProfileTuple $Map 'NewsMinutosAntes' '15' '0' '15' '60' 'Y'
            Set-ProfileTuple $Map 'NewsMinutosDepois' '15' '0' '15' '60' 'Y'
        }
        'FILTER_ATR_TUNING' {
            Set-FixedTuple $Map 'EntradaATR' 'true'
            Set-ProfileTuple $Map 'ATR_TimeFrame' ([string]$Group.TimeFrame) '0' '1' '5' 'Y'
            Set-ProfileTuple $Map 'PeriodoATR' '13' '7' '3' '28' 'Y'
        }
        'FILTER_MTF_TUNING' {
            Set-FixedTuple $Map 'AtivarFiltroMTF' 'true'
            Set-ProfileTuple $Map 'TimeFrame' ([string]$Group.TimeFrame) '0' '1' '5' 'Y'
            Set-BooleanOptimization $Map 'MTF_RequererAmbos' 'false'
        }
        'EXIT_GATE_SCREEN' {
            Set-BooleanOptimization $Map 'AtivarTake' 'true'
            Set-BooleanOptimization $Map 'AtivarBreakeven' 'true'
            Set-BooleanOptimization $Map 'AtivarTrailATR' 'false'
        }
        'EXIT_ORGANIC_SCREEN' {
            Set-FixedTuple $Map 'AtivarTake' 'true'
            Set-BooleanOptimization $Map 'TakeOrganico' 'false'
        }
        'EXIT_REVERSAL_SCREEN' {
            Set-Exposure $Map 'BOTH_HEDGE' 1
            Set-FixedTuple $Map 'GridMode' '0'
            Set-ProfileTuple $Map 'ReversalExitMode' '2' '0' '1' '2' 'Y'
        }
        'EXIT_SLTP_TUNING' {
            Set-FixedTuple $Map 'AtivarStop' 'true'
            Set-FixedTuple $Map 'AtivarTake' 'true'
            Set-FixedTuple $Map 'TakeOrganico' 'false'
            Set-ProfileTuple $Map 'Stop' ([string]$Group.Stop) '1.5' '0.5' '6.0' 'Y'
            Set-ProfileTuple $Map 'Take' ([string]$Group.Take) '1.5' '0.5' '6.0' 'Y'
        }
        'EXIT_CANDLE_TUNING' {
            Set-ProfileTuple $Map 'VelaStop' '0' '0' '1' '3' 'Y'
            Set-ProfileTuple $Map 'VelaTake' '0' '0' '1' '3' 'Y'
        }
        'EXIT_BE_TUNING' {
            Set-FixedTuple $Map 'AtivarBreakeven' 'true'
            Set-ProfileTuple $Map 'BreakevenDistancia' '1.0' '0.5' '0.25' '3.0' 'Y'
        }
        'EXIT_TRAIL_TUNING' {
            Set-FixedTuple $Map 'AtivarTrailATR' 'true'
            Set-ProfileTuple $Map 'MetodoDeCalculo' '1' '0' '1' '4' 'Y'
            Set-ProfileTuple $Map 'TrailVela' '0' '0' '1' '3' 'Y'
            Set-ProfileTuple $Map 'Trail' ([string]$Group.Trail) '1.0' '0.5' '5.0' 'Y'
        }
        'EXIT_ORGANIC_TUNING' {
            Set-FixedTuple $Map 'AtivarTake' 'true'
            Set-FixedTuple $Map 'TakeOrganico' 'true'
            Set-ProfileTuple $Map 'VelaTake' '0' '0' '1' '3' 'Y'
            Set-ProfileTuple $Map 'Take' ([string]$Group.Take) '1.0' '0.5' '5.0' 'Y'
        }
        'EXIT_REVERSAL_FILTER_TUNING' {
            Set-FixedTuple $Map 'ReversalExitMode' '2'
            Set-BooleanOptimization $Map 'ReversalExitUseEntryFilters' 'false'
        }
        'RISK_PERCENT' {
            Set-FixedTuple $Map 'PositionSizeMode' '0'
            Set-FixedTuple $Map 'AtivarStop' 'true'
            Set-ProfileTuple $Map 'PositionSizeValue' '1.0' '0.25' '0.25' '2.0' 'Y'
            Set-ProfileTuple $Map 'TradeCapitalPercentage' '100' '25' '25' '100' 'Y'
        }
        'RISK_MONETARY' {
            Set-FixedTuple $Map 'PositionSizeMode' '1'
            Set-ProfileTuple $Map 'PositionSizeValue' '5000' '1000' '1000' '10000' 'Y'
        }
        'RISK_FIXED_LOT' {
            Set-FixedTuple $Map 'PositionSizeMode' '2'
            Set-ProfileTuple $Map 'PositionSizeValue' '0.01' '0.01' '0.01' '0.10' 'Y'
        }
        'RISK_FIXED_R' {
            Set-FixedTuple $Map 'PositionSizeMode' '3'
            Set-FixedTuple $Map 'AtivarStop' 'true'
            Set-FixedTuple $Map 'GridMode' '0'
            Set-FixedTuple $Map 'RecoveryMode' '0'
            Set-ProfileTuple $Map 'PositionSizeValue' '1.0' '0.25' '0.25' '2.0' 'Y'
            Set-ProfileTuple $Map 'MaxRiscoTradeR' '1.0' '0.5' '0.5' '3.0' 'Y'
        }
        'RISK_PROTECTION' {
            Set-ProfileTuple $Map 'DailyLossLimitPercent' '2' '1' '1' '5' 'Y'
            Set-ProfileTuple $Map 'MaxEquityDrawdownPercent' '30' '10' '5' '40' 'Y'
            Set-ProfileTuple $Map 'MinFreeMarginPercent' '50' '20' '10' '80' 'Y'
        }
        'RISK_ALLOCATION' {
            Set-ProfileTuple $Map 'TradeCapitalPercentage' '100' '25' '25' '100' 'Y'
        }
        'RECOVERY_MARTINGALE' {
            Set-FixedTuple $Map 'PositionSizeMode' '2'
            Set-FixedTuple $Map 'RecoveryMode' '1'
            Set-FixedTuple $Map 'GridMode' '0'
            Set-FixedTuple $Map 'MaxMartingaleLot' '0'
            Set-Exposure $Map $Side 1
            Set-ProfileTuple $Map 'PositionSizeValue' '0.01' '0.01' '0.01' '0.03' 'Y'
            Set-ProfileTuple $Map 'Multiplicador' '1.5' '1.25' '0.25' '2.0' 'Y'
            Set-ProfileTuple $Map 'MaxMartingaleSteps' '3' '1' '1' '5' 'Y'
        }
        'RECOVERY_DALEMBERT' {
            Set-FixedTuple $Map 'PositionSizeMode' '2'
            Set-FixedTuple $Map 'RecoveryMode' '2'
            Set-FixedTuple $Map 'GridMode' '0'
            Set-FixedTuple $Map 'MaxMartingaleLot' '0'
            Set-Exposure $Map $Side 1
            Set-ProfileTuple $Map 'PositionSizeValue' '0.01' '0.01' '0.01' '0.03' 'Y'
            Set-ProfileTuple $Map 'DAlembertStep' '0.02' '0.01' '0.01' '0.05' 'Y'
            Set-ProfileTuple $Map 'MaxMartingaleSteps' '3' '1' '1' '5' 'Y'
        }
        'GRID_TUNING' {
            Set-FixedTuple $Map 'AtivarStop' 'false'
            Set-FixedTuple $Map 'AtivarTake' 'true'
            Set-FixedTuple $Map 'TakeOrganico' 'false'
            Set-FixedTuple $Map 'AtivarBreakeven' 'false'
            Set-FixedTuple $Map 'AtivarTrailATR' 'false'
            Set-FixedTuple $Map 'ReversalExitMode' '0'
            Set-FixedTuple $Map 'PositionSizeMode' '2'
            Set-FixedTuple $Map 'PositionSizeValue' '0.01'
            Set-FixedTuple $Map 'RecoveryMode' '0'
            Set-FixedTuple $Map 'GridMode' ([string]$v.GridMode)
            Set-FixedTuple $Map 'Hedging' 'true'
            Set-FixedTuple $Map 'EntryMethod' '0'
            Set-Exposure $Map $Side 5
            Set-FixedTuple $Map 'Hedging' 'true'
            Set-ProfileTuple $Map 'Multiplicador' '1.5' '1.0' '0.25' '2.0' 'Y'
            Set-ProfileTuple $Map 'DistanciaMinima' '2.0' '1.0' '0.5' '4.0' 'Y'
            Set-ProfileTuple $Map 'Take' ([string]$Group.Take) '1.5' '0.5' '5.0' 'Y'
            Set-BooleanOptimization $Map 'UsarsomenteATRGRID' 'false'
            if ($Side -eq 'BUY') {
                Set-ProfileTuple $Map 'MaxLongTrades' '5' '2' '1' '6' 'Y'
            }
            else {
                Set-ProfileTuple $Map 'MaxShortTrades' '5' '2' '1' '6' 'Y'
            }
            Set-FixedTuple $Map 'selectedFormula' '1'
        }
        'SCHEDULE_START' {
            Set-ProfileTuple $Map 'TOD_From_Hour' '0' '0' '3' '18' 'Y'
            Set-BooleanOptimization $Map 'Fecharordensforadohorario' 'false'
        }
        'SCHEDULE_END' {
            Set-FixedTuple $Map 'TOD_From_Hour' '0'
            Set-FixedTuple $Map 'TOD_To_Min' '0'
            Set-ProfileTuple $Map 'TOD_To_Hour' '18' '6' '3' '21' 'Y'
            Set-BooleanOptimization $Map 'Fecharordensforadohorario' 'false'
        }
        'SCHEDULE_WEEKDAYS' {
            foreach ($name in @('TradeMonday', 'TradeTuesday', 'TradeWednesday', 'TradeThursday', 'TradeFriday')) {
                Set-BooleanOptimization $Map $name 'true'
            }
        }
        'SCHEDULE_WEEKEND' {
            Set-BooleanOptimization $Map 'TradeSaturday' 'true'
            Set-BooleanOptimization $Map 'TradeSunday' 'true'
        }
        'WFO_FIXED' {
            Set-FixedTuple $Map 'AtivarWFO' 'true'
            Set-ProfileTuple $Map 'MetodoDeEntradawfo' '1' '0' '1' '1' 'Y'
            Set-FixedTuple $Map 'wfo_windowSize' ([string]$v.Window)
            Set-FixedTuple $Map 'wfo_customWindowSizeDays' '0'
            Set-FixedTuple $Map 'wfo_stepSize' ([string]$v.Step)
            Set-FixedTuple $Map 'wfo_customStepSizePercent' '0'
            Set-ProfileTuple $Map 'selectedFormula' '7' '1' '1' '14' 'Y'
        }
        'WFO_CUSTOM' {
            Set-FixedTuple $Map 'AtivarWFO' 'true'
            Set-ProfileTuple $Map 'MetodoDeEntradawfo' '1' '0' '1' '1' 'Y'
            Set-FixedTuple $Map 'wfo_windowSize' '-1'
            Set-ProfileTuple $Map 'wfo_customWindowSizeDays' '120' '60' '30' '240' 'Y'
            Set-FixedTuple $Map 'wfo_stepSize' '-1'
            Set-ProfileTuple $Map 'wfo_customStepSizePercent' '20' '10' '5' '30' 'Y'
            Set-ProfileTuple $Map 'selectedFormula' '7' '1' '1' '14' 'Y'
        }
        default {
            throw "Unknown profile kind: $($Definition.Kind)"
        }
    }
}

function New-SetContent {
    param(
        [Parameter(Mandatory)][hashtable]$Values,
        [Parameter(Mandatory)][pscustomobject]$Metadata
    )
    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add("; White Rabbit X optimization profile generated $generatedAt")
    $lines.Add('; SetRole=OPTIMIZATION_PROFILE')
    $lines.Add("; OptimizationStage=$($Metadata.OptimizationStage)")
    $lines.Add("; ParameterFamily=$($Metadata.ParameterFamily)")
    $lines.Add("; EnabledOptimizationParameters=$($Metadata.EnabledOptimizationParameters)")
    $lines.Add("; CartesianPasses=$($Metadata.CartesianPasses)")
    $lines.Add("; RecommendedAlgorithm=$($Metadata.RecommendedAlgorithm)")
    $lines.Add("; Status=$($Metadata.Status)")
    $lines.Add("; Dependencies=$($Metadata.Dependencies)")
    $lines.Add('; Never use this file directly in a live chart. Promote a validated winner to a fixed preset with every flag set to N.')
    for ($index = 4; $index -lt $script:templateLines.Count; $index++) {
        $line = [string]$script:templateLines[$index]
        if ($line -match '^([^;=]+)=(.*)$') {
            $name = $matches[1]
            $value = if ($Values.ContainsKey($name)) { [string]$Values[$name] } else { [string]$script:templateValues[$name] }
            $lines.Add("$name=$value")
        }
        else {
            $lines.Add($line)
        }
    }
    return ($lines -join "`r`n") + "`r`n"
}

function Get-OriginalLibraryAudit {
    param([Parameter(Mandatory)][string]$Root)
    $files = @(Get-ChildItem -LiteralPath $Root -Recurse -File -Filter '*.set' | Sort-Object FullName)
    $totalFlags = 0L
    $withFlags = 0
    $zeroFlags = 0
    $maximumPasses = 0L
    $maximumRelativePath = ''
    $indexLines = [System.Collections.Generic.List[string]]::new()
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($Root.Length).TrimStart('\').Replace('\', '/')
        $text = [IO.File]::ReadAllText($file.FullName, $setEncoding)
        $flagCount = 0
        $passes = 1L
        foreach ($line in [regex]::Split($text, '\r\n|\n|\r')) {
            if ($line -match '^([^;=]+)=(.*)$') {
                $parts = Get-TupleParts $matches[2]
                if ($null -ne $parts -and $parts[4] -eq 'Y') {
                    $flagCount++
                    $passes *= Get-CandidateCount $matches[1] $parts
                }
            }
        }
        $totalFlags += $flagCount
        if ($flagCount -eq 0) { $zeroFlags++ } else { $withFlags++ }
        if ($passes -gt $maximumPasses) {
            $maximumPasses = $passes
            $maximumRelativePath = $relative
        }
        $indexLines.Add("$relative|$((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash)")
    }
    return [pscustomobject]@{
        SetCount = $files.Count
        ZeroFlagSets = $zeroFlags
        FlaggedSets = $withFlags
        TotalFlags = $totalFlags
        MaximumPasses = $maximumPasses
        MaximumPassesFile = $maximumRelativePath
        PathHashInventorySHA256 = Get-Sha256Text ($indexLines -join "`n")
    }
}

function Add-Definition {
    param(
        [Parameter(Mandatory)][string]$Folder,
        [Parameter(Mandatory)][string]$Code,
        [Parameter(Mandatory)][string]$Stage,
        [Parameter(Mandatory)][string]$ParameterFamily,
        [Parameter(Mandatory)][string]$System,
        [Parameter(Mandatory)][string]$Kind,
        [Parameter(Mandatory)][string]$Status,
        [Parameter(Mandatory)][string]$Dependencies,
        [string]$Indicator = 'I00_MACD',
        [string]$EntryMethod = 'M01_SIGNAL_CROSS',
        [AllowNull()][object]$Variant = $null,
        [string[]]$Groups = @(),
        [string[]]$Sides = @('BUY', 'SELL')
    )
    if ($Groups.Count -eq 0) {
        $Groups = @($script:groupCodes)
    }
    $script:definitions.Add([pscustomobject]@{
        Folder = $Folder
        Code = $Code
        OptimizationStage = $Stage
        ParameterFamily = $ParameterFamily
        System = $System
        Kind = $Kind
        Status = $Status
        Dependencies = $Dependencies
        Indicator = $Indicator
        EntryMethod = $EntryMethod
        Variant = $Variant
        Groups = $Groups
        Sides = $Sides
    })
}

$libraryRootFull = Get-NormalizedFullPath $LibraryRoot
$templateFull = Get-NormalizedFullPath $TemplatePath
$sourceFull = Get-NormalizedFullPath $EaSourcePath
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path (Split-Path -Parent $libraryRootFull) 'White_Rabbit_X_Optimization_Profiles'
}
$outputRootFull = Get-NormalizedFullPath $OutputRoot
if ([string]::IsNullOrWhiteSpace($WfoEndDate)) {
    $WfoEndDate = Get-Date -Format 'yyyy.MM.dd'
}
$parsedDate = [datetime]::MinValue
if (-not [datetime]::TryParseExact($WfoEndDate, 'yyyy.MM.dd', $invariant, [Globalization.DateTimeStyles]::None, [ref]$parsedDate)) {
    throw "WfoEndDate must use yyyy.MM.dd: $WfoEndDate"
}
$script:wfoEndDate = $WfoEndDate

foreach ($required in @($libraryRootFull, $templateFull, $sourceFull)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required path not found: $required"
    }
}
if ($outputRootFull -eq $libraryRootFull) {
    throw 'OutputRoot must be a sibling library, not the 6,029-preset library.'
}
$driveRoot = [IO.Path]::GetPathRoot($outputRootFull).TrimEnd('\', '/')
if ($outputRootFull -eq $driveRoot) {
    throw "Refusing to use a drive root as OutputRoot: $outputRootFull"
}
if ($MaxCartesianPasses -lt 2 -or $MaxOptimizationFlags -lt 1) {
    throw 'Invalid optimization safety limits.'
}

$markerPath = Join-Path $outputRootFull '.white-rabbit-x-optimization-library'
if (Test-Path -LiteralPath $outputRootFull) {
    $existingItems = @(Get-ChildItem -LiteralPath $outputRootFull -Force)
    if ($existingItems.Count -gt 0) {
        if (-not $RebuildExisting) {
            throw "OutputRoot is not empty. Back it up and re-run with -RebuildExisting: $outputRootFull"
        }
        if (-not (Test-Path -LiteralPath $markerPath) -or
            ([IO.File]::ReadAllText($markerPath).Trim() -ne $markerText)) {
            throw "Refusing rebuild because the generated-library marker is missing or invalid: $markerPath"
        }
        foreach ($item in $existingItems) {
            $safeItem = Assert-ChildPath $outputRootFull $item.FullName
            Remove-Item -LiteralPath $safeItem -Recurse -Force
        }
    }
}
New-Item -ItemType Directory -Force -Path $outputRootFull | Out-Null
[IO.File]::WriteAllText($markerPath, $markerText + "`r`n", $utf8Bom)

$templateText = [IO.File]::ReadAllText($templateFull, $setEncoding)
$templateLines = [System.Collections.Generic.List[string]]::new()
foreach ($line in [regex]::Split($templateText, '\r\n|\n|\r')) {
    $templateLines.Add($line)
}
while ($templateLines.Count -gt 0 -and $templateLines[$templateLines.Count - 1] -eq '') {
    $templateLines.RemoveAt($templateLines.Count - 1)
}
$templateValues = [ordered]@{}
$templateOrder = [System.Collections.Generic.List[string]]::new()
foreach ($line in $templateLines) {
    if ($line -match '^([^;=]+)=(.*)$') {
        $name = $matches[1]
        if ($templateValues.Contains($name)) {
            throw "Duplicate input in template: $name"
        }
        $templateValues[$name] = $matches[2]
        $templateOrder.Add($name)
    }
}
$sourceInputNames = [System.Collections.Generic.List[string]]::new()
foreach ($line in [IO.File]::ReadAllLines($sourceFull)) {
    if ($line -match '^\s*input\s+(?!group\b)[A-Za-z_][A-Za-z0-9_]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*=') {
        $sourceInputNames.Add($matches[1])
    }
}
if ($sourceInputNames.Count -ne $templateOrder.Count) {
    throw "Schema mismatch: source has $($sourceInputNames.Count) inputs; template has $($templateOrder.Count)."
}
for ($index = 0; $index -lt $templateOrder.Count; $index++) {
    if ($sourceInputNames[$index] -ne $templateOrder[$index]) {
        throw "Schema/order mismatch at index ${index}: source=$($sourceInputNames[$index]) template=$($templateOrder[$index])"
    }
}
$script:templateValues = $templateValues
$script:templateOrder = $templateOrder
$script:templateLines = $templateLines

$allOptimizationDisabled = @{}
foreach ($name in $templateValues.Keys) {
    $value = [string]$templateValues[$name]
    $parts = Get-TupleParts $value
    if ($null -ne $parts) {
        $parts[4] = 'N'
        $allOptimizationDisabled[[string]$name] = $parts -join '||'
    }
    else {
        $allOptimizationDisabled[[string]$name] = $value
    }
}
$script:allOptimizationDisabled = $allOptimizationDisabled

$groups = @(
    [pscustomobject]@{ Code = '01_Forex'; Label = 'Forex'; TimeFrame = 2; Stop = '2.5'; Take = '3.0'; Trail = '2.5'; Slippage = '5' },
    [pscustomobject]@{ Code = '02_Metals'; Label = 'Metals'; TimeFrame = 2; Stop = '3.0'; Take = '3.5'; Trail = '3.0'; Slippage = '10' },
    [pscustomobject]@{ Code = '03_Cryptocurrencies'; Label = 'Cryptocurrencies'; TimeFrame = 4; Stop = '4.0'; Take = '5.0'; Trail = '4.0'; Slippage = '20' },
    [pscustomobject]@{ Code = '04_Indices_Energies'; Label = 'Indices_Energies'; TimeFrame = 2; Stop = '3.5'; Take = '4.0'; Trail = '3.5'; Slippage = '15' },
    [pscustomobject]@{ Code = '05_US_Stocks_CFD'; Label = 'US_Stocks_CFD'; TimeFrame = 4; Stop = '3.0'; Take = '4.0'; Trail = '3.0'; Slippage = '10' }
)
$script:groupCodes = @($groups.Code)

$indicators = @(
    [pscustomobject]@{ Code = 'I00_MACD'; Value = 0; Fast = 12; Slow = 26; Signal = 9; TuneFast = 12; FastStart = 6; FastStep = 2; FastStop = 16; TuneSlow = 28; SlowStart = 20; SlowStep = 4; SlowStop = 40; TuneSignal = 9; SignalStart = 5; SignalStep = 2; SignalStop = 13; UsesSlow = $true; UsesSignal = $true; UsesPrice = $true },
    [pscustomobject]@{ Code = 'I01_EMA_CROSS'; Value = 1; Fast = 12; Slow = 26; Signal = 9; TuneFast = 12; FastStart = 6; FastStep = 2; FastStop = 16; TuneSlow = 28; SlowStart = 20; SlowStep = 4; SlowStop = 40; TuneSignal = 9; SignalStart = 9; SignalStep = 1; SignalStop = 9; UsesSlow = $true; UsesSignal = $false; UsesPrice = $true },
    [pscustomobject]@{ Code = 'I02_MOMENTUM'; Value = 2; Fast = 14; Slow = 26; Signal = 9; TuneFast = 13; FastStart = 7; FastStep = 3; FastStop = 28; TuneSlow = 26; SlowStart = 26; SlowStep = 1; SlowStop = 26; TuneSignal = 9; SignalStart = 3; SignalStep = 2; SignalStop = 15; UsesSlow = $false; UsesSignal = $true; UsesPrice = $true },
    [pscustomobject]@{ Code = 'I03_STOCHASTIC'; Value = 3; Fast = 14; Slow = 26; Signal = 3; TuneFast = 13; FastStart = 5; FastStep = 2; FastStop = 21; TuneSlow = 26; SlowStart = 26; SlowStep = 1; SlowStop = 26; TuneSignal = 4; SignalStart = 2; SignalStep = 2; SignalStop = 8; UsesSlow = $false; UsesSignal = $true; UsesPrice = $false },
    [pscustomobject]@{ Code = 'I04_TRIX'; Value = 4; Fast = 15; Slow = 26; Signal = 9; TuneFast = 13; FastStart = 5; FastStep = 4; FastStop = 29; TuneSlow = 26; SlowStart = 26; SlowStep = 1; SlowStop = 26; TuneSignal = 9; SignalStart = 3; SignalStep = 2; SignalStop = 15; UsesSlow = $false; UsesSignal = $true; UsesPrice = $true },
    [pscustomobject]@{ Code = 'I05_ICHIMOKU'; Value = 5; Fast = 9; Slow = 26; Signal = 52; TuneFast = 9; FastStart = 5; FastStep = 2; FastStop = 15; TuneSlow = 27; SlowStart = 18; SlowStep = 3; SlowStop = 36; TuneSignal = 48; SignalStart = 40; SignalStep = 8; SignalStop = 80; UsesSlow = $true; UsesSignal = $true; UsesPrice = $false }
)
$script:indicators = $indicators

$definitions = [System.Collections.Generic.List[object]]::new()
$script:definitions = $definitions

foreach ($indicator in $indicators) {
    Add-Definition '01_Entry_Screening' "ES_$($indicator.Code)" '01_ENTRY_SCREEN' 'ENTRY_METHOD_TIMEFRAME' 'ENTRY_SCREEN' 'ENTRY_SCREEN' 'CONTROLLED_OPTIMIZATION' 'Compare one indicator at a time; use the winning method/timeframe as fixed inputs in Stage 02.' $indicator.Code 'M00_TO_M06' $indicator
}
foreach ($indicator in $indicators) {
    Add-Definition '02_Indicator_Tuning' "IT_$($indicator.Code)" '02_INDICATOR_TUNING' 'INDICATOR_PERIODS' 'INDICATOR_TUNING' 'INDICATOR_TUNING' 'CONTROLLED_OPTIMIZATION' 'Requires a winner from Stage 01; copy the winning timeframe and entry method before running.' $indicator.Code 'FIX_FROM_STAGE_01' $indicator
}

Add-Definition '03_Filter_Screening' 'FS01_CORE_STACK' '03_FILTER_SCREEN' 'FILTER_GATES' 'FILTER_SCREEN' 'FILTER_CORE_SCREEN' 'CONTROLLED_OPTIMIZATION' 'Run after entry tuning; retest the selected stack in isolation.'
Add-Definition '03_Filter_Screening' 'FS02_NEWS_GATE' '03_FILTER_SCREEN' 'NEWS_FILTER_GATE' 'FILTER_SCREEN' 'FILTER_NEWS_SCREEN' 'CSV_REQUIRED' 'When the news gate is true, WhiteRabbit_News.csv must exist in Common\\Files for backtests.'
Add-Definition '03_Filter_Screening' 'FS03_MA_MODES' '03_FILTER_SCREEN' 'MA_FILTER_CATEGORICAL' 'FILTER_SCREEN' 'FILTER_MA_SCREEN' 'CONTROLLED_OPTIMIZATION' 'MA parameters stay fixed; tune them only after selecting method/rule/direction.'
Add-Definition '03_Filter_Screening' 'FS04_ADX_MODE' '03_FILTER_SCREEN' 'ADX_FILTER_CATEGORICAL' 'FILTER_SCREEN' 'FILTER_ADX_SCREEN' 'CONTROLLED_OPTIMIZATION' 'ADX period and threshold stay fixed until Stage 04.'
Add-Definition '03_Filter_Screening' 'FS05_VOLATILITY_MODE' '03_FILTER_SCREEN' 'VOLATILITY_FILTER_CATEGORICAL' 'FILTER_SCREEN' 'FILTER_VOL_SCREEN' 'CONTROLLED_OPTIMIZATION' 'Uses the shared ATR source; changing ATR later requires exit/grid retesting.'
Add-Definition '03_Filter_Screening' 'FS06_MTF_ALIGNMENT' '03_FILTER_SCREEN' 'MTF_FILTER_CATEGORICAL' 'FILTER_SCREEN' 'FILTER_MTF_SCREEN' 'CONTROLLED_OPTIMIZATION' 'Higher timeframes are derived from the entry timeframe.'

Add-Definition '04_Filter_Tuning' 'FT01_MA_PARAMETERS' '04_FILTER_TUNING' 'MA_FILTER_PARAMETERS' 'FILTER_TUNING' 'FILTER_MA_TUNING' 'CONTROLLED_OPTIMIZATION' 'Requires the MA categorical winner from Stage 03; copy MA method/rule/direction first.'
Add-Definition '04_Filter_Tuning' 'FT02_ADX_PARAMETERS' '04_FILTER_TUNING' 'ADX_FILTER_PARAMETERS' 'FILTER_TUNING' 'FILTER_ADX_TUNING' 'CONTROLLED_OPTIMIZATION' 'Requires the ADX mode winner from Stage 03.'
Add-Definition '04_Filter_Tuning' 'FT03_NEWS_WINDOW' '04_FILTER_TUNING' 'NEWS_FILTER_PARAMETERS' 'FILTER_TUNING' 'FILTER_NEWS_TUNING' 'CSV_REQUIRED' 'WhiteRabbit_News.csv and relevant manual currencies are required.'
Add-Definition '04_Filter_Tuning' 'FT04_ATR_SOURCE' '04_FILTER_TUNING' 'SHARED_ATR_SOURCE' 'FILTER_TUNING' 'FILTER_ATR_TUNING' 'CONTROLLED_OPTIMIZATION' 'ATR source is shared with SL/TP/Trail/Grid; rerun downstream stages after selecting it.'
Add-Definition '04_Filter_Tuning' 'FT05_MTF_BASE' '04_FILTER_TUNING' 'MTF_BASE_ALIGNMENT' 'FILTER_TUNING' 'FILTER_MTF_TUNING' 'CONTROLLED_OPTIMIZATION' 'Do not combine with entry-period tuning in the same run.'

Add-Definition '05_Exit_Screening' 'XS01_PRIMARY_GATES' '05_EXIT_SCREEN' 'EXIT_GATES' 'EXIT_SCREEN' 'EXIT_GATE_SCREEN' 'CONTROLLED_OPTIMIZATION' 'Stop remains enabled as the safety anchor; screen Take, Breakeven and Trail gates.'
Add-Definition '05_Exit_Screening' 'XS02_ORGANIC_TAKE' '05_EXIT_SCREEN' 'TAKE_MODE' 'EXIT_SCREEN' 'EXIT_ORGANIC_SCREEN' 'CONTROLLED_OPTIMIZATION' 'Take remains enabled; this compares fixed ATR TP with organic ATR TP.'
Add-Definition '05_Exit_Screening' 'XS03_REVERSAL_MODE' '05_EXIT_SCREEN' 'REVERSAL_EXIT_MODE' 'EXIT_SCREEN' 'EXIT_REVERSAL_SCREEN' 'HEDGE_ACCOUNT_REQUIRED' 'Opposite-order mode requires bilateral exposure and a real MT5 hedging account.' 'I00_MACD' 'M01_SIGNAL_CROSS' $null @() @('BOTH_HEDGE')

Add-Definition '06_Exit_Tuning' 'XT01_SLTP_ATR' '06_EXIT_TUNING' 'SLTP_ATR_MULTIPLIERS' 'EXIT_TUNING' 'EXIT_SLTP_TUNING' 'CONTROLLED_OPTIMIZATION' 'Requires selected entry/filter stack; Stop and Take are tuned together only.'
Add-Definition '06_Exit_Tuning' 'XT02_CANDLE_OFFSETS' '06_EXIT_TUNING' 'SLTP_CANDLE_OFFSETS' 'EXIT_TUNING' 'EXIT_CANDLE_TUNING' 'CONTROLLED_OPTIMIZATION' 'Run after ATR source selection.'
Add-Definition '06_Exit_Tuning' 'XT03_BREAKEVEN' '06_EXIT_TUNING' 'BREAKEVEN_DISTANCE' 'EXIT_TUNING' 'EXIT_BE_TUNING' 'CONTROLLED_OPTIMIZATION' 'Breakeven distance is a multiple of the initial SL distance.'
Add-Definition '06_Exit_Tuning' 'XT04_TRAIL_ATR' '06_EXIT_TUNING' 'TRAIL_ATR_GEOMETRY' 'EXIT_TUNING' 'EXIT_TRAIL_TUNING' 'CONTROLLED_OPTIMIZATION' 'Run after ATR source selection.'
Add-Definition '06_Exit_Tuning' 'XT05_ORGANIC_TAKE' '06_EXIT_TUNING' 'ORGANIC_TAKE_GEOMETRY' 'EXIT_TUNING' 'EXIT_ORGANIC_TUNING' 'CONTROLLED_OPTIMIZATION' 'Organic take uses last-trade anchor plus ATR multiple.'
Add-Definition '06_Exit_Tuning' 'XT06_REVERSAL_FILTERS' '06_EXIT_TUNING' 'REVERSAL_EXIT_FILTER_POLICY' 'EXIT_TUNING' 'EXIT_REVERSAL_FILTER_TUNING' 'CONTROLLED_OPTIMIZATION' 'Indicator-signal exit stays active; compare raw signal versus entry-filtered signal.'

Add-Definition '07_Position_Sizing_Risk' 'RK01_PERCENT' '07_RISK_TUNING' 'PERCENT_RISK_SIZE' 'POSITION_SIZING' 'RISK_PERCENT' 'CONTROLLED_OPTIMIZATION' 'Stop Loss is mandatory; validate risk on the actual symbol and deposit currency.'
Add-Definition '07_Position_Sizing_Risk' 'RK02_MONETARY' '07_RISK_TUNING' 'MONETARY_POSITION_SIZE' 'POSITION_SIZING' 'RISK_MONETARY' 'BROKER_CALIBRATION_REQUIRED' 'Currency-per-lot scale is account and symbol dependent.'
Add-Definition '07_Position_Sizing_Risk' 'RK03_FIXED_LOT' '07_RISK_TUNING' 'FIXED_LOT_SIZE' 'POSITION_SIZING' 'RISK_FIXED_LOT' 'BROKER_VOLUME_REVIEW' 'Volume min/step/max must be checked on the actual broker symbol.'
Add-Definition '07_Position_Sizing_Risk' 'RK04_FIXED_R' '07_RISK_TUNING' 'FIXED_R_SIZE_CAP' 'POSITION_SIZING' 'RISK_FIXED_R' 'CONTROLLED_OPTIMIZATION' 'Stop Loss is mandatory; Grid and D-Alembert remain disabled.'
Add-Definition '07_Position_Sizing_Risk' 'RK05_PROTECTIONS' '07_RISK_TUNING' 'LOSS_DD_MARGIN_GUARDS' 'RISK_PROTECTION' 'RISK_PROTECTION' 'CONTROLLED_OPTIMIZATION' 'Optimize only after the trading logic is stable; reject low-trade-count winners.'
Add-Definition '07_Position_Sizing_Risk' 'RK06_CAPITAL_ALLOCATION' '07_RISK_TUNING' 'CAPITAL_ALLOCATION' 'RISK_PROTECTION' 'RISK_ALLOCATION' 'CONTROLLED_OPTIMIZATION' 'Use one MagicNumber allocation plan per portfolio.'

Add-Definition '08_Recovery' 'RC01_MARTINGALE_FIXEDLOT' '08_RECOVERY_TUNING' 'MARTINGALE_CYCLE' 'MARTINGALE' 'RECOVERY_MARTINGALE' 'HIGH_RISK_OPTIMIZATION' 'One position per side only; MaxMartingaleLot stays 0 and must be calibrated per broker before any forward demo.'
Add-Definition '08_Recovery' 'RC02_DALEMBERT_FIXEDLOT' '08_RECOVERY_TUNING' 'DALEMBERT_CYCLE' 'DALEMBERT' 'RECOVERY_DALEMBERT' 'HIGH_RISK_OPTIMIZATION' 'Fixed Lot only, Grid disabled, one position per side; calibrate a broker-valid hard lot cap afterward.'

Add-Definition '09_Grid' 'GR01_SEPARATE' '09_GRID_TUNING' 'GRID_SEPARATE_GEOMETRY' 'GRID_SEPARATE' 'GRID_TUNING' 'HIGH_RISK_HEDGE_REQUIRED' 'Real MT5 hedging account required; use one direction per profile and validate basket stress/fees.' 'I00_MACD' 'M00_REVERSAL' ([pscustomobject]@{ GridMode = 1 })
Add-Definition '09_Grid' 'GR02_UNIFIED' '09_GRID_TUNING' 'GRID_UNIFIED_GEOMETRY' 'GRID_UNIFIED' 'GRID_TUNING' 'HIGH_RISK_HEDGE_REQUIRED' 'Real MT5 hedging account required; unified basket TP and partial fills require stress tests.' 'I00_MACD' 'M00_REVERSAL' ([pscustomobject]@{ GridMode = 2 })

Add-Definition '10_Schedule' 'SC01_START_HOUR' '10_SCHEDULE_TUNING' 'SESSION_START' 'TRADING_SESSION' 'SCHEDULE_START' 'BROKER_TIME_REVIEW' 'Hours use broker server time; tune the end boundary in a separate run.'
Add-Definition '10_Schedule' 'SC02_END_HOUR' '10_SCHEDULE_TUNING' 'SESSION_END' 'TRADING_SESSION' 'SCHEDULE_END' 'BROKER_TIME_REVIEW' 'Hours use broker server time; apply the winning start hour before this stage.'
Add-Definition '10_Schedule' 'SC03_WEEKDAYS' '10_SCHEDULE_TUNING' 'TRADING_WEEKDAYS' 'TRADING_DAYS' 'SCHEDULE_WEEKDAYS' 'CONTROLLED_OPTIMIZATION' 'Discard the all-disabled or statistically sparse combinations.'
Add-Definition '10_Schedule' 'SC04_CRYPTO_WEEKEND' '10_SCHEDULE_TUNING' 'CRYPTO_WEEKEND_DAYS' 'TRADING_DAYS' 'SCHEDULE_WEEKEND' 'CONTROLLED_OPTIMIZATION' 'Crypto only; verify the broker actually offers weekend quotes.' 'I00_MACD' 'M01_SIGNAL_CROSS' $null @('03_Cryptocurrencies')

foreach ($window in @(
    [pscustomobject]@{ Code = 'WF01_YEAR_HALF'; Window = 360; Step = 180 },
    [pscustomobject]@{ Code = 'WF02_HALF_QUARTER'; Window = 180; Step = 90 },
    [pscustomobject]@{ Code = 'WF03_QUARTER_MONTH'; Window = 90; Step = 30 },
    [pscustomobject]@{ Code = 'WF04_MONTH_WEEK'; Window = 30; Step = 7 }
)) {
    Add-Definition '11_WFO' $window.Code '11_WFO_VALIDATION' 'WFO_WINDOW_FORMULA' 'WFO' 'WFO_FIXED' 'WFO_DATE_REVIEW' 'Set input_end_date equal to the tester end date and provide enough history for IS plus OOS.' 'I00_MACD' 'M01_SIGNAL_CROSS' $window
}
Add-Definition '11_WFO' 'WF05_CUSTOM' '11_WFO_VALIDATION' 'WFO_CUSTOM_WINDOW_FORMULA' 'WFO' 'WFO_CUSTOM' 'WFO_DATE_REVIEW' 'Custom step is a positive percentage of the custom IS window; align input_end_date with tester end date.'

$originalManifestPath = Join-Path $libraryRootFull 'MANIFESTO_SETS.csv'
if (-not (Test-Path -LiteralPath $originalManifestPath)) {
    throw "Original preset manifest not found: $originalManifestPath"
}
$originalManifest = @(Import-Csv -LiteralPath $originalManifestPath -Delimiter ';')
if ($originalManifest.Count -ne 6029) {
    throw "Expected 6,029 original manifest rows, found $($originalManifest.Count)."
}
$originalMagics = [Collections.Generic.HashSet[int]]::new()
foreach ($row in $originalManifest) {
    if (-not $originalMagics.Add([int]$row.MagicNumber)) {
        throw "Duplicate MagicNumber in original manifest: $($row.MagicNumber)"
    }
}

$manifest = [System.Collections.Generic.List[object]]::new()
$magicCounter = 0
foreach ($definition in $definitions) {
    foreach ($groupCode in $definition.Groups) {
        $group = $groups | Where-Object Code -eq $groupCode | Select-Object -First 1
        if ($null -eq $group) {
            throw "Definition references unknown group: $groupCode"
        }
        foreach ($side in $definition.Sides) {
            $magicCounter++
            $magic = $MagicBase + $magicCounter
            if ($originalMagics.Contains($magic)) {
                throw "Generated MagicNumber collides with original library: $magic"
            }
            $strategyName = "WRX OPT $($definition.Code) $groupCode $side"
            $map = New-BaseMap $group $side $magic $strategyName
            Configure-Profile $map $definition $group $side
            Set-ProfileValue $map 'NomedaEstrategia' $strategyName
            Set-FixedTuple $map 'MagicNumber' ([string]$magic)

            $enabled = @(Get-EnabledOptimization $map)
            if ($enabled.Count -lt 1 -or $enabled.Count -gt $MaxOptimizationFlags) {
                throw "$strategyName has $($enabled.Count) enabled flags; allowed range is 1..$MaxOptimizationFlags."
            }
            $passes = 1L
            foreach ($item in $enabled) {
                if ($passes -gt [long]::MaxValue / $item.Candidates) {
                    throw "Cartesian pass overflow in $strategyName"
                }
                $passes *= $item.Candidates
            }
            if ($passes -gt $MaxCartesianPasses) {
                throw "$strategyName has $passes Cartesian passes; limit is $MaxCartesianPasses."
            }
            $algorithm = if ($passes -le 500) { 'COMPLETE_SEARCH' } else { 'FAST_GENETIC' }
            $relative = Join-Path $definition.Folder (Join-Path $groupCode "$($definition.Code)_$side.set")
            $relativeSlash = $relative.Replace('\', '/')
            $metadata = [pscustomobject]@{
                OptimizationStage = $definition.OptimizationStage
                ParameterFamily = $definition.ParameterFamily
                EnabledOptimizationParameters = ($enabled.Name -join ',')
                CartesianPasses = $passes
                RecommendedAlgorithm = $algorithm
                Status = $definition.Status
                Dependencies = $definition.Dependencies
            }
            $content = New-SetContent $map $metadata
            $target = Assert-ChildPath $outputRootFull (Join-Path $outputRootFull $relative)
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
            [IO.File]::WriteAllText($target, $content, $setEncoding)

            $manifest.Add([pscustomobject]@{
                SetRole = 'OPTIMIZATION_PROFILE'
                OptimizationStage = $definition.OptimizationStage
                ParameterFamily = $definition.ParameterFamily
                System = $definition.System
                Group = $groupCode
                Asset = 'GROUP_TEMPLATE'
                Side = $side
                Indicator = $definition.Indicator
                EntryMethod = $definition.EntryMethod
                EnabledOptimizationParameters = ($enabled.Name -join ',')
                OptimizationFlagCount = $enabled.Count
                CartesianPasses = $passes
                RecommendedAlgorithm = $algorithm
                MagicNumber = $magic
                Status = $definition.Status
                Dependencies = $definition.Dependencies
                RelativePath = $relativeSlash
                SHA256 = ''
            })
        }
    }
}

if ($manifest.Count -ne $magicCounter) {
    throw 'Internal manifest count mismatch.'
}
foreach ($row in $manifest) {
    $absolute = Join-Path $outputRootFull $row.RelativePath.Replace('/', '\')
    $row.SHA256 = (Get-FileHash -LiteralPath $absolute -Algorithm SHA256).Hash
}
$manifestPath = Join-Path $outputRootFull 'MANIFESTO_OTIMIZACAO.csv'
$manifest | Export-Csv -LiteralPath $manifestPath -Delimiter ';' -NoTypeInformation -Encoding utf8BOM

$originalAudit = Get-OriginalLibraryAudit $libraryRootFull
$stageSummary = @($manifest | Group-Object OptimizationStage | Sort-Object Name | ForEach-Object {
    [pscustomobject]@{
        Stage = $_.Name
        Profiles = $_.Count
        MaxPasses = ($_.Group.CartesianPasses | Measure-Object -Maximum).Maximum
        MaxFlags = ($_.Group.OptimizationFlagCount | Measure-Object -Maximum).Maximum
    }
})
$statusSummary = @($manifest | Group-Object Status | Sort-Object Name | ForEach-Object {
    [pscustomobject]@{ Status = $_.Name; Profiles = $_.Count }
})
$newMagicUnique = @($manifest.MagicNumber | Sort-Object -Unique).Count
$maxNewPasses = ($manifest.CartesianPasses | Measure-Object -Maximum).Maximum
$maxNewFlags = ($manifest.OptimizationFlagCount | Measure-Object -Maximum).Maximum
$manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash

$readmeLines = [System.Collections.Generic.List[string]]::new()
$readmeLines.Add('# White Rabbit X - Optimization Profiles')
$readmeLines.Add('')
$readmeLines.Add('Esta biblioteca e separada dos 6.029 presets operacionais/pesquisa. Aqui, cada .set e um experimento pequeno e declarado; na biblioteca Asset Library, os arquivos existentes permanecem intactos.')
$readmeLines.Add('')
$readmeLines.Add('Regras de projeto:')
$readmeLines.Add('')
$readmeLines.Add('- SetRole sempre e `OPTIMIZATION_PROFILE`.')
$readmeLines.Add("- Entre 1 e $MaxOptimizationFlags flags Y por arquivo.")
$readmeLines.Add("- No maximo $MaxCartesianPasses passes cartesianos por arquivo.")
$readmeLines.Add('- Parametros categoricos, periodos, filtros, saidas e risco sao separados em estagios.')
$readmeLines.Add('- Dashboard, labels e tema do grafico ficam desligados para reduzir custo de otimizacao.')
$readmeLines.Add('- MagicNumbers sao exclusivos e nao colidem com a Asset Library.')
$readmeLines.Add('- Nenhum perfil deve ser usado diretamente em conta real.')
$readmeLines.Add('')
$readmeLines.Add('## Ordem recomendada')
$readmeLines.Add('')
$readmeLines.Add('1. Entry Screening')
$readmeLines.Add('2. Indicator Tuning')
$readmeLines.Add('3. Filter Screening')
$readmeLines.Add('4. Filter Tuning')
$readmeLines.Add('5. Exit Screening')
$readmeLines.Add('6. Exit Tuning')
$readmeLines.Add('7. Position Sizing and Risk')
$readmeLines.Add('8. Recovery (alto risco, opcional)')
$readmeLines.Add('9. Grid (alto risco, conta hedging)')
$readmeLines.Add('10. Schedule')
$readmeLines.Add('11. WFO e validacao final')
$readmeLines.Add('')
$readmeLines.Add('Copie o vencedor de cada estagio para o proximo arquivo antes de carregar o proximo .set. Nao ligue de novo todos os eixos Y ao mesmo tempo.')
$readmeLines.Add('')
$readmeLines.Add('## Inventario')
$readmeLines.Add('')
$readmeLines.Add('| Estagio | Perfis | Max passes | Max flags Y |')
$readmeLines.Add('|---|---:|---:|---:|')
foreach ($row in $stageSummary) {
    $readmeLines.Add("| $($row.Stage) | $($row.Profiles) | $($row.MaxPasses) | $($row.MaxFlags) |")
}
$readmeLines.Add('')
$readmeLines.Add("Total: **$($manifest.Count) perfis**. Manifesto: ``MANIFESTO_OTIMIZACAO.csv``.")
$readmeLines.Add('')
$readmeLines.Add('## Ferramentas')
$readmeLines.Add('')
$readmeLines.Add('- Gerador: `White_Rabbit_X_Asset_Library_Sets\\tools\\Generate_White_Rabbit_X_Optimization_Profiles.ps1`')
$readmeLines.Add('- Validador: `White_Rabbit_X_Asset_Library_Sets\\tools\\Validate_White_Rabbit_X_Optimization_Profiles.ps1`')
$readmeLines.Add('')
$readmeLines.Add('Leia `TUTORIAL_OTIMIZACAO.md` antes do primeiro teste.')
Write-Utf8BomFile (Join-Path $outputRootFull 'README.md') (($readmeLines -join "`r`n") + "`r`n")

$tutorial = @'
# Tutorial de otimizacao - White Rabbit X

## 1. Antes de abrir o Strategy Tester

1. Escolha um unico simbolo real do broker e confirme sufixo, digitos, volume minimo/passo e custos.
2. Para Grid ou `BOTH_HEDGE`, use uma conta MT5 realmente hedging. Netting nao representa pernas independentes.
3. Para filtro de noticias em backtest, gere/copiei `WhiteRabbit_News.csv` para `Terminal\Common\Files`.
4. Use dados, spread, comissao e slippage realistas. Um resultado sem custos nao e um vencedor.

## 2. Carregar um perfil

1. Abra o Strategy Tester e selecione `White Rabbit X (Global Multi-Indicator).ex5`.
2. Selecione simbolo, periodo historico e modelagem.
3. Em Inputs, clique Load e abra apenas um arquivo desta biblioteca.
4. Confirme no cabecalho do arquivo/manifesto: `SetRole=OPTIMIZATION_PROFILE`, estagio, dependencias, flags Y e passes.
5. Use `Complete search` quando o manifesto recomendar `COMPLETE_SEARCH`; use `Fast genetic based algorithm` quando recomendar `FAST_GENETIC`.
6. Nunca marque parametros extras como Y durante o mesmo estagio.

## 3. Fluxo em estagios

1. Triagem: escolha indicador/metodo/timeframe.
2. Periodos: fixe o vencedor e ajuste somente os periodos do indicador.
3. Filtros: primeiro ligue/desligue e escolha modos; depois ajuste parametros do filtro vencedor.
4. Saidas: primeiro escolha gates; depois ajuste SL/TP/BE/Trail em arquivos separados.
5. Risco: calibre sizing e protecoes somente depois da logica de entrada/saida.
6. Martingale, D'Alembert e Grid sao ramos alternativos de alto risco, nao complementos automaticos.
7. Sessao/dias usam horario do servidor do broker.
8. WFO: ajuste `input_end_date` para o mesmo fim do teste e mantenha OOS nunca visto.

## 4. Escolha do vencedor

Nao escolha apenas o maior lucro. Exija numero minimo de trades, estabilidade entre vizinhos, drawdown aceitavel, custos adversos, OOS, Monte Carlo de custos e forward-demo.

## 5. Promover para preset

1. Copie os valores vencedores para um arquivo novo.
2. Mude todas as flags `Y` para `N`.
3. Use outro MagicNumber exclusivo do portfolio.
4. Nomeie simbolo, broker, timeframe, intervalo de dados e data da validacao.
5. Salve fora desta biblioteca como preset candidato; somente depois de OOS/forward-demo ele pode virar preset operacional.

## Alertas por sistema

- Martingale: uma posicao por lado; o dashboard mostra o ciclo de perdas corrente, mas isso nao substitui limite de passos/lote.
- D'Alembert: apenas Fixed Lot, Grid desligado e passo de lote positivo.
- Grid Separate/Unified: Take habilitado, distancia ATR positiva, Recovery desligado, pelo menos duas posicoes no lado ativo e conta hedging.
- Percentage e Fixed-R: Stop Loss obrigatorio.
- `MaxMartingaleLot=0` significa sem teto interno alem do broker. Os perfis de recovery deixam esse campo fixo para evitar ranges invalidos entre brokers; defina um teto valido antes de forward-demo.
'@
Write-Utf8BomFile (Join-Path $outputRootFull 'TUTORIAL_OTIMIZACAO.md') (($tutorial.TrimEnd() -replace "`n", "`r`n") + "`r`n")

$auditLines = [System.Collections.Generic.List[string]]::new()
$auditLines.Add('# Auditoria - arquitetura de presets versus otimizacao')
$auditLines.Add('')
$auditLines.Add("Gerado em: $generatedAt")
$auditLines.Add('')
$auditLines.Add('## Biblioteca original preservada')
$auditLines.Add('')
$auditLines.Add("- Sets: $($originalAudit.SetCount)")
$auditLines.Add("- Sem flags Y: $($originalAudit.ZeroFlagSets)")
$auditLines.Add("- Com flags Y: $($originalAudit.FlaggedSets)")
$auditLines.Add("- Total de flags Y: $($originalAudit.TotalFlags)")
$auditLines.Add("- Maior produto cartesiano observado: $($originalAudit.MaximumPasses) em '$($originalAudit.MaximumPassesFile)'")
$auditLines.Add("- SHA-256 do indice 'relative-path|file-sha256': $($originalAudit.PathHashInventorySHA256)")
$auditLines.Add('')
$auditLines.Add('As tuplas Y antigas sao numericamente formadas, mas varios presets ligam eixos independentes ao mesmo tempo. Isso mistura papel de preset com papel de experimento e gera ate dezenas de milhares de combinacoes por arquivo.')
$auditLines.Add('')
$auditLines.Add('## Nova biblioteca')
$auditLines.Add('')
$auditLines.Add("- Perfis: $($manifest.Count)")
$auditLines.Add("- MagicNumbers unicos: $newMagicUnique")
$auditLines.Add("- Faixa de MagicNumbers: $($manifest[0].MagicNumber) a $($manifest[$manifest.Count - 1].MagicNumber)")
$auditLines.Add("- Maximo de flags Y: $maxNewFlags")
$auditLines.Add("- Maximo de passes cartesianos: $maxNewPasses")
$auditLines.Add("- Limites contratuais: flags <= $MaxOptimizationFlags; passes <= $MaxCartesianPasses")
$auditLines.Add("- Inputs por arquivo e por EA: $($templateOrder.Count)")
$auditLines.Add("- SHA-256 do manifesto: $manifestHash")
$auditLines.Add('')
$auditLines.Add('## Status')
$auditLines.Add('')
$auditLines.Add('| Status | Perfis |')
$auditLines.Add('|---|---:|')
foreach ($row in $statusSummary) {
    $auditLines.Add("| $($row.Status) | $($row.Profiles) |")
}
$auditLines.Add('')
$auditLines.Add('## Decisoes de seguranca')
$auditLines.Add('')
$auditLines.Add('- A Asset Library nao e reescrita pelo gerador novo.')
$auditLines.Add('- WFO enums nao sao otimizados como faixas numericas continuas; somente pares validos viram perfis fixos.')
$auditLines.Add('- Indicadores com ordem entre periodos usam ranges que garantem Fast < Slow e, no Ichimoku, Slow < Senkou B em todas as combinacoes.')
$auditLines.Add('- Modos de sizing com unidades diferentes ficam em arquivos separados.')
$auditLines.Add('- Martingale e D-Alembert ficam separados do Grid.')
$auditLines.Add('- Opposite-order reversal recebe perfil bilateral hedging separado.')
$auditLines.Add('- Dashboard/labels/tema ficam desligados na otimizacao.')
Write-Utf8BomFile (Join-Path $outputRootFull 'AUDITORIA_OTIMIZACAO.md') (($auditLines -join "`r`n") + "`r`n")

$summary = [ordered]@{
    generatedAt = $generatedAt
    outputRoot = $outputRootFull
    setRole = 'OPTIMIZATION_PROFILE'
    profiles = $manifest.Count
    inputSchemaCount = $templateOrder.Count
    uniqueMagicNumbers = $newMagicUnique
    firstMagicNumber = $manifest[0].MagicNumber
    lastMagicNumber = $manifest[$manifest.Count - 1].MagicNumber
    maximumOptimizationFlags = $maxNewFlags
    maximumCartesianPasses = $maxNewPasses
    manifestSHA256 = $manifestHash
    originalLibrary = $originalAudit
    stageSummary = $stageSummary
    statusSummary = $statusSummary
}
Write-Utf8BomFile (Join-Path $outputRootFull 'AUDIT_SUMMARY.json') (($summary | ConvertTo-Json -Depth 8) + "`r`n")

[pscustomobject]@{
    OutputRoot = $outputRootFull
    Profiles = $manifest.Count
    SchemaInputs = $templateOrder.Count
    FirstMagic = $manifest[0].MagicNumber
    LastMagic = $manifest[$manifest.Count - 1].MagicNumber
    MaxFlags = $maxNewFlags
    MaxCartesianPasses = $maxNewPasses
    ManifestSHA256 = $manifestHash
    OriginalSetsPreserved = $originalAudit.SetCount
    OriginalInventorySHA256 = $originalAudit.PathHashInventorySHA256
}
