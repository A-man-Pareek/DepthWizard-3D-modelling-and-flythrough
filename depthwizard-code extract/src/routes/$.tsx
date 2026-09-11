import { createFileRoute, Link } from "@tanstack/react-router";
import { GridBackdrop, HudButton } from "@/components/dw/primitives";

export const Route = createFileRoute("/$")({
  head: () => ({
    meta: [
      { title: "Sector Not Found | DepthWizard" },
      { name: "description", content: "This DepthWizard sector does not exist." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: NotFound,
});

function NotFound() {
  return (
    <div className="relative grid min-h-[70vh] place-items-center overflow-hidden px-4">
      <GridBackdrop />
      <div className="relative max-w-md text-center">
        <p className="label-mono text-primary/80">ERROR 404</p>
        <h1 className="mt-3 font-display text-3xl tracking-[0.12em] text-primary uppercase text-glow sm:text-4xl">
          Sector Not Found
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          The requested sector is outside the mapped area of this console.
        </p>
        <div className="mt-7 flex justify-center">
          <Link to="/">
            <HudButton>Return to Home</HudButton>
          </Link>
        </div>
      </div>
    </div>
  );
}
