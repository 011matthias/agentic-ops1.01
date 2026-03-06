# Testing Utilities

Helper scripts for live testing and development of automations.

## Utilities

### [smartlead_campaign.py](smartlead_campaign.py)

Operations for testing Smartlead campaigns.

```bash
# Create a new campaign
uv run python scripts/testing-utils/smartlead_campaign.py create --name "My Campaign" --timezone "America/New_York"

# Generate test leads
uv run python scripts/testing-utils/smartlead_campaign.py create-test-leads --count 10 --output leads.json

# Add leads from file to campaign
uv run python scripts/testing-utils/smartlead_campaign.py add-leads --campaign-id 123456 --leads-file leads.json

# Add a single lead
uv run python scripts/testing-utils/smartlead_campaign.py add-leads --campaign-id 123456 \
    --email test@example.com --first-name John --last-name Doe

# Setup campaign sequences
uv run python scripts/testing-utils/smartlead_campaign.py setup-sequence --campaign-id 123456 --sequences-file sequences.json

# Update campaign settings
uv run python scripts/testing-utils/smartlead_campaign.py update-settings --campaign-id 123456 --name "My Campaign" --timezone "America/New_York"

# Get campaign statistics
uv run python scripts/testing-utils/smartlead_campaign.py stats --campaign-id 123456

# List leads in campaign
uv run python scripts/testing-utils/smartlead_campaign.py list-leads --campaign-id 123456
```

### [airtable_records.py](airtable_records.py)

Create and manage Airtable records during testing.

```bash
# Create a single record
uv run python scripts/testing-utils/airtable_records.py create --base-id appXXXXX --table-id tblXXXXX \
    --field Name="John Doe" --field Email="john@example.com"

# Create records from JSON file
uv run python scripts/testing-utils/airtable_records.py create --base-id appXXXXX --table-id tblXXXXX --input records.json

# List records
uv run python scripts/testing-utils/airtable_records.py list --base-id appXXXXX --table-id tblXXXXX

# List all records (handles pagination)
uv run python scripts/testing-utils/airtable_records.py list --base-id appXXXXX --table-id tblXXXXX --all

# Get a specific record
uv run python scripts/testing-utils/airtable_records.py get --base-id appXXXXX --table-id tblXXXXX --record-id recXXXXX

# Update a record
uv run python scripts/testing-utils/airtable_records.py update --base-id appXXXXX --table-id tblXXXXX \
    --record-id recXXXXX --field Name="Jane Doe"
```

### [airtable_cleanup.py](airtable_cleanup.py)

Clean up Airtable tables after testing.

```bash
# Count records
uv run python scripts/testing-utils/airtable_cleanup.py count --base-id appXXXXX --table-id tblXXXXX

# Count records matching a formula
uv run python scripts/testing-utils/airtable_cleanup.py count --base-id appXXXXX --table-id tblXXXXX \
    --formula "NOT({Status} = 'active')"

# Delete all records (with confirmation)
uv run python scripts/testing-utils/airtable_cleanup.py delete-all --base-id appXXXXX --table-id tblXXXXX

# Delete all records (no confirmation, for scripts)
uv run python scripts/testing-utils/airtable_cleanup.py delete-all --base-id appXXXXX --table-id tblXXXXX --force

# Dry run to see what would be deleted
uv run python scripts/testing-utils/airtable_cleanup.py delete-all --base-id appXXXXX --table-id tblXXXXX --dry-run

# Delete records matching a formula
uv run python scripts/testing-utils/airtable_cleanup.py delete-matching --base-id appXXXXX --table-id tblXXXXX \
    --formula "{Created} < DATETIME_PARSE('2024-01-01')"
```

## Environment Variables

You can set API keys as environment variables instead of passing them each time:

```bash
export SMARTLEAD_API_KEY="your_smartlead_api_key"
export AIRTABLE_API_KEY="your_airtable_api_key"

# Now you can omit --api-key flag
uv run python scripts/testing-utils/smartlead_campaign.py stats --campaign-id 123456
```

## Common Testing Workflows

### Setting up a Smartlead campaign for testing

```bash
# 1. Create a new campaign (returns campaign_id)
CAMPAIGN_ID=$(uv run python scripts/testing-utils/smartlead_campaign.py create --name "Test Campaign")

# 2. Setup email sequences
uv run python scripts/testing-utils/smartlead_campaign.py setup-sequence --campaign-id $CAMPAIGN_ID --sequences-file sequences.json

# 3. Generate test leads
uv run python scripts/testing-utils/smartlead_campaign.py create-test-leads --count 5 --output test_leads.json

# 4. Add leads to campaign
uv run python scripts/testing-utils/smartlead_campaign.py add-leads --campaign-id $CAMPAIGN_ID --leads-file test_leads.json

# 5. Check campaign stats
uv run python scripts/testing-utils/smartlead_campaign.py stats --campaign-id $CAMPAIGN_ID
```

### Creating test records in Airtable

```bash
# Create a few test records
uv run python scripts/testing-utils/airtable_records.py create --base-id appXXXXX --table-id tblXXXXX \
    --field Name="Test Lead 1" --field Email="test1@example.com"

uv run python scripts/testing-utils/airtable_records.py create --base-id appXXXXX --table-id tblXXXXX \
    --field Name="Test Lead 2" --field Email="test2@example.com"

# Verify they were created
uv run python scripts/testing-utils/airtable_records.py list --base-id appXXXXX --table-id tblXXXXX
```

### Cleaning up test data

```bash
# Preview what would be deleted
uv run python scripts/testing-utils/airtable_cleanup.py delete-all --base-id appXXXXX --table-id tblXXXXX --dry-run

# Actually delete (after confirming)
uv run python scripts/testing-utils/airtable_cleanup.py delete-all --base-id appXXXXX --table-id tblXXXXX

# Or delete only test records (if you have a way to identify them)
uv run python scripts/testing-utils/airtable_cleanup.py delete-matching --base-id appXXXXX --table-id tblXXXXX \
    --formula "FIND('test', LOWER({Email}))"
```

## JSON File Format

### Leads file format (for Smartlead)

```json
{
  "lead_list": [
    {
      "email": "test@example.com",
      "first_name": "Test",
      "last_name": "User",
      "company_name": "Test Company"
    }
  ]
}
```

### Sequences file format (for Smartlead)

Use this to setup email sequences for a campaign:

```json
[
  {
    "seq_number": 1,
    "seq_delay_days": 0,
    "seq_variants": [
      {
        "subject": "Test Email 1",
        "email_body": "<p>Hi {{first_name}},</p><p>This is a test email.</p>"
      }
    ]
  },
  {
    "seq_number": 2,
    "seq_delay_days": 3,
    "seq_variants": [
      {
        "subject": "Follow-up",
        "email_body": "<p>Hi {{first_name}},</p><p>Just following up!</p>"
      }
    ]
  }
]
```

### Records file format (for Airtable)

```json
{
  "records": [
    {
      "Name": "John Doe",
      "Email": "john@example.com",
      "Status": "active"
    },
    {
      "Name": "Jane Smith",
      "Email": "jane@example.com",
      "Status": "pending"
    }
  ]
}
```

## Notes

- These scripts use PEP 723 inline dependencies, so UV will automatically install required packages
- All scripts have `--help` for detailed usage information
- Be careful with delete operations - use `--dry-run` first to preview
