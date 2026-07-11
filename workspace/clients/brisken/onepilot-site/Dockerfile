# Container image for the gated Brisken OnePilot prototype host (Fly.io).
# Tiny FastAPI/uvicorn app: serves the prototype HTML behind an access code
# and appends reviewer feedback to a JSONL file on the mounted volume (/data).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
# ./site/index.html is synced from the canonical deliverable by sync-site.py
# before deploy (it is gitignored, but present in the build context).
COPY site ./site

ENV BRISKEN_SITE_DATA=/data \
    BRISKEN_SITE_HTML=/app/site/index.html

EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
