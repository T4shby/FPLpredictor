FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app

COPY pyproject.toml README.md /app/
COPY backend /app/backend
COPY data /app/data
COPY features /app/features
COPY modelling /app/modelling
COPY backtest /app/backtest
COPY worker /app/worker
COPY optimisation /app/optimisation
COPY scripts /app/scripts
COPY config /app/config
COPY docs /app/docs

RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
