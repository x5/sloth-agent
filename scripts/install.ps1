# Sloth Agent Installation Script for Windows (PowerShell)
#
# Usage:
#   iwr -useb https://raw.githubusercontent.com/x5/sloth-agent/main/scripts/install.ps1 | iex
#   & ([scriptblock]::Create((iwr -useb https://raw.githubusercontent.com/x5/sloth-agent/main/scripts/install.ps1))) -NoInit

param(
    [switch]$NoInit
)

$ErrorActionPreference = "Stop"

$SLOTH_DIR = "$HOME\.sloth-agent"
$REPO_URL = "git@github.com:x5/sloth-agent.git"
$BRANCH = "main"

$GREEN = "`e[0;32m"
$RED = "`e[0;31m"
$YELLOW = "`e[1;33m"
$NC = "`e[0m" # No Color

Write-Host "${GREEN}Installing Sloth Agent...${NC}" -ForegroundColor Green

# Check for -NoInit flag
$SkipInit = $NoInit.IsPresent

# Check git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "${RED}Error: git is not installed.${NC}" -ForegroundColor Red
    Write-Host "Please install git first: https://git-scm.com/download/win"
    exit 1
}

# Check uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "${YELLOW}uv not found, installing...${NC}" -ForegroundColor Yellow
    $uvInstaller = "$env:TEMP\uv-install.ps1"
    Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -OutFile $uvInstaller
    powershell -ExecutionPolicy Bypass -File $uvInstaller
    Remove-Item $uvInstaller -ErrorAction SilentlyContinue
    $env:PATH = "$HOME\.local\bin;$env:PATH"
}

# Clone or update repo
if (Test-Path "$SLOTH_DIR\.git") {
    Write-Host "${YELLOW}Updating existing installation...${NC}" -ForegroundColor Yellow
    Set-Location $SLOTH_DIR
    git pull origin $BRANCH
} else {
    Write-Host "${GREEN}Cloning Sloth Agent to $SLOTH_DIR...${NC}" -ForegroundColor Green
    git clone $REPO_URL $SLOTH_DIR
    Set-Location $SLOTH_DIR
}

# Create virtual environment and install
Write-Host "${GREEN}Setting up Python environment...${NC}" -ForegroundColor Green
uv venv "$SLOTH_DIR\.venv"
& "$SLOTH_DIR\.venv\Scripts\Activate.ps1"
uv pip install -e .

# Add to PowerShell profile
$PROFILE_FILE = $PROFILE
if (Test-Path $PROFILE_FILE) {
    $profileContent = Get-Content $PROFILE_FILE -Raw -ErrorAction SilentlyContinue
    if (-not ($profileContent -match "\.sloth-agent")) {
        Add-Content -Path $PROFILE_FILE -Value ""
        Add-Content -Path $PROFILE_FILE -Value "# Sloth Agent"
        Add-Content -Path $PROFILE_FILE -Value "`$env:PATH = `"$SLOTH_DIR;`$env:PATH`""
        Write-Host "${GREEN}Added PATH to `$PROFILE${NC}" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "${GREEN}Sloth Agent installed successfully!${NC}" -ForegroundColor Green
Write-Host ""
Write-Host "To get started:"
Write-Host "  1. Restart PowerShell or run: . `$PROFILE"
Write-Host "  2. Initialize a project: sloth init --project ~/my-project"
Write-Host ""
Write-Host "For help: sloth --help"
