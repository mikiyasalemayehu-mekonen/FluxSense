# apps/api/app/ml/hf_client.py

import httpx
import base64
import os
from PIL import Image
import numpy as np
import io

HF_API_URL = "https://router.huggingface.co/hf-inference/models"
HF_TOKEN   = os.getenv("HF_API_TOKEN", "").strip()


def _get_headers() -> dict:
    """Return headers with auth only if token is set."""
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    return headers


def _image_to_base64(image_path: str) -> str:
    import rasterio
    with rasterio.open(image_path) as src:
        r = src.read(1)
        g = src.read(2)
        b = src.read(3)
    arr = np.stack([r, g, b], axis=-1)
    arr = (np.clip(arr, 0, 1) * 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


async def run_segmentation(image_path: str) -> dict:
    img_b64  = _image_to_base64(image_path)
    headers  = _get_headers()
    url      = f"{HF_API_URL}/nvidia/segformer-b0-finetuned-ade-512-512"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json={"inputs": img_b64})
        if resp.status_code == 503:
            import asyncio
            await asyncio.sleep(25)
            resp = await client.post(url, headers=headers, json={"inputs": img_b64})
        resp.raise_for_status()
        return resp.json()


async def run_summarization(text: str) -> str:
    if not text or len(text) < 100:
        return "No sufficient text to summarize."

    headers = _get_headers()
    url     = f"{HF_API_URL}/sshleifer/distilbart-cnn-6-6"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            url, headers=headers,
            json={
                "inputs": text[:1024],
                "parameters": {"max_length": 150, "min_length": 40, "do_sample": False},
            },
        )
        if resp.status_code == 503:
            import asyncio
            await asyncio.sleep(25)
            resp = await client.post(url, headers=headers, json={"inputs": text[:1024]})
        resp.raise_for_status()
        result = resp.json()
        return result[0]["summary_text"] if result else text[:200]


async def run_zero_shot(text: str, labels: list[str]) -> dict:
    headers = _get_headers()
    url     = f"{HF_API_URL}/typeform/distilbert-base-uncased-mnli"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            url, headers=headers,
            json={"inputs": text, "parameters": {"candidate_labels": labels}},
        )
        if resp.status_code == 503:
            import asyncio
            await asyncio.sleep(25)
            resp = await client.post(
                url, headers=headers,
                json={"inputs": text, "parameters": {"candidate_labels": labels}},
            )
        resp.raise_for_status()
        return resp.json()