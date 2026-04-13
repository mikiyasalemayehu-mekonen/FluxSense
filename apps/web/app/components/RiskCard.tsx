// apps/web/components/RiskCard.tsx

import { TileAnalysis } from "@/app/lib/api";
import { Droplets, Trees, Building2, Zap } from "lucide-react";
import clsx from "clsx";

const LABEL_COLORS: Record<string, string> = {
  low:      "text-emerald-400 border-emerald-400/30 bg-emerald-400/10",
  moderate: "text-amber-400  border-amber-400/30  bg-amber-400/10",
  high:     "text-orange-400 border-orange-400/30 bg-orange-400/10",
  critical: "text-red-400    border-red-400/30    bg-red-400/10",
};

const TREND_ICONS: Record<string, string> = {
  rising:  "↑",
  falling: "↓",
  stable:  "→",
};

interface Props {
  analysis: TileAnalysis;
  loading?: boolean;
}

export default function RiskCard({ analysis, loading }: Props) {
  const risk = analysis.risk;
  const seg  = analysis.segmentation;
  const nlp  = analysis.nlp;

  if (loading) {
    return (
      <div className="animate-pulse space-y-3 p-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-8 bg-white/5 rounded-lg" />
        ))}
      </div>
    );
  }

  if (!risk) {
    return (
      <div className="p-4 text-sm text-white/50">
        Risk data unavailable for this region.
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">

      {/* Overall score */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-1">
            Risk score
          </p>
          <div className="flex items-baseline gap-2">
            <span className="text-5xl font-bold text-white">
              {Math.round(risk.overall_score)}
            </span>
            <span className="text-white/40 text-sm">/100</span>
          </div>
        </div>
        <div className={clsx(
          "px-3 py-1.5 rounded-full border text-sm font-medium uppercase tracking-wide",
          LABEL_COLORS[risk.label]
        )}>
          {risk.label} {TREND_ICONS[risk.trend]}
        </div>
      </div>

      {/* Score bar */}
      <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
        <div
          className={clsx("h-full rounded-full transition-all duration-700", {
            "bg-emerald-400": risk.label === "low",
            "bg-amber-400":   risk.label === "moderate",
            "bg-orange-400":  risk.label === "high",
            "bg-red-400":     risk.label === "critical",
          })}
          style={{ width: `${risk.overall_score}%` }}
        />
      </div>

      {/* Signal breakdown */}
      <div className="grid grid-cols-2 gap-2">
        {[
          { icon: Trees,    label: "Vegetation", value: risk.vegetation_score,  color: "text-emerald-400" },
          { icon: Droplets, label: "Water",      value: risk.water_score,       color: "text-blue-400" },
          { icon: Building2,label: "Urban exp.", value: risk.urban_exposure,    color: "text-slate-400" },
          { icon: Zap,      label: "Event",      value: risk.event_score,       color: "text-amber-400" },
        ].map(({ icon: Icon, label, value, color }) => (
          <div key={label}
            className="bg-white/5 rounded-xl p-3 flex items-center gap-2">
            <Icon size={14} className={color} />
            <div>
              <p className="text-xs text-white/40">{label}</p>
              <p className="text-sm font-medium text-white">
                {Math.round(value)}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Event type */}
      {nlp && (
        <div className="bg-white/5 rounded-xl p-3">
          <p className="text-xs text-white/40 mb-1">Detected event</p>
          <p className="text-sm font-medium capitalize text-white">
            {nlp.event_type}
            <span className="text-white/40 font-normal ml-1">
              ({Math.round(nlp.event_confidence * 100)}% conf.)
            </span>
          </p>
        </div>
      )}

      {/* Land cover */}
      {seg && (
        <div className="bg-white/5 rounded-xl p-3">
          <p className="text-xs text-white/40 mb-2">Land cover</p>
          <div className="space-y-1.5">
            {Object.entries(seg.class_coverage)
              .filter(([, v]) => v > 0)
              .sort(([, a], [, b]) => b - a)
              .map(([cls, pct]) => (
                <div key={cls} className="flex items-center gap-2">
                  <span className="text-xs text-white/50 w-20 capitalize">
                    {cls}
                  </span>
                  <div className="flex-1 h-1.5 bg-white/10 rounded-full">
                    <div
                      className="h-full bg-white/40 rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-white/50 w-10 text-right">
                    {pct.toFixed(1)}%
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* NLP summary */}
      {nlp?.summary && nlp.summary !== "No recent situation reports found for this region." && (
        <div className="bg-white/5 rounded-xl p-3">
          <p className="text-xs text-white/40 mb-1">Situation brief</p>
          <p className="text-xs text-white/70 leading-relaxed">
            {nlp.summary}
          </p>
        </div>
      )}

      <p className="text-xs text-white/30 leading-relaxed">
        {risk.explanation}
      </p>
    </div>
  );
}