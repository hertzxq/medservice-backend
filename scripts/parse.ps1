param(
    [Parameter(Mandatory = $true, Position = 0)]
    [int]$BranchId,

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Platforms
)

. "$PSScriptRoot\_common.ps1"

$ValidPlatforms = @('yandex_maps', 'google_maps', '2gis', 'prodoctorov')

if (-not $Platforms -or $Platforms.Count -eq 0) {
    $Platforms = $ValidPlatforms
    Write-Host "No platforms specified - using all: $($Platforms -join ', ')" -ForegroundColor DarkGray
}

$invalid = $Platforms | Where-Object { $_ -notin $ValidPlatforms }
if ($invalid) {
    throw "Unknown platforms: $($invalid -join ', '). Allowed: $($ValidPlatforms -join ', ')."
}

$EnvVars = Import-DotEnv
$token = Get-AdminToken -EnvVars $EnvVars
$headers = New-AuthHeaders -Token $token

$payload = @{ branch_id = $BranchId; platforms = $Platforms } | ConvertTo-Json -Compress

Write-Host "-> POST /parsing/trigger-by-branch  branch=$BranchId  platforms=$($Platforms -join ',')"
try {
    $resp = Invoke-RestMethod -Uri "$($EnvVars.API_BASE)/parsing/trigger-by-branch" -Method Post `
        -Headers $headers -Body $payload -TimeoutSec 15
} catch {
    $err = $_.Exception
    $detail = ''
    if ($err.Response) {
        try {
            $stream = $err.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($stream)
            $detail = $reader.ReadToEnd()
        } catch {}
    }
    throw "trigger-by-branch FAIL: $($err.Message)$([Environment]::NewLine)$detail"
}
Write-Host "  accepted: $($resp.message)" -ForegroundColor Green
Write-Host ''

$lastProgress = ''
while ($true) {
    Start-Sleep -Seconds 3
    try {
        $s = Invoke-RestMethod -Uri "$($EnvVars.API_BASE)/parsing/status" -Method Get -Headers $headers -TimeoutSec 10
    } catch {
        Write-Host "status unavailable: $($_.Exception.Message)" -ForegroundColor Yellow
        continue
    }

    if ($s.progress -and $s.progress -ne $lastProgress) {
        Write-Host "  [$(Get-Date -Format HH:mm:ss)] $($s.progress)"
        $lastProgress = $s.progress
    }

    if ($s.status -eq 'completed' -or $s.status -eq 'error') {
        Write-Host ''
        Write-Host "=== Result ($($s.status)) ==="
        if ($s.last_result) {
            $s.last_result | ConvertTo-Json -Depth 8
        }
        if ($s.status -eq 'error') { exit 1 }
        break
    }
}
