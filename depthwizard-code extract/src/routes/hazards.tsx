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
  return (
    <Panel
      eyebrow="HAZARD 01"
      title="Flood Simulation"
      right={<StatusBadge kind="proposed" />}
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
        <Readout label="Inundation Model" value="NOT RUN" tone="muted" />
        <Readout label="Input Required" value="DSM + RAINFALL" tone="muted" />
      </div>
      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
        Proposed module. The slider drives a visual water plane only — no hydrological computation
        is performed and no inundation results are produced.
      </p>
    </Panel>
  );
}

function EarthquakeCard() {
  const [magnitude, setMagnitude] = useState(6.2);
  const rings = [1, 2, 3];
  return (
    <Panel
      eyebrow="HAZARD 02"
      title="Earthquake Impact"
      right={<StatusBadge kind="proposed" />}
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
        <Readout label="Shaking Model" value="NOT RUN" tone="muted" />
        <Readout label="Input Required" value="SOIL + STRUCTURES" tone="muted" />
      </div>
      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
        Proposed module. Rings are an illustrative sketch of an epicentre control — no attenuation
        model, ground-motion estimate or damage projection is calculated.
      </p>
    </Panel>
  );
}

function LandslideCard() {
  const [slope, setSlope] = useState(28);
  const factors = [
    { label: "Slope", icon: Activity },
    { label: "Aspect", icon: Waves },
    { label: "Curvature", icon: Activity },
    { label: "Land Cover", icon: Droplets },
    { label: "Drainage", icon: Droplets },
  ];
  return (
    <Panel
      eyebrow="HAZARD 03"
      title="Landslide Susceptibility"
      right={<StatusBadge kind="integration-ready" />}
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
      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
        Integration-ready interface. The heat pattern responds to the threshold control for layout
        purposes only — susceptibility scoring requires the terrain-analysis service.
      </p>
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
            title="Hazard Analysis"
            subtitle="Proposed hazard modules for the DepthWizard chain. These are interface prototypes — no hazard results are computed or simulated."
          />
          <StatusBadge kind="proposed" label="PROPOSED MODULES" className="self-center" />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3 rounded-lg border border-warning/30 bg-warning/8 p-4">
          <p className="text-xs leading-relaxed text-muted-foreground">
            <span className="font-mono tracking-[0.12em] text-warning uppercase">Note:</span> every
            panel on this page is proposed / future functionality. Controls affect the visualisation
            sketch only.
          </p>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          <FloodCard />
          <EarthquakeCard />
          <LandslideCard />
        </div>
      </div>
    </div>
  );
}
