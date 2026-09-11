import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useRef } from "react";
import { Grid3x3, Layers, Mountain, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { useDw } from "@/lib/dw-state";
import { ImageIngest } from "@/components/dw/ImageIngest";
import { GlbViewer } from "@/components/dw/GlbViewer";
import { HudButton, Panel, Readout, SectionHeading, StatusBadge } from "@/components/dw/primitives";
import { ElevationPanel, SceneStatsPanel } from "@/components/dw/TerrainStats";

export const Route = createFileRoute("/terrain")({
  head: () => ({
    meta: [
      { title: "Terrain — Image Ingest, DSM & 3D Surface | DepthWizard" },
      {
        name: "description",
        content:
          "Ingest a satellite scene, inspect RGB preview and height/DSM metadata, and explore the reconstructed terrain surface in an interactive WebGL viewer.",
      },
      { property: "og:title", content: "Terrain — DepthWizard" },
      {
        property: "og:description",
        content: "RGB preview, DSM metadata and an interactive 3D terrain surface.",
      },
    ],
  }),
  component: TerrainPage,
});

/** Deterministic synthetic height grid so the readouts are reproducible demo data, not fake results. */
function useHeightGrid(size = 8) {
  return useMemo(() => {
    const rows: number[][] = [];
    for (let r = 0; r < size; r++) {
      const row: number[] = [];
      for (let c = 0; c < size; c++) {
        const x = (c / (size - 1)) * 2 - 1;
        const y = (r / (size - 1)) * 2 - 1;
        const h =
          0.6 * Math.exp(-(x * x + y * y) * 2.2) +
          0.25 * Math.sin(x * 3.1) * Math.cos(y * 2.7) +
          0.15;
        row.push(Math.max(0, h));
      }
      rows.push(row);
    }
    return rows;
  }, [size]);
}

function TerrainPage() {
  const { image, glbFile, demoRequested, setDemoRequested, settings } = useDw();
  const grid = useHeightGrid();
  const ingestRef = useRef<HTMLDivElement>(null);

  const flat = grid.flat();
  const min = Math.min(...flat);
  const max = Math.max(...flat);
  const mean = flat.reduce((a, b) => a + b, 0) / flat.length;

  useEffect(() => {
    if (typeof window !== "undefined" && window.location.hash === "#ingest") {
      ingestRef.current?.scrollIntoView({
        behavior: settings.motion ? "smooth" : "auto",
        block: "start",
      });
    }
  }, [settings.motion]);

  return (
    <div className="px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-[1600px]">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionHeading
            kicker="Module 01 · 02"
            title="Terrain Reconstruction"
            subtitle="Ingest the source scene, review height/DSM metadata and inspect the reconstructed surface in the 3D viewer."
          />
          <div className="flex flex-wrap gap-2">
            <HudButton
              variant="outline"
              onClick={() => {
                setDemoRequested(true);
                toast.success("DEMO TERRAIN LOADED", {
                  description: "Procedural reference surface — not measured data.",
                });
              }}
            >
              <Sparkles className="size-3.5" /> Load Demo Terrain
            </HudButton>
            <StatusBadge kind="active" className="self-center" />
          </div>
        </div>

        <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_340px]">
          <div className="space-y-4">
            <Panel
              eyebrow="SOURCE"
              title="RGB Preview"
              right={
                image ? (
                  <StatusBadge kind="active" label="LOADED" />
                ) : (
                  <StatusBadge kind="coming-soon" label="NO IMAGE" />
                )
              }
              bodyClassName="p-0"
            >
              <div className="relative aspect-[16/9] w-full overflow-hidden bg-background/60">
                <div className="hud-grid-fine absolute inset-0 opacity-40" />
                {image ? (
                  <img
                    src={image.url}
                    alt={`RGB preview of ingested scene ${image.name}`}
                    className="relative size-full object-contain"
                  />
                ) : (
                  <div className="relative grid size-full place-items-center text-center">
                    <div>
                      <Mountain className="mx-auto size-6 text-primary" />
                      <p className="mt-3 font-display text-sm tracking-[0.14em]">NO SCENE INGESTED</p>
                      <p className="mt-2 text-xs text-muted-foreground">
                        Upload a satellite image below to populate the preview.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </Panel>

            <Panel
              eyebrow="SURFACE"
              title="3D Terrain Viewer"
              right={<StatusBadge kind="active" label="WEBGL" />}
              bodyClassName="p-3"
            >
              <GlbViewer
                file={glbFile}
                demo={demoRequested || !glbFile}
                className="h-[52vh] min-h-[380px]"
              />
              <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
                Orbit with drag, zoom with scroll. Reset View, Wireframe, Grid and Height
                Exaggeration live in the viewer dock and also follow the console Settings panel.
              </p>
            </Panel>
          </div>

          <aside className="space-y-4">
            <Panel
              eyebrow="HEIGHT / DSM"
              title="Elevation Metadata"
              right={<StatusBadge kind="integration-ready" />}
            >
              <div className="grid grid-cols-2 gap-2">
                <Readout label="Grid" value="8 × 8" />
                <Readout label="Samples" value={flat.length} />
                <Readout label="Min (norm.)" value={min.toFixed(3)} />
                <Readout label="Max (norm.)" value={max.toFixed(3)} tone="primary" />
                <Readout label="Mean (norm.)" value={mean.toFixed(3)} />
                <Readout label="Source" value="DEMO GRID" tone="muted" />
              </div>
              <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
                Values are a deterministic demo height field in normalised units. Metric DSM values
                require the height-estimation service, which is not part of this frontend build.
              </p>
            </Panel>

            <Panel
              eyebrow="HEIGHT GRID"
              title="Normalised Sample Matrix"
              right={<Grid3x3 className="size-3.5 text-primary" />}
              bodyClassName="p-3"
            >
              <div className="grid grid-cols-8 gap-[3px]">
                {flat.map((h, i) => (
                  <div
                    key={i}
                    title={h.toFixed(3)}
                    className="aspect-square rounded-[2px]"
                    style={{
                      background: `color-mix(in oklch, var(--primary) ${Math.round(
                        18 + h * 82,
                      )}%, var(--surface))`,
                    }}
                  />
                ))}
              </div>
              <div className="mt-3 flex items-center justify-between font-mono text-[10px] text-muted-foreground">
                <span>LOW {min.toFixed(2)}</span>
                <span className="text-primary">HIGH {max.toFixed(2)}</span>
              </div>
            </Panel>

            <SceneStatsPanel />
            <ElevationPanel />
            <div className="hud-panel flex items-center gap-2 px-3 py-2">
              <Layers className="size-3.5 text-primary" />
              <span className="label-mono">Pipeline: ingest → DSM → surface</span>
            </div>
          </aside>
        </div>

        <section ref={ingestRef} id="ingest" className="mt-10 scroll-mt-24">
          <SectionHeading
            kicker="Image Input"
            title="Satellite image ingest"
            subtitle="Drop a JPG, PNG, TIFF or GeoTIFF scene. Files are inspected locally in the browser — nothing is transmitted."
          />
          <div className="mt-6">
            <ImageIngest />
          </div>
        </section>
      </div>
    </div>
  );
}
