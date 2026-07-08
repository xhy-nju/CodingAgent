FROM node:22-bookworm AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json ./package.json
RUN npm install --no-package-lock
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY pyproject.toml ./
COPY src ./src
COPY config ./config
COPY demos ./demos
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "coding_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]
