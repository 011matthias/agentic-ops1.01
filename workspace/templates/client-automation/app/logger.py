"""
Execution logger with step-level tracking.

Logs to local database and triggers self-healing on failures.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, Any
from contextlib import contextmanager
import uuid
import httpx
import logging

from .db import SessionLocal, ExecutionLog
from .config import get_settings

settings = get_settings()
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
    Logs automation execution to local database with step-level detail.

    Usage:
        logger = ExecutionLogger("a1_recurring_orders", trigger="cron")

        with logger.step("Fetch contracts") as step:
            contracts = fetch_contracts()
            step.output_summary = f"Found {len(contracts)} contracts"

        with logger.step("Create orders") as step:
            created = create_orders(contracts)
            step.output_summary = f"Created {len(created)} orders"

        logger.finalize("success")
    """

    def __init__(self, automation_id: str, trigger: str = "manual"):
        self.automation_id = automation_id
        self.trigger = trigger
        self.run_id = str(uuid.uuid4())
        self.steps: list[Step] = []
        self.started_at = datetime.utcnow()
        self._current_step: Optional[Step] = None

    @contextmanager
    def step(self, name: str):
        """Context manager for step execution with automatic timing."""
        step = Step(
            name=name,
            status="running",
            started_at=datetime.utcnow().isoformat()
        )
        self.steps.append(step)
        self._current_step = step
        start = datetime.utcnow()

        logger.info(f"[{self.automation_id}] Step started: {name}")

        try:
            yield step
            step.status = "success"
            logger.info(f"[{self.automation_id}] Step completed: {name}")
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            logger.error(f"[{self.automation_id}] Step failed: {name} - {e}")
            raise
        finally:
            step.ended_at = datetime.utcnow().isoformat()
            step.duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
            self._current_step = None

    def log_output(self, summary: str):
        """Add output summary to current step."""
        if self._current_step:
            self._current_step.output_summary = summary

    def finalize(self, status: str, error: Optional[str] = None, resolution: Optional[str] = None):
        """Save execution log to database."""
        ended_at = datetime.utcnow()
        duration_ms = int((ended_at - self.started_at).total_seconds() * 1000)

        db = SessionLocal()
        try:
            log = ExecutionLog(
                run_id=self.run_id,
                automation_id=self.automation_id,
                trigger=self.trigger,
                status=status,
                started_at=self.started_at,
                ended_at=ended_at,
                duration_ms=duration_ms,
                steps=[asdict(s) for s in self.steps],
                error=error,
                resolution=resolution
            )
            db.add(log)
            db.commit()
            logger.info(f"[{self.automation_id}] Execution logged: {status} ({duration_ms}ms)")
        except Exception as e:
            logger.error(f"Failed to save execution log: {e}")
        finally:
            db.close()

        # Trigger self-healing on failure
        if status == "failed":
            self._trigger_self_healing(error)

    def _trigger_self_healing(self, error: Optional[str]):
        """POST to self-healing webhook if configured."""
        webhook_url = settings.self_healing_webhook
        if not webhook_url:
            logger.info("Self-healing webhook not configured, skipping")
            return

        try:
            httpx.post(
                webhook_url,
                json={
                    "client_id": settings.client_id,
                    "automation_id": self.automation_id,
                    "run_id": self.run_id,
                    "error": error,
                    "steps": [asdict(s) for s in self.steps]
                },
                timeout=30
            )
            logger.info(f"Self-healing webhook triggered for {self.automation_id}")
        except Exception as e:
            logger.error(f"Failed to trigger self-healing: {e}")
