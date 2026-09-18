<#
.SYNOPSIS
Nis JavaSmell-in: dosja zgjidhet me dialog, dhe shfletuesi hapet vetë.

.DESCRIPTION
Deri tani nisja kërkonte dy dritare terminali, një ndryshore mjedisi dhe një
shteg të shkruar me dorë. Kush nuk e ka ndërtuar sistemin nuk ka arsye t'i dijë
ato, dhe gabimi më i shpeshtë gjatë demonstrimit vinte pikërisht prej tyre
(VD-126). Ky skript i bën të tria hapat vetë:

  1. hap dialogun e Windows-it për të zgjedhur dosjen ku rrinë projektet Java;
  2. nis një proces të vetëm që shërben ndërfaqen dhe API-në, me atë dosje si
     rrënjë të lejuar (VD-127);
  3. pret derisa ai përgjigjet, dhe hap shfletuesin.

Ndërfaqja ndërtohet vetëm kur mungon ose kur kodi i saj është më i ri se
ndërtimi; pas kësaj, nisja nuk kërkon Node.

Dosja e zgjedhur mbahet mend, ndaj herën e dytë dialogu e ofron atë të parën.
Asnjë ndryshim nuk bëhet te kodi i projektit që analizohet: shkrimi i një
rishkrimi kërkon veprim të veçantë brenda ndërfaqes.

.PARAMETER Root
Dosja e lejuar, kur dikush e di paraprakisht dhe nuk do dialogun.

.PARAMETER Repo
Rrënja e depos së JavaSmell-it. Parazgjedhja është dosja mbi këtë skript, që
skedari të punojë edhe i kopjuar te Desktopi, po të jepet ky parametër.

.PARAMETER NoBrowser
I nis shërbimet pa hapur shfletuesin. Ekziston për provën e vetë nisësit: një
provë që hap një dritare shfletuesi te makina e dikujt nuk është provë e mirë.
#>
param(
    [string]$Root = '',
    [string]$Repo = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'

# Ku mbahet dosja e zgjedhur herën e fundit. Te `LOCALAPPDATA` e jo te depoja,
# sepse është zgjedhje e kësaj makine dhe nuk i përket kodit.
$stateDir = Join-Path $env:LOCALAPPDATA 'JavaSmell'
$stateFile = Join-Path $stateDir 'rrenja.txt'

$python = Join-Path $Repo '.venv\Scripts\python.exe'
$backend = Join-Path $Repo 'backend'
$frontend = Join-Path $Repo 'frontend'

function Fail([string]$message) {
    Write-Host ''
    Write-Host "  $message" -ForegroundColor Red
    Write-Host ''
    Read-Host '  Shtyp Enter për t''u mbyllur'
    exit 1
}

function Ask-ForFolder([string]$current) {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = 'Zgjidh dosjen ku rrinë projektet Java. Analiza lexon vetëm brenda saj.'
    $dialog.ShowNewFolderButton = $false
    if ($current -and (Test-Path -LiteralPath $current)) {
        $dialog.SelectedPath = $current
    } else {
        $dialog.SelectedPath = [Environment]::GetFolderPath('Desktop')
    }
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        return $dialog.SelectedPath
    }
    return ''
}

function Wait-For([string]$url, [int]$seconds, [string]$what) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $url -TimeoutSec 3 -UseBasicParsing | Out-Null
            return $true
        } catch {
            Start-Sleep -Milliseconds 700
        }
    }
    Write-Host "  $what nuk u përgjigj brenda $seconds sekondash." -ForegroundColor Yellow
    return $false
}

function Port-Busy([int]$port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $connect = $client.BeginConnect('127.0.0.1', $port, $null, $null)
        if (-not $connect.AsyncWaitHandle.WaitOne(400)) { return $false }
        $client.EndConnect($connect)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

Write-Host ''
Write-Host '  JavaSmell' -ForegroundColor Cyan
Write-Host '  Detektimi i code smells dhe rekomandimet për refaktorim'
Write-Host ''

if (-not (Test-Path -LiteralPath $python)) {
    Fail "Mjedisi Python nuk u gjend te $python. Krijoje me: python -m venv .venv"
}
$dist = Join-Path $frontend 'dist\index.html'
$hasNode = Test-Path -LiteralPath (Join-Path $frontend 'node_modules')

# A duhet ndërtuar ndërfaqja: kur mungon, ose kur ndonjë skedar i saj — apo
# rezultatet që ajo i fut brenda ndërtimit — është më i ri se ndërtimi.
function Interface-Is-Stale {
    if (-not (Test-Path -LiteralPath $dist)) { return $true }
    $built = (Get-Item -LiteralPath $dist).LastWriteTime
    $sources = @(Get-ChildItem -LiteralPath (Join-Path $frontend 'src') -Recurse -File)
    $sources += @(Get-ChildItem -LiteralPath (Join-Path $Repo 'data\results') -Filter '*.json' -File)
    foreach ($name in 'index.html', 'package.json', 'vite.config.ts') {
        $sources += Get-Item -LiteralPath (Join-Path $frontend $name)
    }
    return [bool]($sources | Where-Object { $_.LastWriteTime -gt $built } | Select-Object -First 1)
}

if (Interface-Is-Stale) {
    if (-not $hasNode) {
        if (-not (Test-Path -LiteralPath $dist)) {
            Fail "Ndërfaqja nuk është ndërtuar dhe varësitë e saj mungojnë. Ekzekuto një herë: npm install --prefix `"$frontend`""
        }
        Write-Host '  Ndërfaqja është më e vjetër se kodi i saj, por Node mungon; hapet ndërtimi ekzistues.' -ForegroundColor Yellow
    } else {
        Write-Host '  Duke ndërtuar ndërfaqen (vetëm kur ajo ka ndryshuar)…'
        Push-Location $frontend
        try {
            & npm run build | Out-Null
            if ($LASTEXITCODE -ne 0) { Fail 'Ndërtimi i ndërfaqes dështoi. Ekzekuto «npm run build» te frontend/ për ta parë gabimin.' }
        } finally {
            Pop-Location
        }
    }
}

# Portat kontrollohen para dialogut, që dosja të mos zgjidhet për një server që
# nuk do të nisej. Një server i vjetër te porti 8000 mban rrënjën e vet, dhe
# ndërfaqja do të analizonte atë dosje e jo atë që zgjodhi përdoruesi — gabimi
# është i heshtur, ndaj nisja ndalet me mesazh (VD-126).
if (Port-Busy 8000) {
    Fail 'Porti 8000 është i zënë: JavaSmell-i ndoshta është ndezur në një dritare tjetër. Mbylle atë dritare dhe provo sërish.'
}

if (-not $Root) {
    $remembered = ''
    if (Test-Path -LiteralPath $stateFile) {
        $remembered = (Get-Content -LiteralPath $stateFile -Raw).Trim()
    }
    $Root = Ask-ForFolder $remembered
}
if (-not $Root) {
    Write-Host '  Asnjë dosje nuk u zgjodh; nisja u ndal.' -ForegroundColor Yellow
    exit 0
}
if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
    Fail "Dosja `"$Root`" nuk ekziston."
}

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
Set-Content -LiteralPath $stateFile -Value $Root -Encoding utf8

Write-Host "  Dosja e lejuar: $Root"
Write-Host '  Duke nisur JavaSmell-in…'

# Një proces i vetëm, në dritaren e vet që dalja të shihet po të duhet. Lidhet
# vetëm te 127.0.0.1, dhe `JAVASMELL_ROOT` caktohet vetëm për të.
$server = Start-Process -FilePath 'cmd.exe' -WorkingDirectory $backend -PassThru -ArgumentList @(
    '/c', "title JavaSmell && set JAVASMELL_ROOT=$Root&& `"$python`" -m uvicorn javasmell.api.bundle:create_bundle --factory --host 127.0.0.1 --port 8000"
)

$ready = Wait-For 'http://127.0.0.1:8000/api/health' 60 'JavaSmell-i'

if ($ready) {
    if (-not $NoBrowser) { Start-Process 'http://localhost:8000' }
    Write-Host '  Gati. Ndërfaqja u hap te http://localhost:8000' -ForegroundColor Green
    Write-Host '  Te ndërfaqja shtyp «Zgjidh një projekt Java», ose importo një depo nga GitHub.'
} else {
    Write-Host '  Shiko dritaren «JavaSmell» për mesazhin e gabimit.' -ForegroundColor Yellow
}

Write-Host ''
Write-Host '  Mbyllja e kësaj dritareje e ndal edhe JavaSmell-in.'
if ([Environment]::UserInteractive -and -not $env:JAVASMELL_NO_WAIT) {
    # Pa konsolë interaktive — p.sh. kur nisësi provohet nga një skript —
    # `Read-Host` dështon me gabim në vend që të presë, ndaj pyetja bëhet vetëm
    # atje ku ka kush t'i përgjigjet.
    try { Read-Host '  Shtyp Enter për të ndalur JavaSmell-in' | Out-Null } catch { }
}

foreach ($process in @($server)) {
    if ($process -and -not $process.HasExited) {
        # `taskkill /T` merr edhe fëmijët: `cmd` nis uvicorn-in, dhe vrasja e
        # vetëm prindit do ta linte portin të zënë.
        Start-Process -FilePath 'taskkill.exe' -ArgumentList @('/PID', $process.Id, '/T', '/F') -WindowStyle Hidden -Wait
    }
}
Write-Host '  JavaSmell-i u ndal.'
