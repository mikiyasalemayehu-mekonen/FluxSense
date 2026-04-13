// apps/web/lib/api.ts

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface BoundingBox {
  min_lon: number;
  min_lat: number;
  max_lon: number;
  max_lat: number;
}

export interface TileAnalysis {
  tile_id: string;
  bbox: BoundingBox;
  image_url: string;
  preview_url: string;
  acquired_at: string;
  status: string;
  message: string;
  segmentation: {
    result_id: string;
    dominant_class: string;
    class_coverage: Record<string, number>;
    colored_mask_url: string;
  };
  detection: {
    object_count: number;
    infrastructure_count: number;
    detections: Array<{ label: string; score: number; bbox_px: number[] }>;
  };
  nlp: {
    summary: string;
    event_type: string;
    event_confidence: number;
    sources: Array<{ title: string; url: string; source: string }>;
  };
  risk: {
    overall_score: number;
    label: string;
    trend: string;
    vegetation_score: number;
    water_score: number;
    urban_exposure: number;
    event_score: number;
    explanation: string;
  } | null;
}

export interface RiskForecast {
  tile_id: string;
  current: TileAnalysis["risk"];
  forecast: {
    points: Array<{ date: string; score: number }>;
    trend: string;
    peak_risk_date: string | null;
    confidence: string;
  };
  history: Array<{ overall_score: number; acquired_at: string }>;
}

export async function analyseTile(
  bbox: BoundingBox,
  dateFrom: string,
  dateTo: string
): Promise<TileAnalysis> {
  const res = await fetch(`${BASE}/satellite/tile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      bbox,
      date_from: dateFrom,
      date_to: dateTo,
      resolution: 10,
    }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getRiskForecast(
  bbox: BoundingBox
): Promise<RiskForecast> {
  const params = new URLSearchParams({
    min_lon: String(bbox.min_lon),
    min_lat: String(bbox.min_lat),
    max_lon: String(bbox.max_lon),
    max_lat: String(bbox.max_lat),
  });
  const res = await fetch(`${BASE}/risk/forecast?${params}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}