FROM public.ecr.aws/docker/library/python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PIP_DEFAULT_TIMEOUT=120 PIP_RETRIES=10
WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY data/demo_documents.json ./data/demo_documents.json
RUN pip install --upgrade pip && pip install -e .
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data/reports /app/data/raw \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
