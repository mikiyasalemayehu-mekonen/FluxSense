FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    gcc \
    libpq-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q --timeout=300 \
    "https://download.pytorch.org/whl/cpu/torch-2.3.0%2Bcpu-cp311-cp311-linux_x86_64.whl" \
    -O /tmp/torch.whl && \
    wget -q --timeout=300 \
    "https://download.pytorch.org/whl/cpu/torchvision-0.18.0%2Bcpu-cp311-cp311-linux_x86_64.whl" \
    -O /tmp/torchvision.whl && \
    pip install --no-cache-dir /tmp/torch.whl /tmp/torchvision.whl && \
    rm /tmp/torch.whl /tmp/torchvision.whl

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 -r requirements.txt

COPY . .

RUN python cache_models.py

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]