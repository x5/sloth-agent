#!/bin/bash
# Sloth Agent Installation Script for macOS / Linux / WSL2
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/x5/sloth-agent/main/scripts/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/x5/sloth-agent/main/scripts/install.sh | bash -s -- --no-init

set -e

SLOTH_DIR="${HOME}/.sloth-agent"
REPO_URL="git@github.com:x5/sloth-agent.git"
BRANCH="main"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing Sloth Agent...${NC}"

# Check for --no-init flag
SKIP_INIT=false
for arg in "$@"; do
    case $arg in
        --no-init)
            SKIP_INIT=true
            ;;
    esac
done

# Check git
if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: git is not installed.${NC}"
    echo "Please install git first: https://git-scm.com/downloads"
    exit 1
fi

# Check uv
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}uv not found, installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "${HOME}/.local/bin/env" 2>/dev/null || true
    export PATH="${HOME}/.local/bin:${PATH}"
fi

# Clone or update repo
if [ -d "${SLOTH_DIR}/.git" ]; then
    echo -e "${YELLOW}Updating existing installation...${NC}"
    cd "${SLOTH_DIR}"
    git pull origin "${BRANCH}"
else
    echo -e "${GREEN}Cloning Sloth Agent to ${SLOTH_DIR}...${NC}"
    git clone "${REPO_URL}" "${SLOTH_DIR}"
    cd "${SLOTH_DIR}"
fi

# Create virtual environment and install
echo -e "${GREEN}Setting up Python environment...${NC}"
uv venv "${SLOTH_DIR}/.venv"
source "${SLOTH_DIR}/.venv/bin/activate"
uv pip install -e .

# Add to shell rc
BASHRC="${HOME}/.bashrc"
ZSHRC="${HOME}/.zshrc"
SHELL_RC=""

if [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$BASHRC"
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$ZSHRC"
fi

if [ -n "$SHELL_RC" ] && [ -f "$SHELL_RC" ]; then
    if ! grep -q ".sloth-agent" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Sloth Agent" >> "$SHELL_RC"
        echo "export PATH=\"${SLOTH_DIR}:\${PATH}\"" >> "$SHELL_RC"
        echo -e "${GREEN}Added PATH to ${SHELL_RC}${NC}"
    fi
fi

echo ""
echo -e "${GREEN}Sloth Agent installed successfully!${NC}"
echo ""
echo "To get started:"
echo "  1. Restart your terminal or run: source ${SHELL_RC}"
echo "  2. Initialize a project: sloth init --project ~/my-project"
echo ""
echo "For help: sloth --help"
