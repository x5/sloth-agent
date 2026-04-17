"""Tests for DeployerAgent (plan Task 16)."""

import os
from sloth_agent.agents.deployer import DeployerAgent, DeployResult

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_deployer_basic():
    agent = DeployerAgent()
    assert agent is not None


def test_deploy_with_script_and_smoke_pass():
    """有部署脚本 + smoke test 通过 → success=True。"""
    agent = DeployerAgent()
    result = agent.deploy_with_script(
        deploy_script=os.path.join(FIXTURES, "deploy_pass.sh"),
        smoke_test_script=os.path.join(FIXTURES, "smoke_pass.sh"),
        branch="test-branch",
    )
    assert result.success is True
    assert result.smoke_test_passed is True
    assert result.branch == "test-branch"


def test_deploy_smoke_fail_triggers_rollback():
    """有部署脚本 + smoke test 失败 → success=False + rollback。"""
    agent = DeployerAgent()
    result = agent.deploy_with_script(
        deploy_script=os.path.join(FIXTURES, "deploy_pass.sh"),
        smoke_test_script=os.path.join(FIXTURES, "smoke_fail.sh"),
        branch="test-branch",
    )
    assert result.success is False
    assert result.smoke_test_passed is False
    assert result.rollback_performed is True
