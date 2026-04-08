// apps/web/components/ForecastChart.tsx

"use client";

import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { RiskForecast } from "@/app/lib/api";

interface Props {
  forecast: RiskForecast;
}

const LABEL_COLOR: Record<string, string> = {
  low:      "#34d399",
  moderate: "#fbbf24",
  high:     "#fb923c",
  critical: "#f87171",
};

export default function ForecastChart({ forecast }: Props) {
  const color = LABEL_COLOR[forecast.current?.label ?? "low"];

  const data = forecast.forecast?.points.map((p) => ({
    date:  p.date.slice(5),   // show MM-DD
    score: p.score,
  })) ?? [];

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-white/40 uppercase tracking-widest">
          7-day forecast
        </p>
        <span className="text-xs text-white/40">
          Confidence: {forecast.forecast?.confidence ?? "—"}
        </span>
      </div>

      <ResponsiveContainer width="100%" height={140}>
        <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "#111",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: "rgba(255,255,255,0.5)" }}
            itemStyle={{ color }}
          />
          <ReferenceLine y={50} stroke="rgba(255,255,255,0.1)" strokeDasharray="3 3" />
          <ReferenceLine y={70} stroke="rgba(255,100,100,0.2)" strokeDasharray="3 3" />
          <Area
            type="monotone"
            dataKey="score"
            stroke={color}
            strokeWidth={2}
            fill="url(#riskGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>

      {forecast.forecast?.peak_risk_date && (
        <p className="text-xs text-orange-400">
          ⚠ Peak risk expected {forecast.forecast.peak_risk_date}
        </p>
      )}
    </div>
  );
}