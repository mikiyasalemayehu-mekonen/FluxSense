# apps/api/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import satellite

app = FastAPI(
    title="FluxSense API",
    description="Environmental risk intelligence platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(satellite.router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}