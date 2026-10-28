"""What this process is and how long it has been running (backlog item 50).

Criss's "Failed to fetch" on the attach dialog (2026-09-10) could not be
explained, and the reason is structural: a fetch that rejects never got a
response, so the request never reached this app and NO server-side log can
ever contain it. The machine that served that day was replaced within the
hour and its logs went with it. The hosting half of the item turned out to
be a non-issue (the live machine was already pinned always-on), which
removed the cold-start theory and left the failure unexplained.

What remains buildable is the thing that makes a RECURRENCE provable. This
module is its foundation: one home for the process's own identity and age,
read by `/healthz` and stamped onto every client failure report, so the two
can never disagree about which machine answered.

The decisive comparison it enables: if a client says a request failed N
seconds ago and this process has been running for fewer than N seconds,
then this process did not exist when that request was made. The machine was
replaced or restarted underneath it, which is exactly the question the
backlog item asks and could not answer in September. Fly's own machine
event log is the corroborating source; it outlives the machine, so a report
timestamp is enough to look the event up later.

Uptime is measured on the monotonic clock so an NTP correction cannot make
a process look older or younger than it is; `started_at` is wall-clock,
for a human reading the row.

Build identity (backlog item 120) rides in the same snapshot, for the same
reason the machine id does: a stand-in looking at the app has to be able to
answer "is what I am looking at what I just shipped" without asking the
author. Until this existed the release list said only "Release" and the app
said nothing, so tying a running app to a commit meant correlating
timestamps by hand.

Two values, and NEITHER is a file anybody edits.

`image` is `FLY_IMAGE_REF`, which Fly sets on the machine from the image it
actually booted. No human writes it and no file holds it, so it cannot be
stale; it is also the exact string `flyctl releases --image` prints, which
makes it the join from a running process back to a release.

`commit` is baked into the image at build time (Dockerfile `ARG
GIT_COMMIT` becomes `ENV EXPENSE_RECON_COMMIT`), so it travels INSIDE the
artifact. That is what stops it going quietly stale: the version-file
failure, where a file claims one version while the code is another, needs
the claim and the code to be two separate things that can drift apart, and
here they are one layer of one image. A given image always reports the same
commit, and `image` names that image.

The failure still possible is absence: a deploy that omits `--build-arg
GIT_COMMIT=...` bakes an empty string. That reads as `""`, which is visibly
not a commit, and `image` still identifies the release. So the worst this
can do is decline to answer, never answer wrongly, which is the only trade
worth making in something an emergency reads.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

# Captured at import, which for this app is process start.
_STARTED_MONOTONIC = time.monotonic()
_STARTED_AT = datetime.now(timezone.utc)


def uptime_seconds() -> float:
    """Seconds this process has been running, on the monotonic clock."""
    return time.monotonic() - _STARTED_MONOTONIC


def started_at() -> str:
    return _STARTED_AT.isoformat()


def commit() -> str:
    """The commit this image was built from, or "" if the build did not say.

    Empty is a truthful "I cannot tell you", never a guess. Nothing falls
    back to reading git: the container holds no repository (the build
    context is this module directory and `.dockerignore` excludes `.git/`),
    so a fallback could only invent something.
    """
    return os.environ.get("EXPENSE_RECON_COMMIT", "").strip()


def image() -> str:
    """The image this machine booted, as Fly reports it at runtime.

    Identical to the string `flyctl releases --image` prints, so this is
    how a running process is tied back to a release.
    """
    return os.environ.get("FLY_IMAGE_REF", "").strip()


def snapshot() -> dict:
    """The parallel block `/healthz` and every failure report carry.

    Empty strings off Fly (local dev, tests): absent identity is stated as
    absent rather than invented, so a local row never reads like a
    production one. The same holds for `commit` and `image`.

    Build identity lives HERE rather than only in the health route so that
    every surface stamping this snapshot reports the same string, with no
    second stamp to keep in step.

    Since 2026-09-21 that includes the stored client-error rows, which
    carry `server_commit` and `server_image` beside `machine` and
    `process_started_at`. The stamp happens when the report ARRIVES, so a
    row keeps the build that served the failure however many deploys later
    it is read; before the columns existed, a historical failure could be
    tied to a build only while its serving process was still up, and after
    that only by correlating timestamps against Fly's release list. Rows
    written before the migration read `""` for the same reason an unstamped
    build does: the answer is not recoverable, and a back-fill could only
    write the build doing the back-filling.
    """
    return {
        "machine": os.environ.get("FLY_MACHINE_ID", ""),
        "region": os.environ.get("FLY_REGION", ""),
        "app": os.environ.get("FLY_APP_NAME", ""),
        "commit": commit(),
        "image": image(),
        "started_at": started_at(),
        "uptime_s": round(uptime_seconds(), 1),
    }


def process_predates(seconds_ago: float | None) -> bool | None:
    """Was this process already running `seconds_ago` seconds back?

    The probe's whole point. ``None`` when the caller could not say when
    the failure happened, because "unknown" must never read as "no": a
    false "the machine restarted" would send the next investigation
    chasing the hosting theory that already cost this item one cycle.
    """
    if seconds_ago is None:
        return None
    return uptime_seconds() >= seconds_ago
