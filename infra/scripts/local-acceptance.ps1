param(
  [Parameter(Mandatory = $false)]
  [ValidateSet("qa_demo_v1", "sample_v1")]
  [string]$EvalDataset = "qa_demo_v1"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Local Acceptance Snapshot Start ==="

Write-Host "[1/3] Frontend build"
& "$PSScriptRoot\\local-frontend.ps1" -Action build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] Backend key tests"
& "$PSScriptRoot\\local-backend.ps1" -Action test -TestScope key
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/3] Offline evaluation"
& "$PSScriptRoot\\local-evaluation.ps1" -Dataset $EvalDataset
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Local Acceptance Snapshot Passed ==="
