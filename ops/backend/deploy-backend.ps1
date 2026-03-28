param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("dev", "test", "prod")]
  [string]$Environment,

  [Parameter(Mandatory = $false)]
  [string]$ImageName = "enterprise-rag-backend",

  [Parameter(Mandatory = $false)]
  [string]$ImageTag = ""
)

$ErrorActionPreference = "Stop"

if (-not $ImageTag) {
  $ImageTag = Get-Date -Format "yyyyMMddHHmmss"
}

$fullImage = "$ImageName:release-$ImageTag"
Write-Host "Build backend image: $fullImage"

docker build -f ops/backend/Dockerfile.fastapi -t $fullImage .

Write-Host "Image built. Push/deploy is platform-specific and should be executed in CI for env: $Environment"
Write-Host "Recommended next step: tag and push image, then update service image in runtime platform."
