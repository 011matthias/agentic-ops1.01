# /// script
# dependencies = [
#     "httpx",
#     "pydantic",
#     "pydantic-settings",
# ]
# ///
"""
A6.4 Data Cleaning - Real Data Test

This script connects to the actual Airtable and tests the automation
with real data in dry-run mode.

Usage:
    cd clients/herbox-sweden/automations
    uv run scripts/test_a6_4_real_data.py

    # Or with live mode (actually cleans data):
    uv run scripts/test_a6_4_real_data.py --live

Requirements:
    - AIRTABLE_TOKEN set in environment
    - AIRTABLE_BASE_ID set in environment
    - OPENROUTER_API_KEY set in environment (for live mode)
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.automations.data_cleaning import run_data_cleaning
from app.config import get_settings

settings = get_settings()


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def print_result(label: str, value: Any, status: str = "INFO"):
    """Print a result line."""
    icon = {
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARN": "⚠️ ",
        "INFO": "•",
    }.get(status, "•")
    print(f"  {icon} {label}: {value}")


async def main():
    """Run the real data test."""
    print_section("A6.4: Lead Data Cleaning - Real Data Test")
    print(f"\n  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check environment variables
    print_section("Environment Check")

    env_ok = True

    if settings.airtable_token:
        print_result("AIRTABLE_TOKEN", "✓ Set", "SUCCESS")
    else:
        print_result("AIRTABLE_TOKEN", "✗ Not set", "ERROR")
        env_ok = False

    if settings.airtable_base_id:
        print_result("AIRTABLE_BASE_ID", settings.airtable_base_id, "SUCCESS")
    else:
        print_result("AIRTABLE_BASE_ID", "✗ Not set", "ERROR")
        env_ok = False

    if settings.openrouter_api:
        print_result("OPENROUTER_API_KEY", "✓ Set", "SUCCESS")
    else:
        print_result("OPENROUTER_API_KEY", "✗ Not set", "WARN")
        print_result("Note", "Required for live mode only", "INFO")

    if not env_ok:
        print("\n❌ Required environment variables not set. Exiting.")
        sys.exit(1)

    # Parse arguments
    live_mode = "--live" in sys.argv
    dry_run = not live_mode

    print_section("Test Configuration")
    print_result("Mode", "LIVE (will modify data)" if live_mode else "DRY RUN (no modifications)", "WARN" if live_mode else "INFO")

    # Airtable configuration
    print("\n  Airtable Configuration:")
    print_result("Base ID", settings.airtable_base_id, "INFO")
    print_result("Accounts Table", "tblIJVWxf1QbpowuS", "INFO")
    print_result("Contacts Table", "tblsI8jeqv1B16MTk", "INFO")

    # GPT configuration
    print("\n  GPT Configuration:")
    print_result("Model", "openai/gpt-4o-mini (via OpenRouter)", "INFO")
    print_result("Temperature", "0", "INFO")

    if live_mode and not settings.openrouter_api:
        print("\n❌ OPENROUTER_API_KEY required for live mode. Exiting.")
        sys.exit(1)

    # Run the automation
    print_section("Running Automation")

    try:
        result = await run_data_cleaning(
            dry_run=dry_run,
            openrouter_api_key=settings.openrouter_api,
            airtable_token=settings.airtable_token,
        )

        # Display results
        print_section("Results")

        print("\n  Accounts:")
        print_result("Found", result.get("accounts_found", 0), "INFO")
        print_result("Cleaned", result.get("accounts_cleaned", 0), "SUCCESS")
        print_result("Failed", result.get("accounts_failed", 0), "ERROR" if result.get("accounts_failed", 0) > 0 else "INFO")

        print("\n  Contacts:")
        print_result("Found", result.get("contacts_found", 0), "INFO")
        print_result("Cleaned", result.get("contacts_cleaned", 0), "SUCCESS")
        print_result("Failed", result.get("contacts_failed", 0), "ERROR" if result.get("contacts_failed", 0) > 0 else "INFO")

        # Show samples
        if result.get("cleaned_accounts"):
            print("\n  Sample Cleaned Accounts:")
            for acc in result.get("cleaned_accounts", [])[:3]:
                print_result("Original", acc.get("original", "N/A"), "INFO")
                print_result("Cleaned", acc.get("cleaned", "N/A"), "SUCCESS")
                print()

        if result.get("cleaned_contacts"):
            print("  Sample Cleaned Contacts:")
            for con in result.get("cleaned_contacts", [])[:3]:
                print_result("Original", con.get("original", "N/A"), "INFO")
                print_result("Dutch", con.get("dutch", "N/A"), "SUCCESS")
                print()

        # Show failures if any
        if result.get("failed_accounts"):
            print_section("Failed Accounts")
            for fail in result.get("failed_accounts", [])[:5]:
                print_result("Record ID", fail.get("id", "N/A"), "ERROR")
                print_result("Error", fail.get("error", "Unknown"), "ERROR")
                print()

        if result.get("failed_contacts"):
            print_section("Failed Contacts")
            for fail in result.get("failed_contacts", [])[:5]:
                print_result("Record ID", fail.get("id", "N/A"), "ERROR")
                print_result("Error", fail.get("error", "Unknown"), "ERROR")
                print()

        # Cost estimation
        print_section("Cost Estimation")

        total_requests = result.get("accounts_cleaned", 0) + result.get("contacts_cleaned", 0)
        if total_requests > 0:
            # gpt-4o-mini pricing (approximate)
            cost_per_request = 0.00003  # ~$0.03 per 1000 requests
            estimated_cost = total_requests * cost_per_request

            print_result("Total GPT calls", total_requests, "INFO")
            print_result("Estimated cost", f"${estimated_cost:.4f}", "INFO")
            print_result("Cost per request", f"${cost_per_request:.6f}", "INFO")
        else:
            print_result("Total GPT calls", 0, "INFO")
            print_result("Estimated cost", "$0.00", "INFO")

        # Final status
        print_section("Status")

        total_failed = result.get("accounts_failed", 0) + result.get("contacts_failed", 0)
        total_processed = result.get("accounts_cleaned", 0) + result.get("contacts_cleaned", 0)

        if total_failed > 0:
            print_result("Status", f"Completed with {total_failed} failures", "WARN")
        elif total_processed > 0:
            print_result("Status", "Completed successfully", "SUCCESS")
        else:
            print_result("Status", "No data to process", "INFO")

        print(f"\n  Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return 0 if total_failed == 0 else 1

    except Exception as e:
        print_section("Error")
        print_result("Error", str(e), "ERROR")
        import traceback
        print("\n  Traceback:")
        print("  " + "\n  ".join(traceback.format_exc().split("\n")))
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
