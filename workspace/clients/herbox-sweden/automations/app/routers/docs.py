"""
Documentation routes for serving automation docs in the dashboard.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from ..auth import require_auth
from ..config import get_settings

router = APIRouter(prefix="/docs")
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()

# Optional: try to import markdown for rendering
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False


def get_docs_list() -> list[dict]:
    """Scan docs folder and return list of available documentation."""
    docs = []
    client_docs_path = Path("docs/client")

    if client_docs_path.exists():
        for doc_file in sorted(client_docs_path.glob("*.md")):
            # Read first line as title
            content = doc_file.read_text()
            lines = content.split("\n")
            title = lines[0].replace("#", "").strip() if lines else doc_file.stem

            # Try to extract description from second paragraph
            description = ""
            for line in lines[1:10]:
                line = line.strip()
                if line and not line.startswith("#"):
                    description = line[:100]
                    break

            docs.append({
                "id": doc_file.stem,
                "name": title,
                "description": description or f"Documentation for {doc_file.stem}"
            })

    return docs


def render_markdown(content: str) -> str:
    """Convert markdown to HTML, with fallback to pre-formatted text."""
    if MARKDOWN_AVAILABLE:
        return markdown.markdown(
            content,
            extensions=['tables', 'fenced_code', 'toc']
        )
    else:
        # Fallback: wrap in pre tags for basic readability
        return f"<pre style='white-space: pre-wrap;'>{content}</pre>"


@router.get("", response_class=HTMLResponse)
async def docs_index(
    request: Request,
    _: str = Depends(require_auth)
):
    """Documentation index page listing all available docs."""
    docs = get_docs_list()
    return templates.TemplateResponse("docs.html", {
        "request": request,
        "client_id": settings.client_id,
        "client_display_name": settings.client_display_name,
        "docs": docs,
        "markdown_available": MARKDOWN_AVAILABLE
    })


@router.get("/client/{doc_id}", response_class=HTMLResponse)
async def client_doc(
    request: Request,
    doc_id: str,
    _: str = Depends(require_auth)
):
    """Serve client-facing documentation."""
    doc_path = Path(f"docs/client/{doc_id}.md")
    if not doc_path.exists():
        raise HTTPException(status_code=404, detail="Documentation not found")

    content = doc_path.read_text()
    html_content = render_markdown(content)

    # Extract title from first line
    title = content.split("\n")[0].replace("#", "").strip()

    return templates.TemplateResponse("doc_view.html", {
        "request": request,
        "client_id": settings.client_id,
        "client_display_name": settings.client_display_name,
        "title": title,
        "content": html_content,
        "doc_type": "client",
        "doc_id": doc_id
    })


@router.get("/technical/{doc_id}", response_class=HTMLResponse)
async def technical_doc(
    request: Request,
    doc_id: str,
    _: str = Depends(require_auth)
):
    """Serve technical documentation (for developers)."""
    doc_path = Path(f"docs/technical/{doc_id}.md")
    if not doc_path.exists():
        raise HTTPException(status_code=404, detail="Documentation not found")

    content = doc_path.read_text()
    html_content = render_markdown(content)

    # Extract title from first line
    title = content.split("\n")[0].replace("#", "").strip()

    return templates.TemplateResponse("doc_view.html", {
        "request": request,
        "client_id": settings.client_id,
        "client_display_name": settings.client_display_name,
        "title": title,
        "content": html_content,
        "doc_type": "technical",
        "doc_id": doc_id
    })
