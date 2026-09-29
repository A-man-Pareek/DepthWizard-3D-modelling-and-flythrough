import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { useDw, type Settings } from "@/lib/dw-state";
import { HudButton } from "./primitives";
import { cn } from "@/lib/utils";

const themes: { id: Settings["theme"]; label: string }[] = [
  { id: "abyss", label: "Abyss" },
  { id: "midnight", label: "Midnight" },
  { id: "steel", label: "Steel" },
];

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-sm border border-border/70 bg-background/40 px-3 py-2.5">
      <span className="label-mono">{label}</span>
      {children}
    </div>
  );
}

function Switch({ on, onClick }: { on: boolean; onClick: () => void }) {
  return (
    <button
      role="switch"
      aria-checked={on}
      onClick={onClick}
      className={cn(
        "relative h-5 w-10 rounded-full border transition-colors",
        on ? "border-primary/60 bg-primary/25" : "border-border bg-surface-2",
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 size-3.5 rounded-full transition-all",
          on ? "left-5 bg-primary" : "left-0.5 bg-muted-foreground",
        )}
      />
    </button>
  );
}

export function SettingsPanel({ onClose }: { onClose: () => void }) {
  const { settings, updateSettings, resetSettings } = useDw();
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
      className="fixed inset-0 z-[60] bg-background/70 backdrop-blur-sm"
    >
      <div
        ref={ref}
        role="dialog"
        aria-label="Settings"
        className="hud-panel absolute top-20 right-4 w-[min(360px,calc(100vw-2rem))] p-4"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="label-mono">CONSOLE</p>
            <h2 className="font-display text-sm tracking-[0.14em] uppercase">Settings</h2>
          </div>
          <button
            aria-label="Close settings"
            onClick={onClose}
            className="grid size-7 place-items-center rounded-sm border border-border text-muted-foreground hover:text-primary"
          >
            <X className="size-3.5" />
          </button>
        </div>

        <div className="mt-4 space-y-2">
          <Row label="Interface Theme">
            <div className="flex rounded-sm border border-border p-0.5">
              {themes.map((t) => (
                <button
                  key={t.id}
                  onClick={() => updateSettings({ theme: t.id })}
                  className={cn(
                    "rounded-sm px-2 py-1 font-mono text-[10px] tracking-[0.12em] uppercase",
                    settings.theme === t.id
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground",
                  )}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </Row>
          <Row label="Grid Visibility">
            <Switch on={settings.grid} onClick={() => updateSettings({ grid: !settings.grid })} />
          </Row>
          <Row label="Wireframe">
            <Switch
              on={settings.wireframe}
              onClick={() => updateSettings({ wireframe: !settings.wireframe })}
            />
          </Row>
          <div className="rounded-sm border border-border/70 bg-background/40 px-3 py-2.5">
            <div className="flex items-center justify-between">
              <span className="label-mono">Terrain Height Exaggeration</span>
              <span className="font-mono text-[10px] text-primary">
                {settings.exaggeration.toFixed(1)}×
              </span>
            </div>
            <input
              type="range"
              min={0.2}
              max={4}
              step={0.1}
              value={settings.exaggeration}
              onChange={(e) => updateSettings({ exaggeration: Number(e.target.value) })}
              className="mt-2.5 h-1 w-full cursor-pointer appearance-none rounded-full bg-surface-2 accent-primary"
            />
          </div>
          <Row label="Motion / Animation">
            <Switch
              on={settings.motion}
              onClick={() => updateSettings({ motion: !settings.motion })}
            />
          </Row>
        </div>

        <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
          Viewer settings apply to the terrain and flythrough scenes. Preferences are held for this
          session only — nothing is stored on a server.
        </p>

        <div className="mt-4 flex gap-2">
          <HudButton variant="outline" className="flex-1" onClick={resetSettings}>
            Reset
          </HudButton>
          <HudButton className="flex-1" onClick={onClose}>
            Close
          </HudButton>
        </div>
      </div>
    </div>
  );
}
