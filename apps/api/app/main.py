# apps/api/app/main.py

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.database import init_db
from app.routers import satellite, documents, risk

# Create the directory BEFORE the app object is built
os.makedirs("data/tiles", exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="FluxSense API",
    description="Environmental risk intelligence platform",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
   allow_origins=[
    "http://localhost:3000",
    "https://flux-sense.vercel.app",
    "https://*.vercel.app",
],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/tiles", StaticFiles(directory="data/tiles"), name="tiles")

app.include_router(satellite.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(risk.router,      prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}