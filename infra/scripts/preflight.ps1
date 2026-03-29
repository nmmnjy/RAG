param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("dev", "test", "prod")]
  [string]$Environment,

  [Parameter(Mandatory = $false)]
  [ValidateSet("core", "vector", "qa", "all", "real")]
  [string]$Profile = "core",

  [Parameter(Mandatory = $false)]
  [switch]$RealMode
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

$requiredRealVars = @(
  "EMBEDDING_API_KEY",
  "LLM_API_KEY",
  "EMBEDDING_BASE_URL",
  "LLM_BASE_URL"
)

$requiredVars = @()
if ($Profile -eq "core") {
  $requiredVars += $requiredCoreVars
} elseif ($Profile -eq "vector") {
  $requiredVars += $requiredCoreVars + $requiredVectorVars
} elseif ($Profile -eq "qa") {
  $requiredVars += $requiredCoreVars + $requiredQaVars
} elseif ($Profile -eq "real") {
  $requiredVars += $requiredCoreVars + $requiredVectorVars + $requiredQaVars + $requiredRealVars
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

if ($RealMode -or $Profile -eq "real") {
  $realModeViolations = @()
  if ($env:EMBEDDING_PROVIDER -ne "openai_compatible") {
    $realModeViolations += "EMBEDDING_PROVIDER must be openai_compatible in real mode."
  }
  if ($env:LLM_PROVIDER -ne "openai_compatible") {
    $realModeViolations += "LLM_PROVIDER must be openai_compatible in real mode."
  }
  if ($env:EMBEDDING_PROVIDER_ENABLE_REAL -notin @("true", "True", "1")) {
    $realModeViolations += "EMBEDDING_PROVIDER_ENABLE_REAL must be true in real mode."
  }
  if ($env:LLM_PROVIDER_ENABLE_REAL -notin @("true", "True", "1")) {
    $realModeViolations += "LLM_PROVIDER_ENABLE_REAL must be true in real mode."
  }
  if ($realModeViolations.Count -gt 0) {
    Write-Host "Real mode validation failed:"
    $realModeViolations | ForEach-Object { Write-Host "- $_" }
    exit 1
  }
}

Write-Host "Preflight passed."
