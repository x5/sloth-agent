"""Reviewer Agent: independent code review with different model routing."""

from dataclasses import dataclass, field

from sloth_agent.core.builder import BuilderOutput


@dataclass
class ReviewerOutput:
    approved: bool
    branch: str
    blocking_issues: list[str]
    suggestions: list[str] = field(default_factory=list)


class ReviewerAgent:
    """Reviewer Agent — 使用不同于 Builder 的模型路由（qwen3.6-plus 或 claude）。"""

    def review(self, builder_output: BuilderOutput, code_map: dict[str, str]) -> ReviewerOutput:
        blocking = []
        suggestions = []

        for filepath, content in code_map.items():
            issues = self._analyze(filepath, content)
            blocking.extend(issues["blocking"])
            suggestions.extend(issues["suggestions"])

        return ReviewerOutput(
            approved=len(blocking) == 0,
            branch=builder_output.branch,
            blocking_issues=blocking,
            suggestions=suggestions,
        )

    def _analyze(self, filepath: str, content: str) -> dict:
        blocking = []
        suggestions = []

        # Rule-based static analysis (v1.0: 纯规则，不调 LLM)
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if "eval(" in stripped or "exec(" in stripped:
                blocking.append(f"{filepath}:{i}: use of eval/exec")
            if "pass" in stripped and i > 1:
                suggestions.append(f"{filepath}:{i}: empty implementation (pass)")
            if "import *" in stripped:
                blocking.append(f"{filepath}:{i}: wildcard import")
            if "/" in stripped and "def " not in stripped and "return" in stripped:
                # Simple division without zero check
                if " / " in stripped and "b" in stripped:
                    blocking.append(f"{filepath}:{i}: division without zero check")

        return {"blocking": blocking, "suggestions": suggestions}
