import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Bot, Loader2, Send, UserRound, Sparkles } from "lucide-react";
import { useDw } from "@/lib/dw-state";
import { HudButton, Panel, SectionHeading, StatusBadge } from "@/components/dw/primitives";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/copilot")({
  head: () => ({
    meta: [
      { title: "GeoLLM AI Copilot — Geospatial Intelligence | DepthWizard" },
      {
        name: "description",
        content:
          "DepthWizard GeoLLM AI Copilot: Natural language queries for 3D terrain elevation, structural height, and disaster vulnerability.",
      },
      { property: "og:title", content: "GeoLLM AI Copilot — DepthWizard" },
      {
        property: "og:description",
        content: "Geospatial AI Assistant powered by DepthWizard GeoLLM engine.",
      },
    ],
  }),
  component: CopilotPage,
});

const examples = [
  "What is the maximum elevation and height profile?",
  "Assess flood vulnerability for building structures",
  "Identify safe evacuation grounds & high-elevation zones",
  "Summarize landslide slope susceptibility & recommendations",
];

type Msg = { role: "user" | "geollm"; text: string; model?: string };

function CopilotPage() {
  const { scene, measurements } = useDw();
  const [input, setInput] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [msgs.length, loading]);

  const send = async (text: string) => {
    const q = text.trim();
    if (!q || loading) return;

    setMsgs((m) => [...m, { role: "user", text: q }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/geollm/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: q,
          context: {
            max_height: scene?.maxY || 6.5,
            building_count: 48,
            hazard_type: "FLOOD",
            measurements_count: measurements.length,
          },
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setMsgs((m) => [
          ...m,
          { role: "geollm", text: data.response, model: data.model || "DepthWizard GeoLLM-v2" },
        ]);
      } else {
        setMsgs((m) => [
          ...m,
          { role: "geollm", text: "⚠️ GeoLLM service error. Please verify backend status." },
        ]);
      }
    } catch (e) {
      setMsgs((m) => [
        ...m,
        { role: "geollm", text: "⚠️ GeoLLM service offline. Ensure backend app.py is running on port 8000." },
      ]);
    }
    setLoading(false);
  };

  return (
    <div className="px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-[1100px]">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionHeading
            kicker="Module 11 · GeoLLM AI Copilot"
            title="Geospatial AI Assistant"
            subtitle="Ask natural language questions about 3D terrain elevation, structural footprints, and hazard mitigation."
          />
          <StatusBadge
            kind="active"
            label="GEOLLM ONLINE — ACTIVE"
            className="self-center"
          />
        </div>

        <Panel
          eyebrow="GEOLLM ENGINE"
          title="Geospatial Intelligence Conversation"
          right={<StatusBadge kind="active" label="MODEL CONNECTED" />}
          className="mt-6"
          bodyClassName="p-0"
        >
          <div className="h-[52vh] min-h-[360px] space-y-3 overflow-y-auto p-4">
            {msgs.length === 0 && (
              <div className="grid h-full place-items-center text-center">
                <div>
                  <Sparkles className="mx-auto size-7 text-primary animate-pulse" />
                  <p className="mt-3 font-display text-sm tracking-[0.14em] text-primary">GEOLLM ENGINE READY</p>
                  <p className="mt-2 max-w-sm text-xs leading-relaxed text-muted-foreground">
                    Select a quick query below or type your question. DepthWizard GeoLLM will analyze local terrain telemetry and structural footprints.
                  </p>
                </div>
              </div>
            )}
            {msgs.map((m, i) => (
              <div
                key={i}
                className={cn("flex gap-2.5", m.role === "user" ? "justify-end" : "justify-start")}
              >
                {m.role === "geollm" && (
                  <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-sm border border-primary/40 bg-primary/10 text-primary">
                    <Bot className="size-3.5" />
                  </span>
                )}
                <div
                  className={cn(
                    "max-w-[85%] rounded-sm border px-3.5 py-2.5 text-xs leading-relaxed",
                    m.role === "user"
                      ? "border-primary/40 bg-primary/12 text-foreground"
                      : "border-border/70 bg-background/50 text-foreground/90 whitespace-pre-wrap font-sans",
                  )}
                >
                  {m.role === "geollm" && (
                    <span className="mb-1.5 flex items-center gap-1.5 font-mono text-[9px] tracking-[0.16em] text-primary uppercase">
                      <Sparkles className="size-2.5" /> {m.model || "GeoLLM Engine"}
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
            {loading && (
              <div className="flex items-center gap-2 text-xs text-primary font-mono pl-2">
                <Loader2 className="size-3.5 animate-spin" /> GeoLLM analyzing terrain telemetry & risk layers…
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div className="border-t border-border p-3">
            <div className="flex flex-wrap gap-1.5">
              {examples.map((q) => (
                <button
                  key={q}
                  onClick={() => send(q)}
                  disabled={loading}
                  className="rounded-sm border border-border/70 bg-background/40 px-2.5 py-1.5 font-mono text-[10px] tracking-[0.1em] text-muted-foreground uppercase transition-colors hover:border-primary/50 hover:text-primary disabled:opacity-50"
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
                placeholder="Ask GeoLLM about flood risk, building heights, or safe evacuation grounds…"
                aria-label="Message GeoLLM"
                disabled={loading}
                className="flex-1 rounded-sm border border-border bg-background/60 px-3 py-2.5 font-mono text-xs text-foreground outline-none placeholder:text-muted-foreground focus:border-primary/60 disabled:opacity-50"
              />
              <HudButton type="submit" disabled={loading}>
                {loading ? <Loader2 className="size-3.5 animate-spin" /> : <Send className="size-3.5" />} Send
              </HudButton>
            </form>
          </div>
        </Panel>
      </div>
    </div>
  );
}
