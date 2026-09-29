import { Link } from "@tanstack/react-router";
import { Menu, Mountain, Settings, UserRound, X } from "lucide-react";
import { useState } from "react";
import { StatusBadge } from "./primitives";
import { SettingsPanel } from "./SettingsPanel";
import { ProfilePanel } from "./ProfilePanel";
import { cn } from "@/lib/utils";

const links = [
  { to: "/", label: "Home" },
  { to: "/terrain", label: "Terrain" },
  { to: "/flythrough", label: "3D Flythrough" },
  { to: "/hazards", label: "Hazard Analysis" },
  { to: "/damage", label: "Damage Analysis" },
  { to: "/copilot", label: "AI Copilot" },
  { to: "/reports", label: "Reports" },
] as const;

export function Navbar() {
  const [open, setOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/85 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[1600px] items-center gap-6 px-4 sm:px-6">
        <Link to="/" className="group flex items-center gap-2.5">
          <span className="relative grid size-8 place-items-center rounded-sm border border-primary/40 bg-primary/10">
            <Mountain className="size-4 text-primary" />
            <span className="absolute inset-0 rounded-sm ring-1 ring-primary/20 transition group-hover:ring-primary/50" />
          </span>
          <span className="leading-none">
            <span className="block font-display text-base tracking-[0.22em] text-glow">
              DEPTHWIZARD
            </span>
            <span className="label-mono mt-0.5 block text-[9px] tracking-[0.2em]">
              PS 26175 · 8086 CREW
            </span>
          </span>
        </Link>

        <nav className="ml-2 hidden flex-1 items-center gap-0.5 lg:flex">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              activeOptions={{ exact: l.to === "/" }}
              className="relative rounded-sm px-3 py-2 font-mono text-[11px] tracking-[0.14em] text-muted-foreground uppercase transition-colors hover:text-foreground data-[status=active]:text-primary"
            >
              {l.label}
              <span className="absolute inset-x-3 -bottom-px hidden h-px bg-primary shadow-[0_0_10px_oklch(0.83_0.135_195/0.8)] data-[status=active]:block" />
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2 lg:ml-0">
          <StatusBadge kind="online" label="SYSTEM ONLINE" className="hidden sm:inline-flex" />
          <button
            aria-label="Settings"
            onClick={() => {
              setProfileOpen(false);
              setSettingsOpen((v) => !v);
            }}
            className="grid size-8 place-items-center rounded-sm border border-border text-muted-foreground transition-colors hover:border-primary/50 hover:text-primary"
          >
            <Settings className="size-3.5" />
          </button>
          <button
            aria-label="Account"
            onClick={() => {
              setSettingsOpen(false);
              setProfileOpen((v) => !v);
            }}
            className="grid size-8 place-items-center rounded-sm border border-border text-muted-foreground transition-colors hover:border-primary/50 hover:text-primary"
          >
            <UserRound className="size-3.5" />
          </button>
          <button
            aria-label="Menu"
            onClick={() => setOpen((v) => !v)}
            className="grid size-8 place-items-center rounded-sm border border-border text-muted-foreground lg:hidden"
          >
            {open ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>
      </div>

      <div
        className={cn(
          "grid overflow-hidden border-t border-border transition-all duration-300 lg:hidden",
          open ? "max-h-96" : "max-h-0",
        )}
      >
        <nav className="flex flex-col p-2">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              onClick={() => setOpen(false)}
              activeOptions={{ exact: l.to === "/" }}
              className="rounded-sm px-3 py-2.5 font-mono text-[11px] tracking-[0.14em] text-muted-foreground uppercase data-[status=active]:bg-surface-2 data-[status=active]:text-primary"
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
      {settingsOpen && <SettingsPanel onClose={() => setSettingsOpen(false)} />}
      {profileOpen && <ProfilePanel onClose={() => setProfileOpen(false)} />}
    </header>
  );
}
