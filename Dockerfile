# Production image (TRD §8, SUG-19): one container serving API + built SPA.
# Stage 1: build the React app.
FROM node:26-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime.
FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY data/ /app/data/
COPY --from=frontend /app/frontend/dist /app/frontend/dist
RUN useradd --create-home bonik && mkdir -p /var/lib/bonik/uploads && chown bonik /var/lib/bonik/uploads
USER bonik
ENV UPLOAD_DIR=/var/lib/bonik/uploads
EXPOSE 8000
# Behind the host's HTTPS proxy: trust X-Forwarded-For so audit IPs and the per-IP auth limit see the
# real client, not the proxy (else one busy user could block every login). PORT is set by hosts like Render.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips \"${FORWARDED_ALLOW_IPS:-*}\""]
