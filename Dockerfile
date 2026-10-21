# One image: FastAPI serves the API at /api and the built frontend at /.
FROM node:22-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
COPY artifacts/ /app/artifacts/
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/app backend/app
COPY ml/miach_panel.py ml/miach_panel.py
COPY ml/results_multi/ ml/results_multi/
COPY artifacts/ artifacts/
COPY --from=web /app/frontend/dist frontend/dist
WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
