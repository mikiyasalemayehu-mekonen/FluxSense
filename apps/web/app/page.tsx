// apps/web/app/page.tsx

"use client";

import { useCallback, useState } from "react";
import dynamic from "next/dynamic";
import clsx from "clsx";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  BarChart3,
  Eye,
  FileText,
  Globe2,
  Layers3,
  Loader2,
  MapPinned,
  Satellite,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import RiskCard from "../app/components/RiskCard";
import ForecastChart from "../app/components/ForecastChart";
import {
  BoundingBox,
  TileAnalysis,
  RiskForecast,
  analyseTile,
  getRiskForecast,
} from "../app/lib/api";

const Map = dynamic(() => import("../app/components/Map"), { ssr: false });

type Tab = "risk" | "forecast" | "sources";

const DATE_FROM = "2024-06-01";
const DATE_TO   = "2024-06-30";

const featureCards = [
  {
    icon: ShieldCheck,
    title: "Unified risk scoring",
    text: "Blend segmentation, detection, and report intelligence into one clear score.",
  },
  {
    icon: MapPinned,
    title: "Interactive geospatial workspace",
    text: "Select a region on the map and inspect the exact area under analysis.",
  },
  {
    icon: TrendingUp,
    title: "Forecast-ready insights",
    text: "Track pressure trends over time and plan response before conditions escalate.",
  },
];

const steps = [
  {
    number: "01",
    title: "Draw a region",
    text: "Select any bounding box on the map to define the area you want to monitor.",
  },
  {
    number: "02",
    title: "Run analysis",
    text: "Fuse satellite preview, segmentation, detection, and NLP in a single workflow.",
  },
  {
    number: "03",
    title: "Act on evidence",
    text: "Review the risk score, forecast, and source documents in one place.",
  },
];

const tabs: Tab[] = ["risk", "forecast", "sources"];

export default function Home() {
  const [bbox,     setBbox]     = useState<BoundingBox | null>(null);
  const [analysis, setAnalysis] = useState<TileAnalysis | null>(null);
  const [forecast, setForecast] = useState<RiskForecast | null>(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);
  const [tab,      setTab]      = useState<Tab>("risk");
  const [showMask, setShowMask] = useState(false);

  const handleBboxDrawn = useCallback((nextBbox: BoundingBox) => {
    setBbox(nextBbox);
    setAnalysis(null);
    setForecast(null);
    setError(null);
    setShowMask(false);
  }, []);

  const handleAnalyse = async () => {
    if (!bbox) return;
    setLoading(true);
    setError(null);
    try {
      const [result, nextForecast] = await Promise.all([
        analyseTile(bbox, DATE_FROM, DATE_TO),
        getRiskForecast(bbox).catch(() => null),
      ]);
      setAnalysis(result);
      setForecast(nextForecast);
      setTab("risk");
    } catch (nextError: unknown) {
      setError(nextError instanceof Error ? nextError.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="relative min-h-screen overflow-x-hidden bg-[#070A13] text-white">
      {/* Background blobs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-[-8rem] top-[-9rem] h-72 w-72 rounded-full bg-cyan-500/20 blur-3xl" />
        <div className="absolute right-[-6rem] top-24 h-80 w-80 rounded-full bg-fuchsia-500/20 blur-3xl" />
        <div className="absolute bottom-[-10rem] left-1/3 h-96 w-96 rounded-full bg-amber-400/10 blur-3xl" />
      </div>

      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 py-5 sm:px-6 lg:px-8 lg:py-8">

        {/* ── Header ─────────────────────────────────────────────── */}
        <header className="flex flex-wrap items-center justify-between gap-4 rounded-3xl border border-white/10 bg-white/5 px-5 py-4 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 shadow-lg shadow-cyan-500/20">
              <Satellite size={20} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-[0.24em] text-white/70 uppercase">FluxSense</p>
              <p className="text-xs text-white/45">Environmental risk intelligence</p>
            </div>
          </div>
          <nav className="hidden items-center gap-6 text-sm text-white/60 md:flex">
            <a href="#platform" className="transition hover:text-white">Platform</a>
            <a href="#workflow" className="transition hover:text-white">Workflow</a>
            <a href="#demo"     className="transition hover:text-white">Live demo</a>
          </nav>
          <a href="#demo"
            className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-2 text-sm font-medium text-cyan-100 transition hover:border-cyan-300/50 hover:bg-cyan-400/15">
            Launch workspace <ArrowRight size={16} />
          </a>
        </header>

        {/* ── Hero ───────────────────────────────────────────────── */}
        <section className="grid items-center gap-8 lg:grid-cols-[1.06fr_0.94fr] lg:gap-10">
          <div className="space-y-7">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-xs font-medium text-cyan-100 backdrop-blur-sm">
              <Sparkles size={14} />
              Satellite + NLP + forecasting in one product
            </div>
            <div className="space-y-5">
              <h1 className="max-w-3xl text-5xl font-bold leading-[0.95] tracking-[-0.05em] text-white sm:text-6xl lg:text-7xl">
                Monitor environmental risk with a sharper, faster workflow.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-white/70 sm:text-lg">
                FluxSense turns satellite imagery, segmentation, detection, and report intelligence into a live command center for environmental monitoring and risk planning.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <a href="#demo"
                className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-100">
                Try the live demo <ArrowRight size={16} />
              </a>
              <a href="#platform"
                className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:border-white/25 hover:bg-white/10">
                Explore platform
              </a>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                { icon: Globe2,   label: "Coverage", value: "Global regions" },
                { icon: Layers3,  label: "Signals",  value: "Satellite + reports" },
                { icon: BarChart3,label: "Output",   value: "Risk + forecast" },
              ].map(({ icon: Icon, label, value }) => (
                <div key={label} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4 backdrop-blur-sm">
                  <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-xl bg-white/10 text-cyan-200">
                    <Icon size={18} />
                  </div>
                  <p className="text-xs uppercase tracking-[0.22em] text-white/40">{label}</p>
                  <p className="mt-1 text-sm font-medium text-white">{value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Hero card */}
          <div className="relative">
            <div className="absolute inset-0 rounded-[2rem] bg-gradient-to-br from-cyan-500/20 via-blue-500/10 to-fuchsia-500/20 blur-2xl" />
            <div className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-slate-950/75 p-5 shadow-2xl backdrop-blur-xl">
              <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-white/45">Command center</p>
                  <p className="mt-1 text-lg font-semibold text-white">Live monitoring snapshot</p>
                </div>
                <div className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs text-emerald-100">
                  Active
                </div>
              </div>
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                {[
                  { icon: Satellite,   title: "Satellite preview", text: "Visual context for the selected region." },
                  { icon: Activity,    title: "Signal fusion",     text: "Risk score, detection, and NLP combined." },
                  { icon: FileText,    title: "Evidence trail",    text: "Linked sources and report snippets." },
                  { icon: TrendingUp,  title: "Forecast layer",    text: "Direction and peak risk timing." },
                ].map(({ icon: Icon, title, text }) => (
                  <div key={title} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-400/10 text-cyan-200">
                      <Icon size={16} />
                    </div>
                    <p className="text-sm font-semibold text-white">{title}</p>
                    <p className="mt-1 text-sm leading-6 text-white/55">{text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── Features ───────────────────────────────────────────── */}
        <section id="platform" className="grid gap-4 md:grid-cols-3">
          {featureCards.map(({ icon: Icon, title, text }) => (
            <div key={title}
              className="group rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl transition hover:-translate-y-1 hover:border-cyan-400/25">
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400/20 to-blue-500/20 text-cyan-200">
                <Icon size={22} />
              </div>
              <h2 className="text-xl font-semibold text-white">{title}</h2>
              <p className="mt-3 text-sm leading-7 text-white/60">{text}</p>
            </div>
          ))}
        </section>

        {/* ── Workflow ───────────────────────────────────────────── */}
        <section id="workflow" className="grid gap-4 lg:grid-cols-3">
          {steps.map(({ number, title, text }) => (
            <div key={number} className="rounded-3xl border border-white/10 bg-[#0B1020]/80 p-6 backdrop-blur-xl">
              <p className="text-3xl font-semibold tracking-[-0.06em] text-cyan-200">{number}</p>
              <h3 className="mt-4 text-lg font-semibold text-white">{title}</h3>
              <p className="mt-2 text-sm leading-7 text-white/60">{text}</p>
            </div>
          ))}
        </section>

        {/* ── Live demo ──────────────────────────────────────────── */}
        <section id="demo" className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">

          {/* Map panel */}
          <div className="overflow-hidden rounded-[2rem] border border-white/10 bg-slate-950/70 shadow-2xl backdrop-blur-xl">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 px-5 py-4">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-white/40">Live workspace</p>
                <h2 className="mt-1 text-2xl font-semibold text-white">Draw a region and analyse it</h2>
              </div>
              <button
                onClick={handleAnalyse}
                disabled={!bbox || loading}
                className={clsx(
                  "inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold transition",
                  !bbox || loading
                    ? "cursor-not-allowed bg-white/8 text-white/30"
                    : "bg-cyan-400 text-slate-950 hover:bg-cyan-300"
                )}
              >
                {loading ? (
                  <><Loader2 size={16} className="animate-spin" /> Running analysis</>
                ) : (
                  <><Satellite size={16} /> {bbox ? "Analyse region" : "Draw a region first"}</>
                )}
              </button>
            </div>

            {error && (
              <div className="mx-5 mt-5 flex items-start gap-2 rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                <p>{error}</p>
              </div>
            )}

            {analysis?.message && (
              <div className="mx-5 mt-4 inline-flex rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs text-white/70">
                {analysis.message}
              </div>
            )}

            <div className="p-5">
              <div className="h-[560px] overflow-hidden rounded-[1.5rem] border border-white/10 bg-black/20">
                <Map
                  onBboxDrawn={handleBboxDrawn}
                  analysisResult={
                    analysis ? {
                      bbox:       analysis.bbox,
                      previewUrl: analysis.preview_url,
                      maskUrl:    analysis.segmentation?.colored_mask_url ?? "",
                      showMask,
                    } : null
                  }
                />
              </div>
            </div>

            {analysis && (
              <div className="flex flex-wrap items-center gap-2 border-t border-white/10 px-5 py-4">
                <button
                  onClick={() => setShowMask(false)}
                  className={clsx(
                    "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-medium transition",
                    !showMask ? "border-cyan-400/30 bg-cyan-400/15 text-cyan-50" : "border-white/10 bg-white/5 text-white/55"
                  )}
                >
                  <Eye size={14} /> Satellite
                </button>
                <button
                  onClick={() => setShowMask(true)}
                  className={clsx(
                    "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-medium transition",
                    showMask ? "border-cyan-400/30 bg-cyan-400/15 text-cyan-50" : "border-white/10 bg-white/5 text-white/55"
                  )}
                >
                  <Layers3 size={14} /> Segmentation
                </button>
              </div>
            )}
          </div>

          {/* Results sidebar */}
          <aside className="overflow-hidden rounded-[2rem] border border-white/10 bg-[#0B1020]/80 shadow-2xl backdrop-blur-xl">
            <div className="border-b border-white/10 px-5 py-4">
              <p className="text-xs uppercase tracking-[0.28em] text-white/40">Insights</p>
              <h2 className="mt-1 text-2xl font-semibold text-white">
                {analysis ? "Analysis results" : "What you get"}
              </h2>
            </div>

            {analysis ? (
              <>
                <div className="border-b border-white/10 px-4 pt-3">
                  <div className="grid grid-cols-3 gap-2">
                    {tabs.map((item) => (
                      <button key={item} onClick={() => setTab(item)}
                        className={clsx(
                          "rounded-t-2xl px-3 py-3 text-xs font-semibold capitalize transition",
                          tab === item
                            ? "border border-white/10 border-b-transparent bg-white/8 text-white"
                            : "text-white/45 hover:text-white/70"
                        )}>
                        {item}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="max-h-[650px] overflow-y-auto">
                  {tab === "risk" && <RiskCard analysis={analysis} />}

                  {tab === "forecast" && forecast?.forecast ? (
                    <ForecastChart forecast={forecast} />
                  ) : tab === "forecast" && (
                    <div className="p-5 text-sm text-white/40">
                      No forecast data yet for this region.
                    </div>
                  )}

                  {tab === "sources" && (
                    <div className="space-y-3 p-4">
                      <p className="text-xs uppercase tracking-[0.24em] text-white/40">Data sources</p>
                      {!analysis.nlp?.sources?.length ? (
                        <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-white/55">
                          No external reports found for this region.
                        </div>
                      ) : (
                        analysis.nlp.sources.map((source, index) => (
                          <div key={index} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                            <p className="text-sm font-medium text-white">{source.title}</p>
                            <p className="mt-1 text-xs uppercase tracking-[0.2em] text-white/35">{source.source}</p>
                            {source.url && (
                              <a href={source.url} target="_blank" rel="noopener noreferrer"
                                className="mt-3 inline-flex items-center gap-2 text-sm text-cyan-200 transition hover:text-cyan-100">
                                Open report <ArrowRight size={14} />
                              </a>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </>
            ) : loading ? (
              <div className="space-y-3 p-5">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-16 animate-pulse rounded-2xl bg-white/5" />
                ))}
              </div>
            ) : (
              <div className="space-y-5 p-5">
                <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-cyan-400/10 via-blue-400/10 to-fuchsia-400/10 p-5">
                  <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 text-cyan-200">
                    <Sparkles size={20} />
                  </div>
                  <h3 className="text-xl font-semibold text-white">Full AI pipeline on demand</h3>
                  <p className="mt-2 text-sm leading-7 text-white/60">
                    Draw a region, run the analysis, and get satellite segmentation, risk scoring, and NLP report summaries in one response.
                  </p>
                </div>
                <div className="space-y-3">
                  {[
                    "Risk scoring from satellite and NLP signals",
                    "Forecasts that surface pressure changes early",
                    "Source-backed summaries for faster review",
                  ].map((item) => (
                    <div key={item} className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/5 p-4">
                      <div className="mt-0.5 rounded-full bg-emerald-400/15 p-1 text-emerald-300">
                        <ShieldCheck size={14} />
                      </div>
                      <p className="text-sm leading-6 text-white/65">{item}</p>
                    </div>
                  ))}
                </div>
                <p className="rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-sm text-white/55">
                  Draw a rectangle on the map to generate a region-specific analysis, then switch between the risk, forecast, and source tabs.
                </p>
              </div>
            )}
          </aside>
        </section>

        {/* ── Footer CTA ─────────────────────────────────────────── */}
        <section className="rounded-[2rem] border border-white/10 bg-white/5 px-6 py-8 backdrop-blur-xl lg:px-8">
          <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-white/40">Built for operations</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-white sm:text-4xl">
                Environmental intelligence, not a research prototype.
              </h2>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-white/60">
                Strong branding, clear hierarchy, actionable cards, and a live workspace that makes the analysis feel usable in real workflows.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {["One-page product story", "Live map demo", "Risk + forecast panels", "Evidence-linked sources"].map((item) => (
                <div key={item} className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-4 text-sm text-white/65">
                  {item}
                </div>
              ))}
            </div>
          </div>
        </section>

      </div>
    </main>
  );
}