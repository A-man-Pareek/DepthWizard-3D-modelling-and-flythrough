import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

/**
 * Animated wireframe elevation field rendered on a 2D canvas.
 * Purely decorative visualization — no measured data is implied.
 */
export function TerrainField({ className, density = 26 }: { className?: string; density?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let frame = 0;
    let raf = 0;
    let w = 0;
    let h = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    const rows = density;
    const cols = density + 10;

    const height = (x: number, y: number, t: number) =>
      Math.sin(x * 0.55 + t * 0.6) * 0.5 +
      Math.cos(y * 0.42 - t * 0.35) * 0.42 +
      Math.sin((x + y) * 0.28 + t * 0.22) * 0.6;

    const draw = () => {
      frame += 1;
      const t = frame * 0.01;
      ctx.clearRect(0, 0, w, h);

      const cx = w / 2;
      const horizon = h * 0.34;
      const spanX = w * 0.9;
      const depth = h * 0.62;

      const project = (i: number, j: number) => {
        const u = i / (cols - 1) - 0.5;
        const v = j / (rows - 1);
        const persp = 0.35 + v * 0.95;
        const elev = height(i * 0.5, j * 0.5, t);
        const x = cx + u * spanX * persp;
        const y = horizon + v * depth - elev * 26 * persp;
        return { x, y, elev, persp };
      };

      // depth lines
      for (let j = 0; j < rows; j++) {
        ctx.beginPath();
        for (let i = 0; i < cols; i++) {
          const p = project(i, j);
          if (i === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        }
        const a = 0.06 + (j / rows) * 0.5;
        ctx.strokeStyle = `oklch(0.83 0.135 195 / ${a.toFixed(3)})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      for (let i = 0; i < cols; i += 2) {
        ctx.beginPath();
        for (let j = 0; j < rows; j++) {
          const p = project(i, j);
          if (j === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        }
        ctx.strokeStyle = "oklch(0.62 0.19 260 / 0.16)";
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // elevation peaks highlight
      for (let j = 2; j < rows; j += 3) {
        for (let i = 2; i < cols; i += 5) {
          const p = project(i, j);
          if (p.elev > 1.05) {
            ctx.beginPath();
            ctx.arc(p.x, p.y, 1.6, 0, Math.PI * 2);
            ctx.fillStyle = "oklch(0.83 0.135 195 / 0.85)";
            ctx.fill();
          }
        }
      }

      raf = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, [density]);

  return <canvas ref={ref} aria-hidden className={cn("size-full", className)} />;
}
