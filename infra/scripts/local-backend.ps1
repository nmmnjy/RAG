param(
  [Parameter(Mandatory = $false)]
  [ValidateSet("serve", "test")]
  [string]$Action = "test",

  [Parameter(Mandatory = $false)]
  [ValidateSet("key", "all")]
  [string]$TestScope = "key",

  [Parameter(Mandatory = $false)]
  [switch]$IncludeApiTests,

  [Parameter(Mandatory = $false)]
  [string]$BackendDir = "backend",

  [Parameter(Mandatory = $false)]
  [switch]$InstallDeps
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

Push-Location $BackendDir
try {
  if ($InstallDeps) {
    Write-Host "[backend] pip install -r requirements.txt"
    & $pythonExe -m pip install -r requirements.txt
  }

  if ($Action -eq "serve") {
    Write-Host "[backend] uvicorn app.main:app --reload --app-dir . --host 0.0.0.0 --port 8000"
    & $pythonExe -m uvicorn app.main:app --reload --app-dir . --host 0.0.0.0 --port 8000
    if ($LASTEXITCODE -ne 0) {
      throw "backend serve failed."
    }
    return
  }

  if ($TestScope -eq "all") {
    Write-Host "[backend] python -m pytest"
    & $pythonExe -m pytest
    if ($LASTEXITCODE -ne 0) {
      throw "backend tests failed."
    }
    return
  }

  $keyTests = @(
    "tests/unit/test_answer_generation_service.py",
    "tests/unit/test_evaluation_schema.py",
    "tests/unit/test_offline_evaluator.py"
  )
  if ($IncludeApiTests) {
    $keyTests += "tests/api/test_qa_api.py"
  }
  Write-Host "[backend] python -m pytest $($keyTests -join ' ')"
  & $pythonExe -m pytest @keyTests
  if ($LASTEXITCODE -ne 0) {
    throw "backend key tests failed."
  }
} finally {
  Pop-Location
}
