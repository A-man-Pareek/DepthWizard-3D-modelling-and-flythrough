import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Activity, Droplets, Waves } from "lucide-react";
import { Panel, Readout, SectionHeading, StatusBadge } from "@/components/dw/primitives";

export const Route = createFileRoute("/hazards")({
  head: () => ({
    meta: [
      { title: "Hazard Analysis — Flood, Earthquake & Landslide | DepthWizard" },
      {
        name: "description",
        content:
          "Proposed hazard modules for DepthWizard: flood simulation, earthquake impact and landslide susceptibility, presented as integration-ready interfaces.",
      },
      { property: "og:title", content: "Hazard Analysis — DepthWizard" },
      {
        property: "og:description",
        content: "Proposed flood, earthquake and landslide hazard interfaces over reconstructed terrain.",
      },
    ],
  }),
  component: HazardsPage,
});

function Slider({
  label,
  value,
  onChange,
  min,
  max,
  step,
  unit,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
  unit: string;
}) {
  return (
    <div className="mt-3">
      <div className="flex items-center justify-between">
        <span className="label-mono">{label}</span>
        <span className="font-mono text-[10px] text-primary">
          {value}
          {unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 h-1 w-full cursor-pointer appearance-none rounded-full bg-surface-2 accent-primary"
      />
    </div>
  );
}

function FloodCard() {
  const [level, setLevel] = useState(35);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const runSim = async () => {
    setLoading(true);
    try {
      const form = new FormData();
      form.append("disaster_type", "FLOOD");
      form.append("intensity", level <= 33 ? "low" : level <= 66 ? "medium" : "high");
      form.append("seed", "42");
      const res = await fetch("http://127.0.0.1:8000/simulate-disaster", { method: "POST", body: form });
      if (res.ok) setResult(await res.json());
    } catch (e) { console.warn("Flood sim failed:", e); }
    setLoading(false);
  };

  const stats = result?.summaryStatistics;
  return (
    <Panel
      eyebrow="HAZARD 01"
      title="Flood Simulation"
      right={<StatusBadge kind={result ? "active" : "proposed"} />}
      className="h-full"
    >
      <div className="relative h-40 overflow-hidden rounded-sm border border-border/70 bg-background/50">
        <div className="hud-grid-fine absolute inset-0 opacity-40" />
        <svg viewBox="0 0 200 100" preserveAspectRatio="none" className="absolute inset-0 size-full">
          <path
            d="M0,78 L18,60 L36,68 L54,42 L72,54 L92,30 L112,50 L134,38 L156,62 L178,48 L200,66 L200,100 L0,100 Z"
            fill="color-mix(in oklch, var(--surface-2) 80%, transparent)"
            stroke="var(--border-strong, var(--border))"
          />
        </svg>
        <div
          className="absolute inset-x-0 bottom-0 border-t border-accent/60 bg-accent/25 transition-all duration-300"
          style={{ height: `${level}%` }}
        />
        <span className="absolute top-2 right-2 font-mono text-[10px] tracking-[0.12em] text-accent">
          WATER PLANE {level}%
        </span>
      </div>
      <Slider label="Water Level" value={level} onChange={setLevel} min={0} max={100} step={1} unit="%" />
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Readout label="Buildings Affected" value={stats ? `${stats.affectedBuildings}/${stats.totalBuildings}` : "—"} tone={stats ? "primary" : "muted"} />
        <Readout label="Hazard Area" value={stats ? `${Math.round(stats.totalHazardAreaSqMeters)} m²` : "—"} tone={stats ? "primary" : "muted"} />
      </div>
      <button
        onClick={runSim}
        disabled={loading}
        className="mt-3 w-full rounded-sm border border-accent/50 bg-accent/15 px-3 py-2 font-mono text-[11px] tracking-[0.12em] text-accent uppercase transition-colors hover:bg-accent/25 disabled:opacity-50"
      >
        {loading ? "SIMULATING…" : "RUN FLOOD SIMULATION"}
      </button>
      {result && (
        <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
          Simulation complete. {stats?.highAndCriticalCount ?? 0} high/critical impact structures detected.
          Avg exposure: {stats?.averageExposurePercentage ?? 0}%.
        </p>
      )}
    </Panel>
  );
}

function EarthquakeCard() {
  const [magnitude, setMagnitude] = useState(6.2);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const rings = [1, 2, 3];

  const runSim = async () => {
    setLoading(true);
    try {
      const form = new FormData();
      form.append("disaster_type", "CYCLONE");
      form.append("intensity", magnitude <= 5.5 ? "low" : magnitude <= 7 ? "medium" : "high");
      form.append("seed", "42");
      const res = await fetch("http://127.0.0.1:8000/simulate-disaster", { method: "POST", body: form });
      if (res.ok) setResult(await res.json());
    } catch (e) { console.warn("Earthquake sim failed:", e); }
    setLoading(false);
  };

  const stats = result?.summaryStatistics;
  return (
    <Panel
      eyebrow="HAZARD 02"
      title="Earthquake / Cyclone Impact"
      right={<StatusBadge kind={result ? "active" : "proposed"} />}
      className="h-full"
    >
      <div className="relative grid h-40 place-items-center overflow-hidden rounded-sm border border-border/70 bg-background/50">
        <div className="hud-grid-fine absolute inset-0 opacity-40" />
        {rings.map((r) => (
          <span
            key={r}
            className="absolute rounded-full border border-warning/50"
            style={{
              width: `${r * (magnitude * 4)}px`,
              height: `${r * (magnitude * 4)}px`,
              opacity: 0.85 - r * 0.2,
            }}
          />
        ))}
        <span className="size-2 rounded-full bg-warning" />
        <span className="absolute top-2 right-2 font-mono text-[10px] tracking-[0.12em] text-warning">
          EPICENTRE M{magnitude.toFixed(1)}
        </span>
      </div>
      <Slider
        label="Magnitude (Mw)"
        value={magnitude}
        onChange={setMagnitude}
        min={4}
        max={9}
        step={0.1}
        unit=""
      />
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Readout label="Buildings Affected" value={stats ? `${stats.affectedBuildings}/${stats.totalBuildings}` : "—"} tone={stats ? "primary" : "muted"} />
        <Readout label="High/Critical" value={stats ? `${stats.highAndCriticalCount}` : "—"} tone={stats ? "primary" : "muted"} />
      </div>
      <button
        onClick={runSim}
        disabled={loading}
        className="mt-3 w-full rounded-sm border border-warning/50 bg-warning/15 px-3 py-2 font-mono text-[11px] tracking-[0.12em] text-warning uppercase transition-colors hover:bg-warning/25 disabled:opacity-50"
      >
        {loading ? "SIMULATING…" : "RUN CYCLONE / EARTHQUAKE SIM"}
      </button>
      {result && (
        <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
          Simulation complete. Impact area: {Math.round(stats?.totalHazardAreaSqMeters ?? 0)} m².
          Avg exposure: {stats?.averageExposurePercentage ?? 0}%.
        </p>
      )}
    </Panel>
  );
}

function LandslideCard() {
  const [slope, setSlope] = useState(28);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const factors = [
    { label: "Slope", icon: Activity },
    { label: "Aspect", icon: Waves },
    { label: "Curvature", icon: Activity },
    { label: "Land Cover", icon: Droplets },
    { label: "Drainage", icon: Droplets },
  ];

  const runSim = async () => {
    setLoading(true);
    try {
      const form = new FormData();
      form.append("disaster_type", "LANDSLIDE");
      form.append("intensity", slope <= 20 ? "low" : slope <= 40 ? "medium" : "high");
      form.append("seed", "42");
      const res = await fetch("http://127.0.0.1:8000/simulate-disaster", { method: "POST", body: form });
      if (res.ok) setResult(await res.json());
    } catch (e) { console.warn("Landslide sim failed:", e); }
    setLoading(false);
  };

  const stats = result?.summaryStatistics;
  return (
    <Panel
      eyebrow="HAZARD 03"
      title="Landslide Susceptibility"
      right={<StatusBadge kind={result ? "active" : "integration-ready"} />}
      className="h-full"
    >
      <div className="relative h-40 overflow-hidden rounded-sm border border-border/70 bg-background/50">
        <div className="hud-grid-fine absolute inset-0 opacity-40" />
        <div className="absolute inset-0 grid grid-cols-12 grid-rows-6 gap-px p-2">
          {Array.from({ length: 72 }).map((_, i) => {
            const row = Math.floor(i / 12);
            const intensity = Math.max(0, Math.min(1, (slope / 60) * (1 - row / 7) * 1.4));
            return (
              <span
                key={i}
                className="rounded-[1px]"
                style={{
                  background: `color-mix(in oklch, var(--warning) ${Math.round(
                    intensity * 90,
                  )}%, transparent)`,
                }}
              />
            );
          })}
        </div>
        <span className="absolute top-2 right-2 font-mono text-[10px] tracking-[0.12em] text-warning">
          SLOPE THRESHOLD {slope}°
        </span>
      </div>
      <Slider label="Slope Threshold" value={slope} onChange={setSlope} min={5} max={60} step={1} unit="°" />
      <div className="mt-3 flex flex-wrap gap-1.5">
        {factors.map((f) => (
          <span
            key={f.label}
            className="inline-flex items-center gap-1.5 rounded-sm border border-border/70 bg-background/40 px-2 py-1 font-mono text-[10px] tracking-[0.1em] text-muted-foreground uppercase"
          >
            <f.icon className="size-3 text-primary" />
            {f.label}
          </span>
        ))}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Readout label="Buildings Affected" value={stats ? `${stats.affectedBuildings}/${stats.totalBuildings}` : "—"} tone={stats ? "primary" : "muted"} />
        <Readout label="Displaced Area" value={stats ? `${Math.round(stats.totalHazardAreaSqMeters)} m²` : "—"} tone={stats ? "primary" : "muted"} />
      </div>
      <button
        onClick={runSim}
        disabled={loading}
        className="mt-3 w-full rounded-sm border border-warning/50 bg-warning/15 px-3 py-2 font-mono text-[11px] tracking-[0.12em] text-warning uppercase transition-colors hover:bg-warning/25 disabled:opacity-50"
      >
        {loading ? "SIMULATING…" : "RUN LANDSLIDE SIMULATION"}
      </button>
      {result && (
        <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
          Simulation complete. {stats?.highAndCriticalCount ?? 0} high/critical impact structures.
          Avg exposure: {stats?.averageExposurePercentage ?? 0}%.
        </p>
      )}
    </Panel>
  );
}

function WildfireCard() {
  const [intensity, setIntensity] = useState(45);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const runSim = async () => {
    setLoading(true);
    try {
      const form = new FormData();
      form.append("disaster_type", "WILDFIRE");
      form.append("intensity", intensity <= 33 ? "low" : intensity <= 66 ? "medium" : "high");
      form.append("seed", "42");
      const res = await fetch("http://127.0.0.1:8000/simulate-disaster", { method: "POST", body: form });
      if (res.ok) setResult(await res.json());
    } catch (e) { console.warn("Wildfire sim failed:", e); }
    setLoading(false);
  };

  const stats = result?.summaryStatistics;
  return (
    <Panel
      eyebrow="HAZARD 04"
      title="Wildfire & Char Spread"
      right={<StatusBadge kind={result ? "active" : "integration-ready"} />}
      className="h-full"
    >
      <div className="relative h-40 overflow-hidden rounded-sm border border-border/70 bg-background/50">
        <div className="hud-grid-fine absolute inset-0 opacity-40" />
        <div className="absolute inset-0 bg-gradient-to-tr from-amber-950/40 via-orange-900/30 to-red-950/50" />
        <span className="absolute top-2 right-2 font-mono text-[10px] tracking-[0.12em] text-orange-400">
          CHAR SPREAD {intensity}%
        </span>
      </div>
      <Slider label="Fire Intensity" value={intensity} onChange={setIntensity} min={0} max={100} step={1} unit="%" />
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Readout label="Buildings Affected" value={stats ? `${stats.affectedBuildings}/${stats.totalBuildings}` : "—"} tone={stats ? "primary" : "muted"} />
        <Readout label="Burned Area" value={stats ? `${Math.round(stats.totalHazardAreaSqMeters)} m²` : "—"} tone={stats ? "primary" : "muted"} />
      </div>
      <button
        onClick={runSim}
        disabled={loading}
        className="mt-3 w-full rounded-sm border border-orange-500/50 bg-orange-500/15 px-3 py-2 font-mono text-[11px] tracking-[0.12em] text-orange-400 uppercase transition-colors hover:bg-orange-500/25 disabled:opacity-50"
      >
        {loading ? "SIMULATING…" : "RUN WILDFIRE SIMULATION"}
      </button>
      {result && (
        <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
          Simulation complete. {stats?.highAndCriticalCount ?? 0} high/critical impact structures.
          Avg exposure: {stats?.averageExposurePercentage ?? 0}%.
        </p>
      )}
    </Panel>
  );
}

function RiskTiersBreakdown() {
  return (
    <Panel eyebrow="SPATIAL RISK TIER CLASSIFICATION" title="High Risk Area vs Low Risk Area Breakdown" className="mt-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-sm border border-red-500/40 bg-red-500/10 p-3">
          <p className="label-mono text-red-400">HIGH & CRITICAL RISK AREA</p>
          <p className="mt-1 font-mono text-xl font-bold text-red-400">38.4%</p>
          <p className="mt-1 text-[11px] text-red-300/80">Structures &gt;35% exposure, steep slopes, low elevations.</p>
        </div>
        <div className="rounded-sm border border-amber-500/40 bg-amber-500/10 p-3">
          <p className="label-mono text-amber-400">MODERATE RISK AREA</p>
          <p className="mt-1 font-mono text-xl font-bold text-amber-400">24.2%</p>
          <p className="mt-1 text-[11px] text-amber-300/80">Structures 15-35% exposure in buffer zones.</p>
        </div>
        <div className="rounded-sm border border-emerald-500/40 bg-emerald-500/10 p-3">
          <p className="label-mono text-emerald-400">LOW & SAFE RISK AREA</p>
          <p className="mt-1 font-mono text-xl font-bold text-emerald-400">37.4%</p>
          <p className="mt-1 text-[11px] text-emerald-300/80">Elevated ridge ground, &lt;15% exposure.</p>
        </div>
        <div className="rounded-sm border border-primary/40 bg-primary/10 p-3">
          <p className="label-mono text-primary">POPULATION AT RISK</p>
          <p className="mt-1 font-mono text-xl font-bold text-primary">~1,420</p>
          <p className="mt-1 text-[11px] text-muted-foreground">Estimated residents in high/critical zones.</p>
        </div>
      </div>
    </Panel>
  );
}

function HazardsPage() {
  return (
    <div className="px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-[1600px]">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionHeading
            kicker="Module 05 · 06 · 07"
            title="Disaster & Hazard Simulation Engine"
            subtitle="Integrated simulation suite for Flood, Cyclone, Landslide, and Wildfire with spatial risk tier breakdown."
          />
          <StatusBadge kind="active" label="SIMULATION READY" className="self-center" />
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-4">
          <FloodCard />
          <EarthquakeCard />
          <LandslideCard />
          <WildfireCard />
        </div>

        <RiskTiersBreakdown />
      </div>
    </div>
  );
}

export default HazardsPage;
