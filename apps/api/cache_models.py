# apps/api/cache_models.py
from transformers import (
    SegformerImageProcessor,
    SegformerForSemanticSegmentation,
    DetrImageProcessor,
    DetrForObjectDetection,
    pipeline,
)

print("Caching SegFormer...")
SegformerImageProcessor.from_pretrained("nvidia/segformer-b2-finetuned-ade-512-512")
SegformerForSemanticSegmentation.from_pretrained("nvidia/segformer-b2-finetuned-ade-512-512")

print("Caching DETR...")
DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50")

print("Caching NLP models...")
pipeline("summarization", model="sshleifer/distilbart-cnn-6-6")
pipeline("zero-shot-classification", model="typeform/distilbert-base-uncased-mnli")
pipeline("question-answering", model="deepset/roberta-base-squad2")

print("All models cached successfully.")