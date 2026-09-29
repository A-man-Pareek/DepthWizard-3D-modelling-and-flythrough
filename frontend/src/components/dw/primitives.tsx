import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export type StatusKind = "active" | "proposed" | "coming-soon" | "integration-ready" | "online";

const statusStyles: Record<StatusKind, string> = {
  active: "border-chart-5/40 bg-chart-5/10 text-chart-5",
  online: "border-chart-5/40 bg-chart-5/10 text-chart-5",
  proposed: "border-warning/40 bg-warning/10 text-warning",
  "coming-soon": "border-border-strong bg-surface-2 text-muted-foreground",
  "integration-ready": "border-accent/45 bg-accent/12 text-accent",
};

const statusLabels: Record<StatusKind, string> = {
  active: "ACTIVE",
  online: "ONLINE",
  proposed: "PROPOSED",
  "coming-soon": "COMING SOON",
  "integration-ready": "INTEGRATION READY",
};

export function StatusBadge({
  kind,
  label,
  className,
}: {
  kind: StatusKind;
  label?: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 font-mono text-[10px] tracking-[0.16em] whitespace-nowrap",
        statusStyles[kind],
        className,
      )}
    >
      {(kind === "active" || kind === "online") && (
        <span className="animate-pulse-dot size-1.5 rounded-full bg-chart-5" />
      )}
      {label ?? statusLabels[kind]}
    </span>
  );
}

export function Panel({
  title,
  eyebrow,
  right,
  children,
  className,
  bodyClassName,
}: {
  title?: string;
  eyebrow?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cn("hud-panel overflow-hidden", className)}>
      {(title || right) && (
        <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-2.5">
          <div className="min-w-0">
            {eyebrow && <p className="label-mono">{eyebrow}</p>}
            {title && (
              <h3 className="truncate font-display text-sm tracking-[0.12em] uppercase">
                {title}
              </h3>
            )}
          </div>
          {right}
        </header>
      )}
      <div className={cn("p-4", bodyClassName)}>{children}</div>
    </section>
  );
}

export function Readout({
  label,
  value,
  unit,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  unit?: string | undefined;
  tone?: "default" | "primary" | "muted";
}) {
  return (
    <div className="rounded-sm border border-border/70 bg-background/40 px-3 py-2">
      <p className="label-mono">{label}</p>
      <p
        className={cn(
          "mt-1 font-mono text-sm",
          tone === "primary" && "text-primary",
          tone === "muted" && "text-muted-foreground",
        )}
      >
        {value}
        {unit && <span className="ml-1 text-[10px] text-muted-foreground">{unit}</span>}
      </p>
    </div>
  );
}

export function SectionHeading({
  kicker,
  title,
  subtitle,
  className,
}: {
  kicker?: string;
  title: string;
  subtitle?: string;
  className?: string;
}) {
  return (
    <div className={cn("max-w-2xl", className)}>
      {kicker && (
        <p className="label-mono flex items-center gap-2 text-primary/80">
          <span className="h-px w-8 bg-primary/50" />
          {kicker}
        </p>
      )}
      <h2 className="mt-3 font-display text-2xl tracking-tight uppercase sm:text-3xl">{title}</h2>
      {subtitle && <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{subtitle}</p>}
    </div>
  );
}

export function HudButton({
  children,
  variant = "primary",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "outline" | "ghost" | "danger";
}) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-sm px-4 py-2.5 font-mono text-[11px] tracking-[0.16em] uppercase transition-all duration-200 disabled:pointer-events-none disabled:opacity-40",
        variant === "primary" &&
          "bg-primary text-primary-foreground hover:shadow-[0_0_26px_oklch(0.83_0.135_195/0.45)]",
        variant === "outline" &&
          "border border-border-strong bg-surface/60 text-foreground hover:border-primary/60 hover:text-primary",
        variant === "ghost" && "text-muted-foreground hover:bg-surface-2 hover:text-foreground",
        variant === "danger" &&
          "border border-destructive/50 bg-destructive/10 text-destructive hover:bg-destructive/20",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function GridBackdrop({ className }: { className?: string }) {
  return (
    <div className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      <div className="hud-grid animate-grid-drift absolute inset-0 opacity-70" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,transparent_10%,var(--background)_78%)]" />
    </div>
  );
}
