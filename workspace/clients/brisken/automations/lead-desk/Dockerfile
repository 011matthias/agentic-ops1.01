# Container image for the hosted Lead Desk (Fly.io). Binds 0.0.0.0:8080 and
# keeps its SQLite database on a mounted volume at /data. The database holds
# lead PII, so it lives only on the volume and is never committed.
FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src

# Install the package plus the web extra into the system environment so the
# lead-desk-web console script is on PATH.
RUN uv pip install --system --no-cache ".[web]"

ENV LEAD_DESK_DATA=/data
EXPOSE 8080

# --no-open: never try to launch a browser inside the container.
CMD ["lead-desk-web", "--host", "0.0.0.0", "--port", "8080", "--data", "/data", "--no-open"]
