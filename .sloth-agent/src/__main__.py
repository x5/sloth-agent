"""Sloth Agent Framework - Main Entry Point."""

import sys
from pathlib import Path

# Add this directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sloth_agent.core.agent import AgentEvolve


def main():
    """Main entry point for sloth-agent."""
    agent = AgentEvolve()
    agent.run()


if __name__ == "__main__":
    main()
