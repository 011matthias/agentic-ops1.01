"""
Base automation class with built-in logging.

All automations should extend this class for consistent
step logging and error handling.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
import logging

from ..logger import ExecutionLogger
from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class BaseAutomation(ABC):
    """
    Base class for all automations.

    Provides:
    - Automatic step logging
    - Error handling with self-healing trigger
    - Dry run support

    Subclasses implement the abstract methods:
    - initialize(): Setup, validate config
    - fetch_data(): Get data from source systems
    - transform(data): Process/transform data
    - execute(data): Send to destination systems
    - finalize(result): Cleanup, notifications

    Example:
        class MyAutomation(BaseAutomation):
            automation_id = "my_automation"

            def initialize(self):
                self.api_client = SomeClient()

            def fetch_data(self):
                return self.api_client.get_items()

            def transform(self, data):
                return [transform_item(item) for item in data]

            def execute(self, data):
                return self.api_client.create_items(data)

            def finalize(self, result):
                send_notification(f"Created {len(result)} items")
    """

    automation_id: str = "base"  # Override in subclass

    @abstractmethod
    def initialize(self) -> None:
        """Initialize resources, validate configuration."""
        pass

    @abstractmethod
    def fetch_data(self) -> Any:
        """Fetch data from source systems."""
        pass

    @abstractmethod
    def transform(self, data: Any) -> Any:
        """Transform data for destination."""
        pass

    @abstractmethod
    def execute(self, data: Any) -> Any:
        """Execute the main automation logic."""
        pass

    @abstractmethod
    def finalize(self, result: Any) -> None:
        """Cleanup and send notifications."""
        pass

    def run(self, trigger: str = "manual", dry_run: bool = False) -> Any:
        """
        Run the automation with full logging.

        Args:
            trigger: How this run was triggered (cron, webhook, manual)
            dry_run: If True, skip actual execution

        Returns:
            Result from execute() or finalize()
        """
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
            logger.info(f"Automation completed successfully: {self.automation_id}")
            return result

        except Exception as e:
            logger.error(f"Automation failed: {self.automation_id} - {e}")
            exec_logger.finalize("failed", error=str(e))
            raise

    def _summarize_data(self, data: Any) -> str:
        """Generate summary of data for logging."""
        if isinstance(data, list):
            return f"Found {len(data)} items"
        elif isinstance(data, dict):
            return f"Data with {len(data)} keys"
        return str(data)[:100]

    def _summarize_result(self, result: Any) -> str:
        """Generate summary of result for logging."""
        if isinstance(result, list):
            return f"Processed {len(result)} items"
        elif isinstance(result, dict):
            if "count" in result:
                return f"Processed {result['count']} items"
            return f"Result with {len(result)} keys"
        return str(result)[:100]

    def _count_items(self, data: Any) -> int:
        """Count items for dry run summary."""
        if isinstance(data, list):
            return len(data)
        return 1
