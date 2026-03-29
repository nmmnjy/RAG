param(
  [Parameter(Mandatory = $false)]
  [ValidateSet("qa_demo_v1", "sample_v1")]
  [string]$EvalDataset = "qa_demo_v1",

  [Parameter(Mandatory = $false)]
  [ValidateSet("dev", "test", "prod")]
  [string]$Environment = "dev",

  [Parameter(Mandatory = $false)]
  [switch]$IncludeApiTests,

  [Parameter(Mandatory = $false)]
  [switch]$ForbidFallbackWhenRealMode
)

$ErrorActionPreference = "Stop"

Write-Host "=== Real Mode Acceptance Start ==="

Write-Host "[1/3] Preflight (real mode)"
& "$PSScriptRoot\\preflight.ps1" -Environment $Environment -Profile real -RealMode

Write-Host "[2/3] Backend key tests"
$backendArgs = @{
  Action = "test"
  TestScope = "key"
}
if ($IncludeApiTests) {
  $backendArgs.IncludeApiTests = $true
}
& "$PSScriptRoot\\local-backend.ps1" @backendArgs

Write-Host "[3/3] Offline evaluation (runtime_policy real)"
$evalArgs = @{
  Dataset = $EvalDataset
  RealMode = $true
  PassThruReportPath = $true
}
if ($ForbidFallbackWhenRealMode) {
  $evalArgs.ForbidFallbackWhenRealMode = $true
}
$reportOutput = & "$PSScriptRoot\\local-evaluation.ps1" @evalArgs
$reportPath = ($reportOutput | Select-Object -Last 1)

if (-not $reportPath -or -not (Test-Path $reportPath)) {
  throw "Failed to locate evaluation report output path."
}

$report = Get-Content -Raw -Encoding UTF8 $reportPath | ConvertFrom-Json

$providerVisible = $true
foreach ($caseItem in $report.case_reports) {
  $runtime = $caseItem.output_summary.provider_runtime
  if (-not $runtime -or -not $runtime.embedding -or -not $runtime.llm) {
    $providerVisible = $false
    break
  }
}

$realGate = $report.gate_results | Where-Object { $_.rule_name -eq "gate_real_mode_forbid_fallback" } | Select-Object -First 1
if (-not $realGate) {
  throw "gate_real_mode_forbid_fallback is missing in report."
}

Write-Host "report_path=$reportPath"
Write-Host "provider_runtime_visible=$providerVisible"
Write-Host "gate_real_mode_forbid_fallback.passed=$($realGate.passed)"
Write-Host "gate_real_mode_forbid_fallback.metric_value=$($realGate.metric_value)"
Write-Host "gate_real_mode_forbid_fallback.assertion_result=$($realGate.assertion_result)"

if (-not $providerVisible) {
  throw "provider_runtime is not visible in report output."
}

Write-Host "=== Real Mode Acceptance Finished ==="
