"""
Main FastAPI application entry point.

This single service handles:
- Webhooks (incoming events from external systems)
- Dashboard (client-facing status and logs)
- Internal API (manual triggers, self-healing)
"""

import logging
import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .db import init_db
from .config import get_settings
from .routers import webhooks, dashboard, internal, docs

# Configure logging for stdout (Railway captures this)
# Format: timestamp | level | module | message
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,  # Override any existing config
)

# Reduce noise from third-party libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()

    # Ensure all registered automations have settings (default: disabled)
    from .db import SessionLocal, AutomationSettings
    from .automations import list_automation_info

    db = SessionLocal()
    try:
        registered_ids = {auto.id for auto in list_automation_info()}
        existing_ids = {
            s.automation_id for s in
            db.query(AutomationSettings.automation_id).all()
        }

        # Create missing settings (disabled by default)
        for automation_id in registered_ids - existing_ids:
            setting = AutomationSettings(automation_id=automation_id, enabled=False)
            db.add(setting)

        if registered_ids - existing_ids:
            db.commit()
            logger.info(f"Created default settings for {len(registered_ids - existing_ids)} automations")
    finally:
        db.close()

    logger.info(f"Starting {settings.client_id} automations service")
    yield
    logger.info(f"Shutting down {settings.client_id} automations service")


app = FastAPI(
    title=f"{settings.client_id} Automations",
    description="Automation service with webhooks, logging, and client dashboard.",
    lifespan=lifespan,
    docs_url="/api-docs",  # Move Swagger UI to /api-docs (frees /docs for our documentation)
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Mount routers
app.include_router(webhooks.router, prefix="/webhook", tags=["webhooks"])
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(internal.router, tags=["internal"])
app.include_router(docs.router, tags=["docs"])


@app.get("/health")
async def health():
    """Health check endpoint for Railway."""
    return {"status": "healthy", "client": settings.client_id}
