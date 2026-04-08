# FluxSense — Environmental Risk Intelligence

AI-powered satellite analysis platform that fuses Copernicus imagery,
humanitarian reports, and ML models to assess environmental risk in real time.

## Live demo
**[fluxsense.vercel.app](https://fluxsense.vercel.app)**

## What it does
1. User draws a region on the map
2. Sentinel-2 satellite tile is fetched from Copernicus
3. SegFormer classifies land cover (water, vegetation, urban, bare soil)
4. DETR detects infrastructure objects
5. BART summarizes ReliefWeb + USGS situation reports
6. Zero-shot NLI classifier identifies event type (flood, wildfire, drought…)
7. Risk engine computes a 0–100 composite score
8. 7-day forecast generated from historical trend

## Tech stack
- **Backend**: FastAPI, PostGIS, Redis, rasterio
- **ML**: SegFormer, DETR, DistilBART, zero-shot NLI (HuggingFace)
- **Data**: Copernicus Sentinel-2, ReliefWeb, USGS Water Services
- **Frontend**: Next.js, Leaflet, Recharts, Tailwind
- **Infra**: Docker, Fly.io, Vercel

## Run locally
```bash
cp .env.example .env   # fill in your API keys
docker compose up --build
cd apps/web && npm install && npm run dev
```

Open http://localhost:3000