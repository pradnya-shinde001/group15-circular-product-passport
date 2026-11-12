# Image for the Circular Product Passport web app.
#
# Build:  docker build -t circular-passport .                           (small, without photo identification)
#         docker build -t circular-passport --build-arg INSTALL_CLIP=1 . (with CLIP, about 2 GB)
# Easier: docker compose up --build   (see docker-compose.yml)

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PASSPORT_DB=/data/passport.db \
    HF_HOME=/cache/huggingface

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ARG INSTALL_CLIP=0
RUN if [ "$INSTALL_CLIP" = "1" ]; then \
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
        pip install --no-cache-dir transformers; \
    fi

COPY . .

RUN useradd --create-home app && mkdir -p /data /cache && chown -R app /data /cache
USER app

EXPOSE 8000

# Docker checks every 30 s that the home page answers, and marks the container "unhealthy" if not.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
