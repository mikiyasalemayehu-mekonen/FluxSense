FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install torch from pre-downloaded wheels
COPY wheels/ /tmp/wheels/
RUN pip install --no-cache-dir \
    /tmp/wheels/torch-2.3.0+cpu.whl \
    /tmp/wheels/torchvision-0.18.0+cpu.whl \
    && rm -rf /tmp/wheels

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=120 -r requirements.txt

COPY . .

# Pre-download HF models at build time so first request is instant
RUN python -c "
from transformers import (
    SegformerImageProcessor, SegformerForSemanticSegmentation,
    DetrImageProcessor, DetrForObjectDetection,
    pipeline
)
SegformerImageProcessor.from_pretrained('nvidia/segformer-b2-finetuned-ade-512-512')
SegformerForSemanticSegmentation.from_pretrained('nvidia/segformer-b2-finetuned-ade-512-512')
DetrImageProcessor.from_pretrained('facebook/detr-resnet-50')
DetrForObjectDetection.from_pretrained('facebook/detr-resnet-50')
pipeline('summarization', model='sshleifer/distilbart-cnn-6-6')
pipeline('zero-shot-classification', model='typeform/distilbert-base-uncased-mnli')
pipeline('question-answering', model='deepset/roberta-base-squad2')
print('All models cached.')
"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]