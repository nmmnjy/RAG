param(
  [Parameter(Mandatory = $false)]
  [ValidateSet("sample_v1", "qa_demo_v1")]
  [string]$Dataset = "qa_demo_v1",

  [Parameter(Mandatory = $false)]
  [string]$OutputPath = "",

  [Parameter(Mandatory = $false)]
  [string]$BackendDir = "backend",

  [Parameter(Mandatory = $false)]
  [switch]$RealMode,

  [Parameter(Mandatory = $false)]
  [switch]$ForbidFallbackWhenRealMode,

  [Parameter(Mandatory = $false)]
  [switch]$PassThruReportPath
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
  $startTs = Get-Date
  $datasetArgPath = $datasetPath
  $tempManifestPath = $null
  if ($RealMode) {
    $manifestAbsPath = (Resolve-Path $datasetPath).Path
    $datasetObj = Get-Content -Raw -Encoding UTF8 $manifestAbsPath | ConvertFrom-Json
    if (-not $datasetObj.runtime_policy) {
      $datasetObj | Add-Member -MemberType NoteProperty -Name runtime_policy -Value ([pscustomobject]@{})
    }
    if (-not ($datasetObj.runtime_policy.PSObject.Properties.Name -contains "declared_real_mode")) {
      $datasetObj.runtime_policy | Add-Member -MemberType NoteProperty -Name declared_real_mode -Value $true
    } else {
      $datasetObj.runtime_policy.declared_real_mode = $true
    }
    if (-not ($datasetObj.runtime_policy.PSObject.Properties.Name -contains "forbid_fallback_when_real_mode")) {
      $datasetObj.runtime_policy | Add-Member -MemberType NoteProperty -Name forbid_fallback_when_real_mode -Value ([bool]$ForbidFallbackWhenRealMode)
    } else {
      $datasetObj.runtime_policy.forbid_fallback_when_real_mode = [bool]$ForbidFallbackWhenRealMode
    }
    $tempManifestPath = Join-Path (Resolve-Path ".").Path ("tmp_real_eval_" + [guid]::NewGuid().ToString("N") + ".json")
    $manifestJson = $datasetObj | ConvertTo-Json -Depth 100
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($tempManifestPath, $manifestJson, $utf8NoBom)
    $datasetArgPath = $tempManifestPath
  }

  $args = @(
    "-m", "app.evaluation.run_offline_evaluation",
    "--dataset", $datasetArgPath
  )
  if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
    $args += @("--output", $OutputPath)
  }

  Write-Host "[evaluation] python $($args -join ' ')"
  & $pythonExe @args
  if ($LASTEXITCODE -ne 0) {
    throw "offline evaluation failed."
  }

  $resolvedReportPath = ""
  if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
    $resolvedReportPath = (Resolve-Path $OutputPath).Path
  } else {
    $reportsRoot = (Resolve-Path "..\\evaluation\\reports").Path
    $latestReport = Get-ChildItem -Path $reportsRoot -Filter "$Dataset*.json" -File |
      Where-Object { $_.LastWriteTime -ge $startTs.AddSeconds(-1) } |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 1
    if ($latestReport) {
      $resolvedReportPath = $latestReport.FullName
    }
  }

  if ($PassThruReportPath -and $resolvedReportPath) {
    Write-Output $resolvedReportPath
  }
} finally {
  if ($tempManifestPath -and (Test-Path $tempManifestPath)) {
    Remove-Item -Force $tempManifestPath
  }
  Pop-Location
}
