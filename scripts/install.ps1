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

# Ensure Unicode symbols render correctly in PowerShell console
chcp.com 65001 > $null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$SLOTH_DIR = "$HOME\.sloth-agent"
$LOCAL_BIN = "$HOME\.local\bin"
$REPO_URL = "https://github.com/x5/sloth-agent.git"
$BRANCH = "master"

# Colors (ANSI escape sequences — supported in PowerShell 5.1+ and PS7)
$e = [char]27
$GREEN  = "${e}[0;32m"
$RED    = "${e}[0;31m"
$YELLOW = "${e}[1;33m"
$CYAN   = "${e}[0;36m"
$BOLD   = "${e}[1m"
$NC     = "${e}[0m"

function Write-Step   { param([string]$Message) Write-Host "${GREEN}▸${NC} ${BOLD}$Message${NC}" }
function Write-Ok     { param([string]$Message) Write-Host "  ${GREEN}✓${NC} $Message" }
function Write-Warn   { param([string]$Message) Write-Host "  ${YELLOW}⚠${NC} $Message" }
function Write-Fail   { param([string]$Message) Write-Host "  ${RED}✗${NC} $Message" }
function Write-Section { param([string]$Message) Write-Host ""; Write-Host "${CYAN}── $Message ${NC}" }
function Write-Exit {
    param([string]$What, [string]$Next)
    Write-Host ""
    Write-Host "${RED}${BOLD}  ✗  Installation failed${NC}"
    Write-Host "${CYAN}─────────────────────────────────────────────${NC}"
    Write-Host ""
    Write-Host "  ${BOLD}What happened?${NC}"
    Write-Host "    $What"
    Write-Host ""
    Write-Host "  ${BOLD}What to do next?${NC}"
    Write-Host "    $Next"
    Write-Host ""
    Write-Host "  If the issue persists, report it at:"
    Write-Host "    https://github.com/x5/sloth-agent/issues"
    Write-Host ""
    exit 1
}

# ─── Resolve version ────────────────────────────────────────
$tags = git ls-remote --tags --sort=-v:refname $REPO_URL 'v*' 2>$null
if ($tags) {
    $VERSION = ($tags -split "`n" | Select-Object -First 1).Trim() -replace '.*/' -replace '^v'
} else {
    $VERSION = "dev"
}

# ─── Banner ─────────────────────────────────────────────────
Write-Host ""
Write-Host "${GREEN}${BOLD}"
Write-Host "  ╭─────────────────────────────────────╮"
Write-Host "  │   Sloth Agent  $($VERSION.PadRight(14)) │"
Write-Host "  │   Installation                      │"
Write-Host "  ╰─────────────────────────────────────╯"
Write-Host "${NC}"

# ─── Installation Info ──────────────────────────────────────
Write-Host "  ${BOLD}Install Location${NC}"
Write-Host "    $SLOTH_DIR"
Write-Host ""
Write-Host "  ${BOLD}CLI Shim${NC}"
Write-Host "    $LOCAL_BIN\sloth.ps1"
Write-Host ""
Write-Host "  ${BOLD}After install${NC}"
Write-Host "    run ``sloth`` from any project directory"
Write-Host ""

# ─── Step 1: Prerequisites ──────────────────────────────────
Write-Section "Checking prerequisites"

if (Get-Command git -ErrorAction SilentlyContinue) {
    $gitVer = (git --version).Trim()
    Write-Host "    $gitVer"
    Write-Ok "git $gitVer"
} else {
    Write-Exit `
        "Git is not installed on your system." `
        "Install Git: https://git-scm.com/download/win"
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    $uvVer = (uv --version).Trim()
    Write-Ok "uv $uvVer"
} else {
    Write-Warn "uv not found — installing..."
    $uvInstaller = "$env:TEMP\sloth-uv-install.ps1"
    try {
        Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -OutFile $uvInstaller -UseBasicParsing
        powershell -ExecutionPolicy Bypass -File $uvInstaller
        Remove-Item $uvInstaller -ErrorAction SilentlyContinue
        $env:PATH = "$LOCAL_BIN;$env:PATH"
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            $uvVer = (uv --version).Trim()
            Write-Ok "uv $uvVer"
        } else {
            Write-Exit `
                "Failed to install uv automatically." `
                "Install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
        }
    } catch {
        Write-Exit `
            "Failed to download the uv installer." `
            "Check your network and try again. Or install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
    }
}

if (Get-Command python3 -ErrorAction SilentlyContinue) {
    try {
        $pyVer = (python3 --version 2>&1).Trim()
        Write-Ok "python3 $pyVer"
    } catch {
        $pyVer = $null
    }
}
if (-not $pyVer) {
    try {
        $uvPython = (uv python find 2>&1).Trim()
        if ($uvPython -and (Test-Path $uvPython)) {
            $pyVer = (& $uvPython --version 2>&1).Trim()
            Write-Ok "python $pyVer (uv-managed)"
        } else {
            $uvPython = $null
        }
    } catch {
        $uvPython = $null
    }
}
if (-not $pyVer) {
    Write-Warn "no system Python — installing Python 3.12 via uv..."
    uv python install 3.12 *>$null
    $uvPython = (uv python find 2>&1).Trim()
    if ($uvPython -and (Test-Path $uvPython)) {
        $pyVer = (& $uvPython --version 2>&1).Trim()
        Write-Ok "python $pyVer (uv-managed)"
    } else {
        Write-Exit `
            "Failed to install Python via uv." `
            "Try running: uv python install 3.12"
    }
}

# ─── Step 2: Clone or update ────────────────────────────────
Write-Section "Installing"

if ($VERSION -eq "dev") {
    Write-Warn "no release tag found, installing from $BRANCH"
    $LATEST_TAG = $BRANCH
} else {
    Write-Step "Release v$VERSION"
    $LATEST_TAG = "v$VERSION"
}

if (Test-Path "$SLOTH_DIR\.git") {
    Push-Location $SLOTH_DIR
    git fetch origin --tags --force *>$null
    git checkout $LATEST_TAG *>$null
    git reset --hard $LATEST_TAG *>$null
    Pop-Location
    Write-Ok "updated to $LATEST_TAG"
} else {
    Write-Step "Cloning repository..."
    # Clone master with shallow depth, then fetch + checkout the target tag.
    # Annotated tags don't resolve correctly with --depth 1 --branch.
    git clone --quiet --depth 1 --branch $BRANCH $REPO_URL $SLOTH_DIR
    Push-Location $SLOTH_DIR
    git fetch --quiet origin "refs/tags/$LATEST_TAG`:refs/tags/$LATEST_TAG"
    git checkout --quiet $LATEST_TAG
    Pop-Location
    Write-Ok "cloned to $SLOTH_DIR at $LATEST_TAG"
}

# ─── Step 3: Create venv and install ────────────────────────
Write-Step "Setting up environment..."
Push-Location $SLOTH_DIR
uv venv "$SLOTH_DIR\.venv" --quiet *>$null
uv pip install -e . --quiet *>$null
Pop-Location
Write-Ok "dependencies installed"

# ─── Step 4: Create global CLI shim ────────────────────────
Write-Step "Installing CLI shim..."
New-Item -ItemType Directory -Force -Path $LOCAL_BIN | Out-Null

# .ps1 shim
$shimPs1 = @"
& "$HOME\.sloth-agent\.venv\Scripts\sloth.exe" `$args
"@
Set-Content -Path "$LOCAL_BIN\sloth.ps1" -Value $shimPs1 -Encoding UTF8

# .bat shim for cmd.exe compatibility
$batShim = @"
@echo off
"%~dp0sloth.ps1" %*
"@
Set-Content -Path "$LOCAL_BIN\sloth.bat" -Value $batShim -Encoding ASCII
Write-Ok "sloth shim installed"

# ─── Step 5: Ensure ~/.local/bin is on PATH ────────────────
$profilePaths = @()
if ($PROFILE) {
    $profilePaths += $PROFILE
}
$bashrcPath = "$HOME\.bashrc"
if (Test-Path $bashrcPath) {
    $profilePaths += $bashrcPath
}

$pathUpdated = $false
foreach ($p in $profilePaths) {
    if (Test-Path $p) {
        $content = Get-Content $p -Raw -ErrorAction SilentlyContinue
        if ($content -match "\.local\\bin") {
            Write-Ok "$LOCAL_BIN already on PATH"
        } else {
            Add-Content -Path $p -Value ""
            Add-Content -Path $p -Value "# Sloth Agent: add local bin to PATH"
            Add-Content -Path $p -Value "`$env:PATH = `"$LOCAL_BIN;`$env:PATH`""
            $profileName = Split-Path $p -Leaf
            Write-Ok "added $LOCAL_BIN to PATH in $profileName"
        }
        $pathUpdated = $true
    }
}

if (-not $pathUpdated) {
    if ($PROFILE -and -not (Test-Path $PROFILE)) {
        New-Item -ItemType File -Force -Path $PROFILE | Out-Null
        Add-Content -Path $PROFILE -Value "# Sloth Agent: add local bin to PATH"
        Add-Content -Path $PROFILE -Value "`$env:PATH = `"$LOCAL_BIN;`$env:PATH`""
        $profileName = Split-Path $PROFILE -Leaf
        Write-Ok "created $profileName and added $LOCAL_BIN to PATH"
    } else {
        Write-Warn "please ensure $LOCAL_BIN is on your PATH"
    }
}

# ─── Step 6: Verify ────────────────────────────────────────
Write-Section "Verifying"

$venvSloth = "$SLOTH_DIR\.venv\Scripts\sloth.exe"
if (Test-Path $venvSloth) {
    try {
        & $venvSloth --help 2>$null | Out-Null
        Write-Ok "sloth CLI functional"
    } catch {
        Write-Exit `
            "The sloth CLI failed to start after installation." `
            "Run manually: $venvSloth --help`n    If the error persists, report it at: https://github.com/x5/sloth-agent/issues"
    }
} else {
    Write-Exit `
        "sloth.exe not found at $venvSloth" `
        "The installation may be incomplete. Try removing $SLOTH_DIR and running the installer again."
}

$venvPython = "$SLOTH_DIR\.venv\Scripts\python.exe"
$smokeScript = "from evals.smoke_test import run_smoke_test; r = run_smoke_test(); print('PASS' if r.passed else 'FAIL')"
try {
    Push-Location $SLOTH_DIR
    $smokeOutput = & $venvPython -c $smokeScript 2>&1
    Pop-Location
    if ($smokeOutput -match "PASS") {
        Write-Ok "smoke test passed"
    } else {
        Write-Warn "smoke test skipped (API keys not configured)"
    }
} catch {
    Pop-Location 2>$null
    Write-Warn "smoke test skipped (API keys not configured)"
}

# ─── Step 7: API keys ──────────────────────────────────────
Write-Section "Configuration"

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
    Write-Ok "created .env.example"

    if ($env:DEEPSEEK_API_KEY -or $env:QWEN_API_KEY) {
        $envContent = "# Global API Keys`n"
        $envContent += "DEEPSEEK_API_KEY=$($env:DEEPSEEK_API_KEY)`n"
        $envContent += "QWEN_API_KEY=$($env:QWEN_API_KEY)`n"
        $envContent += "`n# Optional providers (uncomment if needed)`n"
        $envContent += "# KIMI_API_KEY=`n# GLM_API_KEY=`n# MINIMAX_API_KEY=`n# XIAOMI_API_KEY=`n"
        Set-Content -Path $envFile -Value $envContent -Encoding UTF8
        Write-Ok "auto-filled .env from environment"
    } else {
        Write-Warn "configure API keys: copy .env.example to .env"
    }
} else {
    Write-Ok ".env already exists"
}

$configJson = "$SLOTH_DIR\config.json"
if (-not (Test-Path $configJson)) {
    $srcConfig = "$SLOTH_DIR\configs\config.json.example"
    if (Test-Path $srcConfig) {
        Copy-Item -Path $srcConfig -Destination $configJson -Force
        Write-Ok "created config.json"
    } else {
        Write-Warn "run ``sloth config init`` to create config"
    }
} else {
    Write-Ok "config.json already exists"
}

# ─── Done ───────────────────────────────────────────────────
Write-Host ""
Write-Host "${GREEN}${BOLD}  ✓  Sloth Agent v$VERSION installed successfully${NC}"
Write-Host "${CYAN}─────────────────────────────────────────────${NC}"
Write-Host ""
Write-Host "  ${BOLD}Welcome to Sloth Agent!${NC}"
Write-Host ""
Write-Host "  You're all set. Run ``sloth`` from any project"
Write-Host "  directory to get started."
Write-Host ""
Write-Host "  ${BOLD}Next steps:${NC}"
Write-Host ""
Write-Host "    1.  Reload shell:  . `$PROFILE"
Write-Host ""
Write-Host "    2.  Set API keys:"
Write-Host "        copy $envExample $envFile"
Write-Host "        notepad $envFile"
Write-Host ""
Write-Host "    3.  Initialize your project:"
Write-Host "        cd ~\my-project"
Write-Host "        sloth init"
Write-Host ""
Write-Host "    4.  Run your first plan:"
Write-Host "        sloth run --plan plan.md"
Write-Host ""
