FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gdal-bin libgdal-dev gcc libpq-dev wget && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --timeout=300 torch==2.3.0+cpu torchvision==0.18.0+cpu --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 -r requirements.txt

COPY . .

RUN python cache_models.py

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]