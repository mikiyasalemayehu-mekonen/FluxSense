"use client";

import { useEffect, useRef, useState } from "react";
import type { BoundingBox } from "../lib/api";

type LeafletModule = typeof import("leaflet");
type LeafletMap = import("leaflet").Map;
type LeafletImageOverlay = import("leaflet").ImageOverlay;
type LeafletRectangle = import("leaflet").Rectangle;
type LeafletLatLng = import("leaflet").LatLng;
type LeafletMouseEvent = import("leaflet").LeafletMouseEvent;

interface Props {
  onBboxDrawn: (bbox: BoundingBox) => void;
  analysisResult?: {
    bbox: BoundingBox;
    previewUrl: string;
    maskUrl: string;
    showMask: boolean;
  } | null;
}

export default function Map({ onBboxDrawn, analysisResult }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<{ map: LeafletMap; L: LeafletModule } | null>(null);
  const overlayRef = useRef<LeafletImageOverlay | null>(null);
  const rectRef = useRef<LeafletRectangle | null>(null);
  const startLatLng = useRef<LeafletLatLng | null>(null);
  const isDragging = useRef(false);
  const [hint, setHint] = useState("Click and drag to draw a region");

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!containerRef.current) return;

    if (mapRef.current) {
      mapRef.current.map.remove();
      mapRef.current = null;
    }

    import("leaflet").then((L) => {
      const container = containerRef.current! as HTMLDivElement & {
        _leaflet_id?: number;
      };

      if (container._leaflet_id) {
        container._leaflet_id = undefined;
      }

      const map = L.map(container, {
        center: [20, 0],
        zoom: 2,
        zoomControl: false,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors",
        maxZoom: 19,
      }).addTo(map);

      L.control.zoom({ position: "topright" }).addTo(map);

      setTimeout(() => map.invalidateSize(), 200);

      map.on("mousedown", (event: LeafletMouseEvent) => {
        map.dragging.disable();
        isDragging.current = true;
        startLatLng.current = event.latlng;

        if (rectRef.current) {
          map.removeLayer(rectRef.current);
          rectRef.current = null;
        }
      });

      map.on("mousemove", (event: LeafletMouseEvent) => {
        if (!isDragging.current || !startLatLng.current) return;

        if (rectRef.current) map.removeLayer(rectRef.current);

        const start = startLatLng.current;

        rectRef.current = L.rectangle(
          [
            [start.lat, start.lng] as [number, number],
            [event.latlng.lat, event.latlng.lng] as [number, number],
          ],
          { color: "#3b82f6", weight: 2, fillOpacity: 0.15 }
        ).addTo(map);
      });

      map.on("mouseup", (event: LeafletMouseEvent) => {
        if (!isDragging.current || !startLatLng.current) return;

        isDragging.current = false;
        map.dragging.enable();

        const start = startLatLng.current;
        const end = event.latlng;

        const bbox: BoundingBox = {
          min_lon: Math.min(start.lng, end.lng),
          min_lat: Math.min(start.lat, end.lat),
          max_lon: Math.max(start.lng, end.lng),
          max_lat: Math.max(start.lat, end.lat),
        };

        if (Math.abs(bbox.max_lon - bbox.min_lon) < 0.01) return;

        startLatLng.current = null;
        setHint("Region selected - click Analyse");
        onBboxDrawn(bbox);
      });

      mapRef.current = { map, L };
    });

    return () => {
      if (mapRef.current) {
        mapRef.current.map.remove();
        mapRef.current = null;
      }
    };
  }, [onBboxDrawn]);

  useEffect(() => {
    if (!mapRef.current || !analysisResult) return;
    const { map, L } = mapRef.current;
    const { bbox, previewUrl, maskUrl, showMask } = analysisResult;

    if (overlayRef.current) {
      map.removeLayer(overlayRef.current);
      overlayRef.current = null;
    }

    const imageUrl = (showMask && maskUrl ? maskUrl : previewUrl)?.replace(
      "http://api:8000",
      "http://localhost:8000"
    );

    if (!imageUrl) return;

    overlayRef.current = L.imageOverlay(
      imageUrl,
      [[bbox.min_lat, bbox.min_lon], [bbox.max_lat, bbox.max_lon]],
      { opacity: 0.85 }
    );

    overlayRef.current.addTo(map);

    map.fitBounds(
      [[bbox.min_lat, bbox.min_lon], [bbox.max_lat, bbox.max_lon]],
      { padding: [60, 60] }
    );
  }, [analysisResult]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div
        ref={containerRef}
        style={{ position: "absolute", inset: 0 }}
      />
      <div style={{
        position: "absolute",
        bottom: 32,
        left: "50%",
        transform: "translateX(-50%)",
        background: "rgba(0,0,0,0.6)",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 999,
        padding: "6px 16px",
        fontSize: 12,
        color: "rgba(255,255,255,0.6)",
        pointerEvents: "none",
        whiteSpace: "nowrap",
      }}>
        {hint}
      </div>
    </div>
  );
}