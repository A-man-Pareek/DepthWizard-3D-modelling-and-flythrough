import { Link } from "@tanstack/react-router";
import { Lock } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { StatusBadge, type StatusKind } from "./primitives";
import { cn } from "@/lib/utils";

export function FeatureCard({
  icon: Icon,
  index,
  title,
  description,
  status,
  to,
}: {
  icon: LucideIcon;
  index: number;
  title: string;
  description: string;
  status: StatusKind;
  to?: string;
}) {
  const locked = status !== "active";

  const body = (
    <div
      className={cn(
        "corner-brackets group relative h-full overflow-hidden p-4 transition-all duration-300 hud-panel",
        locked
          ? "hover:border-warning/40"
          : "hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-[0_0_34px_oklch(0.83_0.135_195/0.16)]",
      )}
    >
      <div className="hud-grid-fine pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-40" />
      <div className="relative flex items-start justify-between gap-3">
        <span
          className={cn(
            "grid size-9 place-items-center rounded-sm border",
            locked
              ? "border-border-strong bg-surface-2 text-muted-foreground"
              : "border-primary/40 bg-primary/10 text-primary",
          )}
        >
          <Icon className="size-4" />
        </span>
        <span className="label-mono">{String(index).padStart(2, "0")}</span>
      </div>
      <h3 className="relative mt-4 font-display text-[13px] tracking-[0.1em] uppercase">{title}</h3>
      <p className="relative mt-2 text-xs leading-relaxed text-muted-foreground">{description}</p>
      <div className="relative mt-4 flex items-center justify-between gap-2">
        <StatusBadge kind={status} />
        {locked ? (
          <span className="flex items-center gap-1 font-mono text-[9px] tracking-[0.14em] text-muted-foreground uppercase">
            <Lock className="size-3" /> Locked
          </span>
        ) : (
          <span className="font-mono text-[9px] tracking-[0.14em] text-primary uppercase opacity-0 transition-opacity group-hover:opacity-100">
            Open →
          </span>
        )}
      </div>
    </div>
  );

  if (to && !locked) {
    return (
      <Link to={to} className="block h-full">
        {body}
      </Link>
    );
  }
  return body;
}
