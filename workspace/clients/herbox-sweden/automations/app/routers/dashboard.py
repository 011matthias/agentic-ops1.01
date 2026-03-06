"""
Dashboard routes for client-facing status and logs.
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
import secrets

from ..db import get_db, ExecutionLog
from ..auth import require_auth
from ..config import get_settings
from ..automations import list_automation_info

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page for dashboard."""
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(request: Request, password: str = Form(...)):
    """Handle login form submission."""
    if secrets.compare_digest(password.encode("utf8"), settings.dashboard_password.encode("utf8")):
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key="session_token",
            value=settings.dashboard_password,
            httponly=True,
            secure=True,
            samesite="lax"
        )
        return response
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid password"}
    )


@router.get("/logout")
async def logout():
    """Clear session and redirect to login."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_auth)
):
    """Main dashboard showing automation status and recent activity."""
    # Get recent logs
    recent_logs = db.query(ExecutionLog).order_by(desc(ExecutionLog.started_at)).limit(50).all()

    # Build summary by automation (latest status for each)
    summary = {}
    for log in recent_logs:
        if log.automation_id not in summary:
            summary[log.automation_id] = log

    return templates.TemplateResponse("index.html", {
        "request": request,
        "client_id": settings.client_id,
        "client_display_name": settings.client_display_name,
        "automations": list_automation_info(),
        "summary": summary,
        "recent_logs": recent_logs[:10]
    })


@router.get("/automations", response_class=HTMLResponse)
async def automations_page(
    request: Request,
    _: str = Depends(require_auth)
):
    """Full list of available automations."""
    return templates.TemplateResponse("automations.html", {
        "request": request,
        "client_id": settings.client_id,
        "client_display_name": settings.client_display_name,
        "automations": list_automation_info(),
    })


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_auth)
):
    """Full execution log history."""
    logs = db.query(ExecutionLog).order_by(desc(ExecutionLog.started_at)).all()
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "client_id": settings.client_id,
        "client_display_name": settings.client_display_name,
        "logs": logs
    })


@router.get("/logs/{run_id}", response_class=HTMLResponse)
async def log_detail(
    request: Request,
    run_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_auth)
):
    """Detailed view of a single execution."""
    log = db.query(ExecutionLog).filter(ExecutionLog.run_id == run_id).first()
    if not log:
        return HTMLResponse("Not found", status_code=404)
    return templates.TemplateResponse("log_detail.html", {
        "request": request,
        "client_id": settings.client_id,
        "client_display_name": settings.client_display_name,
        "log": log
    })


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_auth)
):
    """Automation settings page - enable/disable automations."""
    from ..db import AutomationSettings

    # Get all automations with their settings
    automations = list_automation_info()
    settings_dict = {
        s.automation_id: s
        for s in db.query(AutomationSettings).all()
    }

    # Create missing settings (disabled by default)
    for auto in automations:
        if auto.id not in settings_dict:
            setting = AutomationSettings(automation_id=auto.id, enabled=False)
            db.add(setting)
            db.commit()
            db.refresh(setting)
            settings_dict[auto.id] = setting

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "client_id": settings.client_id,
        "client_display_name": settings.client_display_name,
        "automations": automations,
        "automation_settings": settings_dict
    })


@router.post("/settings/{automation_id}/toggle")
async def toggle_automation(
    automation_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_auth)
):
    """Toggle automation enabled/disabled state."""
    from ..db import get_or_create_automation_setting

    body = await request.json()
    enabled = body.get("enabled", False)

    setting = get_or_create_automation_setting(db, automation_id)
    setting.enabled = enabled
    db.commit()

    return {"status": "updated", "automation_id": automation_id, "enabled": enabled}
