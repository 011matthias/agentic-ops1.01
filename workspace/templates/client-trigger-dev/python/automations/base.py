"""
Base automation class for Trigger.dev projects.

Logs to stderr (captured by Trigger.dev). Outputs JSON result to stdout
(parsed by the TypeScript task wrapper).

All automations should extend this class for consistent
step logging and error handling.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import sys
import uuid
import logging

# Configure logging to stderr so it doesn't interfere with stdout JSON output
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class Step:
    """Individual step within an automation execution."""
    name: str
    status: str  # "running" | "success" | "failed"
    started_at: str
    ended_at: Optional[str] = None
    duration_ms: Optional[int] = None
    output_summary: Optional[str] = None
    error: Optional[str] = None


class ExecutionLogger:
    """
    Logs automation execution to stderr with step-level detail.

    Trigger.dev captures stderr output automatically. The final result
    is printed to stdout as JSON for the TypeScript wrapper to parse.
    """

    def __init__(self, automation_id: str, trigger: str = "trigger-dev"):
        self.automation_id = automation_id
        self.trigger = trigger
        self.run_id = str(uuid.uuid4())
        self.steps: list[Step] = []
        self.started_at = datetime.utcnow()
        self._current_step: Optional[Step] = None

    def step(self, name: str):
        """Context manager for step execution with automatic timing."""
        return _StepContext(self, name)

    def log_output(self, summary: str):
        """Add output summary to current step."""
        if self._current_step:
            self._current_step.output_summary = summary

    def finalize(self, status: str, error: Optional[str] = None):
        """Log final execution summary to stderr."""
        ended_at = datetime.utcnow()
        duration_ms = int((ended_at - self.started_at).total_seconds() * 1000)

        summary = {
            "run_id": self.run_id,
            "automation_id": self.automation_id,
            "trigger": self.trigger,
            "status": status,
            "duration_ms": duration_ms,
            "steps": [asdict(s) for s in self.steps],
        }
        if error:
            summary["error"] = error

        # Log structured summary to stderr
        print(json.dumps(summary), file=sys.stderr)
        logger.info(f"[{self.automation_id}] Execution {status} ({duration_ms}ms)")


class _StepContext:
    """Context manager for step execution."""

    def __init__(self, exec_logger: ExecutionLogger, name: str):
        self._logger = exec_logger
        self._name = name
        self._step: Optional[Step] = None

    def __enter__(self):
        self._step = Step(
            name=self._name,
            status="running",
            started_at=datetime.utcnow().isoformat(),
        )
        self._logger.steps.append(self._step)
        self._logger._current_step = self._step
        self._start = datetime.utcnow()
        logger.info(f"[{self._logger.automation_id}] Step started: {self._name}")
        return self._step

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._step is None:
            return False

        if exc_type is not None:
            self._step.status = "failed"
            self._step.error = str(exc_val)
            logger.error(f"[{self._logger.automation_id}] Step failed: {self._name} - {exc_val}")
        else:
            self._step.status = "success"
            logger.info(f"[{self._logger.automation_id}] Step completed: {self._name}")

        self._step.ended_at = datetime.utcnow().isoformat()
        self._step.duration_ms = int((datetime.utcnow() - self._start).total_seconds() * 1000)
        self._logger._current_step = None
        return False


class BaseAutomation(ABC):
    """
    Base class for all automations in Trigger.dev projects.

    Provides:
    - Automatic step logging (to stderr, captured by Trigger.dev)
    - Error handling
    - Dry run support

    Subclasses implement the abstract methods:
    - initialize(): Setup, validate config
    - fetch_data(): Get data from source systems
    - transform(data): Process/transform data
    - execute(data): Send to destination systems
    - finalize(result): Cleanup, notifications
    """

    automation_id: str = "base"  # Override in subclass

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def fetch_data(self) -> Any:
        pass

    @abstractmethod
    def transform(self, data: Any) -> Any:
        pass

    @abstractmethod
    def execute(self, data: Any) -> Any:
        pass

    @abstractmethod
    def finalize(self, result: Any) -> None:
        pass

    def run(self, trigger: str = "trigger-dev", dry_run: bool = False,
            limit: int | None = None, record_ids: list[str] | None = None) -> Any:
        """
        Run the automation with full logging.

        Returns:
            Result dict (serializable to JSON for Trigger.dev)
        """
        self._limit = limit
        self._record_ids = record_ids or []

        exec_logger = ExecutionLogger(self.automation_id, trigger=trigger)
        logger.info(f"Starting automation: {self.automation_id} (dry_run={dry_run})")

        try:
            with exec_logger.step("Initialize"):
                self.initialize()

            with exec_logger.step("Fetch data") as step:
                data = self.fetch_data()
                step.output_summary = self._summarize_data(data)

            with exec_logger.step("Transform") as step:
                transformed = self.transform(data)
                step.output_summary = self._summarize_data(transformed)

            with exec_logger.step("Execute") as step:
                if dry_run:
                    result = {"dry_run": True, "would_process": self._count_items(transformed)}
                    step.output_summary = f"Dry run: would process {result['would_process']} items"
                else:
                    result = self.execute(transformed)
                    step.output_summary = self._summarize_result(result)

            with exec_logger.step("Finalize"):
                self.finalize(result)

            exec_logger.finalize("success")
            return result

        except Exception as e:
            logger.error(f"Automation failed: {self.automation_id} - {e}")
            exec_logger.finalize("failed", error=str(e))
            raise

    def _summarize_data(self, data: Any) -> str:
        if isinstance(data, list):
            return f"Found {len(data)} items"
        elif isinstance(data, dict):
            return f"Data with {len(data)} keys"
        return str(data)[:100]

    def _summarize_result(self, result: Any) -> str:
        if isinstance(result, list):
            return f"Processed {len(result)} items"
        elif isinstance(result, dict):
            if "count" in result:
                return f"Processed {result['count']} items"
            return f"Result with {len(result)} keys"
        return str(result)[:100]

    def _count_items(self, data: Any) -> int:
        if isinstance(data, list):
            return len(data)
        return 1
