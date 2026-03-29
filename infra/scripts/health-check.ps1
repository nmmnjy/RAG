param(
  [Parameter(Mandatory = $true)]
  [string]$BackendHealthUrl,

  [Parameter(Mandatory = $false)]
  [int]$TimeoutSec = 10
)

$ErrorActionPreference = "Stop"

Write-Host "Health check: $BackendHealthUrl"

$headers = @{
  "x-request-id" = [guid]::NewGuid().ToString()
  "x-trace-id"   = [guid]::NewGuid().ToString()
}

$response = Invoke-WebRequest -Uri $BackendHealthUrl -Method GET -Headers $headers -TimeoutSec $TimeoutSec

if ($response.StatusCode -ne 200) {
  throw "Health check failed, status code: $($response.StatusCode)"
}

Write-Host "Health check passed with status 200."
