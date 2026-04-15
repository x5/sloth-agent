#!/usr/bin/env python3
"""
Sloth Agent Runner - Auto-installs uv if not found and runs the agent.

Usage:
    python run.py                    # Auto-install uv if needed, then run
    python run.py --no-install       # Skip uv auto-install
    python run.py --help             # Show help
"""

import os
import sys
from pathlib import Path


def ensure_uv():
    """Check if uv is installed, if not install it."""
    import subprocess

    # Check if uv is already available
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print(f"uv is installed: {result.stdout.strip()}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try to install uv
    print("uv not found, installing...")

    try:
        # Install uv via official installer
        result = subprocess.run(
            ["curl", "-LsSf", "https://astral.sh/uv/install.sh"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError("Failed to download uv installer")

        # Run the installer
        result = subprocess.run(
            ["sh", "-c", result.stdout],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "INSTALL_DIR": str(Path.home() / ".local" / "bin")},
        )

        if result.returncode == 0:
            print("uv installed successfully")
            return True
        else:
            print(f"uv installation failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"Failed to install uv: {e}")
        return False


def run_agent():
    """Run the agent using uv."""
    import subprocess

    # Get the directory of this script
    script_dir = Path(__file__).parent

    # Check if .venv exists, if not create it
    venv_dir = script_dir / ".venv"
    if not venv_dir.exists():
        print("Creating virtual environment with uv...")
        subprocess.run(["uv", "venv", str(venv_dir)], check=True)

    # Install dependencies
    print("Installing dependencies...")
    subprocess.run(
        ["uv", "pip", "install", "-e", str(script_dir)],
        check=True,
        env={**os.environ, "VIRTUAL_ENV": str(venv_dir)},
    )

    # Run the agent
    print("Starting Sloth Agent...")
    subprocess.run(
        ["python", "-m", "sloth_agent"],
        cwd=script_dir,
        check=True,
    )


def main():
    """Main entry point."""
    if "--no-install" not in sys.argv:
        if not ensure_uv():
            print("Warning: uv not available, falling back to system python")
            print("For best experience, install uv: https://astral.sh/uv")

    try:
        run_agent()
    except KeyboardInterrupt:
        print("\nSloth Agent stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error running agent: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
