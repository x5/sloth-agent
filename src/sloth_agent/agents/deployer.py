"""DeployerAgent: deploy + smoke test + auto-rollback."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field


@dataclass
class DeployResult:
    success: bool
    branch: str
    deploy_log: str = ""
    smoke_test_passed: bool = False
    smoke_test_output: str = ""
    rollback_performed: bool = False


class DeployerAgent:
    """Runs deploy script, then smoke test, then auto-rollback on failure."""

    def deploy_with_script(
        self,
        deploy_script: str,
        smoke_test_script: str,
        branch: str,
        workspace: str = ".",
    ) -> DeployResult:
        # Step 1: run deploy script
        deploy_proc = subprocess.run(
            ["bash", deploy_script],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        deploy_log = deploy_proc.stdout + deploy_proc.stderr

        if deploy_proc.returncode != 0:
            return DeployResult(
                success=False,
                branch=branch,
                deploy_log=deploy_log,
            )

        # Step 2: run smoke test
        smoke_proc = subprocess.run(
            ["bash", smoke_test_script],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        smoke_output = smoke_proc.stdout + smoke_proc.stderr
        smoke_passed = smoke_proc.returncode == 0

        if smoke_passed:
            return DeployResult(
                success=True,
                branch=branch,
                deploy_log=deploy_log,
                smoke_test_passed=True,
                smoke_test_output=smoke_output,
            )

        # Step 3: smoke test failed → auto-rollback
        rollback_log = self._rollback(workspace, branch)
        return DeployResult(
            success=False,
            branch=branch,
            deploy_log=deploy_log,
            smoke_test_passed=False,
            smoke_test_output=smoke_output,
            rollback_performed=True,
        )

    def _rollback(self, workspace: str, branch: str) -> str:
        """Reset workspace to the last committed state."""
        proc = subprocess.run(
            ["git", "checkout", "--force", branch],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        return proc.stdout + proc.stderr
