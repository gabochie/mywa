# Gate 1 secrets guard (mywa) - read-only, exit 1 on leaks
# Run: powershell -File scripts\check-secrets.ps1
$fail = $false
$tracked = git ls-files 2>$null
if ($tracked -match '(^|/)\.env$') { Write-Output "FAIL: .env tracked"; $fail = $true }
if ($tracked -match 'real_out/|contacts\.csv|msgstore\.db') { Write-Output "FAIL: real contact data tracked"; $fail = $true }
$root = Split-Path -Parent $PSScriptRoot
$compose = Get-Content -Raw (Join-Path $root "docker-compose.yml")
if ($compose -match 'docker\.sock') { Write-Output "WARN: docker.sock mounted - keep local-only, never on shared host" }
if ($fail) { exit 1 }
Write-Output "PASS: mywa secrets guard clean"
