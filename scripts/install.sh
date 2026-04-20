#!/bin/bash
# Sloth Agent Installation Script for macOS / Linux / WSL2
#
# Installs Sloth Agent globally so you can run `sloth` from any project directory.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/x5/sloth-agent/master/scripts/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/x5/sloth-agent/master/scripts/install.sh | bash -s -- --no-init

set -eo pipefail

SLOTH_DIR="${HOME}/.sloth-agent"
LOCAL_BIN="${HOME}/.local/bin"
REPO_URL="https://github.com/x5/sloth-agent.git"
BRANCH="master"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

check_no_init() {
    for arg in "$@"; do
        if [ "$arg" = "--no-init" ]; then
            echo "true"
            return
        fi
    done
    echo "false"
}

SKIP_INIT=$(check_no_init "$@")

step() { echo -e "${GREEN}▸${NC} ${BOLD}$1${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
section() { echo ""; echo -e "${CYAN}── $1 ${NC}"; }

die() {
    echo ""
    echo -e "${RED}${BOLD}  ✗  Installation failed${NC}"
    echo -e "${CYAN}─────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}What happened?${NC}"
    echo "    $1"
    echo ""
    echo -e "  ${BOLD}What to do next?${NC}"
    echo "    $2"
    echo ""
    echo -e "  If the issue persists, report it at:"
    echo "    https://github.com/x5/sloth-agent/issues"
    echo ""
    exit 1
}

# ─── Resolve version ────────────────────────────────────────
VERSION=$(git ls-remote --tags --sort=-v:refname "${REPO_URL}" 'v*' 2>/dev/null | head -1 | sed 's/.*\///' | sed 's/^v//')
if [ -z "${VERSION}" ]; then
    VERSION="dev"
fi

# ─── Banner ─────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}"
echo "  ╭─────────────────────────────────────╮"
printf "  │   Sloth Agent  %-14s │\n" "v${VERSION}"
echo "  │   Installation                      │"
echo "  ╰─────────────────────────────────────╯"
echo -e "${NC}"

# ─── Installation Info ──────────────────────────────────────
echo -e "  ${BOLD}Install Location${NC}"
echo "    ${SLOTH_DIR}"
echo ""
echo -e "  ${BOLD}CLI Shim${NC}"
echo "    ${LOCAL_BIN}/sloth"
echo ""
echo -e "  ${BOLD}After install${NC}"
echo "    run \`sloth\` from any project directory"
echo ""

# ─── Step 1: Prerequisites ──────────────────────────────────
section "Checking prerequisites"

if command -v git &>/dev/null; then
    ok "git $(git --version | awk '{print $3}')"
else
    die \
        "Git is not installed on your system." \
        "Install Git: https://git-scm.com/downloads"
fi

if command -v uv &>/dev/null; then
    ok "uv $(uv --version | awk '{print $2}')"
else
    warn "uv not found — installing..."
    UV_INSTALLER=$(mktemp)
    curl -LsSf --connect-timeout 10 --max-time 30 -o "${UV_INSTALLER}" https://astral.sh/uv/install.sh
    sh "${UV_INSTALLER}" >/dev/null 2>&1
    rm -f "${UV_INSTALLER}"
    export PATH="${LOCAL_BIN}:${PATH}"
    if command -v uv &>/dev/null; then
        ok "uv $(uv --version | awk '{print $2}')"
    else
        die \
            "Failed to install uv automatically." \
            "Install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
    fi
fi

if command -v python3 &>/dev/null && python3 --version &>/dev/null 2>&1; then
    ok "python3 $(python3 --version 2>&1 | awk '{print $2}')"
elif uv python find &>/dev/null 2>&1; then
    UV_PYTHON=$(uv python find 2>/dev/null)
    ok "python $( "${UV_PYTHON}" --version 2>&1 | awk '{print $2}') (uv-managed)"
else
    warn "no system Python — installing Python 3.12 via uv..."
    uv python install 3.12 >/dev/null 2>&1
    UV_PYTHON=$(uv python find 2>/dev/null)
    if [ -n "${UV_PYTHON}" ] && "${UV_PYTHON}" --version &>/dev/null 2>&1; then
        ok "python $( "${UV_PYTHON}" --version 2>&1 | awk '{print $2}') (uv-managed)"
    else
        die \
            "Failed to install Python via uv." \
            "Try: uv python install 3.12"
    fi
fi

# ─── Step 2: Clone or update ────────────────────────────────
section "Installing"

if [ "${VERSION}" = "dev" ]; then
    warn "no release tag found, installing from ${BRANCH}"
    LATEST_TAG="${BRANCH}"
else
    step "Release v${VERSION}"
    LATEST_TAG="v${VERSION}"
fi

if [ -d "${SLOTH_DIR}/.git" ]; then
    cd "${SLOTH_DIR}"
    git fetch origin --tags --force >/dev/null 2>&1
    git checkout "${LATEST_TAG}" >/dev/null 2>&1
    git reset --hard "${LATEST_TAG}" >/dev/null 2>&1
    ok "updated to ${LATEST_TAG}"
else
    step "Cloning repository..."
    git clone --quiet --depth 1 --branch "${LATEST_TAG}" "${REPO_URL}" "${SLOTH_DIR}"
    ok "cloned to ${SLOTH_DIR}"
fi

# ─── Step 3: Create venv and install ────────────────────────
step "Setting up environment..."
uv venv "${SLOTH_DIR}/.venv" --quiet
cd "${SLOTH_DIR}"
uv pip install -e . --quiet
ok "dependencies installed"

# ─── Step 4: Create global CLI shim ────────────────────────
step "Installing CLI shim..."
mkdir -p "${LOCAL_BIN}"
cat > "${LOCAL_BIN}/sloth" <<'SHIM'
#!/bin/bash
exec "${HOME}/.sloth-agent/.venv/bin/sloth" "$@"
SHIM
chmod +x "${LOCAL_BIN}/sloth"
ok "sloth shim installed"

# ─── Step 5: Ensure ~/.local/bin is on PATH ────────────────
SHELL_RC=""
if [ -f "${HOME}/.zshrc" ]; then
    SHELL_RC="${HOME}/.zshrc"
elif [ -f "${HOME}/.bashrc" ]; then
    SHELL_RC="${HOME}/.bashrc"
elif [ -f "${HOME}/.profile" ]; then
    SHELL_RC="${HOME}/.profile"
fi

if [ -n "${SHELL_RC}" ] && [ -f "${SHELL_RC}" ]; then
    if ! grep -q ".local/bin" "${SHELL_RC}" 2>/dev/null; then
        echo "" >> "${SHELL_RC}"
        echo "# Sloth Agent: add local bin to PATH" >> "${SHELL_RC}"
        echo "export PATH=\"${LOCAL_BIN}:\${PATH}\"" >> "${SHELL_RC}"
        ok "added ${LOCAL_BIN} to PATH in ${SHELL_RC##*/}"
    else
        ok "${LOCAL_BIN} already on PATH"
    fi
fi

# ─── Step 6: Verify ────────────────────────────────────────
section "Verifying"

if "${SLOTH_DIR}/.venv/bin/sloth" --help &>/dev/null; then
    ok "sloth CLI functional"
else
    die \
        "The sloth CLI failed to start after installation." \
        "Run manually: ${SLOTH_DIR}/.venv/bin/sloth --help
    If the error persists, report it at: https://github.com/x5/sloth-agent/issues"
fi

SMOKE_OUTPUT=$(cd "${SLOTH_DIR}" && "${SLOTH_DIR}/.venv/bin/python" -c \
    "from evals.smoke_test import run_smoke_test; r = run_smoke_test(); print('PASS' if r.passed else 'FAIL')" 2>&1)
if echo "${SMOKE_OUTPUT}" | grep -q "PASS"; then
    ok "smoke test passed"
else
    warn "smoke test skipped (API keys not configured)"
fi

# ─── Step 7: API keys ──────────────────────────────────────
section "Configuration"

if [ ! -f "${SLOTH_DIR}/.env" ]; then
    cat > "${SLOTH_DIR}/.env.example" <<'ENV'
# Global API Keys — copy to .env and fill in your keys
# Required: at least one provider
DEEPSEEK_API_KEY=
QWEN_API_KEY=

# Optional: additional providers (uncomment if needed)
# KIMI_API_KEY=
# GLM_API_KEY=
# MINIMAX_API_KEY=
# XIAOMI_API_KEY=
ENV
    ok "created .env.example"

    if [ -n "${DEEPSEEK_API_KEY:-}" ] || [ -n "${QWEN_API_KEY:-}" ]; then
        cp "${SLOTH_DIR}/.env.example" "${SLOTH_DIR}/.env"
        [ -n "${DEEPSEEK_API_KEY:-}" ] && \
            sed -i.bak "s/^DEEPSEEK_API_KEY=.*/DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}/" "${SLOTH_DIR}/.env" 2>/dev/null || true
        [ -n "${QWEN_API_KEY:-}" ] && \
            sed -i.bak "s/^QWEN_API_KEY=.*/QWEN_API_KEY=${QWEN_API_KEY}/" "${SLOTH_DIR}/.env" 2>/dev/null || true
        rm -f "${SLOTH_DIR}/.env.bak" 2>/dev/null
        ok "auto-filled .env from environment"
    else
        warn "configure API keys: cp ${SLOTH_DIR}/.env.example ${SLOTH_DIR}/.env"
    fi
else
    ok ".env already exists"
fi

CONFIG_JSON="${SLOTH_DIR}/config.json"
if [ ! -f "${CONFIG_JSON}" ]; then
    SRC_CONFIG="${SLOTH_DIR}/configs/config.json.example"
    if [ -f "${SRC_CONFIG}" ]; then
        cp "${SRC_CONFIG}" "${CONFIG_JSON}"
        ok "created config.json"
    else
        warn "run \`sloth config init\` to create config"
    fi
else
    ok "config.json already exists"
fi

# ─── Done ───────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}  ✓  Sloth Agent v${VERSION} installed successfully${NC}"
echo -e "${CYAN}─────────────────────────────────────────────${NC}"
echo ""
echo -e "  ${BOLD}Welcome to Sloth Agent!${NC}"
echo ""
echo "  You're all set. Run \`sloth\` from any project"
echo "  directory to get started."
echo ""
echo -e "  ${BOLD}Next steps:${NC}"
echo ""
echo "    1.  Reload shell:  source ${SHELL_RC:-~/.bashrc}"
echo ""
echo "    2.  Set API keys:"
echo "        cp ${SLOTH_DIR}/.env.example ${SLOTH_DIR}/.env"
echo "        vi ${SLOTH_DIR}/.env"
echo ""
echo "    3.  Initialize your project:"
echo "        cd ~/my-project"
echo "        sloth init"
echo ""
echo "    4.  Run your first plan:"
echo "        sloth run --plan plan.md"
echo ""
