import { AlertTriangle, FileImage, Globe2, X } from "lucide-react";
import { toast } from "sonner";
import { useDw, formatBytes, type PipelineStageId } from "@/lib/dw-state";
import { UploadZone } from "./UploadZone";
import { Pipeline } from "./Pipeline";
import { HudButton, Panel, Readout, StatusBadge } from "./primitives";

const stageOrder: { id: PipelineStageId; label: string; caption?: string }[] = [
  { id: "loaded", label: "Image Loaded" },
  { id: "preprocessing", label: "Preprocessing", caption: "Decode · metadata · normalisation" },
  { id: "height", label: "Height Estimation", caption: "Requires inference endpoint" },
  { id: "dsm", label: "DSM Generated", caption: "Requires inference endpoint" },
  { id: "ready", label: "3D Ready", caption: "Load a GLB in the flythrough viewer" },
];

export function ImageIngest({ compact = false }: { compact?: boolean }) {
  const { image, setImage, stages, runPreprocessing } = useDw();

  const handleFile = (file: File) => {
    const name = file.name.toLowerCase();
    const isTiff = name.endsWith(".tif") || name.endsWith(".tiff");
    const ok =
      isTiff || /\.(jpe?g|png)$/.test(name) || file.type.startsWith("image/");
    if (!ok) {
      toast.error("UNSUPPORTED FORMAT", { description: "Use JPG, PNG, TIFF or GeoTIFF." });
      return;
    }
    const url = URL.createObjectURL(file);

    const commit = (width: number, height: number) => {
      setImage({
        name: file.name,
        type: isTiff ? "TIFF / GeoTIFF" : file.type || "image",
        sizeBytes: file.size,
        url,
        width,
        height,
        georeferenced: isTiff ? null : false,
      });
      toast.success("IMAGE INGESTED", { description: file.name });
      window.setTimeout(runPreprocessing, 1400);
    };

    if (isTiff) {
      // Browsers cannot decode TIFF/GeoTIFF natively — no preview, no invented dimensions.
      commit(0, 0);
      return;
    }
    const img = new Image();
    img.onload = () => commit(img.naturalWidth, img.naturalHeight);
    img.onerror = () => {
      toast.error("DECODE FAILED", { description: "Image could not be read in the browser." });
      URL.revokeObjectURL(url);
    };
    img.src = url;
  };

  const nodes = stageOrder.map((s) => ({
    label: s.label,
    caption: compact ? undefined : s.caption,
    status: stages[s.id],
  }));

  return (
    <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
      <Panel eyebrow="INPUT" title="Satellite Image Ingest" right={<StatusBadge kind="active" />}>
        {!image ? (
          <UploadZone onFile={handleFile} compact={compact} />
        ) : (
          <div className="space-y-4">
            <div className="corner-brackets relative aspect-[16/10] overflow-hidden rounded-sm border border-border bg-background">
              {image.url && image.width > 0 ? (
                <img
                  src={image.url}
                  alt={`Uploaded satellite image ${image.name}`}
                  className="size-full object-cover"
                />
              ) : (
                <div className="grid size-full place-items-center px-6 text-center">
                  <div>
                    <FileImage className="mx-auto size-6 text-warning" />
                    <p className="label-mono mt-2">TIFF PREVIEW UNAVAILABLE IN BROWSER</p>
                  </div>
                </div>
              )}
              <div className="pointer-events-none absolute inset-x-0 top-0 h-px animate-scan bg-gradient-to-r from-transparent via-primary/80 to-transparent" />
              <button
                onClick={() => setImage(null)}
                aria-label="Remove image"
                className="absolute top-2 right-2 grid size-7 place-items-center rounded-sm border border-border bg-background/80 text-muted-foreground transition-colors hover:text-destructive"
              >
                <X className="size-3.5" />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Readout label="File" value={<span className="truncate">{image.name}</span>} />
              <Readout label="Type" value={image.type} />
              <Readout
                label="Resolution"
                value={image.width ? `${image.width} × ${image.height}` : "N/A"}
                tone={image.width ? "primary" : "muted"}
              />
              <Readout label="Size" value={formatBytes(image.sizeBytes)} />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="label-mono flex items-center gap-1.5">
                <Globe2 className="size-3" /> Georeference
              </span>
              {image.georeferenced === null ? (
                <StatusBadge kind="coming-soon" label="METADATA NOT PARSED" />
              ) : (
                <StatusBadge kind="proposed" label="NON-GEOREFERENCED" />
              )}
            </div>
          </div>
        )}
      </Panel>

      <Panel eyebrow="PROCESSING" title="Reconstruction Pipeline">
        <Pipeline nodes={nodes} showStatus className="lg:flex-col" />
        {stages.height === "blocked" && (
          <div className="mt-4 flex gap-3 rounded-sm border border-warning/40 bg-warning/8 p-3">
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
            <p className="text-xs leading-relaxed text-muted-foreground">
              Preprocessing completed in-browser. Height estimation and DSM generation run on the
              inference service, which is not connected to this build — no estimated elevation values
              are shown until it is wired up.
            </p>
          </div>
        )}
        {!image && (
          <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
            Ingest an image to begin. Nothing is uploaded to a server: the file is inspected locally
            in your browser.
          </p>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <HudButton variant="outline" disabled={!image}>
            Run Height Estimation
          </HudButton>
          <StatusBadge kind="integration-ready" label="ENDPOINT NOT CONNECTED" className="self-center" />
        </div>
      </Panel>
    </div>
  );
}
