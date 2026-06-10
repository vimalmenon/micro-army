FROM python:3.13-slim AS builder

WORKDIR /app
COPY services/orpheus/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY services/orpheus/src/ ./src/
COPY shared/ ./shared/
ENV PYTHONPATH=/app/src:/app/shared

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
