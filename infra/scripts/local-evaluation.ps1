param(
  [Parameter(Mandatory = $false)]
  [ValidateSet("sample_v1", "qa_demo_v1")]
  [string]$Dataset = "qa_demo_v1",

  [Parameter(Mandatory = $false)]
  [string]$OutputPath = "",

  [Parameter(Mandatory = $false)]
  [string]$BackendDir = "backend"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackendDir)) {
  throw "Backend directory '$BackendDir' not found."
}

$backendAbs = (Resolve-Path $BackendDir).Path
$pythonExe = Join-Path $backendAbs ".venv\\Scripts\\python.exe"
if (-not (Test-Path $pythonExe)) {
  $pythonExe = "python"
}

if (($pythonExe -eq "python") -and (-not (Get-Command python -ErrorAction SilentlyContinue))) {
  throw "Python not found. Please install Python 3.11+ first."
}

$datasetPath = "..\\evaluation\\datasets\\$Dataset\\manifest.json"
if (-not (Test-Path (Join-Path $BackendDir $datasetPath))) {
  throw "Dataset manifest not found: $datasetPath"
}

Push-Location $BackendDir
try {
  $args = @(
    "-m", "app.evaluation.run_offline_evaluation",
    "--dataset", $datasetPath
  )
  if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
    $args += @("--output", $OutputPath)
  }

  Write-Host "[evaluation] python $($args -join ' ')"
  & $pythonExe @args
  exit $LASTEXITCODE
} finally {
  Pop-Location
}
