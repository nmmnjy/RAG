param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("dev", "test", "prod")]
  [string]$Environment,

  [Parameter(Mandatory = $false)]
  [ValidateSet("core", "vector", "qa", "all")]
  [string]$Profile = "core"
)

$ErrorActionPreference = "Stop"

$requiredCoreVars = @(
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

$requiredVectorVars = @(
  "EMBEDDING_PROVIDER",
  "EMBEDDING_MODEL",
  "EMBEDDING_DIM",
  "VECTOR_REPOSITORY",
  "VECTOR_REPOSITORY_ENABLE_REAL",
  "VECTOR_REPOSITORY_FALLBACK_TO_IN_MEMORY"
)

$requiredQaVars = @(
  "LLM_PROVIDER",
  "LLM_MODEL",
  "LLM_PROVIDER_ENABLE_REAL",
  "LLM_PROVIDER_FALLBACK_TO_MOCK"
)

$requiredVars = @()
if ($Profile -eq "core") {
  $requiredVars += $requiredCoreVars
} elseif ($Profile -eq "vector") {
  $requiredVars += $requiredCoreVars + $requiredVectorVars
} elseif ($Profile -eq "qa") {
  $requiredVars += $requiredCoreVars + $requiredQaVars
} else {
  $requiredVars += $requiredCoreVars + $requiredVectorVars + $requiredQaVars
}
$requiredVars = $requiredVars | Select-Object -Unique

Write-Host "Preflight check for env: $Environment"
Write-Host "Preflight profile: $Profile"

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
