FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --create-home appuser && mkdir -p /app/uploads && chown -R appuser /app
USER appuser

EXPOSE 8000
# 1) bring the database schema up to date, 2) start the API.
# --proxy-headers makes the real visitor IP visible behind the web server (needed for the rate limits).
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*' --workers ${WEB_CONCURRENCY:-2}"]
