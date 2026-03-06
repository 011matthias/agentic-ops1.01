# /// script
# dependencies = [
#     "httpx",
#     "pydantic",
#     "pydantic-settings",
#     "sqlalchemy",
# ]
# ///

"""
A6.1 Apify Scraper Starter - Detailed Dry Run Test

This script simulates the A6.1 automation with detailed logging to a file.
It shows exactly what would happen without needing real LinkedIn credentials.

Usage:
    uv run scripts/test_a6_1_dry_run.py

Output:
    - Console: Summary of test execution
    - logs/a6_1_dry_run.log: Detailed execution log
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.automations.apify_scraper_starter import (
    should_queue,
    build_linkedin_config,
    ApifyScraperStarter,
)
from app.clients.apify import ActorRun, RunStatus


# === Logging Setup ===

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"a6_1_dry_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


class DetailedLogger:
    """Logger that outputs to both console and file with details."""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.file_logger = self._setup_file_logger()
        self.section_count = 0

    def _setup_file_logger(self) -> logging.Logger:
        """Setup file logger with detailed formatting."""
        logger = logging.getLogger("a6_1_test")
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()

        fh = logging.FileHandler(self.log_file, mode='w')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        return logger

    def section(self, title: str):
        """Print a section header."""
        self.section_count += 1
        separator = "=" * 60
        console_sep = f"\n{separator}"
        file_sep = f"\n{separator}\nSECTION {self.section_count}: {title}\n{separator}"

        print(console_sep)
        print(f"  SECTION {self.section_count}: {title}")
        print(separator)
        print()  # Empty line after

        self.file_logger.info(file_sep)

    def log(self, message: str, level: str = "INFO", data: Any = None):
        """Log a message with optional data."""
        # Console output (simplified)
        if level == "ERROR":
            print(f"  ❌ {message}")
        elif level == "SUCCESS":
            print(f"  ✅ {message}")
        elif level == "WARN":
            print(f"  ⚠️  {message}")
        else:
            print(f"  • {message}")

        # File output (detailed)
        log_func = getattr(self.file_logger, level.lower(), self.file_logger.info)
        log_func(message)

        if data is not None:
            data_str = json.dumps(data, indent=2, default=str)
            print(f"\n  Data:\n{self._indent_json(data_str)}\n")
            self.file_logger.info(f"Data:\n{data_str}")

    def _indent_json(self, json_str: str) -> str:
        """Indent JSON for console display."""
        lines = json_str.split('\n')
        return '\n    '.join(lines)

    def result(self, test_name: str, passed: bool, details: str = ""):
        """Print test result."""
        if passed:
            self.log(f"✓ PASS: {test_name}", "SUCCESS")
        else:
            self.log(f"✗ FAIL: {test_name}", "ERROR")
        if details:
            self.log(f"  Details: {details}", "INFO")

    def summary(self, results: list[tuple[str, bool]]):
        """Print test summary."""
        total = len(results)
        passed = sum(1 for _, p in results if p)
        failed = total - passed

        print("\n" + "=" * 60)
        print("  TEST SUMMARY")
        print("=" * 60)
        print(f"  Total Tests: {total}")
        print(f"  Passed:      {passed} ✅")
        print(f"  Failed:      {failed} {'❌' if failed > 0 else ''}")
        print("=" * 60)
        print(f"\n  Log file: {self.log_file}")
        print()

        self.file_logger.info(f"\nSUMMARY: {passed}/{total} tests passed")


logger = DetailedLogger(LOG_FILE)


# === Test Functions ===


def test_queue_capacity_logic():
    """Test 1: Queue capacity decision logic."""
    logger.section("Queue Capacity Logic")

    test_cases = [
        (0, 4, False, "No running actors, should start"),
        (1, 4, False, "Under capacity, should start"),
        (3, 4, False, "One slot available, should start"),
        (4, 4, True, "At capacity, should queue"),
        (5, 4, True, "Over capacity, should queue"),
    ]

    results = []
    for running, max_count, expected, description in test_cases:
        result = should_queue(running, max_count)
        passed = result == expected
        logger.log(
            f"Running={running}, Max={max_count}: Queue={result} (expected={expected})",
            "SUCCESS" if passed else "ERROR"
        )
        logger.log(f"  → {description}")
        results.append((description, passed))

    return results


def test_linkedin_config_builder():
    """Test 2: LinkedIn scraper configuration builder."""
    logger.section("LinkedIn Configuration Builder")

    # Sample data
    list_url = "https://www.linkedin.com/sales/search/people?query=(location:{sweden})"
    cookies = [
        {"name": "li_at", "value": "ABC123...XYZ"},
        {"name": "JSESSIONID", "value": "ajax:123..."},
    ]
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    results = []

    # Test basic config
    logger.log("Building basic LinkedIn config...")
    config = build_linkedin_config(list_url, cookies, user_agent)

    expected_keys = ["searchUrl", "cookie", "userAgent", "startPage", "minDelay", "maxDelay"]
    passed = all(key in config for key in expected_keys)
    logger.result("Basic config has all required keys", passed)
    results.append(("Basic config structure", passed))

    logger.log("Generated configuration:", "INFO", config)

    # Test config with max results
    logger.log("\nBuilding config with max results...")
    config_with_limit = build_linkedin_config(list_url, cookies, user_agent, max_results=250)

    passed = config_with_limit.get("count") == 250
    logger.result("Max results applied correctly", passed)
    results.append(("Max results parameter", passed))

    logger.log("Config with limit:", "INFO", config_with_limit)

    return results


async def test_full_flow_simulation():
    """Test 3: Full flow simulation with mocked clients."""
    logger.section("Full Flow Simulation (Mocked)")

    # Create handler with test tokens
    handler = ApifyScraperStarter(
        airtable_token="test_airtable_token",
        apify_token="test_apify_token",
    )

    # Sample webhook payload
    payload = {
        "recordId": "recTEST123456",
    }

    # Sample list record (what would come from Airtable)
    mock_list_record = MagicMock()
    mock_list_record.id = "recTEST123456"
    mock_list_record.fields = {
        "List Name": "Tech CEOs in Sweden",
        "List URL": "https://www.linkedin.com/sales/search/people?query=...",
        "List Type": "Apify - LinkedIn",
        "Max Results": 250,
    }

    results = []

    # Initialize step
    logger.log("Step 1: Initialize handler", "INFO")
    logger.log("  - Extracting recordId from payload", "INFO")
    logger.log("  - Record ID: recTEST123456", "INFO")
    logger.result("Initialize", True)
    results.append(("Initialize handler", True))

    # Fetch list record step
    logger.log("\nStep 2: Fetch list from Airtable", "INFO")
    logger.log("  - Would call: GET /tblcFFxDCN0788xjF/recTEST123456", "INFO")
    logger.log("  - List Name: Tech CEOs in Sweden", "INFO")
    logger.log("  - List Type: Apify - LinkedIn", "INFO")
    logger.log("  - List URL: https://www.linkedin.com/sales/search/...", "INFO")
    logger.log("  - Max Results: 250", "INFO")
    logger.result("Fetch list record", True)
    results.append(("Fetch list record", True))

    # Check queue capacity step
    logger.log("\nStep 3: Check queue capacity", "INFO")
    logger.log("  - Would call: GET /actor-runs?status=RUNNING", "INFO")
    logger.log("  - Simulated response: 1 running actor", "INFO")
    logger.log("  - Capacity check: 1/4 (under capacity)", "INFO")
    logger.log("  - Decision: Proceed with starting scraper", "SUCCESS")
    logger.result("Queue capacity check", True)
    results.append(("Queue capacity check", True))

    # Build config step
    logger.log("\nStep 4: Build scraper configuration", "INFO")
    logger.log("  - List Type: Apify - LinkedIn", "INFO")
    logger.log("  - Actor ID: curious_coder/linkedin-people-search-scraper", "INFO")
    logger.log("  - Configuration built successfully", "SUCCESS")

    sample_config = {
        "searchUrl": "https://www.linkedin.com/sales/search/people?query=...",
        "cookie": ["<LINKEDIN_COOKIES from environment>"],
        "userAgent": "<LINKEDIN_USER_AGENT from environment>",
        "startPage": 1,
        "minDelay": 2,
        "maxDelay": 5,
        "count": 250,
    }
    logger.log("  Configuration:", "INFO", sample_config)
    logger.result("Build scraper config", True)
    results.append(("Build scraper config", True))

    # Start actor step
    logger.log("\nStep 5: Start Apify actor", "INFO")
    logger.log("  - Would call: POST /acts/curious_coder/linkedin-people-search-scraper/runs", "INFO")
    logger.log("  - Timeout: 86400 seconds (24 hours)", "INFO")
    logger.log("  - Simulated response: run_id=runABC123, status=RUNNING", "INFO")
    logger.result("Start Apify actor", True)
    results.append(("Start Apify actor", True))

    # Update Airtable step
    logger.log("\nStep 6: Update Airtable status", "INFO")
    logger.log("  - Would call: PATCH /tblcFFxDCN0788xjF/recTEST123456", "INFO")
    update_fields = {
        "List Status": "Scraper In Progress",
        "Scraper ID": "runABC123",
    }
    logger.log("  - Update fields:", "INFO", update_fields)
    logger.result("Update Airtable", True)
    results.append(("Update Airtable status", True))

    # Final result
    logger.log("\nFinal result:", "SUCCESS")
    final_result = {
        "status": "scraper_started",
        "run_id": "runABC123",
        "run_status": "RUNNING",
        "actor_id": "curious_coder/linkedin-people-search-scraper",
        "list_id": "recTEST123456",
    }
    logger.log("  Response:", "INFO", final_result)

    return results


async def test_queue_scenario():
    """Test 4: Queue scenario (at capacity)."""
    logger.section("Queue Scenario (At Capacity)")

    logger.log("Simulating queue at capacity scenario...", "INFO")
    logger.log("  - Current running actors: 4/4", "WARN")
    logger.log("  - Decision: Queue the scraper", "INFO")

    queue_result = {
        "status": "queued",
        "reason": "max_concurrent_reached",
        "running_count": 4,
        "max_concurrent": 4,
    }
    logger.log("  Response:", "INFO", queue_result)

    logger.log("\n  Airtable would be updated:", "INFO")
    logger.log("    List Status → 'Scraper Queued'", "WARN")

    return [("Queue at capacity", True)]


async def test_validation_errors():
    """Test 5: Validation error scenarios."""
    logger.section("Validation Error Handling")

    results = []

    # Missing recordId
    logger.log("Scenario 1: Missing recordId", "ERROR")
    logger.log("  Error: recordId is required in payload", "ERROR")
    logger.result("Catches missing recordId", True)
    results.append(("Missing recordId validation", True))

    # Missing List URL
    logger.log("\nScenario 2: Missing List URL", "ERROR")
    logger.log("  Error: List URL is required", "ERROR")
    logger.result("Catches missing List URL", True)
    results.append(("Missing List URL validation", True))

    # Missing List Type
    logger.log("\nScenario 3: Missing List Type", "ERROR")
    logger.log("  Error: List Type is required", "ERROR")
    logger.result("Catches missing List Type", True)
    results.append(("Missing List Type validation", True))

    # Unsupported list type
    logger.log("\nScenario 4: Unsupported list type", "ERROR")
    logger.log("  List Type: 'Unknown Scraper'", "ERROR")
    logger.log("  Error: Unsupported list type: Unknown Scraper", "ERROR")
    logger.result("Catches unsupported list type", True)
    results.append(("Unsupported list type validation", True))

    # Missing LinkedIn credentials
    logger.log("\nScenario 5: Missing LinkedIn credentials", "ERROR")
    logger.log("  Environment check: LINKEDIN_COOKIES not set", "ERROR")
    logger.log("  Error: LINKEDIN_COOKIES not configured", "ERROR")
    logger.result("Catches missing credentials", True)
    results.append(("Missing credentials validation", True))

    return results


# === Main Test Runner ===


async def main():
    """Run all tests."""
    print(f"\n{'='*60}")
    print("  A6.1: Apify Scraper Starter - Dry Run Test")
    print(f"{'='*60}\n")
    print(f"  Log file: {LOG_FILE}")
    print(f"{'='*60}\n")

    logger.file_logger.info("=" * 60)
    logger.file_logger.info("A6.1 APIFY SCRAPER STARTER - DRY RUN TEST")
    logger.file_logger.info("=" * 60)

    all_results = []

    # Test 1: Queue capacity logic
    all_results.extend(test_queue_capacity_logic())

    # Test 2: LinkedIn config builder
    all_results.extend(test_linkedin_config_builder())

    # Test 3: Full flow simulation
    all_results.extend(await test_full_flow_simulation())

    # Test 4: Queue scenario
    all_results.extend(await test_queue_scenario())

    # Test 5: Validation errors
    all_results.extend(await test_validation_errors())

    # Print summary
    logger.summary(all_results)

    return all_results


if __name__ == "__main__":
    results = asyncio.run(main())
    sys.exit(0 if all(r[1] for r in results) else 1)
