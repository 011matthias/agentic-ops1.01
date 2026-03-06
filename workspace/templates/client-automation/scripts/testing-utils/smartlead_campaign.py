#!/usr/bin/env python3
"""
Smartlead Campaign Testing Utility

Provides helper functions for testing Smartlead campaigns.

Usage:
    # Create a new campaign
    uv run python scripts/testing-utils/smartlead_campaign.py create \\
        --name "My Campaign" --timezone "America/New_York"

    # Add leads to an existing campaign
    uv run python scripts/testing-utils/smartlead_campaign.py add-leads \\
        --campaign-id 123456 \\
        --leads-file leads.json

    # Create test leads
    uv run python scripts/testing-utils/smartlead_campaign.py create-test-leads \\
        --count 10 \\
        --output leads.json

    # Get campaign statistics
    uv run python scripts/testing-utils/smartlead_campaign.py stats \\
        --campaign-id 123456
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.0.0",
#     "httpx>=0.25.0",
# ]
# ///

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field


# --- Models ---


class Lead(BaseModel):
    """A lead for Smartlead campaign."""

    email: str = Field(..., description="Lead email address")
    first_name: str | None = Field(None, description="First name")
    last_name: str | None = Field(None, description="Last name")
    company_name: str | None = Field(None, description="Company name")


class AddLeadsRequest(BaseModel):
    """Request to add leads to a campaign."""

    lead_list: list[Lead] = Field(..., description="List of leads to add")


# --- Client ---


class SmartleadTestClient:
    """Simple client for testing Smartlead operations."""

    def __init__(self, api_key: str, base_url: str = "https://server.smartlead.ai"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)

    def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Make a request to Smartlead API."""
        url = f"{self.base_url}/api/v1{endpoint}"
        params = kwargs.get("params", {})
        params["api_key"] = self.api_key

        response = self.client.request(method, url, params=params, **kwargs)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"API Error: {e.response.status_code}", file=sys.stderr)
            print(f"Response: {e.response.text}", file=sys.stderr)
            sys.exit(1)

        return response.json()

    def create_campaign(self, campaign_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new campaign.

        Args:
            campaign_data: Dictionary with campaign settings including:
                - name: Campaign name
                - timezone: Campaign timezone (optional)
                - other campaign settings as needed

        Returns:
            Created campaign data with campaign_id
        """
        return self._request(
            "POST",
            "/campaigns/create",
            json=campaign_data,
        )

    def add_leads(self, campaign_id: int, leads: list[Lead]) -> dict[str, Any]:
        """Add leads to a campaign."""
        return self._request(
            "POST",
            f"/campaigns/{campaign_id}/leads",
            json={"lead_list": [l.model_dump(exclude_none=True) for l in leads]},
        )

    def get_campaign_stats(self, campaign_id: int) -> dict[str, Any]:
        """Get campaign statistics."""
        return self._request("GET", f"/campaigns/{campaign_id}/statistics")

    def get_campaign_leads(
        self, campaign_id: int, page: int = 1, limit: int = 100
    ) -> dict[str, Any]:
        """Get leads from a campaign."""
        return self._request(
            "GET",
            f"/campaigns/{campaign_id}/leads",
            params={"page": page, "limit": limit},
        )

    def save_campaign_sequences(
        self, campaign_id: int, sequences: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Save campaign email sequences.

        Args:
            campaign_id: The campaign ID
            sequences: List of sequence steps with email content

        Each sequence should have:
            seq_number: Step number (1, 2, 3...)
            seq_delay_days: Days from previous step
            seq_variants: List of email variants with subject and email_body
        """
        return self._request(
            "POST",
            f"/campaigns/{campaign_id}/sequences",
            json=sequences,
        )

    def update_campaign_settings(
        self, campaign_id: int, settings: dict[str, Any]
    ) -> dict[str, Any]:
        """Update campaign settings."""
        return self._request(
            "PATCH",
            f"/campaigns/{campaign_id}/settings",
            json=settings,
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()


# --- Utilities ---


def generate_test_leads(count: int) -> list[Lead]:
    """Generate test leads for testing."""
    leads = []
    for i in range(count):
        leads.append(
            Lead(
                email=f"test.lead.{i + 1}@example.com",
                first_name=f"Test",
                last_name=f"Lead{i + 1}",
                company_name=f"Test Company {i + 1}",
            )
        )
    return leads


def load_leads_from_file(path: Path) -> list[Lead]:
    """Load leads from a JSON file."""
    data = json.loads(path.read_text())

    if "lead_list" in data:
        data = data["lead_list"]
    elif "leads" in data:
        data = data["leads"]

    return [Lead(**lead) for lead in data]


# --- Commands ---


def cmd_create_campaign(args: argparse.Namespace) -> None:
    """Create a new Smartlead campaign."""
    api_key = args.api_key or get_env_var("SMARTLEAD_API_KEY")
    client = SmartleadTestClient(api_key)

    try:
        campaign_data = {}

        if args.name:
            campaign_data["name"] = args.name
        if args.timezone:
            campaign_data["timezone"] = args.timezone

        # Load additional settings from file if provided
        if args.settings_file:
            settings_path = Path(args.settings_file)
            if settings_path.exists():
                additional_settings = json.loads(settings_path.read_text())
                campaign_data.update(additional_settings)
            else:
                print(f"Warning: Settings file not found: {settings_path}", file=sys.stderr)

        if not campaign_data.get("name"):
            print("Error: Campaign name is required (--name)", file=sys.stderr)
            sys.exit(1)

        result = client.create_campaign(campaign_data)

        campaign_id = result.get("id") or result.get("campaign_id")
        if campaign_id:
            print(f"✓ Campaign created successfully!")
            print(f"  Campaign ID: {campaign_id}")
            print(f"  Name: {campaign_data.get('name')}")
            if campaign_data.get("timezone"):
                print(f"  Timezone: {campaign_data.get('timezone')}")
        else:
            print(f"Response: {json.dumps(result, indent=2)}")
    finally:
        client.close()


def cmd_create_test_leads(args: argparse.Namespace) -> None:
    """Create test leads and save to file."""
    leads = generate_test_leads(args.count)

    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(
            {"lead_list": [l.model_dump(exclude_none=True) for l in leads]},
            indent=2,
        )
    )

    print(f"Created {len(leads)} test leads -> {output_path}")


def cmd_add_leads(args: argparse.Namespace) -> None:
    """Add leads to a campaign."""
    api_key = args.api_key or get_env_var("SMARTLEAD_API_KEY")
    client = SmartleadTestClient(api_key)

    try:
        if args.leads_file:
            leads = load_leads_from_file(Path(args.leads_file))
        elif args.email:
            leads = [
                Lead(
                    email=args.email,
                    first_name=args.first_name,
                    last_name=args.last_name,
                    company_name=args.company_name,
                )
            ]
        else:
            print("Error: Must provide --leads-file or --email", file=sys.stderr)
            sys.exit(1)

        result = client.add_leads(args.campaign_id, leads)

        print(f"Added {len(leads)} lead(s) to campaign {args.campaign_id}")
        print(f"Result: {json.dumps(result, indent=2)}")
    finally:
        client.close()


def cmd_stats(args: argparse.Namespace) -> None:
    """Get campaign statistics."""
    api_key = args.api_key or get_env_var("SMARTLEAD_API_KEY")
    client = SmartleadTestClient(api_key)

    try:
        stats = client.get_campaign_stats(args.campaign_id)
        print(f"Campaign {args.campaign_id} Statistics:")
        print(json.dumps(stats, indent=2))
    finally:
        client.close()


def cmd_list_leads(args: argparse.Namespace) -> None:
    """List leads in a campaign."""
    api_key = args.api_key or get_env_var("SMARTLEAD_API_KEY")
    client = SmartleadTestClient(api_key)

    try:
        result = client.get_campaign_leads(args.campaign_id, page=args.page, limit=args.limit)
        leads = result.get("leads", [])

        print(f"Leads in campaign {args.campaign_id} (Page {args.page}):")
        print(f"Total: {result.get('total', len(leads))}")
        print()

        for lead in leads:
            print(f"  - {lead.get('email', 'N/A')} | {lead.get('lead_status', 'N/A')}")
    finally:
        client.close()


def cmd_setup_sequence(args: argparse.Namespace) -> None:
    """Setup campaign sequences from JSON file."""
    api_key = args.api_key or get_env_var("SMARTLEAD_API_KEY")
    client = SmartleadTestClient(api_key)

    try:
        sequences_file = Path(args.sequences_file)
        if not sequences_file.exists():
            print(f"Error: Sequences file not found: {sequences_file}", file=sys.stderr)
            sys.exit(1)

        sequences = json.loads(sequences_file.read_text())

        result = client.save_campaign_sequences(args.campaign_id, sequences)

        print(f"Setup {len(sequences)} sequence step(s) for campaign {args.campaign_id}")
        print(f"Result: {json.dumps(result, indent=2)}")
    finally:
        client.close()


def cmd_update_settings(args: argparse.Namespace) -> None:
    """Update campaign settings."""
    api_key = args.api_key or get_env_var("SMARTLEAD_API_KEY")
    client = SmartleadTestClient(api_key)

    try:
        settings = {}
        if args.name:
            settings["campaign_name"] = args.name
        if args.timezone:
            settings["timezone"] = args.timezone

        if not settings:
            print("Error: Must provide at least one setting to update", file=sys.stderr)
            sys.exit(1)

        result = client.update_campaign_settings(args.campaign_id, settings)

        print(f"Updated settings for campaign {args.campaign_id}")
        print(f"Result: {json.dumps(result, indent=2)}")
    finally:
        client.close()


def get_env_var(name: str) -> str:
    """Get environment variable or exit."""
    import os

    value = os.getenv(name)
    if not value:
        print(f"Error: {name} environment variable not set", file=sys.stderr)
        sys.exit(1)
    return value


# --- Main ---


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smartlead Campaign Testing Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new campaign
  python smartlead_campaign.py create --name "My Campaign" --timezone "America/New_York"

  # Create 10 test leads
  python smartlead_campaign.py create-test-leads --count 10 --output leads.json

  # Add leads from file to campaign
  python smartlead_campaign.py add-leads --campaign-id 123456 --leads-file leads.json

  # Add a single lead
  python smartlead_campaign.py add-leads --campaign-id 123456 \\
      --email test@example.com --first-name John --last-name Doe

  # Get campaign stats
  python smartlead_campaign.py stats --campaign-id 123456

  # List campaign leads
  python smartlead_campaign.py list-leads --campaign-id 123456

  # Setup campaign sequences from JSON file
  python smartlead_campaign.py setup-sequence --campaign-id 123456 --sequences-file sequences.json

  # Update campaign settings
  python smartlead_campaign.py update-settings --campaign-id 123456 --name "My Campaign" --timezone "America/New_York"
        """,
    )

    parser.add_argument(
        "--api-key",
        help="Smartlead API key (or set SMARTLEAD_API_KEY env var)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # create
    parser_create_campaign = subparsers.add_parser("create", help="Create a new campaign")
    parser_create_campaign.add_argument(
        "--name", required=True, help="Campaign name"
    )
    parser_create_campaign.add_argument(
        "--timezone", help="Campaign timezone (e.g., 'America/New_York')"
    )
    parser_create_campaign.add_argument(
        "--settings-file", help="JSON file with additional campaign settings"
    )

    # create-test-leads
    parser_create = subparsers.add_parser(
        "create-test-leads", help="Generate test leads"
    )
    parser_create.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of test leads to generate (default: 10)",
    )
    parser_create.add_argument(
        "--output",
        default="leads.json",
        help="Output file path (default: leads.json)",
    )

    # add-leads
    parser_add = subparsers.add_parser("add-leads", help="Add leads to campaign")
    parser_add.add_argument(
        "--campaign-id",
        type=int,
        required=True,
        help="Campaign ID to add leads to",
    )
    parser_add.add_argument(
        "--leads-file", help="JSON file with leads (use output from create-test-leads)"
    )
    parser_add.add_argument("--email", help="Single email address")
    parser_add.add_argument("--first-name", help="First name (for single email)")
    parser_add.add_argument("--last-name", help="Last name (for single email)")
    parser_add.add_argument("--company-name", help="Company name (for single email)")

    # stats
    parser_stats = subparsers.add_parser("stats", help="Get campaign statistics")
    parser_stats.add_argument(
        "--campaign-id",
        type=int,
        required=True,
        help="Campaign ID",
    )

    # list-leads
    parser_list = subparsers.add_parser("list-leads", help="List leads in campaign")
    parser_list.add_argument(
        "--campaign-id",
        type=int,
        required=True,
        help="Campaign ID",
    )
    parser_list.add_argument(
        "--page",
        type=int,
        default=1,
        help="Page number (default: 1)",
    )
    parser_list.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Leads per page (default: 100)",
    )

    # setup-sequence
    parser_sequence = subparsers.add_parser("setup-sequence", help="Setup campaign sequences")
    parser_sequence.add_argument(
        "--campaign-id",
        type=int,
        required=True,
        help="Campaign ID",
    )
    parser_sequence.add_argument(
        "--sequences-file",
        required=True,
        help="JSON file with sequence steps",
    )

    # update-settings
    parser_settings = subparsers.add_parser("update-settings", help="Update campaign settings")
    parser_settings.add_argument(
        "--campaign-id",
        type=int,
        required=True,
        help="Campaign ID",
    )
    parser_settings.add_argument("--name", help="Campaign name")
    parser_settings.add_argument("--timezone", help="Campaign timezone (e.g., 'America/New_York')")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "create": cmd_create_campaign,
        "create-test-leads": cmd_create_test_leads,
        "add-leads": cmd_add_leads,
        "stats": cmd_stats,
        "list-leads": cmd_list_leads,
        "setup-sequence": cmd_setup_sequence,
        "update-settings": cmd_update_settings,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
