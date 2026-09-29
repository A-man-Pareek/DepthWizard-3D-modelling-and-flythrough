import { Suspense, lazy, useEffect, useState } from "react";

const Client = lazy(() => import("./GlbViewerClient"));

function Fallback() {
  return (
    <div className="grid size-full place-items-center rounded-lg border border-border bg-surface/40">
      <p className="label-mono animate-pulse">INITIALISING WEBGL RENDERER…</p>
    </div>
  );
}

export function GlbViewer(props: { file: File | null; demo: boolean; className?: string }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted)
    return (
      <div className={props.className}>
        <Fallback />
      </div>
    );

  return (
    <Suspense
      fallback={
        <div className={props.className}>
          <Fallback />
        </div>
      }
    >
      <Client {...props} />
    </Suspense>
  );
}
