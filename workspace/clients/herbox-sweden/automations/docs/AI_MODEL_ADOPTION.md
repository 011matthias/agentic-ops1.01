# AI Model Configuration Guide

This guide explains how to use centralized AI model configuration when building new automations.

## Quick Reference

### 1. Add Your Model to Config

In [app/config.py](../app/config.py), add your operation:

```python
# In the Settings class, under "=== AI Model Configuration ==="
ai_model_my_operation: str = "openai/gpt-4o-mini"  # A#: Brief description
```

### 2. Use in Your Automation

```python
from ..config import get_settings

settings = get_settings()
MODEL = settings.get_ai_model("my_operation")

# Use the model
response = await openrouter_client.chat(
    model=MODEL,
    messages=[...],
)
```

## Examples

### Example 1: Single Operation
```python
# config.py
ai_model_email_classification: str = "openai/gpt-4o-mini"  # A8: Classify email replies

# automation.py
settings = get_settings()
MODEL = settings.get_ai_model("email_classification")
```

### Example 2: Multiple Operations
```python
# config.py
ai_model_company_cleaning: str = "openai/gpt-4o-mini"  # A6.4: Normalize company names
ai_model_title_translation: str = "openai/gpt-4o-mini"  # A6.4: Dutch job titles

# automation.py
MODEL_CLEAN = settings.get_ai_model("company_cleaning")
MODEL_TRANSLATE = settings.get_ai_model("title_translation")
```

## Benefits

1. **Single source of truth** - All models defined in one place
2. **Easy to swap** - Change models without touching automation code
3. **Production-safe** - Override via environment variables if needed
4. **Self-documenting** - Each model includes automation ID and purpose

## Available Models

See [OpenRouter Models](https://openrouter.ai/models) for available options.

Common choices:
- `openai/gpt-4o-mini` - Fast, cost-effective (default)
- `anthropic/claude-3-haiku` - Fast, good for simple tasks
- `google/gemini-flash` - Fast, cost-effective alternative

## Environment Override

You can override any model via environment variable:

```bash
# Railway variables
AI_MODEL_MY_OPERATION=anthropic/claude-3-haiku
AI_MODEL_DEFAULT=google/gemini-flash
```
