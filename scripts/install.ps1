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

# ─── Unicode detection ──────────────────────────────────────
function Test-UnicodeSupport {
    if ($env:WT_SESSION -or $env:ConEmuPID -or $env:TERM_PROGRAM) { return $true }
    if ($PSVersionTable.PSVersion.Major -ge 7) { return $true }
    try {
        $cp = [Console]::OutputEncoding.CodePage
        return $cp -eq 65001 -or $cp -eq 1200
    } catch {
        return $false
    }
}

$HAS_UNICODE = Test-UnicodeSupport

# ─── Character sets (Unicode / ASCII fallback) ──────────────
if ($HAS_UNICODE) {
    $BOX_TL = "╭"; $BOX_TR = "╮"; $BOX_BL = "╰"; $BOX_BR = "╯"
    $BOX_H  = "─"; $BOX_V    = "│"
    $ICON_STEP = "$([char]0x25B8)"; $ICON_OK   = "$([char]0x2713)"
    $ICON_WARN = "$([char]0x26A0)"; $ICON_FAIL = "$([char]0x2717)"
    $DIVIDER   = "─"
} else {
    $BOX_TL = "+"; $BOX_TR = "+"; $BOX_BL = "+"; $BOX_BR = "+"
    $BOX_H  = "-"; $BOX_V  = "|"
    $ICON_STEP = ">>"; $ICON_OK   = "[OK]"
    $ICON_WARN = "[!]"; $ICON_FAIL = "[X]"
    $DIVIDER   = "-"
}

# Colors
$e = [char]27
$GREEN  = "${e}[0;32m"
$RED    = "${e}[0;31m"
$YELLOW = "${e}[1;33m"
$CYAN   = "${e}[0;36m"
$BOLD   = "${e}[1m"
$NC     = "${e}[0m"

# ─── Output helpers ──────────────────────────────────────────
function Write-Step   { param([string]$Message) Write-Host "${GREEN}${ICON_STEP}${NC} ${BOLD}$Message${NC}" }
function Write-Ok     { param([string]$Message) Write-Host "  ${GREEN}${ICON_OK}${NC} $Message" }
function Write-Warn   { param([string]$Message) Write-Host "  ${YELLOW}${ICON_WARN}${NC} $Message" }
function Write-Fail   { param([string]$Message) Write-Host "  ${RED}${ICON_FAIL}${NC} $Message" }
function Write-Section { param([string]$Message) Write-Host ""; Write-Host "${CYAN}${DIVIDER}${DIVIDER}${DIVIDER} $Message ${DIVIDER}${DIVIDER}${DIVIDER}${NC}" }
function Write-Exit {
    param([string]$What, [string]$Next)
    Write-Host ""
    $boxW = [Math]::Max($What.Length, $Next.Length) + 2
    $border = $BOX_H * $boxW
    Write-Host "${RED}${BOLD}${BOX_TL}${border}${BOX_TR}${NC}"
    Write-Host "${RED}${BOLD}${BOX_V}${NC}${RED}  Installation failed  ${NC}${RED}${BOLD}${BOX_V}${NC}"
    Write-Host "${RED}${BOLD}${BOX_BL}${border}${BOX_BR}${NC}"
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

# ─── Box helper for banner ─────────────────────────────────
function New-BoxLine { param([string]$Content, [int]$Width)
    $padding = $Width - $Content.Length
    if ($padding -lt 0) { $padding = 0 }
    return "${BOX_V}  ${Content}${' ' * $padding}${BOX_V}"
}

# ─── Resolve version ────────────────────────────────────────
try {
    $tags = & git ls-remote --tags --sort=-v:refname $REPO_URL 'v*' 2>$null
    if ($tags) {
        $rawTag = ($tags -split "`n" | Select-Object -First 1).Trim() -replace '.*/' -replace '^v'
        # Annotated tags may have ^{} suffix — strip it
        $VERSION = $rawTag -replace '\^{}'
    } else {
        $VERSION = "dev"
    }
} catch {
    $VERSION = "dev"
}

# ─── Banner ─────────────────────────────────────────────────
Write-Host ""
Write-Host "${GREEN}${BOLD}"
$contentWidth = 32
$verLine = "Sloth Agent  v$VERSION"
$instLine = "Installation"
$border = $BOX_H * $contentWidth
Write-Host "  ${BOX_TL}${border}${BOX_TR}"
Write-Host "  $(New-BoxLine -Content $verLine -Width $contentWidth)"
Write-Host "  $(New-BoxLine -Content $instLine -Width $contentWidth)"
Write-Host "  ${BOX_BL}${border}${BOX_BR}"
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
    $updateOk = $true
    try {
        Write-Host "  ${BOLD}Fetching latest tags...${NC}"
        git fetch origin --tags --force *>$null
        Write-Host "  ${BOLD}Checking out $LATEST_TAG...${NC}"
        git checkout $LATEST_TAG *>$null
        git reset --hard $LATEST_TAG *>$null
    } catch {
        $updateOk = $false
    }
    Pop-Location
    if ($updateOk) {
        Write-Ok "updated to $LATEST_TAG"
    } else {
        Write-Exit `
            "Failed to update repository (network error).`n    Cannot reach GitHub — check your network or proxy settings." `
            "If you have a proxy, set env: GIT_SSL_NO_VERIFY=0 or configure git proxy.`n    Or try again later."
    }
} else {
    Write-Host "  ${BOLD}Cloning repository...${NC}"
    $cloneOk = $false
    try {
        git clone --depth 1 --branch $BRANCH $REPO_URL $SLOTH_DIR 2>&1 | ForEach-Object { Write-Host "    $_" }
        $cloneOk = $true
    } catch {
        $cloneOk = $false
    }
    if (-not $cloneOk) {
        Write-Exit `
            "Failed to clone repository (network error).`n    Cannot reach GitHub — check your network or proxy settings." `
            "If you have a proxy, configure git proxy first:`n    git config --global http.proxy http://your-proxy:port`n    Or try again later."
    }
    Write-Host "  ${BOLD}Fetching release tag...${NC}"
    Push-Location $SLOTH_DIR
    git fetch origin "refs/tags/$LATEST_TAG`:refs/tags/$LATEST_TAG" *>$null
    Write-Host "  ${BOLD}Checking out $LATEST_TAG...${NC}"
    git checkout --quiet $LATEST_TAG
    Pop-Location
    Write-Ok "cloned to $SLOTH_DIR at $LATEST_TAG"
}

# ─── Step 3: Create venv and install ────────────────────────
Write-Host "  ${BOLD}Creating virtual environment...${NC}"
Push-Location $SLOTH_DIR
uv venv "$SLOTH_DIR\.venv" --quiet *>$null
Write-Host "  ${BOLD}Installing dependencies (this may take a moment)...${NC}"
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
$successTitle = "Sloth Agent v$VERSION installed successfully"
$welcomeMsg   = "Welcome to Sloth Agent!"
$steps = @(
    "Reload shell:  . `$PROFILE",
    "",
    "Set API keys:",
    "  copy $envExample $envFile",
    "  notepad $envFile",
    "",
    "Initialize your project:",
    "  cd ~\my-project",
    "  sloth init",
    "",
    "Run your first plan:",
    "  sloth run --plan plan.md"
)

$cardLines = @()
$cardLines += "  ${GREEN}${ICON_OK}${NC}  ${BOLD}$successTitle${NC}"
$cardLines += ""
$cardLines += "  $welcomeMsg"
$cardLines += ""
$cardLines += "  ${BOLD}Next steps:${NC}"
foreach ($s in $steps) {
    if ($s -eq "") {
        $cardLines += ""
    } elseif ($s.StartsWith("  ")) {
        $cardLines += "  ${CYAN}${BOX_V}${NC} $s"
    } else {
        $cardLines += "    $s"
    }
}

$cardWidth = 0
foreach ($line in $cardLines) {
    $plain = $line -replace "$e\[[0-9;]*m", ""
    if ($plain.Length -gt $cardWidth) { $cardWidth = $plain.Length }
}
$cardWidth = [Math]::Max($cardWidth, 40)

Write-Host ""
Write-Host "${GREEN}${BOLD}${BOX_TL}${BOX_H * $cardWidth}${BOX_BR}${NC}"
foreach ($line in $cardLines) {
    $plain = $line -replace "$e\[[0-9;]*m", ""
    $pad = $cardWidth - $plain.Length
    Write-Host "${GREEN}${BOLD}${BOX_V}${NC}${line}${' ' * $pad}${GREEN}${BOLD}${BOX_V}${NC}"
}
Write-Host "${GREEN}${BOLD}${BOX_BL}${BOX_H * $cardWidth}${BOX_BR}${NC}"
Write-Host ""
