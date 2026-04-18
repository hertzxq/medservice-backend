. "$PSScriptRoot\_common.ps1"

$EnvVars = Import-DotEnv
$token = Get-AdminToken -EnvVars $EnvVars
$headers = New-AuthHeaders -Token $token

$s = Invoke-RestMethod -Uri "$($EnvVars.API_BASE)/parsing/status" -Method Get -Headers $headers -TimeoutSec 10

Write-Host "status    : $($s.status)"
Write-Host "lastRunAt : $($s.last_run_at)"
if ($s.progress) { Write-Host "progress  : $($s.progress)" }
if ($s.last_result) {
    Write-Host ''
    Write-Host 'last_result:'
    $s.last_result | ConvertTo-Json -Depth 8
}
