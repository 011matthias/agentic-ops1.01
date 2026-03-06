# N8N Node Mappings

Reference for converting N8N nodes to Python code.

---

## Trigger Nodes

### cron / scheduleTrigger
```python
# Frontmatter
trigger:
  type: cron
  schedule: "{cron_expression}"

# No code needed - handled by Railway cron job
```

### webhook
```python
# Frontmatter
trigger:
  type: webhook
  path: /webhooks/{name}

# Router code
@router.post("/webhooks/{name}")
async def handle_webhook(request: Request):
    data = await request.json()
    automation = MyAutomation()
    return await automation.execute(data)
```

### manualTrigger
```python
# Frontmatter
trigger:
  type: manual

# CLI execution
if __name__ == "__main__":
    automation = MyAutomation()
    asyncio.run(automation.execute())
```

---

## HTTP Nodes

### httpRequest
```python
# N8N
{
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "GET",
    "url": "https://api.example.com/data",
    "authentication": "predefinedCredentialType",
    "headers": { "Accept": "application/json" }
  }
}

# Python
async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.example.com/data",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}
    )
    data = response.json()
```

### HTTP with Query Parameters
```python
# N8N
{
  "parameters": {
    "url": "https://api.example.com/search",
    "qs": {
      "query": "={{ $json.searchTerm }}",
      "limit": 10
    }
  }
}

# Python
params = {
    "query": data["searchTerm"],
    "limit": 10
}
response = await client.get(url, params=params)
```

### HTTP POST with Body
```python
# N8N
{
  "parameters": {
    "method": "POST",
    "url": "https://api.example.com/create",
    "body": {
      "name": "={{ $json.name }}",
      "value": "={{ $json.value }}"
    }
  }
}

# Python
payload = {
    "name": data["name"],
    "value": data["value"]
}
response = await client.post(url, json=payload)
```

---

## Logic Nodes

### if
```python
# N8N
{
  "type": "n8n-nodes-base.if",
  "parameters": {
    "conditions": {
      "string": [{
        "value1": "={{ $json.status }}",
        "operation": "equals",
        "value2": "active"
      }]
    }
  }
}

# Python
if data["status"] == "active":
    # True branch
    pass
else:
    # False branch
    pass
```

### switch
```python
# N8N
{
  "type": "n8n-nodes-base.switch",
  "parameters": {
    "dataPropertyName": "type",
    "rules": [
      {"value": "order"},
      {"value": "invoice"},
      {"value": "payment"}
    ]
  }
}

# Python
match data["type"]:
    case "order":
        # Handle order
        pass
    case "invoice":
        # Handle invoice
        pass
    case "payment":
        # Handle payment
        pass
    case _:
        # Default/fallback
        pass
```

### filter
```python
# N8N Filter node
{
  "type": "n8n-nodes-base.filter",
  "parameters": {
    "conditions": {
      "number": [{
        "value1": "={{ $json.amount }}",
        "operation": "larger",
        "value2": 100
      }]
    }
  }
}

# Python
filtered_items = [item for item in items if item["amount"] > 100]
```

---

## Data Manipulation Nodes

### set
```python
# N8N
{
  "type": "n8n-nodes-base.set",
  "parameters": {
    "values": {
      "string": [
        {"name": "fullName", "value": "={{ $json.firstName }} {{ $json.lastName }}"}
      ]
    }
  }
}

# Python
data["fullName"] = f"{data['firstName']} {data['lastName']}"
```

### merge
```python
# N8N Merge (Append)
{
  "type": "n8n-nodes-base.merge",
  "parameters": {
    "mode": "append"
  }
}

# Python
merged = list1 + list2

# N8N Merge (Combine by Key)
{
  "parameters": {
    "mode": "mergeByKey",
    "propertyName": "id"
  }
}

# Python
merged = {}
for item in list1 + list2:
    key = item["id"]
    if key in merged:
        merged[key].update(item)
    else:
        merged[key] = item
result = list(merged.values())
```

### splitInBatches
```python
# N8N
{
  "type": "n8n-nodes-base.splitInBatches",
  "parameters": {
    "batchSize": 10
  }
}

# Python
def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

for batch in chunks(items, 10):
    # Process batch
    pass
```

### removeDuplicates
```python
# N8N
{
  "type": "n8n-nodes-base.removeDuplicates",
  "parameters": {
    "propertyName": "email"
  }
}

# Python
seen = set()
unique = []
for item in items:
    if item["email"] not in seen:
        seen.add(item["email"])
        unique.append(item)
```

### sort
```python
# N8N
{
  "type": "n8n-nodes-base.sort",
  "parameters": {
    "sortFieldsUi": [{
      "fieldName": "createdAt",
      "order": "descending"
    }]
  }
}

# Python
sorted_items = sorted(items, key=lambda x: x["createdAt"], reverse=True)
```

---

## Code Node

### code (JavaScript)
```python
# N8N
{
  "type": "n8n-nodes-base.code",
  "parameters": {
    "jsCode": "const items = $input.all();\nreturn items.map(item => ({...item.json, processed: true}));"
  }
}

# Python - Manual conversion needed
# Review the JavaScript logic and rewrite in Python
items = input_data
result = [{**item, "processed": True} for item in items]
```

---

## External Service Nodes

### slack
```python
# N8N
{
  "type": "n8n-nodes-base.slack",
  "parameters": {
    "channel": "#alerts",
    "text": "={{ $json.message }}"
  }
}

# Python (using webhook)
async def send_slack(message: str, channel: str = "#alerts"):
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json={
            "channel": channel,
            "text": message
        })
```

### openAi
```python
# N8N
{
  "type": "@n8n/n8n-nodes-langchain.openAi",
  "parameters": {
    "model": "gpt-4",
    "prompt": "={{ $json.prompt }}"
  }
}

# Python (using OpenRouter)
async def call_llm(prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
            json={
                "model": "openai/gpt-4",
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        return response.json()["choices"][0]["message"]["content"]
```

### gmail
```python
# N8N
{
  "type": "n8n-nodes-base.gmail",
  "parameters": {
    "sendTo": "={{ $json.email }}",
    "subject": "Notification",
    "message": "={{ $json.body }}"
  }
}

# Python (using SMTP or API)
# Recommend using a service like SendGrid or Postmark
async def send_email(to: str, subject: str, body: str):
    # Implementation depends on email service choice
    pass
```

---

## Utility Nodes

### wait
```python
# N8N
{
  "type": "n8n-nodes-base.wait",
  "parameters": {
    "unit": "seconds",
    "amount": 5
  }
}

# Python
import asyncio
await asyncio.sleep(5)
```

### noOp (No Operation)
```python
# N8N noOp node - just passes data through
# Python - no code needed, just continue flow
pass
```

### respondToWebhook
```python
# N8N
{
  "type": "n8n-nodes-base.respondToWebhook",
  "parameters": {
    "respondWith": "json",
    "responseBody": "={{ $json }}"
  }
}

# Python (FastAPI)
return JSONResponse(content=data)
```

---

## Notes

- Always verify credential handling matches Python environment
- Complex JavaScript in Code nodes requires manual review
- Some N8N-specific features (like $runIndex) need alternative approaches
- Test converted code thoroughly before deployment
