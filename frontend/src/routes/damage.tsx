import { createFileRoute } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { SplitSquareHorizontal } from "lucide-react";
import { useDw } from "@/lib/dw-state";
import { UploadZone } from "@/components/dw/UploadZone";
import { Panel, Readout, SectionHeading, StatusBadge } from "@/components/dw/primitives";

export const Route = createFileRoute("/damage")({
  head: () => ({
    meta: [
      { title: "Damage Analysis — Before / After Comparison | DepthWizard" },
      {
        name: "description",
        content:
          "Compare before and after scenes with a swipe slider and review the change-detection interface. Demo / integration-ready, no automated detection is run.",
      },
      { property: "og:title", content: "Damage Analysis — DepthWizard" },
      {
        property: "og:description",
        content: "Before/after swipe comparison and change-detection interface for disaster scenes.",
      },
    ],
  }),
  component: DamagePage,
});

const DEMO_BEFORE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='800' height='450'><rect width='800' height='450' fill='#0d1b24'/><g fill='#1c7293' opacity='0.85'>${Array.from(
      { length: 40 },
      (_, i) =>
        `<rect x='${(i % 10) * 80 + 12}' y='${Math.floor(i / 10) * 110 + 16}' width='56' height='${
          40 + ((i * 17) % 50)
        }' rx='3'/>`,
    ).join("")}</g><g stroke='#20313d' stroke-width='6'><path d='M0 118 H800'/><path d='M0 228 H800'/><path d='M0 338 H800'/></g><text x='16' y='436' fill='#5ee9ff' font-family='monospace' font-size='16'>DEMO SCENE · BEFORE</text></svg>`,
  );

const DEMO_AFTER =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='800' height='450'><rect width='800' height='450' fill='#0d1b24'/><g fill='#1c7293' opacity='0.85'>${Array.from(
      { length: 40 },
      (_, i) =>
        i % 3 === 0
          ? ""
          : `<rect x='${(i % 10) * 80 + 12}' y='${Math.floor(i / 10) * 110 + 16}' width='56' height='${
              40 + ((i * 17) % 50)
            }' rx='3'/>`,
    ).join("")}</g><g fill='#c98a2e' opacity='0.5'>${Array.from(
      { length: 14 },
      (_, i) =>
        `<rect x='${(i * 57) % 740}' y='${(i * 91) % 380}' width='${28 + (i % 4) * 12}' height='${
          24 + (i % 3) * 14
        }' rx='4'/>`,
    ).join(
      "",
    )}</g><g stroke='#20313d' stroke-width='6'><path d='M0 118 H800'/><path d='M0 228 H800'/><path d='M0 338 H800'/></g><text x='16' y='436' fill='#f2b544' font-family='monospace' font-size='16'>DEMO SCENE · AFTER</text></svg>`,
  );

function DamagePage() {
  const { beforeImage, afterImage, setBeforeImage, setAfterImage } = useDw();
  const [pos, setPos] = useState(50);
  const frameRef = useRef<HTMLDivElement>(null);

  const before = beforeImage ?? DEMO_BEFORE;
  const after = afterImage ?? DEMO_AFTER;
  const usingDemo = !beforeImage && !afterImage;

  return (
    <div className="px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-[1600px]">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionHeading
            kicker="Module 09"
            title="Damage Analysis"
            subtitle="Swipe between pre- and post-event scenes. The comparison is fully interactive; automated detection is not connected."
          />
          <StatusBadge kind="integration-ready" label="DEMO / INTEGRATION READY" className="self-center" />
        </div>

        <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_340px]">
          <div className="space-y-4">
            <Panel
              eyebrow="COMPARISON"
              title="Before / After Slider"
              right={
                <span className="font-mono text-[10px] tracking-[0.12em] text-primary">
                  {pos}% AFTER
                </span>
              }
              bodyClassName="p-3"
            >
              <div
                ref={frameRef}
                className="relative aspect-[16/9] w-full overflow-hidden rounded-sm border border-border/70 bg-background/60 select-none"
              >
                <img src={before} alt="Scene before the event" className="absolute inset-0 size-full object-cover" />
                <div className="absolute inset-0 overflow-hidden" style={{ width: `${pos}%` }}>
                  <img
                    src={after}
                    alt="Scene after the event"
                    className="absolute inset-0 h-full object-cover"
                    style={{ width: frameRef.current?.clientWidth ?? "100%" }}
                  />
                </div>
                <div
                  className="pointer-events-none absolute inset-y-0 w-px bg-primary shadow-[0_0_14px_oklch(0.83_0.135_195/0.9)]"
                  style={{ left: `${pos}%` }}
                />
                <span className="absolute top-2 left-2 font-mono text-[10px] tracking-[0.12em] text-primary">
                  AFTER
                </span>
                <span className="absolute top-2 right-2 font-mono text-[10px] tracking-[0.12em] text-muted-foreground">
                  BEFORE
                </span>
                <input
                  aria-label="Comparison position"
                  type="range"
                  min={0}
                  max={100}
                  value={pos}
                  onChange={(e) => setPos(Number(e.target.value))}
                  className="absolute inset-x-0 bottom-3 mx-4 h-1 cursor-pointer appearance-none rounded-full bg-surface-2 accent-primary"
                />
              </div>
              {usingDemo && (
                <p className="mt-3 font-mono text-[10px] tracking-[0.12em] text-warning uppercase">
                  Showing demo scenes — upload your own imagery below.
                </p>
              )}
            </Panel>

            <div className="grid gap-4 md:grid-cols-2">
              <Panel eyebrow="INPUT" title="Before Image">
                <UploadZone
                  compact
                  title="DROP BEFORE IMAGE"
                  hint="JPG / PNG"
                  accept="image/*"
                  onFile={(f) => setBeforeImage(URL.createObjectURL(f))}
                />
              </Panel>
              <Panel eyebrow="INPUT" title="After Image">
                <UploadZone
                  compact
                  title="DROP AFTER IMAGE"
                  hint="JPG / PNG"
                  accept="image/*"
                  onFile={(f) => setAfterImage(URL.createObjectURL(f))}
                />
              </Panel>
            </div>
          </div>

          <aside className="space-y-4">
            <Panel
              eyebrow="ANALYSIS"
              title="Damage Analysis"
              right={<StatusBadge kind="integration-ready" />}
            >
              <div className="grid grid-cols-2 gap-2">
                <Readout label="Detection Model" value="NOT CONNECTED" tone="muted" />
                <Readout label="Structures Lost" value="—" tone="muted" />
                <Readout label="Damage Index" value="—" tone="muted" />
                <Readout label="Confidence" value="—" tone="muted" />
              </div>
              <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
                No automated damage detection runs in this frontend build, so no numbers are
                reported. The panel is wired and ready for a detection service.
              </p>
            </Panel>

            <Panel eyebrow="CHANGE DETECTION" title="Pixel Difference">
              <ul className="space-y-2">
                {["Structural change", "Vegetation change", "Water extent change", "Debris field"].map(
                  (l) => (
                    <li
                      key={l}
                      className="flex items-center justify-between rounded-sm border border-border/70 bg-background/40 px-3 py-2"
                    >
                      <span className="font-mono text-[11px] tracking-[0.1em] uppercase">{l}</span>
                      <StatusBadge kind="coming-soon" label="AWAITING SERVICE" />
                    </li>
                  ),
                )}
              </ul>
            </Panel>

            <Panel eyebrow="METRICS" title="Affected Area">
              <div className="grid grid-cols-2 gap-2">
                <Readout label="Area Assessed" value="—" tone="muted" />
                <Readout label="Affected Area" value="—" tone="muted" />
                <Readout label="Georeference" value="REQUIRED" tone="muted" />
                <Readout label="Method" value="MANUAL REVIEW" />
              </div>
              <p className="mt-3 flex items-start gap-2 text-[11px] leading-relaxed text-muted-foreground">
                <SplitSquareHorizontal className="mt-0.5 size-3.5 shrink-0 text-primary" />
                Area metrics need georeferenced input and a detection service; nothing is estimated
                here.
              </p>
            </Panel>
          </aside>
        </div>
      </div>
    </div>
  );
}
