param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("dev", "test", "prod")]
  [string]$Environment
)

$ErrorActionPreference = "Stop"

$requiredVars = @(
  "APP_ENV",
  "APP_PORT",
  "DB_URL",
  "SUPABASE_URL",
  "SUPABASE_KEY",
  "LLM_API_KEY",
  "EMBEDDING_MODEL",
  "LOG_LEVEL",
  "API_VERSION"
)

Write-Host "Preflight check for env: $Environment"

$missing = @()
foreach ($key in $requiredVars) {
  if (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($key))) {
    continue
  }
  $missing += $key
}

if ($missing.Count -gt 0) {
  Write-Host "Missing environment variables:"
  $missing | ForEach-Object { Write-Host "- $_" }
  exit 1
}

Write-Host "Preflight passed."
