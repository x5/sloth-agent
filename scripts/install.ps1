# Sloth Agent Installation Script for Windows (PowerShell)
#
# Installs Sloth Agent globally so you can run `sloth` from any project directory.
#
# Usage:
#   iwr -useb https://raw.githubusercontent.com/x5/sloth-agent/master/scripts/install.ps1 | iex
#   iwr -useb https://raw.githubusercontent.com/x5/sloth-agent/master/scripts/install.ps1 | iex -args "--no-init"

param(
    [switch]$NoInit
)

$ErrorActionPreference = "Stop"

$SLOTH_DIR = "$HOME\.sloth-agent"
$LOCAL_BIN = "$HOME\.local\bin"
$REPO_URL = "https://github.com/x5/sloth-agent.git"
$BRANCH = "master"

# Colors
$GREEN = "`e[0;32m"
$RED = "`e[0;31m"
$YELLOW = "`e[1;33m"
$NC = "`e[0m"

function Write-Step { param([string]$Message) Write-Host "${GREEN}>${NC} $Message" }
function Write-Ok   { param([string]$Message) Write-Host "  ${GREEN}v${NC} $Message" }
function Write-Warn { param([string]$Message) Write-Host "  ${YELLOW}!${NC} $Message" }
function Write-Fail { param([string]$Message) Write-Host "  ${RED}x${NC} $Message" }

# Banner
Write-Host ""
Write-Host "${GREEN}"
Write-Host "======================================"
Write-Host "        Sloth Agent Installer         "
Write-Host "======================================"
Write-Host "${NC}"
Write-Host ""
Write-Host "Sloth Agent will be installed to: $SLOTH_DIR"
Write-Host "CLI shim will be placed in: $LOCAL_BIN"
Write-Host "After installation, run sloth from any project directory."
Write-Host ""

$SkipInit = $NoInit.IsPresent

# ─── Step 1: Self-check ─────────────────────────────────────
Write-Host "Checking prerequisites..."

if (Get-Command git -ErrorAction SilentlyContinue) {
    $gitVer = git --version
    Write-Ok "git: $gitVer"
} else {
    Write-Fail "git not found"
    Write-Host "  Install: https://git-scm.com/download/win"
    exit 1
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    $uvVer = uv --version
    Write-Ok "uv: $uvVer"
} else {
    Write-Warn "uv not found, installing..."
    $uvInstaller = "$env:TEMP\uv-install.ps1"
    try {
        Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -OutFile $uvInstaller
        powershell -ExecutionPolicy Bypass -File $uvInstaller
        Remove-Item $uvInstaller -ErrorAction SilentlyContinue
        $env:PATH = "$LOCAL_BIN;$env:PATH"
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            Write-Ok "uv installed: $(uv --version)"
        } else {
            Write-Fail "uv install failed. Please install manually."
            exit 1
        }
    } catch {
        Write-Fail "uv install failed: $_"
        exit 1
    }
}

if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pyVer = python3 --version
    Write-Ok "python3: $pyVer"
} else {
    Write-Warn "python3 not found - uv will manage Python for you"
}

# ─── Step 2: Clone or update ────────────────────────────────
# Resolve the latest release tag
$tags = git ls-remote --tags --sort=-v:refname $REPO_URL 'v*'
if ($tags) {
    $LATEST_TAG = ($tags -split "`n" | Select-Object -First 1) -replace '.*/'
} else {
    $LATEST_TAG = $BRANCH
    Write-Warn "no release tag found, falling back to $BRANCH"
}

if (Test-Path "$SLOTH_DIR\.git") {
    Write-Step "Updating existing installation at $SLOTH_DIR..."
    Push-Location $SLOTH_DIR
    git fetch origin --tags --force
    git checkout $LATEST_TAG
    git reset --hard $LATEST_TAG
    Pop-Location
    Write-Ok "pinned to $LATEST_TAG"
} else {
    Write-Step "Cloning Sloth Agent to $SLOTH_DIR..."
    git clone --depth 1 --branch $LATEST_TAG $REPO_URL $SLOTH_DIR
    Write-Ok "cloned ($LATEST_TAG)"
}

# ─── Step 3: Create venv and install ────────────────────────
Write-Step "Setting up Python environment..."
Push-Location $SLOTH_DIR
uv venv "$SLOTH_DIR\.venv" --quiet

# Install via uv (always use uv, never bare pip)
uv pip install -e . --quiet
Pop-Location
Write-Ok "dependencies installed"

# ─── Step 4: Create global CLI shim ────────────────────────
Write-Step "Installing CLI shim to $LOCAL_BIN\sloth..."

New-Item -ItemType Directory -Force -Path $LOCAL_BIN | Out-Null

$shimPath = "$LOCAL_BIN\sloth.ps1"
$shimContent = @"
# Sloth Agent CLI shim — delegates to the hidden venv
& "$HOME\.sloth-agent\.venv\Scripts\sloth.exe" `$args
"@
Set-Content -Path $shimPath -Value $shimContent -Encoding UTF8
Write-Ok "sloth shim installed"

# Also create a .bat shim for cmd.exe compatibility
$batShimPath = "$LOCAL_BIN\sloth.bat"
$batShimContent = @"
@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0sloth.ps1" %*
"@
Set-Content -Path $batShimPath -Value $batShimContent -Encoding ASCII
Write-Ok "sloth.bat shim installed (cmd.exe compatibility)"

# ─── Step 5: Ensure ~/.local/bin is on PATH ────────────────
$profilePaths = @()
if ($PROFILE -and (Test-Path $PROFILE)) {
    $profilePaths += $PROFILE
}
$bashrcPath = "$HOME\.bashrc"
if (Test-Path $bashrcPath) {
    $profilePaths += $bashrcPath
}

$pathUpdated = $false
foreach ($p in $profilePaths) {
    $content = Get-Content $p -Raw -ErrorAction SilentlyContinue
    if ($content -and $content -notmatch "\.local\\bin") {
        Add-Content -Path $p -Value ""
        Add-Content -Path $p -Value "# Sloth Agent: add local bin to PATH"
        Add-Content -Path $p -Value "`$env:PATH = `"$LOCAL_BIN;`$env:PATH`""
        Write-Ok "added $LOCAL_BIN to PATH in $p"
        $pathUpdated = $true
    } elseif ($content -and $content -match "\.local\\bin") {
        Write-Ok "$LOCAL_BIN already on PATH"
        $pathUpdated = $true
    }
}

if (-not $pathUpdated) {
    # Create profile if it doesn't exist
    if ($PROFILE -and -not (Test-Path $PROFILE)) {
        New-Item -ItemType File -Force -Path $PROFILE | Out-Null
        Add-Content -Path $PROFILE -Value "# Sloth Agent: add local bin to PATH"
        Add-Content -Path $PROFILE -Value "`$env:PATH = `"$LOCAL_BIN;`$env:PATH`""
        Write-Ok "created $PROFILE and added $LOCAL_BIN to PATH"
    } else {
        Write-Warn "please ensure $LOCAL_BIN is on your PATH"
    }
}

# ─── Step 6: Verify ────────────────────────────────────────
Write-Host ""
Write-Step "Verifying installation..."

$venvSloth = "$SLOTH_DIR\.venv\Scripts\sloth.exe"
if (Test-Path $venvSloth) {
    try {
        & $venvSloth --help 2>$null | Out-Null
        Write-Ok "sloth CLI is functional"
    } catch {
        Write-Fail "sloth CLI failed to start"
        Write-Host "  Debug: $venvSloth --help"
        exit 1
    }
} else {
    Write-Fail "sloth CLI not found"
    Write-Host "  Debug: $venvSloth"
    exit 1
}

# ─── Step 7: Quick smoke ────────────────────────────────────
Write-Step "Running smoke test..."
$venvPython = "$SLOTH_DIR\.venv\Scripts\python.exe"
$smokeScript = "from evals.smoke_test import run_smoke_test; r = run_smoke_test(); print('PASS' if r.passed else 'FAIL')"
try {
    Push-Location $SLOTH_DIR
    $smokeOutput = & $venvPython -c $smokeScript 2>&1
    Pop-Location
    if ($smokeOutput -match "PASS") {
        Write-Ok "smoke test passed"
    } else {
        Write-Warn "smoke test skipped or failed (normal if API keys not configured)"
    }
} catch {
    Pop-Location 2>$null
    Write-Warn "smoke test skipped (normal if API keys not configured)"
}

# ─── Step 8: Setup global API keys ────────────────────────
Write-Step "Setting up global API key template..."

$envExample = "$SLOTH_DIR\.env.example"
$envFile = "$SLOTH_DIR\.env"

if (-not (Test-Path $envFile)) {
    $exampleContent = @"
# Global API Keys — copy to .env and fill in your keys
# Required: at least one provider
DEEPSEEK_API_KEY=
QWEN_API_KEY=

# Optional: additional providers (uncomment if needed)
# KIMI_API_KEY=
# GLM_API_KEY=
# MINIMAX_API_KEY=
# XIAOMI_API_KEY=
"@
    Set-Content -Path $envExample -Value $exampleContent -Encoding UTF8
    Write-Ok "created .env.example template"

    # If user has env vars set, auto-populate
    $hasKeys = $false
    if ($env:DEEPSEEK_API_KEY -or $env:QWEN_API_KEY) {
        $envContent = "# Global API Keys`n"
        $envContent += "DEEPSEEK_API_KEY=$($env:DEEPSEEK_API_KEY)`n"
        $envContent += "QWEN_API_KEY=$($env:QWEN_API_KEY)`n"
        $envContent += "`n# Optional providers (uncomment if needed)`n"
        $envContent += "# KIMI_API_KEY=`n"
        $envContent += "# GLM_API_KEY=`n"
        $envContent += "# MINIMAX_API_KEY=`n"
        $envContent += "# XIAOMI_API_KEY=`n"
        Set-Content -Path $envFile -Value $envContent -Encoding UTF8
        Write-Ok "auto-filled .env from current environment variables"
    } else {
        Write-Warn "please configure API keys: copy .env.example to .env and edit"
    }
} else {
    Write-Ok "global .env already exists"
}

# Setup global config.json template
$configJson = "$SLOTH_DIR\config.json"
if (-not (Test-Path $configJson)) {
    $srcConfig = "$SLOTH_DIR\configs\config.json.example"
    if (Test-Path $srcConfig) {
        Copy-Item -Path $srcConfig -Destination $configJson -Force
        Write-Ok "created config.json template"
    } else {
        Write-Warn "config.json.example not found, please run: sloth config init"
    }
} else {
    Write-Ok "global config.json already exists"
}

# ─── Done ───────────────────────────────────────────────────
Write-Host ""
Write-Host "${GREEN}=============================================${NC}"
Write-Host "${GREEN}  Sloth Agent installed successfully!${NC}"
Write-Host "${GREEN}=============================================${NC}"
Write-Host ""
Write-Host "API Key 配置（项目级 .env 优先级高于全局）："
Write-Host ""
Write-Host "  方式一：全局配置（所有项目共用）"
Write-Host "    编辑 $envFile"
Write-Host ""
Write-Host "  方式二：项目配置（覆盖全局，仅当前项目生效）"
Write-Host "    编辑 [项目目录]/.env"
Write-Host ""
Write-Host "Next steps:"
Write-Host ""
Write-Host "  1. Restart PowerShell or run: . `$PROFILE"
Write-Host ""
Write-Host "  2. Configure your API keys:"
Write-Host "       copy $envExample $envFile"
Write-Host "       notepad $envFile"
Write-Host ""
Write-Host "  3. Go to your project and initialize:"
Write-Host "       cd ~/my-project"
Write-Host "       sloth init"
Write-Host ""
Write-Host "  4. Run your first plan:"
Write-Host "       sloth run --plan plan.md"
Write-Host ""
