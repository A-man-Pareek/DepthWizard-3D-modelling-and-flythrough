import { useEffect, useRef } from "react";
import { UserRound, X } from "lucide-react";
import { StatusBadge, HudButton } from "./primitives";

export function ProfilePanel({ onClose }: { onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    const onDown = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) onClose();
    };
    window.addEventListener("keydown", onKey);
    const t = window.setTimeout(() => document.addEventListener("mousedown", onDown), 0);
    return () => {
      window.clearTimeout(t);
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onDown);
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-[60]"
    >
      <div
        ref={ref}
        role="dialog"
        aria-label="Profile"
        className="hud-panel absolute top-20 right-4 w-[min(320px,calc(100vw-2rem))] p-4"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-sm border border-primary/40 bg-primary/10 text-primary">
              <UserRound className="size-4" />
            </span>
            <div>
              <p className="font-display text-sm tracking-[0.18em] text-glow">DEPTHWIZARD</p>
              <p className="label-mono mt-0.5">8086 CREW</p>
            </div>
          </div>
          <button
            aria-label="Close profile"
            onClick={onClose}
            className="grid size-7 place-items-center rounded-sm border border-border text-muted-foreground hover:text-primary"
          >
            <X className="size-3.5" />
          </button>
        </div>

        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between rounded-sm border border-border/70 bg-background/40 px-3 py-2.5">
            <span className="label-mono">Access</span>
            <StatusBadge kind="proposed" label="DEMO MODE" />
          </div>
          <div className="flex items-center justify-between rounded-sm border border-border/70 bg-background/40 px-3 py-2.5">
            <span className="label-mono">Status</span>
            <StatusBadge kind="online" label="SYSTEM ONLINE" />
          </div>
          <div className="flex items-center justify-between rounded-sm border border-border/70 bg-background/40 px-3 py-2.5">
            <span className="label-mono">Problem Statement</span>
            <span className="font-mono text-[10px] text-primary">PS 26175</span>
          </div>
        </div>

        <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
          No accounts or sign-in are used. This build runs entirely in your browser.
        </p>

        <HudButton variant="outline" className="mt-4 w-full" onClick={onClose}>
          Close
        </HudButton>
      </div>
    </div>
  );
}
