import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Bot, Send, UserRound } from "lucide-react";
import { useDw } from "@/lib/dw-state";
import { HudButton, Panel, SectionHeading, StatusBadge } from "@/components/dw/primitives";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/copilot")({
  head: () => ({
    meta: [
      { title: "AI Copilot — Geospatial Chat Interface | DepthWizard" },
      {
        name: "description",
        content:
          "A GeoLLM-style copilot interface for terrain questions. Integration-ready: responses are clearly labelled demo text, no model is connected.",
      },
      { property: "og:title", content: "AI Copilot — DepthWizard" },
      {
        property: "og:description",
        content: "Terrain question interface for the DepthWizard geospatial copilot.",
      },
    ],
  }),
  component: CopilotPage,
});

const examples = [
  "What is the highest point?",
  "Where is the steepest region?",
  "Which areas should be inspected first?",
  "Show me terrain measurements.",
];

type Msg = { role: "user" | "demo"; text: string };

function demoAnswer(q: string, ctx: { max?: number | undefined; points: number }) {
  const lower = q.toLowerCase();
  if (lower.includes("highest") || lower.includes("peak"))
    return ctx.max !== undefined
      ? `The loaded mesh reaches a maximum height of ${ctx.max.toFixed(2)} scene units. Metric elevation needs georeferenced scale from the estimation service.`
      : "No terrain is loaded yet. Open the Terrain or 3D Flythrough page and load a model, and the measured maximum height will appear here.";
  if (lower.includes("steep") || lower.includes("slope"))
    return "Slope and aspect derivation is a proposed module. Once the DSM service is connected, the copilot will report the steepest cells with their gradient.";
  if (lower.includes("inspect") || lower.includes("first") || lower.includes("priority"))
    return "Inspection prioritisation depends on hazard and damage layers, which are integration-ready but not computed in this build. No priority ranking is invented here.";
  if (lower.includes("measure"))
    return ctx.points > 0
      ? `You have ${ctx.points} raycast measurement point(s) collected in this session. They are listed in the measurement panel of the 3D viewer.`
      : "No measurement points yet. Click the terrain surface in the 3D viewer to cast rays and collect elevation points.";
  return "This interface is not connected to a language model, so no answer is generated. Once the GeoLLM service is wired up, this question will be answered from the loaded terrain data.";
}

function CopilotPage() {
  const { scene, measurements } = useDw();
  const [input, setInput] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [msgs.length]);

  const send = (text: string) => {
    const q = text.trim();
    if (!q) return;
    setMsgs((m) => [
      ...m,
      { role: "user", text: q },
      { role: "demo", text: demoAnswer(q, { max: scene?.maxY, points: measurements.length }) },
    ]);
    setInput("");
  };

  return (
    <div className="px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-[1100px]">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionHeading
            kicker="Module 11"
            title="AI Copilot"
            subtitle="Ask natural-language questions about the terrain. No language model is connected — every reply below is clearly labelled demo text."
          />
          <StatusBadge
            kind="integration-ready"
            label="AI COPILOT — INTEGRATION READY"
            className="self-center"
          />
        </div>

        <Panel
          eyebrow="GEOLLM"
          title="Terrain Conversation"
          right={<StatusBadge kind="proposed" label="NO MODEL CONNECTED" />}
          className="mt-6"
          bodyClassName="p-0"
        >
          <div className="h-[52vh] min-h-[360px] space-y-3 overflow-y-auto p-4">
            {msgs.length === 0 && (
              <div className="grid h-full place-items-center text-center">
                <div>
                  <Bot className="mx-auto size-6 text-primary" />
                  <p className="mt-3 font-display text-sm tracking-[0.14em]">COPILOT STANDING BY</p>
                  <p className="mt-2 max-w-sm text-xs leading-relaxed text-muted-foreground">
                    Pick an example question or type your own. Replies are static demo text until an
                    LLM service is connected.
                  </p>
                </div>
              </div>
            )}
            {msgs.map((m, i) => (
              <div
                key={i}
                className={cn("flex gap-2.5", m.role === "user" ? "justify-end" : "justify-start")}
              >
                {m.role === "demo" && (
                  <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-sm border border-primary/40 bg-primary/10 text-primary">
                    <Bot className="size-3.5" />
                  </span>
                )}
                <div
                  className={cn(
                    "max-w-[80%] rounded-sm border px-3 py-2.5 text-xs leading-relaxed",
                    m.role === "user"
                      ? "border-primary/40 bg-primary/12 text-foreground"
                      : "border-border/70 bg-background/40 text-muted-foreground",
                  )}
                >
                  {m.role === "demo" && (
                    <span className="mb-1.5 block font-mono text-[9px] tracking-[0.16em] text-warning uppercase">
                      Demo response
                    </span>
                  )}
                  {m.text}
                </div>
                {m.role === "user" && (
                  <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-sm border border-border bg-surface-2 text-muted-foreground">
                    <UserRound className="size-3.5" />
                  </span>
                )}
              </div>
            ))}
            <div ref={endRef} />
          </div>

          <div className="border-t border-border p-3">
            <div className="flex flex-wrap gap-1.5">
              {examples.map((q) => (
                <button
                  key={q}
                  onClick={() => send(q)}
                  className="rounded-sm border border-border/70 bg-background/40 px-2.5 py-1.5 font-mono text-[10px] tracking-[0.1em] text-muted-foreground uppercase transition-colors hover:border-primary/50 hover:text-primary"
                >
                  {q}
                </button>
              ))}
            </div>
            <form
              className="mt-3 flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                send(input);
              }}
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about elevation, slope, risk zones…"
                aria-label="Message the copilot"
                className="flex-1 rounded-sm border border-border bg-background/60 px-3 py-2.5 font-mono text-xs text-foreground outline-none placeholder:text-muted-foreground focus:border-primary/60"
              />
              <HudButton type="submit">
                <Send className="size-3.5" /> Send
              </HudButton>
            </form>
          </div>
        </Panel>
      </div>
    </div>
  );
}
