import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";
import { DwProvider } from "@/lib/dw-state";
import { Navbar } from "@/components/dw/Navbar";
import { Toaster } from "@/components/ui/sonner";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="font-display text-7xl font-bold text-primary text-glow">404</h1>
        <h2 className="mt-4 font-display text-xl tracking-[0.14em] uppercase">Sector not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-sm bg-primary px-4 py-2 font-mono text-[11px] tracking-[0.16em] text-primary-foreground uppercase"
          >
            Return to command center
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="font-display text-xl tracking-[0.12em] uppercase">System fault</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Something went wrong on our end. You can try refreshing or head back home.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex items-center justify-center rounded-sm bg-primary px-4 py-2 font-mono text-[11px] tracking-[0.16em] text-primary-foreground uppercase"
          >
            Retry
          </button>
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-sm border border-border-strong bg-surface px-4 py-2 font-mono text-[11px] tracking-[0.16em] uppercase"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "DepthWizard — Single-View Height Estimation & 3D Flythrough" },
      {
        name: "description",
        content:
          "DepthWizard turns a single satellite image into an elevation-aware 3D terrain for disaster intelligence. SIH 2026, PS 26175, 8086 Crew.",
      },
      { name: "author", content: "8086 Crew" },
      { property: "og:title", content: "DepthWizard — Single-View Height Estimation" },
      {
        property: "og:description",
        content:
          "Geospatial command console for single-view height estimation, DSM reconstruction and 3D terrain flythrough.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap",
      },
      { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();

  return (
    <QueryClientProvider client={queryClient}>
      <DwProvider>
        <div className="flex min-h-screen flex-col">
          <Navbar />
          {/* Required: nested routes render here. Removing <Outlet /> breaks all child routes. */}
          <main className="flex-1">
            <Outlet />
          </main>
          <footer className="border-t border-border bg-background/60 px-4 py-5 sm:px-6">
            <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3">
              <p className="label-mono">
                DEPTHWIZARD · SINGLE-VIEW HEIGHT ESTIMATION &amp; 3D FLYTHROUGH
              </p>
              <p className="label-mono">SIH 2026 · PS 26175 · DISASTER MANAGEMENT · 8086 CREW</p>
            </div>
          </footer>
        </div>
        <Toaster position="bottom-right" />
      </DwProvider>
    </QueryClientProvider>
  );
}
