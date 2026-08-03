# Pull all contacts from a USB-connected Android phone via ADB into data\adb_contacts.tsv
# Prerequisite: USB debugging enabled on the phone, and adb on PATH (or set $ADB below).
param(
    [string]$Adb = "adb",
    [string]$OutDir = "data"
)

$ErrorActionPreference = "Stop"
if (-not (Get-Command $Adb -ErrorAction SilentlyContinue)) {
    Write-Error "adb not found. Install platform-tools and enable USB debugging on your phone."
    exit 1
}

& $Adb devices
$devices = (& $Adb devices | Select-String "\tdevice$").Count
if ($devices -eq 0) {
    Write-Error "No authorized device found. Connect your phone and accept the USB debugging prompt."
    exit 1
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$target = Join-Path $OutDir "adb_contacts.tsv"

$tmp = Join-Path $env:TEMP "wa_contacts_tmp"
if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

Write-Host "Querying Contacts Provider on device..."
# Name + number pairs via the standard content provider.
& $Adb exec-out content query --uri content://com.android.contacts/data/phones --projection display_name:data1 | Out-File -Encoding utf8 (Join-Path $tmp "phones.txt")
& $Adb exec-out content query --uri content://contacts/phones --projection display_name:data1 | Out-File -Encoding utf8 (Join-Path $tmp "phones2.txt")

$rows = @()
foreach ($f in @("phones.txt", "phones2.txt")) {
    $p = Join-Path $tmp $f
    if (-not (Test-Path $p)) { continue }
    foreach ($line in Get-Content -LiteralPath $p) {
        $line = $line -replace "^\s*Row: \d+ " , ""
        if ($line -match 'display_name=(.*),\s*data1=(.*)$' -or
            $line -match 'display_name=(.*?),\s*data1=(.+)$') {
            $name = $Matches[1].Trim()
            $num = $Matches[2].Trim()
            if ($num) { $rows += "$name`t$num" }
        }
    }
}

$unique = @($rows | Sort-Object -Unique)
$unique | Set-Content -Encoding utf8 -LiteralPath $target
Write-Host "Wrote $($unique.Count) contacts -> $target"
Write-Host "Next: python -m mywa -i data"
