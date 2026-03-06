---
id: a1
type: automation
name: Positive Reply Notifier
stage: build
status: implemented
needs_fixes: false
version: 1.1.0
created: &id001 2026-01-09
updated: 2026-02-07
orchestrator: trigger-dev
trigger:
  type: webhook
  webhook_event: smartlead.email.reply
systems:
- smartlead
- openrouter
- slack
owner: team@uplifted.se
last_changes:
- Migrated from FastAPI/Railway to Trigger.dev
- Automation code moved to python/automations/
- API clients moved to python/clients/
- TypeScript task wrapper created at src/trigger/a1-reply-notifier.ts
- Removed FastAPI infrastructure (dashboard, cron, internal API)
next_steps:
- Set up Trigger.dev project (cloud or self-hosted)
- Configure environment variables in Trigger.dev dashboard
- Point Smartlead webhook to Trigger.dev endpoint
- Deploy with npx trigger.dev deploy
stage_history:
- stage: build
  date: *id001
---

# A1: Positive Reply Notifier

## Goal

**Problem:** Manual monitoring of hundreds of email replies to identify interested prospects, leading to missed opportunities and wasted time.

**Solution:** Auto-classify replies using AI and instantly notify Slack for positive responses.

**Business Value:** Immediate notification of hot leads, no missed opportunities, sales team focuses only on interested prospects.

## Flow Diagram

## API References

| System | Endpoints | Auth | Rate Limit |
| --- | --- | --- | --- |
| Smartlead | Webhook (inbound) | Webhook secret | N/A |
| OpenRouter | POST /chat/completions | API Key | 200 req/min |
| Slack | POST webhook URL | Webhook URL | N/A |

**API Clients:**

-   `app/clients/openrouter.py` - LLM classification
    
-   Slack via webhook (no client needed)
    

## Step Details

### 1\. Initialize

-   Validate webhook payload structure
    
-   Verify webhook secret (if configured)
    
-   **Output:** Validated payload
    

### 2\. Fetch Data

-   Extract from Smartlead payload:
    
    -   `reply_text` - The email reply content
        
    -   `lead_email` - Lead's email address
        
    -   `lead_name` - Lead's name
        
    -   `campaign_name` - Source campaign
        
    -   `sequence_number` - Which email in sequence
        
    -   `inbox_id` - For building reply link
        
-   **Output:** Structured reply data
    

### 3\. Transform

-   Build classification prompt for AI:
    
    ```
    Classify this email reply as Positive or Not Positive.
    
    Positive means: showing interest, asking questions, requesting call/meeting,
    wants more information, or any engagement beyond "not interested"
    
    Reply: {reply_text}
    
    Respond with JSON: {classification, confidence, reasoning}
    ```
    
-   **Output:** AI prompt payload
    

### 4\. Execute

-   Send prompt to OpenRouter (Claude or GPT model)
    
-   Parse classification response
    
-   If Positive:
    
    -   Build rich Slack notification with:
        
        -   Lead name and email
            
        -   Reply preview (first 200 chars)
            
        -   AI classification and confidence
            
        -   AI reasoning
            
        -   Direct link to inbox
            
    -   Send to Slack webhook
        
-   **Output:** Classification result + notification status
    

### 5\. Finalize

-   Log to database:
    
    -   Reply ID, lead info
        
    -   Classification result
        
    -   Confidence score
        
    -   Notification sent status
        
-   Update dashboard stats
    
-   Return success response to Smartlead
    
-   **Output:** Processing complete
    

## Edge Cases & Error Handling

| Scenario | Handling | Recovery |
| --- | --- | --- |
| Invalid webhook payload | Return 400, log error | N/A |
| Empty reply text | Classify as "Unable to classify" | Log warning |
| OpenRouter timeout | Retry once with longer timeout | Log as pending |
| OpenRouter error | Log error, skip notification | Manual review |
| Slack webhook fails | Log error, continue | Manual notification |
| Non-JSON AI response | Parse best effort | Log raw response |

## Testing

### Unit Tests

```python
def test_parse_smartlead_webhook():
    """Test webhook payload parsing."""
    payload = {
        "event_type": "EMAIL_REPLY",
        "reply_text": "Yes, I'm interested!",
        "lead": {"email": "test@example.com", "name": "Test Lead"}
    }
    result = parse_smartlead_webhook(payload)
    assert result["reply_text"] == "Yes, I'm interested!"
    assert result["lead_email"] == "test@example.com"

def test_build_classification_prompt():
    """Test AI prompt construction."""
    reply_data = {"reply_text": "Sounds interesting, tell me more"}
    prompt = build_classification_prompt(reply_data)
    assert "Sounds interesting" in prompt
    assert "Positive or Not Positive" in prompt

def test_parse_ai_response():
    """Test AI response parsing."""
    ai_response = '{"classification": "Positive", "confidence": 0.95, "reasoning": "Shows interest"}'
    result = parse_ai_response(ai_response)
    assert result["classification"] == "Positive"
    assert result["confidence"] == 0.95
```

### Integration Tests

```python
def test_a1_dry_run():
    """Full automation in dry-run mode."""
    automation = PositiveReplyNotifier()
    result = automation.run(dry_run=True, payload=sample_webhook)
    assert result["dry_run"] is True
    assert "classification" in result

def test_a1_classification_positive():
    """Test positive reply is classified correctly."""
    positive_replies = [
        "Yes, I'd love to learn more!",
        "Can you send me a proposal?",
        "Let's schedule a call"
    ]
    for reply in positive_replies:
        result = classify_reply(reply)
        assert result["classification"] == "Positive"

def test_a1_classification_negative():
    """Test negative reply is classified correctly."""
    negative_replies = [
        "Not interested",
        "Remove me from your list",
        "Stop emailing me"
    ]
    for reply in negative_replies:
        result = classify_reply(reply)
        assert result["classification"] == "Not Positive"
```

### Acceptance Criteria

- [x] Webhook receives and parses Smartlead payload
- [ ] AI correctly classifies positive vs not positive (90%+ accuracy)
- [ ] Slack notification includes: lead info, reply preview, AI reasoning, confidence
- [ ] Slack notification includes direct inbox link
- [ ] Dashboard shows all processed replies with classification
- [ ] Dry run mode works without sending notifications
- [ ] Invalid payloads return 400 with error details

## Implementation Notes

**Code Location:** `app/automations/positive_reply_notifier.py`

**Webhook Route:** `app/routers/webhooks.py` → POST /webhook/smartlead

**AI Model Configuration:**

```python
DEFAULT_MODEL = "anthropic/claude-3-haiku"  # Fast, cheap for classification
FALLBACK_MODEL = "openai/gpt-3.5-turbo"
```

**Environment Variables:**

| Variable | Required | Description |
| --- | --- | --- |
| OPENROUTER_API_KEY | Yes | OpenRouter API key |
| SLACK_WEBHOOK_URL | Yes | Slack incoming webhook URL |
| SMARTLEAD_WEBHOOK_SECRET | No | Webhook verification secret |

## Changelog

| Version | Date | Changes |
| --- | --- | --- |
| 1.0.0 | 2026-01-09 | Initial specification (migrated from combined spec) |