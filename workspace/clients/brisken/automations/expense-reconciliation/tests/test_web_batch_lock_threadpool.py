"""The batch writer lock must never be taken on the event loop.

Backlog item 18, found by the 2026-08-21 delete-month adversarial review.
`_BATCH_ADD_LOCK` serializes every read-modify-write on a batch snapshot, and
an OCR ingest holds it for MINUTES. A sync (`def`) handler blocking on it
parks a threadpool worker, which is fine. An `async def` handler blocking on
it parks the EVENT LOOP: every endpoint stops answering, `/healthz` included,
so Fly's health check fails and the machine restarts, which kills the very
ingest that was holding the lock.

`delete_run` was already made sync for this reason. `set-aside/restore` and
the cards-assignment endpoint both read a JSON body first, so they stay
`async def` and hand the locked span to the threadpool instead. A blocked
handler now holds an anyio threadpool worker rather than the loop; with a
single operator that is not a contention risk, and it is the same trade
`delete_run` already makes.

The test holds the lock from another thread and asserts `/healthz` still
answers while a locked endpoint is waiting on it. Without the fix the probe
thread never returns.
"""
from __future__ import annotations

import threading
import time

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web import service  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

# Generous: the assertion is "answers at all while the lock is held", not
# "answers fast". A parked loop never answers, so a slow machine cannot make
# this flake into a false failure.
PROBE_TIMEOUT_S = 20.0


@pytest.fixture
def batch(tmp_path, monkeypatch):
    """A real batch id: both endpoints validate the run BEFORE taking the
    lock, so an unknown id 404s without ever reaching it and would make this
    test pass against the very bug it guards."""
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(extraction_responses=[ExtractedReceipt(
        date="2026-07-01", total="42.50", currency="USD", vendor="Staples",
        reference="", line_items=(), confidence=0.9, notes="")])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    app = create_app(tmp_path)
    with TestClient(app) as c:
        resp = c.post(
            "/api/expense-batches",
            files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
            data={"legal_entity": "Corporate Services", "label": "Lock fixture"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert c.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
        yield c, body["batch_id"]


def _in_thread(fn) -> threading.Thread:
    thread = threading.Thread(target=fn, daemon=True)
    thread.start()
    return thread


@pytest.mark.parametrize(
    "suffix,body",
    [
        # both take `with _BATCH_ADD_LOCK` as their first real action, so a
        # bad file / unknown card key still blocks on acquisition first
        ("/set-aside/restore", {"file": "a.jpg"}),
        ("/cards", {"assignments": [{"hint": "Visa", "card": "nope"}]}),
    ],
)
def test_locked_endpoint_does_not_park_the_event_loop(batch, suffix, body):
    client, batch_id = batch
    path = f"/api/expense-batches/{batch_id}{suffix}"
    lock = service._BATCH_ADD_LOCK
    assert lock.acquire(timeout=5), "lock already held; a prior test leaked it"
    caller = None
    probe: dict[str, object] = {}
    try:
        # The endpoint under test: it will block on the held lock. What must
        # NOT happen is the event loop being parked while it waits.
        caller = _in_thread(lambda: client.post(path, json=body))
        time.sleep(0.5)

        def _probe():
            try:
                probe["status"] = client.get("/healthz").status_code
            except Exception as exc:  # noqa: BLE001 - recorded, asserted below
                probe["error"] = repr(exc)

        probe_thread = _in_thread(_probe)
        probe_thread.join(timeout=PROBE_TIMEOUT_S)
        assert not probe_thread.is_alive(), (
            f"/healthz did not answer within {PROBE_TIMEOUT_S}s while the batch "
            f"writer lock was held and {path} was in flight: the handler is "
            f"blocking on the lock from the event loop. Hand the locked span to "
            f"run_in_threadpool (or make the handler sync)."
        )
        assert probe.get("status") == 200, probe
    finally:
        lock.release()
        if caller is not None:
            caller.join(timeout=PROBE_TIMEOUT_S)


# ── the static guard: catch the NEXT one before it ships ─────────────


def _locked_service_functions() -> set[str]:
    """Every `service.py` function whose body takes `_BATCH_ADD_LOCK`,
    derived from the source so a new one joins the guard for free."""
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(service))
    locked = {"batch_write_lock"}  # hands the lock to callers outside the module
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.With) and any(
                isinstance(item.context_expr, ast.Name)
                and item.context_expr.id == "_BATCH_ADD_LOCK"
                for item in inner.items
            ):
                locked.add(node.name)
                break
    return locked


def _called_names(node) -> set[str]:
    """Names called directly inside `node`, NOT descending into a nested
    sync `def` — that is exactly the threadpool escape hatch, so a call
    inside one is fine."""
    import ast

    names: set[str] = set()
    stack = list(ast.iter_child_nodes(node))
    while stack:
        child = stack.pop()
        if isinstance(child, (ast.FunctionDef, ast.Lambda)):
            continue  # sync closure / lambda -> handed to the threadpool
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
        stack.extend(ast.iter_child_nodes(child))
    return names


def test_no_async_handler_calls_a_locked_service_function():
    """An `async def` route that calls a lock-taking service function
    directly parks the event loop for as long as the lock is held. Either
    make the handler sync, or move the call into a sync closure handed to
    `run_in_threadpool`."""
    import ast
    import inspect

    from expense_recon.web import app as app_module

    locked = _locked_service_functions()
    assert "restore_set_aside_file" in locked and "assign_batch_cards" in locked, locked

    tree = ast.parse(inspect.getsource(app_module))
    offenders = {
        node.name: sorted(_called_names(node) & locked)
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and (_called_names(node) & locked)
    }
    assert not offenders, (
        f"async handler(s) blocking the event loop on the batch writer lock: "
        f"{offenders}. An OCR ingest holds that lock for minutes; a parked loop "
        f"stops /healthz and Fly restarts the machine, killing the ingest. Move "
        f"the call into a sync closure and `await run_in_threadpool(...)`, as "
        f"post_restore_set_aside and post_batch_cards do."
    )
