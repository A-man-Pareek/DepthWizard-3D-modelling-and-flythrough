import { Activity, Ruler, Triangle } from "lucide-react";
import { useDw } from "@/lib/dw-state";
import { Panel, Readout, StatusBadge } from "./primitives";

export function SceneStatsPanel() {
  const { scene } = useDw();
  return (
    <Panel
      eyebrow="SCENE"
      title="Loaded Geometry"
      right={scene ? <StatusBadge kind="active" label="LOADED" /> : <StatusBadge kind="coming-soon" label="EMPTY" />}
    >
      <div className="grid grid-cols-2 gap-2">
        <Readout label="Model" value={scene ? scene.label : "—"} />
        <Readout
          label="Source"
          value={scene ? (scene.source === "demo" ? "PROCEDURAL DEMO" : "USER GLB") : "—"}
        />
        <Readout
          label="Vertices"
          value={scene ? scene.vertices.toLocaleString() : "—"}
          tone={scene ? "primary" : "muted"}
        />
        <Readout
          label="Triangles"
          value={scene ? scene.triangles.toLocaleString() : "—"}
          tone={scene ? "primary" : "muted"}
        />
        <Readout label="Texture" value={scene ? (scene.textured ? "PRESENT" : "NONE") : "—"} />
        <Readout label="Renderer" value="WEBGL / THREE.JS" />
      </div>
    </Panel>
  );
}

export function ElevationPanel() {
  const { scene } = useDw();
  const unit = scene?.source === "demo" ? "units" : "units";
  return (
    <Panel eyebrow="ELEVATION" title="Height Range">
      <div className="grid grid-cols-3 gap-2">
        <Readout label="Min" value={scene ? scene.minY.toFixed(2) : "N/A"} unit={scene ? unit : undefined} />
        <Readout
          label="Max"
          value={scene ? scene.maxY.toFixed(2) : "N/A"}
          unit={scene ? unit : undefined}
          tone="primary"
        />
        <Readout label="Mean" value={scene ? scene.meanY.toFixed(2) : "N/A"} unit={scene ? unit : undefined} />
      </div>
      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
        Values are measured from the loaded mesh geometry in scene units. Metric elevation requires
        georeferenced scale metadata from the estimation service.
      </p>
    </Panel>
  );
}

export function MeasurementPanel() {
  const { measurements, clearMeasurements } = useDw();
  return (
    <Panel
      eyebrow="RAYCASTING"
      title="Terrain Points"
      right={
        measurements.length > 0 ? (
          <button
            onClick={clearMeasurements}
            className="font-mono text-[10px] tracking-[0.14em] text-destructive uppercase"
          >
            Clear
          </button>
        ) : (
          <StatusBadge kind="active" />
        )
      }
    >
      {measurements.length === 0 ? (
        <p className="flex items-start gap-2 text-xs leading-relaxed text-muted-foreground">
          <Activity className="mt-0.5 size-3.5 shrink-0 text-primary" />
          Click anywhere on the 3D terrain to cast a ray and inspect that point. Multiple points can
          be collected; segment distances are computed between consecutive picks.
        </p>
      ) : (
        <ul className="space-y-2">
          {measurements.map((m, i) => (
            <li key={m.id} className="rounded-sm border border-border/70 bg-background/40 p-3">
              <div className="flex items-center justify-between">
                <span className="label-mono text-primary">POINT {String(i + 1).padStart(2, "0")}</span>
                <span className="flex items-center gap-1.5 font-mono text-xs text-primary">
                  <Triangle className="size-3" />
                  {m.elevation.toFixed(2)}
                </span>
              </div>
              <p className="mt-1.5 font-mono text-[10px] text-muted-foreground">
                X {m.x.toFixed(2)} · Y {m.y.toFixed(2)} · Z {m.z.toFixed(2)}
              </p>
              {m.distanceFromPrev !== null && (
                <p className="mt-1 flex items-center gap-1.5 font-mono text-[10px] text-accent">
                  <Ruler className="size-3" /> Δ {m.distanceFromPrev.toFixed(2)} units from previous
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

export function AnalysisLayersPanel() {
  const layers = [
    { label: "Elevation", kind: "active" as const },
    { label: "Measurement", kind: "active" as const },
    { label: "Slope", kind: "coming-soon" as const },
    { label: "Risk Overlay", kind: "coming-soon" as const },
  ];
  return (
    <Panel eyebrow="ANALYSIS" title="Layers">
      <ul className="space-y-2">
        {layers.map((l) => (
          <li
            key={l.label}
            className="flex items-center justify-between rounded-sm border border-border/70 bg-background/40 px-3 py-2"
          >
            <span className="font-mono text-[11px] tracking-[0.1em] uppercase">{l.label}</span>
            <StatusBadge kind={l.kind} />
          </li>
        ))}
      </ul>
    </Panel>
  );
}
