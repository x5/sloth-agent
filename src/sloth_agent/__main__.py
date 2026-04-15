"""Sloth Agent Framework - Main Entry Point."""

import sys
from pathlib import Path

# Add this directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sloth_agent.cli.app import app


def main():
    """Main entry point for sloth-agent."""
    app()


if __name__ == "__main__":
    main()
