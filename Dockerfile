FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install torch CPU-only séparément — layer cachée tant que ça ne change pas
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install requirements — layer cachée tant que requirements.txt ne change pas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code — layer qui change le plus souvent
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]