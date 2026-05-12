# Sloth Agent — one-command dev launcher (Windows PowerShell)
# Starts backend + Tauri desktop app (with Vite HMR)
#
# Usage:
#   .\dev.ps1
#   .\dev.ps1 -BackendUrl "http://127.0.0.1:9090"

param(
    [string]$BackendUrl = "http://127.0.0.1:8080"
)

$ErrorActionPreference = "Stop"

$ROOT = $PSScriptRoot
$BACKEND_DIR = Join-Path $ROOT "backend"
$SRC_TAURI = Join-Path $ROOT "src-tauri"

$env:SLOTH_BACKEND_URL = $BackendUrl

$uri = [uri]$BackendUrl
$actualPort = if ($uri.Port -ne -1) { $uri.Port } else { 8080 }

Write-Host "=== Sloth Agent Dev Launcher (Windows) ==="
Write-Host "Backend URL: $BackendUrl"
Write-Host "Backend port: $actualPort"
Write-Host ""

Write-Host "Starting backend..."
$backendJob = Start-Job -ScriptBlock {
    param($dir, $port)
    Set-Location $dir
    uv run uvicorn app.main:app --reload --port $port
} -ArgumentList $BACKEND_DIR, $actualPort

Write-Host "Waiting for backend (health check)..."
$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $null = Invoke-WebRequest -Uri "$BackendUrl/api/health" -TimeoutSec 1 -UseBasicParsing
        $healthy = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $healthy) {
    Write-Warning "Backend health check timed out — continuing anyway"
} else {
    Write-Host "Backend is ready."
}

Write-Host "Starting Tauri (Rust compile + Vite HMR)..."
try {
    Set-Location $SRC_TAURI
    cargo tauri dev
} finally {
    Write-Host "Shutting down backend..."
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -ErrorAction SilentlyContinue
}
