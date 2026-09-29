import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Boxes,
  Compass,
  ExternalLink,
  Eye,
  Keyboard,
  Maximize2,
  Plane,
  Sparkles,
} from "lucide-react";
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
      { title: "3D Flythrough & Raycasting — DepthWizard" },
      {
        name: "description",
        content:
          "Explore 3D reconstructed terrain with first-person flythrough, raycasting building measurement, and real-world elevation profiling.",
      },
    ],
  }),
  component: FlythroughPage,
});

function FlythroughPage() {
  const { glbFile, setGlbFile, glbUrl, demoRequested, setDemoRequested, heightMetadata } = useDw();
  const [activeTab, setActiveTab] = useState<"integrated" | "myproject2">("integrated");

  const loadGlb = (file: File) => {
    if (!/\.(glb|gltf)$/i.test(file.name)) {
      toast.error("UNSUPPORTED FORMAT", { description: "Provide a .glb or .gltf model." });
      return;
    }
    setDemoRequested(false);
    setGlbFile(file);
  };

  const resolvedGlbUrl = glbUrl || "http://127.0.0.1:8000/download/imgg_fresh.glb";
  const myproject2Url = `http://localhost:5174/?model=${encodeURIComponent(resolvedGlbUrl)}&_t=${Date.now()}`;

  return (
    <div className="px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-[1600px]">
        {/* Header Bar */}
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionHeading
            kicker="Module 03 — 04"
            title="3D Terrain & Flythrough"
            subtitle="Real-time WebGL rendering of reconstructed terrain. Orbit, fly, and use raycasting to measure real-world elevation and building dimensions."
          />
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex rounded-sm border border-border bg-background p-0.5">
              <button
                type="button"
                onClick={() => setActiveTab("integrated")}
                className={`flex items-center gap-1.5 rounded-sm px-3 py-1 text-xs font-medium transition-colors ${
                  activeTab === "integrated"
                    ? "bg-primary text-primary-foreground font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Eye className="size-3.5" /> Orbit & Elevation View
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("myproject2")}
                className={`flex items-center gap-1.5 rounded-sm px-3 py-1 text-xs font-medium transition-colors ${
                  activeTab === "myproject2"
                    ? "bg-primary text-primary-foreground font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Plane className="size-3.5" /> 3D Viewer Flythrough & Raycasting
              </button>
            </div>

            <a href={myproject2Url} target="_blank" rel="noreferrer">
              <HudButton variant="outline">
                <Maximize2 className="mr-1.5 size-3.5" /> Open Fullscreen
              </HudButton>
            </a>

            <HudButton
              variant="outline"
              onClick={() => {
                setGlbFile(null);
                setDemoRequested(true);
                toast.success("DEMO TERRAIN LOADED", {
                  description: "Procedural reference geometry loaded.",
                });
              }}
            >
              <Sparkles className="size-3.5" /> Load Demo
            </HudButton>
            <StatusBadge kind="active" className="self-center" />
          </div>
        </div>

        {/* Main Workspace */}
        <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_340px]">
          <div className="space-y-4">
            {activeTab === "integrated" ? (
              <GlbViewer
                file={glbFile}
                demo={demoRequested || !glbFile}
                className="h-[60vh] min-h-[440px] xl:h-[74vh]"
              />
            ) : (
              <div className="relative h-[60vh] min-h-[440px] xl:h-[74vh] overflow-hidden rounded-md border border-border bg-black">
                <iframe
                  src={myproject2Url}
                  title="3D Viewer Flythrough and Raycasting Viewer"
                  className="size-full border-none"
                  allow="pointer-lock; fullscreen"
                />
                <div className="pointer-events-none absolute bottom-3 left-3 rounded-sm border border-border/80 bg-background/90 px-3 py-1.5 backdrop-blur-sm">
                  <p className="font-mono text-[10px] tracking-wider text-primary uppercase">
                    3D Viewer PointerLock Active • Click viewer to capture cursor • ESC to exit
                  </p>
                </div>
              </div>
            )}

            {/* Sub-panels */}
            <div className="grid gap-4 md:grid-cols-2">
              <Panel eyebrow="MODEL INPUT" title="GLB / glTF Reconstructed Model">
                <UploadZone
                  compact
                  title="DROP .GLB MODEL HERE"
                  hint="GLB / glTF"
                  accept=".glb,.gltf,model/gltf-binary"
                  onFile={loadGlb}
                />
                {glbFile && (
                  <p className="mt-3 font-mono text-[10px] tracking-[0.12em] text-primary uppercase">
                    Loaded Model: {glbFile.name}
                  </p>
                )}
                {glbUrl && !glbFile && (
                  <p className="mt-3 font-mono text-[10px] tracking-[0.12em] text-primary uppercase">
                    Backend Model: {glbUrl}
                  </p>
                )}
              </Panel>

              <Panel eyebrow="CONTROLS" title="Flight Reference & Raycasting">
                <ul className="grid grid-cols-2 gap-2 font-mono text-[10px] tracking-[0.12em] uppercase">
                  {[
                    ["W A S D", "Fly / Move"],
                    ["Space", "Ascend"],
                    ["Shift", "Descend"],
                    ["Mouse", "Look"],
                    ["Click", "Raycast Building / Point"],
                    ["Esc", "Exit PointerLock"],
                  ].map(([k, v]) => (
                    <li
                      key={k}
                      className="flex items-center justify-between gap-2 rounded-sm border border-border/70 bg-background/40 px-2.5 py-2"
                    >
                      <span className="text-primary font-bold">{k}</span>
                      <span className="text-muted-foreground">{v}</span>
                    </li>
                  ))}
                </ul>
                <p className="mt-3 flex items-start gap-2 text-[11px] leading-relaxed text-muted-foreground">
                  <Keyboard className="mt-0.5 size-3.5 shrink-0 text-primary" />
                  Toggle to "MyProject2 Flythrough & Raycasting" above to lock pointer and inspect building dimensions directly in meters.
                </p>
              </Panel>
            </div>
          </div>

          {/* Sidebar */}
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
