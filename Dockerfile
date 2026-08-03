# mywa — WhatsApp contact intelligence (pure Python stdlib, zero third-party deps)
FROM python:3.11-slim

ENV PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy application source only. Sensitive data (contacts/, real_out/) is
# bind-mounted as a volume and never baked into an image.
COPY . .

# Default entrypoint exposes the CLI (run/serve). Override via CMD in compose.
ENTRYPOINT ["python", "-m", "mywa"]

# Dashboard default port when serving.
EXPOSE 8080