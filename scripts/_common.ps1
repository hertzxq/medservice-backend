Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Import-DotEnv {
    $path = Join-Path $PSScriptRoot '.env'
    if (-not (Test-Path $path)) {
        throw ".env not found next to the script ($path). Copy .env.example to .env and fill it in."
    }
    $vars = @{}
    foreach ($line in Get-Content $path) {
        $trim = $line.Trim()
        if (-not $trim -or $trim.StartsWith('#')) { continue }
        $i = $trim.IndexOf('=')
        if ($i -lt 1) { continue }
        $k = $trim.Substring(0, $i).Trim()
        $v = $trim.Substring($i + 1).Trim()
        if ($v.StartsWith('"') -and $v.EndsWith('"')) { $v = $v.Substring(1, $v.Length - 2) }
        $vars[$k] = $v
    }
    foreach ($key in 'API_BASE','ADMIN_USERNAME','ADMIN_PASSWORD') {
        if (-not $vars.ContainsKey($key) -or -not $vars[$key]) {
            throw "Missing $key in .env"
        }
    }
    return $vars
}

function Get-AdminToken {
    param([hashtable]$EnvVars)
    $body = @{ username = $EnvVars.ADMIN_USERNAME; password = $EnvVars.ADMIN_PASSWORD } | ConvertTo-Json -Compress
    try {
        $resp = Invoke-RestMethod -Uri "$($EnvVars.API_BASE)/auth/login" -Method Post `
            -ContentType 'application/json' -Body $body -TimeoutSec 10
    } catch {
        throw "Login failed: $($_.Exception.Message). Is the backend running? Creds correct?"
    }
    if (-not $resp.user.isSuperuser) {
        throw "Account '$($EnvVars.ADMIN_USERNAME)' is not a superuser. Parsing requires admin."
    }
    return $resp.accessToken
}

function New-AuthHeaders {
    param([string]$Token)
    return @{ Authorization = "Bearer $Token"; 'Content-Type' = 'application/json' }
}
