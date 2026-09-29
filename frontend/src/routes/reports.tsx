import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Download, Eye, FileDown } from "lucide-react";
import { toast } from "sonner";
import { useDw } from "@/lib/dw-state";
import { HudButton, Panel, SectionHeading, StatusBadge, type StatusKind } from "@/components/dw/primitives";

export const Route = createFileRoute("/reports")({
  head: () => ({
    meta: [
      { title: "Reports & Export — Terrain, Hazard & Damage | DepthWizard" },
      {
        name: "description",
        content:
          "Export dashboard for DSM, 3D terrain, measurements, hazard, damage and AI summary artefacts. Exports are generated in the browser from session data.",
      },
      { property: "og:title", content: "Reports & Export — DepthWizard" },
      {
        property: "og:description",
        content: "Browser-side export dashboard for DepthWizard session artefacts.",
      },
    ],
  }),
  component: ReportsPage,
});

function download(name: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
  toast.success("EXPORT WRITTEN", { description: `${name} generated in your browser.` });
}

function ReportsPage() {
  const { image, scene, measurements } = useDw();
  const navigate = useNavigate();

  const cards: {
    title: string;
    eyebrow: string;
    status: StatusKind;
    note: string;
    to?: "/terrain" | "/flythrough" | "/hazards" | "/damage" | "/copilot";
    data?: () => unknown;
  }[] = [
    {
      title: "Height / DSM",
      eyebrow: "REPORT 01",
      status: image ? "active" : "coming-soon",
      note: "Ingested scene metadata and the normalised demo height grid summary.",
      to: "/terrain",
      data: () => ({
        kind: "height-dsm",
        generatedInBrowser: true,
        image: image
          ? { name: image.name, type: image.type, width: image.width, height: image.height }
          : null,
        metricDsm: "unavailable — estimation service not connected",
      }),
    },
    {
      title: "3D Terrain",
      eyebrow: "REPORT 02",
      status: scene ? "active" : "coming-soon",
      note: "Geometry statistics measured from the mesh currently loaded in the viewer.",
      to: "/flythrough",
      data: () => ({ kind: "3d-terrain", generatedInBrowser: true, scene }),
    },
    {
      title: "Terrain Measurements",
      eyebrow: "REPORT 03",
      status: measurements.length ? "active" : "coming-soon",
      note: "Raycast points collected in this session, with elevations in scene units.",
      to: "/flythrough",
      data: () => ({ kind: "measurements", generatedInBrowser: true, points: measurements }),
    },
    {
      title: "Hazard Analysis",
      eyebrow: "REPORT 04",
      status: "proposed",
      note: "Flood, earthquake and landslide modules are proposed — no results to export.",
      to: "/hazards",
    },
    {
      title: "Damage Analysis",
      eyebrow: "REPORT 05",
      status: "integration-ready",
      note: "Comparison interface is ready; detection output requires an analysis service.",
      to: "/damage",
    },
    {
      title: "AI Summary",
      eyebrow: "REPORT 06",
      status: "integration-ready",
      note: "Copilot narrative export becomes available once a language model is connected.",
      to: "/copilot",
    },
  ];

  return (
    <div className="px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-[1600px]">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionHeading
            kicker="Module 12"
            title="Reports & Export"
            subtitle="Export what the browser actually holds. Nothing is generated on a server — unavailable artefacts stay marked as such."
          />
          <StatusBadge kind="integration-ready" label="BROWSER-SIDE EXPORT" className="self-center" />
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {cards.map((c) => {
            const exportable = Boolean(c.data);
            return (
              <Panel
                key={c.title}
                eyebrow={c.eyebrow}
                title={c.title}
                right={<StatusBadge kind={c.status} />}
                className="h-full"
              >
                <p className="text-xs leading-relaxed text-muted-foreground">{c.note}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <HudButton
                    variant="outline"
                    className="px-3 py-2"
                    disabled={!c.to}
                    onClick={() => c.to && navigate({ to: c.to })}
                  >
                    <Eye className="size-3" /> View
                  </HudButton>
                  <HudButton
                    variant="outline"
                    className="px-3 py-2"
                    disabled={!exportable}
                    onClick={() =>
                      download(
                        `depthwizard-${c.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.json`,
                        c.data!(),
                      )
                    }
                  >
                    <FileDown className="size-3" /> Export
                  </HudButton>
                  <HudButton
                    className="px-3 py-2"
                    disabled={!exportable}
                    onClick={() =>
                      download(
                        `depthwizard-${c.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-full.json`,
                        { ...(c.data!() as object), exportedAt: new Date().toISOString() },
                      )
                    }
                  >
                    <Download className="size-3" /> Download
                  </HudButton>
                </div>
                {!exportable && (
                  <p className="mt-3 font-mono text-[10px] tracking-[0.12em] text-warning uppercase">
                    No data to export yet
                  </p>
                )}
              </Panel>
            );
          })}
        </div>
      </div>
    </div>
  );
}
