"""
Apify API Client Package

A typed Python client for the Apify API v2.

Requirements:
    - httpx>=0.25.0
    - pydantic>=2.0.0

Usage:
    from apify import ApifyClient

    client = ApifyClient(token="your_api_token")

    # Run an actor
    run = client.run_actor("apify/web-scraper", input={"startUrls": [{"url": "https://example.com"}]})

    # Wait for completion and get results
    import time
    while run.status in ["READY", "RUNNING"]:
        time.sleep(5)
        run = client.get_run(run.id)

    # Get dataset items
    items = client.get_dataset_items(run.default_dataset_id)
    print(f"Scraped {len(items)} items")

Async Usage:
    import asyncio
    from apify import AsyncApifyClient

    async def main():
        async with AsyncApifyClient(token="your_api_token") as client:
            run = await client.run_actor("apify/web-scraper", input={...})
            items = await client.get_dataset_items(run.default_dataset_id)

    asyncio.run(main())
"""

from .client import ApifyClient, ApifyError, AsyncApifyClient
from .models import (
    Actor,
    ActorList,
    ActorListItem,
    ActorRunStatus,
    ActorStats,
    ActorVersion,
    Build,
    BuildList,
    BuildStatus,
    CreateActorRequest,
    CreateEnvVarRequest,
    CreateScheduleRequest,
    CreateTaskRequest,
    CreateVersionRequest,
    CreateWebhookRequest,
    Dataset,
    DatasetList,
    DefaultRunOptions,
    EnvVar,
    KeyList,
    KeyRecord,
    KeyValueStore,
    KeyValueStoreList,
    MonthlyUsage,
    QueueRequest,
    RequestQueue,
    Run,
    RunList,
    RunOptions,
    RunStats,
    Schedule,
    ScheduleList,
    SourceType,
    Task,
    TaskList,
    UpdateActorRequest,
    UpdateTaskRequest,
    User,
    UserLimits,
    Webhook,
    WebhookEventType,
    WebhookList,
)

__all__ = [
    # Clients
    "ApifyClient",
    "AsyncApifyClient",
    "ApifyError",
    # Enums
    "ActorRunStatus",
    "BuildStatus",
    "SourceType",
    "WebhookEventType",
    # Actor models
    "Actor",
    "ActorList",
    "ActorListItem",
    "ActorStats",
    "ActorVersion",
    "DefaultRunOptions",
    "CreateActorRequest",
    "UpdateActorRequest",
    "CreateVersionRequest",
    "EnvVar",
    "CreateEnvVarRequest",
    # Run models
    "Run",
    "RunList",
    "RunStats",
    "RunOptions",
    # Build models
    "Build",
    "BuildList",
    # Task models
    "Task",
    "TaskList",
    "CreateTaskRequest",
    "UpdateTaskRequest",
    # Dataset models
    "Dataset",
    "DatasetList",
    # Key-Value Store models
    "KeyValueStore",
    "KeyValueStoreList",
    "KeyList",
    "KeyRecord",
    # Request Queue models
    "RequestQueue",
    "QueueRequest",
    # Schedule models
    "Schedule",
    "ScheduleList",
    "CreateScheduleRequest",
    # Webhook models
    "Webhook",
    "WebhookList",
    "CreateWebhookRequest",
    # User models
    "User",
    "UserLimits",
    "MonthlyUsage",
]
