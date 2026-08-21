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
COPY pyproject.toml ./
COPY src ./src

# Install the package plus the web extra into the system environment, so the
# expense-recon-web console script is on PATH.
RUN uv pip install --system --no-cache ".[web]"

ENV EXPENSE_RECON_WEB_DATA=/data
EXPOSE 8080

# --no-open: never try to launch a browser inside the container.
CMD ["expense-recon-web", "--host", "0.0.0.0", "--port", "8080", "--data", "/data", "--no-open"]
