"""
Daily cron job - triggers daily automations.

Railway cron schedule: 0 7 * * * (07:00 UTC = 08:00 CET)

This script calls the main service's /run endpoint to trigger automations.
"""

import httpx
import os
import sys

SERVICE_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN")
INTERNAL_KEY = os.getenv("INTERNAL_API_KEY")


def trigger_automation(automation_id: str) -> bool:
    """Trigger an automation via the internal API."""
    if not SERVICE_URL:
        print("ERROR: RAILWAY_PUBLIC_DOMAIN not set")
        return False

    url = f"https://{SERVICE_URL}/run/{automation_id}"
    headers = {"X-Internal-Key": INTERNAL_KEY or ""}

    try:
        response = httpx.post(url, headers=headers, timeout=30)
        if response.status_code == 200:
            print(f"SUCCESS: Triggered {automation_id}")
            return True
        else:
            print(f"ERROR: {automation_id} returned {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR: Failed to trigger {automation_id}: {e}")
        return False


def main():
    """Run all daily automations."""
    print("Starting daily cron job...")

    # Add your daily automations here:
    automations = [
        # "a1_recurring_orders",
        "example",  # Example automation for testing
    ]

    results = []
    for automation_id in automations:
        success = trigger_automation(automation_id)
        results.append((automation_id, success))

    # Summary
    print("\n=== Daily Cron Summary ===")
    for automation_id, success in results:
        status = "OK" if success else "FAILED"
        print(f"  {automation_id}: {status}")

    # Exit with error if any failed
    if not all(success for _, success in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
