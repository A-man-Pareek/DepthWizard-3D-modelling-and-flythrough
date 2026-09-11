import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Boxes,
  Bot,
  Crosshair,
  Download,
  Droplets,
  Layers,
  Mountain,
  Radar,
  ScanLine,
  ShieldCheck,
  SplitSquareHorizontal,
  Sparkles,
  Waves,
  Activity,
} from "lucide-react";
import { GridBackdrop, HudButton, SectionHeading, StatusBadge } from "@/components/dw/primitives";
import { TerrainField } from "@/components/dw/TerrainField";
import { Pipeline } from "@/components/dw/Pipeline";
import { FeatureCard } from "@/components/dw/FeatureCard";
import { ImageIngest } from "@/components/dw/ImageIngest";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "DepthWizard — Geospatial Command Center | PS 26175" },
      {
        name: "description",
        content:
          "From a single satellite image to a living 3D terrain. DepthWizard delivers single-view height estimation, DSM reconstruction and 3D flythrough for disaster intelligence.",
      },
      { property: "og:title", content: "DepthWizard — Geospatial Command Center" },
      {
        property: "og:description",
        content:
          "Single-view height estimation and interactive 3D exploration for disaster intelligence. SIH 2026 · PS 26175 · 8086 Crew.",
      },
    ],
  }),
  component: Home,
});

const pipeline = [
  { label: "Single View" },
  { label: "Height Estimation" },
  { label: "DSM Generation" },
  { label: "3D Reconstruction" },
  { label: "Interactive Exploration" },
  { label: "Disaster Intelligence" },
];

const modules = [
  {
    icon: ScanLine,
    title: "Single-View Height Estimation",
    description: "Estimate terrain height from a single RGB satellite image.",
    status: "active" as const,
    to: "/terrain",
  },
  {
    icon: Layers,
    title: "DSM Reconstruction",
    description: "Generate an elevation-aware Digital Surface Model from estimated depth.",
    status: "active" as const,
    to: "/terrain",
  },
  {
    icon: Mountain,
    title: "3D Terrain Reconstruction",
    description: "Convert the height grid into an interactive textured 3D terrain.",
    status: "active" as const,
    to: "/flythrough",
  },
  {
    icon: Crosshair,
    title: "Raycasting & Terrain Measurement",
    description: "Click directly on the 3D terrain to inspect elevation and spatial information.",
    status: "active" as const,
    to: "/flythrough",
  },
  {
    icon: ShieldCheck,
    title: "Safe / High-Risk Zone Detection",
    description: "Identify terrain regions using configurable environmental and terrain parameters.",
    status: "proposed" as const,
  },
  {
    icon: Droplets,
    title: "Flood Simulation",
    description: "Visualize potential flood propagation across the reconstructed terrain.",
    status: "proposed" as const,
  },
  {
    icon: Waves,
    title: "Earthquake Impact Analysis",
    description: "Visualize earthquake impact zones over the reconstructed 3D terrain.",
    status: "proposed" as const,
  },
  {
    icon: Activity,
    title: "Landslide Susceptibility",
    description: "Analyse terrain factors such as slope, aspect, curvature, land cover and drainage.",
    status: "proposed" as const,
  },
  {
    icon: SplitSquareHorizontal,
    title: "Before / After Damage Analysis",
    description: "Compare imagery from before and after a disaster and visualize detected changes.",
    status: "proposed" as const,
  },
  {
    icon: Sparkles,
    title: "AI-Assisted 3D Model Correction",
    description: "Detect anomalies and refine unstable or inconsistent regions of the terrain.",
    status: "proposed" as const,
  },
  {
    icon: Bot,
    title: "Geospatial AI Copilot",
    description: "Ask natural-language questions about the terrain, elevation and risk layers.",
    status: "proposed" as const,
  },
  {
    icon: Download,
    title: "Exportable Analysis",
    description: "Export terrain, measurements, maps and analysis results.",
    status: "proposed" as const,
  },
];

function Home() {
  return (
    <div>
      {/* HERO */}
      <section className="relative overflow-hidden border-b border-border">
        <GridBackdrop />
        <div className="relative mx-auto grid max-w-[1600px] items-center gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:py-24">
          <div className="animate-rise">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge kind="online" label="PS ID 26175" />
              <StatusBadge kind="coming-soon" label="DISASTER MANAGEMENT" />
              <StatusBadge kind="coming-soon" label="8086 CREW" />
            </div>
            <h1 className="mt-6 font-display text-4xl leading-[1.05] tracking-tight uppercase sm:text-5xl xl:text-6xl">
              From a single image
              <br />
              <span className="text-primary text-glow">to a living 3D terrain.</span>
            </h1>
            <p className="mt-5 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
              Single-view height estimation and interactive 3D exploration for disaster
              intelligence.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/terrain" hash="ingest">
                <HudButton>
                  <ScanLine className="size-3.5" /> Upload Satellite Image
                </HudButton>
              </Link>
              <Link to="/flythrough">
                <HudButton variant="outline">
                  <Boxes className="size-3.5" /> Open 3D Viewer
                </HudButton>
              </Link>
            </div>
            <dl className="mt-10 grid max-w-lg grid-cols-3 gap-3">
              {[
                { k: "Problem Statement", v: "DepthWizard" },
                { k: "Domain", v: "Disaster Mgmt" },
                { k: "Pipeline Stages", v: "06" },
              ].map((s) => (
                <div key={s.k} className="hud-panel px-3 py-2.5">
                  <dt className="label-mono">{s.k}</dt>
                  <dd className="mt-1 font-mono text-xs text-primary">{s.v}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="corner-brackets relative aspect-[4/3] overflow-hidden rounded-lg border border-border bg-background/60">
            <div className="hud-grid-fine absolute inset-0 opacity-50" />
            <TerrainField className="relative" />
            <div className="pointer-events-none absolute inset-x-0 top-0 h-px animate-scan bg-gradient-to-r from-transparent via-primary/80 to-transparent" />
            <div className="pointer-events-none absolute top-3 left-3 font-mono text-[10px] leading-relaxed tracking-[0.14em] text-muted-foreground">
              <p>ELEVATION FIELD · SYNTHETIC PREVIEW</p>
              <p className="text-primary">LAT 28.6139 N · LON 77.2090 E</p>
            </div>
            <div className="pointer-events-none absolute right-3 bottom-3 flex items-center gap-2">
              <StatusBadge kind="online" label="RENDER LOOP" />
            </div>
          </div>
        </div>
      </section>

      {/* PIPELINE */}
      <section className="border-b border-border bg-surface/20 px-4 py-14 sm:px-6">
        <div className="mx-auto max-w-[1600px]">
          <SectionHeading
            kicker="Intelligence Pipeline"
            title="Single view to disaster intelligence"
            subtitle="Every stage of the DepthWizard chain, from raw imagery through elevation reconstruction to actionable terrain intelligence."
          />
          <Pipeline nodes={pipeline} className="mt-8" />
        </div>
      </section>

      {/* INGEST */}
      <section id="ingest" className="border-b border-border px-4 py-14 sm:px-6">
        <div className="mx-auto max-w-[1600px]">
          <SectionHeading
            kicker="Image Input"
            title="Satellite image ingest"
            subtitle="Drop a JPG, PNG, TIFF or GeoTIFF scene. Files are inspected locally in the browser — nothing is transmitted."
          />
          <div className="mt-8">
            <ImageIngest />
          </div>
        </div>
      </section>

      {/* MODULES */}
      <section className="relative px-4 py-14 sm:px-6">
        <div className="mx-auto max-w-[1600px]">
          <SectionHeading
            kicker="Capability Map"
            title="Disaster intelligence modules"
            subtitle="Four modules are live in this prototype. The remaining modules are architected and marked as proposed — no results are simulated for them."
          />
          <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {modules.map((m, i) => (
              <FeatureCard key={m.title} index={i + 1} {...m} />
            ))}
          </div>
          <div className="mt-8 flex flex-wrap items-center gap-3 rounded-lg border border-accent/30 bg-accent/8 p-4">
            <Radar className="size-4 text-accent" />
            <p className="text-xs leading-relaxed text-muted-foreground">
              <span className="font-mono tracking-[0.12em] text-accent uppercase">
                Prototype scope:
              </span>{" "}
              image ingest → 3D terrain → flythrough → raycast measurement are functional. Hazard
              simulation, damage assessment and the geospatial copilot are integration-ready
              interfaces awaiting their analysis services.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
