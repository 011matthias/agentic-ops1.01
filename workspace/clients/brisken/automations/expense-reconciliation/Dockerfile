# Container image for the hosted review workbench (Fly.io).
# Local use does not need this; `expense-recon-web` runs the same app
# directly. The hosted app binds 0.0.0.0:8080 and keeps its run database
# and receipt files on a mounted volume at /data.
FROM python:3.12-slim

# DejaVu carries the full Latin set (umlauts, euro sign) the body-only
# mail renderer needs; Pillow's embedded default font does not.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src

# Install the package plus the web extra into the system environment, so the
# expense-recon-web console script is on PATH.
#
# The versions come from uv.lock, not from the open ranges in
# pyproject.toml (backlog item 124). Installing from the ranges meant each
# deploy resolved whatever was newest that day, so two deploys a week apart
# could run different FastAPI / openai / pypdf / aiosmtpd builds and a green
# suite proved nothing about the set production actually ran. The lock is
# exported to a fully pinned, hash-checked requirements file and installed
# first; the project itself then goes in with --no-deps so nothing can
# re-resolve a dependency behind the lock. An upgrade is now a commit that
# moves uv.lock, which the suite then runs against.
# --frozen: never re-lock during a build (a drifted lock fails the build
# instead of silently resolving something new).
RUN uv export --frozen --no-dev --extra web --no-emit-project \
        --format requirements-txt -o /tmp/requirements.lock.txt \
    && uv pip install --system --no-cache -r /tmp/requirements.lock.txt \
    && uv pip install --system --no-cache --no-deps . \
    && rm /tmp/requirements.lock.txt

ENV EXPENSE_RECON_WEB_DATA=/data
EXPOSE 8080

# --no-open: never try to launch a browser inside the container.
CMD ["expense-recon-web", "--host", "0.0.0.0", "--port", "8080", "--data", "/data", "--no-open"]
