#!/bin/bash
# Sloth Agent Installation Script for macOS / Linux / WSL2
#
# Installs Sloth Agent globally so you can run `sloth` from any project directory.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/x5/sloth-agent/main/scripts/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/x5/sloth-agent/main/scripts/install.sh | bash -s -- --no-init

set -e

SLOTH_DIR="${HOME}/.sloth-agent"
LOCAL_BIN="${HOME}/.local/bin"
REPO_URL="https://github.com/x5/sloth-agent.git"
BRANCH="main"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

banner() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════╗"
    echo "║        Sloth Agent Installer         ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "${NC}"
}

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

step() {
    echo -e "${GREEN}▸${NC} $1"
}

ok() {
    echo -e "  ${GREEN}✓${NC} $1"
}

warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

fail() {
    echo -e "  ${RED}✗${NC} $1"
}

banner

echo ""
echo "Sloth Agent will be installed to: ${SLOTH_DIR}"
echo "CLI shim will be placed in: ${LOCAL_BIN}"
echo "After installation, run sloth from any project directory."
echo ""

# ─── Step 1: Self-check ─────────────────────────────────────
echo "Checking prerequisites..."

if command -v git &>/dev/null; then
    GIT_VER=$(git --version)
    ok "git: ${GIT_VER}"
else
    fail "git not found"
    echo "  Install: https://git-scm.com/downloads"
    exit 1
fi

if command -v uv &>/dev/null; then
    UV_VER=$(uv --version)
    ok "uv: ${UV_VER}"
else
    warn "uv not found, installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${LOCAL_BIN}:${PATH}"
    if command -v uv &>/dev/null; then
        ok "uv installed: $(uv --version)"
    else
        fail "uv install failed. Please install manually."
        exit 1
    fi
fi

if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version)
    ok "python3: ${PY_VER}"
else
    warn "python3 not found — uv will manage Python for you"
fi

# ─── Step 2: Clone or update ────────────────────────────────
if [ -d "${SLOTH_DIR}/.git" ]; then
    step "Updating existing installation at ${SLOTH_DIR}..."
    cd "${SLOTH_DIR}"
    git fetch origin "${BRANCH}"
    git reset --hard "origin/${BRANCH}"
    ok "pulled latest"
else
    step "Cloning Sloth Agent to ${SLOTH_DIR}..."
    git clone "${REPO_URL}" "${SLOTH_DIR}"
    cd "${SLOTH_DIR}"
    ok "cloned"
fi

# ─── Step 3: Create venv and install ────────────────────────
step "Setting up Python environment..."
uv venv "${SLOTH_DIR}/.venv" --quiet

# Install via uv (always use uv, never bare pip)
cd "${SLOTH_DIR}"
uv pip install -e . --quiet
ok "dependencies installed"

# ─── Step 4: Create global CLI shim ────────────────────────
step "Installing CLI shim to ${LOCAL_BIN}/sloth..."

mkdir -p "${LOCAL_BIN}"

cat > "${LOCAL_BIN}/sloth" <<'SHIM'
#!/bin/bash
# Sloth Agent CLI shim — activates the hidden venv and runs sloth
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

if [ -n "$SHELL_RC" ] && [ -f "$SHELL_RC" ]; then
    if ! grep -q ".local/bin" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Sloth Agent: add uv / local bin to PATH" >> "$SHELL_RC"
        echo "export PATH=\"${LOCAL_BIN}:\${PATH}\"" >> "$SHELL_RC"
        ok "added ${LOCAL_BIN} to PATH in ${SHELL_RC}"
    else
        ok "${LOCAL_BIN} already on PATH"
    fi
fi

# ─── Step 6: Verify ────────────────────────────────────────
echo ""
step "Verifying installation..."

if "${SLOTH_DIR}/.venv/bin/sloth" --help &>/dev/null; then
    ok "sloth CLI is functional"
else
    fail "sloth CLI failed to start"
    echo "  Debug: ${SLOTH_DIR}/.venv/bin/sloth --help"
    exit 1
fi

# ─── Step 7: Quick smoke ────────────────────────────────────
step "Running smoke test..."
SMOKE_OUTPUT=$(cd "${SLOTH_DIR}" && "${SLOTH_DIR}/.venv/bin/python" -c \
    "from evals.smoke_test import run_smoke_test; r = run_smoke_test(); print('PASS' if r.passed else 'FAIL')" 2>&1)
if echo "$SMOKE_OUTPUT" | grep -q "PASS"; then
    ok "smoke test passed"
else
    warn "smoke test skipped or failed (normal if API keys not configured)"
fi

# ─── Step 8: Setup global API keys ────────────────────────
step "Setting up global API key template..."

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
    ok "created .env.example template"

    # If user has env vars set, auto-populate
    if [ -n "${DEEPSEEK_API_KEY:-}" ] || [ -n "${QWEN_API_KEY:-}" ]; then
        cp "${SLOTH_DIR}/.env.example" "${SLOTH_DIR}/.env"
        if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
            sed -i.bak "s/^DEEPSEEK_API_KEY=.*/DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}/" "${SLOTH_DIR}/.env" 2>/dev/null || \
            sed -i "s/^DEEPSEEK_API_KEY=.*/DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}/" "${SLOTH_DIR}/.env"
            rm -f "${SLOTH_DIR}/.env.bak" 2>/dev/null
        fi
        if [ -n "${QWEN_API_KEY:-}" ]; then
            sed -i.bak "s/^QWEN_API_KEY=.*/QWEN_API_KEY=${QWEN_API_KEY}/" "${SLOTH_DIR}/.env" 2>/dev/null || \
            sed -i "s/^QWEN_API_KEY=.*/QWEN_API_KEY=${QWEN_API_KEY}/" "${SLOTH_DIR}/.env"
            rm -f "${SLOTH_DIR}/.env.bak" 2>/dev/null
        fi
        ok "auto-filled .env from current environment variables"
    else
        warn "please configure API keys: cp ${SLOTH_DIR}/.env.example ${SLOTH_DIR}/.env && edit"
    fi
else
    ok "global .env already exists"
fi

# Setup global config.json template
CONFIG_JSON="${SLOTH_DIR}/config.json"
if [ ! -f "${CONFIG_JSON}" ]; then
    SRC_CONFIG="${SLOTH_DIR}/configs/config.json.example"
    if [ -f "${SRC_CONFIG}" ]; then
        cp "${SRC_CONFIG}" "${CONFIG_JSON}"
        ok "created config.json template"
    else
        warn "config.json.example not found, please run: sloth config init"
    fi
else
    ok "global config.json already exists"
fi

# ─── Done ───────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Sloth Agent installed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo "API Key 配置（项目级 .env 优先级高于全局）："
echo ""
echo "  方式一：全局配置（所有项目共用）"
echo "    编辑 ~/.sloth-agent/.env"
echo ""
echo "  方式二：项目配置（覆盖全局，仅当前项目生效）"
echo "    编辑 [项目目录]/.env"
echo ""
echo "Next steps:"
echo ""
echo "  1. Restart your terminal or run: source ${SHELL_RC:-~/.bashrc}"
echo ""
echo "  2. Configure your API keys:"
echo "       cp ~/.sloth-agent/.env.example ~/.sloth-agent/.env"
echo "       vi ~/.sloth-agent/.env"
echo ""
echo "  3. Go to your project and initialize:"
echo "       cd ~/my-project"
echo "       sloth init"
echo ""
echo "  4. Run your first plan:"
echo "       sloth run --plan plan.md"
echo ""
