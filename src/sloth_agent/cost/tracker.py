"""CostTracker — record LLM calls, track budget, persist to filesystem."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sloth_agent.cost.models import CostBreakdown, CostRecord, BudgetStatus
from sloth_agent.cost.pricing import calculate_cost, get_pricing, get_budget_defaults


class CostTracker:
    """Cost tracker for LLM calls.

    Persists records to JSONL files under <storage_dir>/cost/.
    Tracks daily and per-scenario totals.
    """

    def __init__(
        self,
        storage_dir: Path | str | None = None,
        pricing_path: Path | str | None = None,
    ):
        self._storage = Path(storage_dir) if storage_dir else Path.cwd() / ".sloth" / "cost"
        self._storage.mkdir(parents=True, exist_ok=True)

        self.pricing = get_pricing(pricing_path)
        self.budget = get_budget_defaults(pricing_path)
        self.records: list[CostRecord] = []

        # In-memory accumulators
        self.daily_total: float = 0.0
        self.scenario_totals: dict[str, float] = {}

        # Load existing records from today
        self._load_today()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_call(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        scenario_id: str | None = None,
        phase_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
    ) -> CostRecord:
        """Record one LLM call's cost."""
        input_cost, output_cost = calculate_cost(
            model, provider, input_tokens, output_tokens, self.pricing
        )
        total_cost = input_cost + output_cost

        record = CostRecord(
            timestamp=time.time(),
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            scenario_id=scenario_id,
            phase_id=phase_id,
            agent_id=agent_id,
            run_id=run_id,
            call_id=uuid.uuid4().hex[:12],
        )

        self.records.append(record)
        self.daily_total += total_cost

        if scenario_id:
            self.scenario_totals[scenario_id] = (
                self.scenario_totals.get(scenario_id, 0.0) + total_cost
            )

        self._append_record(record)
        return record

    # ------------------------------------------------------------------
    # Budget checks
    # ------------------------------------------------------------------

    def check_budget(self, scope: str = "daily") -> BudgetStatus:
        """Check budget usage for the given scope."""
        if scope == "daily":
            limit = self.budget["daily_limit"]
            used = self.daily_total
        elif scope == "scenario":
            return self._check_all_scenarios()
        else:
            raise ValueError(f"Unknown budget scope: {scope}")

        used_percent = used / limit if limit > 0 else 0.0
        soft_limit = limit * self.budget["soft_limit_percent"]
        hard_limit = limit * self.budget["hard_limit_percent"]

        if used >= hard_limit:
            return BudgetStatus(
                scope=scope, limit=limit, used=used,
                remaining=max(0.0, limit - used),
                used_percent=used_percent,
                status="hard_exceeded", action="stop_all",
            )
        elif used >= soft_limit:
            return BudgetStatus(
                scope=scope, limit=limit, used=used,
                remaining=max(0.0, limit - used),
                used_percent=used_percent,
                status="soft_limit_reached", action="degrade",
            )
        else:
            return BudgetStatus(
                scope=scope, limit=limit, used=used,
                remaining=limit - used,
                used_percent=used_percent,
                status="ok", action="continue",
            )

    def _check_all_scenarios(self) -> BudgetStatus:
        """Return the worst-case scenario budget status."""
        limit = self.budget["scenario_limit"]
        worst = BudgetStatus(
            scope="scenario", limit=limit, used=0.0,
            remaining=limit, used_percent=0.0,
            status="ok", action="continue",
        )
        for sid, used in self.scenario_totals.items():
            used_percent = used / limit if limit > 0 else 0.0
            if used >= limit:
                return BudgetStatus(
                    scope=f"scenario:{sid}", limit=limit, used=used,
                    remaining=0.0, used_percent=used_percent,
                    status="hard_exceeded", action="stop_all",
                )
            elif used >= limit * self.budget["soft_limit_percent"]:
                if worst.status == "ok":
                    worst = BudgetStatus(
                        scope=f"scenario:{sid}", limit=limit, used=used,
                        remaining=limit - used, used_percent=used_percent,
                        status="soft_limit_reached", action="degrade",
                    )
        return worst

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_daily_cost(self, date: str | None = None) -> float:
        """Get total cost for a given date (YYYY-MM-DD). Defaults to today."""
        if date is None:
            return self.daily_total
        return sum(
            r.total_cost for r in self.records
            if self._ts_to_date(r.timestamp) == date
        )

    def get_daily_tokens(self, date: str | None = None) -> int:
        """Get total tokens for a given date (YYYY-MM-DD). Defaults to today."""
        today = date or self._today_str()
        return sum(
            r.input_tokens + r.output_tokens for r in self.records
            if self._ts_to_date(r.timestamp) == today
        )

    def get_cost_by_model(self) -> dict[str, float]:
        """Aggregate cost by model."""
        by_model: dict[str, float] = {}
        for r in self.records:
            by_model[r.model] = by_model.get(r.model, 0.0) + r.total_cost
        return by_model

    def get_cost_by_provider(self) -> dict[str, float]:
        """Aggregate cost by provider."""
        by_provider: dict[str, float] = {}
        for r in self.records:
            by_provider[r.provider] = by_provider.get(r.provider, 0.0) + r.total_cost
        return by_provider

    def forecast_daily_cost(self, current_hour: int | None = None) -> float:
        """Linear extrapolation of today's cost to 24h."""
        if current_hour is None:
            current_hour = datetime.now().hour
        if current_hour == 0:
            return self.daily_total
        hourly_rate = self.daily_total / current_hour
        return hourly_rate * 24

    def get_breakdown(self) -> CostBreakdown:
        """Full cost breakdown."""
        by_provider: dict[str, float] = {}
        by_scenario: dict[str, float] = {}
        by_model: dict[str, float] = {}
        total_tokens = 0

        for r in self.records:
            by_provider[r.provider] = by_provider.get(r.provider, 0.0) + r.total_cost
            sid = r.scenario_id or "unknown"
            by_scenario[sid] = by_scenario.get(sid, 0.0) + r.total_cost
            by_model[r.model] = by_model.get(r.model, 0.0) + r.total_cost
            total_tokens += r.input_tokens + r.output_tokens

        return CostBreakdown(
            total=sum(by_provider.values()),
            by_provider=by_provider,
            by_scenario=by_scenario,
            by_model=by_model,
            total_tokens=total_tokens,
            total_calls=len(self.records),
        )

    def get_total_cost(self) -> float:
        """Total cost across all records."""
        return sum(r.total_cost for r in self.records)

    def get_usage_by_model(self) -> dict[str, dict[str, int | float]]:
        """Usage stats per model."""
        usage: dict[str, dict[str, int | float]] = {}
        for r in self.records:
            if r.model not in usage:
                usage[r.model] = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0, "calls": 0}
            usage[r.model]["input_tokens"] += r.input_tokens  # type: ignore
            usage[r.model]["output_tokens"] += r.output_tokens  # type: ignore
            usage[r.model]["cost"] += r.total_cost  # type: ignore
            usage[r.model]["calls"] += 1  # type: ignore
        return usage

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_today(self) -> None:
        """Load today's records from JSONL."""
        path = self._today_file()
        if not path.exists():
            return

        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            self.records.append(CostRecord(**data))
            self.daily_total += self.records[-1].total_cost
            if self.records[-1].scenario_id:
                sid = self.records[-1].scenario_id
                self.scenario_totals[sid] = (
                    self.scenario_totals.get(sid, 0.0) + self.records[-1].total_cost
                )

    def _append_record(self, record: CostRecord) -> None:
        """Append one record to today's JSONL file."""
        path = self._today_file()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(self._record_to_dict(record)) + "\n")

    def _today_file(self) -> Path:
        """Path to today's JSONL file."""
        return self._storage / f"{self._today_str()}.jsonl"

    @staticmethod
    def _today_str() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def _ts_to_date(ts: float) -> str:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

    @staticmethod
    def _record_to_dict(r: CostRecord) -> dict:
        return {
            "timestamp": r.timestamp,
            "provider": r.provider,
            "model": r.model,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "input_cost": r.input_cost,
            "output_cost": r.output_cost,
            "total_cost": r.total_cost,
            "scenario_id": r.scenario_id,
            "phase_id": r.phase_id,
            "agent_id": r.agent_id,
            "run_id": r.run_id,
            "call_id": r.call_id,
        }
