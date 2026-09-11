import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { cn } from "@/lib/utils";

export function UploadZone({
  title = "DROP SATELLITE IMAGE HERE",
  hint = "JPG / PNG / TIFF / GeoTIFF",
  accept = ".jpg,.jpeg,.png,.tif,.tiff,image/*",
  onFile,
  className,
  compact = false,
}: {
  title?: string;
  hint?: string;
  accept?: string;
  onFile: (file: File) => void;
  className?: string;
  compact?: boolean;
}) {
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        const f = e.dataTransfer.files?.[0];
        if (f) onFile(f);
      }}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
      className={cn(
        "corner-brackets group relative cursor-pointer overflow-hidden rounded-lg border border-dashed transition-all duration-300",
        compact ? "px-4 py-8" : "px-6 py-14",
        drag
          ? "border-primary bg-primary/10 shadow-[0_0_38px_oklch(0.83_0.135_195/0.28)]"
          : "border-border-strong bg-surface/40 hover:border-primary/60 hover:bg-primary/5",
        className,
      )}
    >
      <div className="hud-grid-fine pointer-events-none absolute inset-0 opacity-40" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px animate-scan bg-gradient-to-r from-transparent via-primary/70 to-transparent" />
      <div className="relative flex flex-col items-center text-center">
        <span className="grid size-11 place-items-center rounded-sm border border-primary/40 bg-primary/10 text-primary transition-transform duration-300 group-hover:-translate-y-0.5">
          <UploadCloud className="size-5" />
        </span>
        <p className="mt-4 font-display text-sm tracking-[0.16em]">{title}</p>
        <p className="label-mono mt-2">{hint}</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
          e.target.value = "";
        }}
      />
    </div>
  );
}
