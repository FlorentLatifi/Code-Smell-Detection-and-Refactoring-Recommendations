<#
.SYNOPSIS
Nis JavaSmell-in: dosja zgjidhet me dialog, dhe shfletuesi hapet vetë.

.DESCRIPTION
Deri tani nisja kërkonte dy dritare terminali, një ndryshore mjedisi dhe një
shteg të shkruar me dorë. Kush nuk e ka ndërtuar sistemin nuk ka arsye t'i dijë
ato, dhe gabimi më i shpeshtë gjatë demonstrimit vinte pikërisht prej tyre
(VD-126). Ky skript i bën të tria hapat vetë:

  1. hap dialogun e Windows-it për të zgjedhur dosjen ku rrinë projektet Java;
  2. nis API-në me atë dosje si rrënjë të lejuar, dhe ndërfaqen;
  3. pret derisa shërbimet përgjigjen, dhe hap shfletuesin.

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
if (-not (Test-Path -LiteralPath (Join-Path $frontend 'node_modules'))) {
    Fail "Varësitë e ndërfaqes mungojnë. Ekzekuto një herë: npm install --prefix `"$frontend`""
}

# Portat kontrollohen para dialogut, që dosja të mos zgjidhet për një server që
# nuk do të nisej. Një server i vjetër te porti 8000 mban rrënjën e vet, dhe
# ndërfaqja do të analizonte atë dosje e jo atë që zgjodhi përdoruesi — gabimi
# është i heshtur, ndaj nisja ndalet me mesazh (VD-126).
foreach ($port in @(8000, 5173)) {
    if (Port-Busy $port) {
        Fail "Porti $port është i zënë: JavaSmell-i ndoshta është ndezur në një dritare tjetër. Mbylle atë dritare dhe provo sërish."
    }
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
Write-Host '  Duke nisur shërbimet…'

# Dy dritare të veçanta, që daljen e secilit shërbim ta shohë kush e kërkon.
# `JAVASMELL_ROOT` caktohet vetëm për procesin e API-së.
$api = Start-Process -FilePath 'cmd.exe' -WorkingDirectory $backend -PassThru -ArgumentList @(
    '/c', "title JavaSmell API && set JAVASMELL_ROOT=$Root&& `"$python`" -m uvicorn javasmell.api.app:create_app --factory --port 8000"
)
$ui = Start-Process -FilePath 'cmd.exe' -WorkingDirectory $frontend -PassThru -ArgumentList @(
    '/c', 'title JavaSmell nderfaqja && npm run dev'
)

$apiReady = Wait-For 'http://127.0.0.1:8000/health' 40 'API-ja'
$uiReady = Wait-For 'http://localhost:5173' 90 'Ndërfaqja'

if ($apiReady -and $uiReady) {
    if (-not $NoBrowser) { Start-Process 'http://localhost:5173' }
    Write-Host '  Gati. Ndërfaqja u hap te http://localhost:5173' -ForegroundColor Green
    Write-Host '  Te ndërfaqja shtyp «Zgjidh një projekt Java», ose importo një depo nga GitHub.'
} else {
    Write-Host '  Shiko dy dritaret e shërbimeve për mesazhin e gabimit.' -ForegroundColor Yellow
}

Write-Host ''
Write-Host '  Mbyllja e kësaj dritareje i ndal edhe shërbimet.'
if ([Environment]::UserInteractive -and -not $env:JAVASMELL_NO_WAIT) {
    # Pa konsolë interaktive — p.sh. kur nisësi provohet nga një skript —
    # `Read-Host` dështon me gabim në vend që të presë, ndaj pyetja bëhet vetëm
    # atje ku ka kush t'i përgjigjet.
    try { Read-Host '  Shtyp Enter për të ndalur JavaSmell-in' | Out-Null } catch { }
}

foreach ($process in @($api, $ui)) {
    if ($process -and -not $process.HasExited) {
        # `taskkill /T` merr edhe fëmijët: `cmd` nis uvicorn-in dhe node-in, dhe
        # vrasja e vetëm prindit do t'i lërë portat e zëna.
        Start-Process -FilePath 'taskkill.exe' -ArgumentList @('/PID', $process.Id, '/T', '/F') -WindowStyle Hidden -Wait
    }
}
Write-Host '  Shërbimet u ndalën.'
