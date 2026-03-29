param(
  [Parameter(Mandatory = $false)]
  [ValidateSet("dev", "build")]
  [string]$Action = "build",

  [Parameter(Mandatory = $false)]
  [string]$FrontendDir = "frontend",

  [Parameter(Mandatory = $false)]
  [switch]$InstallDeps
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $FrontendDir)) {
  throw "Frontend directory '$FrontendDir' not found."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm not found. Please install Node.js LTS first."
}

Push-Location $FrontendDir
try {
  if ($InstallDeps) {
    Write-Host "[frontend] npm install"
    npm install
  }

  if ($Action -eq "dev") {
    Write-Host "[frontend] npm run dev"
    npm run dev
    if ($LASTEXITCODE -ne 0) {
      throw "frontend dev failed."
    }
  } else {
    Write-Host "[frontend] npm run build"
    npm run build
    if ($LASTEXITCODE -ne 0) {
      Write-Host "[frontend] npm run build failed, fallback to webpack build"
      npx next build --webpack
      if ($LASTEXITCODE -ne 0) {
        throw "frontend build failed."
      }
    }
  }
} finally {
  Pop-Location
}
