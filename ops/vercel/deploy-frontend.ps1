param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("dev", "test", "prod")]
  [string]$Environment,

  [Parameter(Mandatory = $false)]
  [string]$FrontendDir = "frontend"
)

$ErrorActionPreference = "Stop"

Write-Host "Deploy frontend to Vercel - env: $Environment"

if (-not (Get-Command vercel -ErrorAction SilentlyContinue)) {
  throw "vercel CLI not found. Please install with npm i -g vercel."
}

if (-not (Test-Path $FrontendDir)) {
  throw "Frontend directory '$FrontendDir' not found."
}

Push-Location $FrontendDir
try {
  if ($Environment -eq "prod") {
    vercel --prod
  } else {
    vercel
  }
} finally {
  Pop-Location
}
