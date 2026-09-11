import { createFileRoute } from "@tanstack/react-router";
import { Boxes, Keyboard, Sparkles } from "lucide-react";
import { useDw } from "@/lib/dw-state";
import { GlbViewer } from "@/components/dw/GlbViewer";
import { UploadZone } from "@/components/dw/UploadZone";
import { HudButton, Panel, SectionHeading, StatusBadge } from "@/components/dw/primitives";
import {
  AnalysisLayersPanel,
  ElevationPanel,
  MeasurementPanel,
  SceneStatsPanel,
} from "@/components/dw/TerrainStats";
import { toast } from "sonner";

export const Route = createFileRoute("/flythrough")({
  head: () => ({
    meta: [
      { title: "3D Flythrough — GLB Terrain Viewer | DepthWizard" },
      {
        name: "description",
        content:
          "Load a GLB terrain model and explore it with orbit and first-person flythrough, raycast elevation measurement and height exaggeration controls.",
      },
      { property: "og:title", content: "3D Flythrough — DepthWizard" },
      {
        property: "og:description",
        content: "Immersive WebGL terrain viewer with flythrough navigation and raycast measurement.",
      },
    ],
  }),
  component: FlythroughPage,
});

function FlythroughPage() {
  const { glbFile, setGlbFile, demoRequested, setDemoRequested } = useDw();

  const loadGlb = (file: File) => {
    if (!/\.(glb|gltf)$/i.test(file.name)) {
      toast.error("UNSUPPORTED FORMAT", { description: "Provide a .glb or .gltf model." });
      return;
    }
    setDemoRequested(false);
    setGlbFile(file);
  };

  return (
    <div className="px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-[1600px]">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionHeading
            kicker="Module 03 · 04"
            title="3D Flythrough"
            subtitle="Real-time WebGL rendering of reconstructed terrain. Orbit, fly and click the surface to measure elevation."
          />
          <div className="flex flex-wrap gap-2">
            <HudButton
              variant="outline"
              onClick={() => {
                setGlbFile(null);
                setDemoRequested(true);
                toast.success("DEMO TERRAIN LOADED", {
                  description: "Procedural reference geometry — not measured data.",
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
            <GlbViewer
              file={glbFile}
              demo={demoRequested || !glbFile}
              className="h-[60vh] min-h-[420px] xl:h-[74vh]"
            />
            <div className="grid gap-4 md:grid-cols-2">
              <Panel eyebrow="MODEL INPUT" title="GLB / glTF Upload">
                <UploadZone
                  compact
                  title="DROP .GLB MODEL HERE"
                  hint="GLB / glTF"
                  accept=".glb,.gltf,model/gltf-binary"
                  onFile={loadGlb}
                />
                {glbFile && (
                  <p className="mt-3 font-mono text-[10px] tracking-[0.12em] text-primary uppercase">
                    Loaded: {glbFile.name}
                  </p>
                )}
              </Panel>
              <Panel eyebrow="CONTROLS" title="Flight Reference">
                <ul className="grid grid-cols-2 gap-2 font-mono text-[10px] tracking-[0.12em] uppercase">
                  {[
                    ["W A S D", "Move"],
                    ["Space", "Ascend"],
                    ["Shift", "Descend"],
                    ["Mouse", "Look"],
                    ["Esc", "Exit flythrough"],
                    ["Click", "Raycast point"],
                  ].map(([k, v]) => (
                    <li
                      key={k}
                      className="flex items-center justify-between gap-2 rounded-sm border border-border/70 bg-background/40 px-2.5 py-2"
                    >
                      <span className="text-primary">{k}</span>
                      <span className="text-muted-foreground">{v}</span>
                    </li>
                  ))}
                </ul>
                <p className="mt-3 flex items-start gap-2 text-[11px] leading-relaxed text-muted-foreground">
                  <Keyboard className="mt-0.5 size-3.5 shrink-0 text-primary" />
                  Switch to First Person in the viewer dock to capture the pointer and fly the scene.
                </p>
              </Panel>
            </div>
          </div>

          <aside className="space-y-4">
            <div className="hud-panel flex items-center gap-2 px-3 py-2">
              <Boxes className="size-3.5 text-primary" />
              <span className="label-mono">Terrain Intelligence</span>
            </div>
            <SceneStatsPanel />
            <ElevationPanel />
            <MeasurementPanel />
            <AnalysisLayersPanel />
          </aside>
        </div>
      </div>
    </div>
  );
}
