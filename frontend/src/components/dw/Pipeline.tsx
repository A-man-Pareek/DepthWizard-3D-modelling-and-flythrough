import { Check, ChevronRight, Loader2, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StageStatus } from "@/lib/dw-state";

export type PipelineNode = {
  label: string;
  caption?: string | undefined;
  status?: StageStatus;
};

export function Pipeline({
  nodes,
  className,
  showStatus = false,
}: {
  nodes: PipelineNode[];
  className?: string;
  showStatus?: boolean;
}) {
  return (
    <ol className={cn("flex flex-col gap-2 lg:flex-row lg:items-stretch", className)}>
      {nodes.map((n, i) => {
        const status = n.status ?? "complete";
        return (
          <li key={n.label} className="flex flex-1 items-center gap-2">
            <div
              className={cn(
                "hud-panel relative flex-1 px-3 py-3 transition-all duration-300",
                status === "complete" && "border-primary/40 shadow-[var(--glow-primary)]",
                status === "running" && "border-accent/50",
                status === "blocked" && "border-warning/40",
              )}
            >
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "grid size-5 shrink-0 place-items-center rounded-full border font-mono text-[9px]",
                    status === "complete" && "border-primary/60 bg-primary/15 text-primary",
                    status === "running" && "border-accent/60 bg-accent/15 text-accent",
                    status === "blocked" && "border-warning/60 bg-warning/15 text-warning",
                    status === "pending" && "border-border-strong text-muted-foreground",
                  )}
                >
                  {status === "complete" ? (
                    <Check className="size-3" />
                  ) : status === "running" ? (
                    <Loader2 className="size-3 animate-spin" />
                  ) : status === "blocked" ? (
                    <Lock className="size-2.5" />
                  ) : (
                    String(i + 1).padStart(2, "0")
                  )}
                </span>
                <span className="font-mono text-[10px] leading-tight tracking-[0.14em] uppercase">
                  {n.label}
                </span>
              </div>
              {n.caption && (
                <p className="mt-1.5 pl-7 text-[10px] leading-snug text-muted-foreground">
                  {n.caption}
                </p>
              )}
              {showStatus && status === "running" && (
                <div className="mt-2 ml-7 h-0.5 overflow-hidden rounded-full bg-surface-2">
                  <div className="h-full w-1/3 animate-flow bg-accent" />
                </div>
              )}
            </div>
            {i < nodes.length - 1 && (
              <ChevronRight className="hidden size-4 shrink-0 text-primary/50 lg:block" />
            )}
          </li>
        );
      })}
    </ol>
  );
}
