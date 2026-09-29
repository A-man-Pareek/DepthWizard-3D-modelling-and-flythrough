import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  ExternalLink,
  FileImage,
  Globe2,
  Loader2,
  Plane,
  Rocket,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { useDw, formatBytes, type PipelineStageId } from "@/lib/dw-state";
import { UploadZone } from "./UploadZone";
import { Pipeline } from "./Pipeline";
import { HudButton, Panel, Readout, StatusBadge } from "./primitives";

const stageOrder: { id: PipelineStageId; label: string; caption?: string }[] = [
  { id: "loaded", label: "Image Loaded" },
  { id: "preprocessing", label: "Preprocessing", caption: "Optical normalization & tiling" },
  { id: "height", label: "Height & Segmentation", caption: "HTC-DC Net + SegFormer" },
  { id: "dsm", label: "DSM & Grid Export", caption: "GeoTIFF & Height Grid JSON" },
  { id: "ready", label: "3D GLB Ready", caption: "2D-to-3D mesh & Flythrough" },
];

export function ImageIngest({ compact = false }: { compact?: boolean }) {
  const {
    image,
    setImage,
    stages,
    processImageWithBackend,
    glbUrl,
    heightMetadata,
  } = useDw();

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleFile = (file: File) => {
    const name = file.name.toLowerCase();
    const isTiff = name.endsWith(".tif") || name.endsWith(".tiff");
    const ok =
      isTiff || /\.(jpe?g|png|avif|webp)$/.test(name) || file.type.startsWith("image/");
    if (!ok) {
      toast.error("UNSUPPORTED FORMAT", { description: "Use JPG, PNG, TIFF, AVIF or GeoTIFF." });
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
        sourceFile: file,
      });
      toast.success("IMAGE INGESTED", { description: "Triggering automatic 3D pipeline..." });

      // Automatically trigger unified backend pipeline
      setIsSubmitting(true);
      processImageWithBackend(file).finally(() => setIsSubmitting(false));
    };

    if (isTiff) {
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

  const handleManualRun = () => {
    if (!image?.sourceFile) {
      toast.error("NO SOURCE FILE", { description: "Please upload an image file first." });
      return;
    }
    setIsSubmitting(true);
    processImageWithBackend(image.sourceFile).finally(() => setIsSubmitting(false));
  };

  const nodes = stageOrder.map((s) => ({
    label: s.label,
    caption: compact ? undefined : s.caption,
    status: stages[s.id],
  }));

  const isRunning = stages.height === "running" || stages.dsm === "running" || isSubmitting;
  const isComplete = stages.ready === "complete";
  const baseName = image ? image.name.replace(/\.[^/.]+$/, "") : "";

  return (
    <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
      <Panel
        eyebrow="INPUT"
        title="Optical Satellite Imagery"
        right={<StatusBadge kind={isRunning ? "active" : isComplete ? "active" : "proposed"} />}
      >
        {!image ? (
          <UploadZone onFile={handleFile} compact={compact} />
        ) : (
          <div className="space-y-4">
            <div className="corner-brackets relative aspect-[16/10] overflow-hidden rounded-sm border border-border bg-background">
              {image.url && image.width > 0 ? (
                <img
                  src={image.url}
                  alt={`Uploaded optical image ${image.name}`}
                  className="size-full object-cover"
                />
              ) : (
                <div className="grid size-full place-items-center px-6 text-center">
                  <div>
                    <FileImage className="mx-auto size-6 text-warning" />
                    <p className="label-mono mt-2">TIFF / GEOTIFF RASTER READY FOR PIPELINE</p>
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
                value={image.width ? `${image.width} × ${image.height}` : "Raster Stream"}
                tone={image.width ? "primary" : "muted"}
              />
              <Readout label="Size" value={formatBytes(image.sizeBytes)} />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="label-mono flex items-center gap-1.5">
                <Globe2 className="size-3" /> Georeference
              </span>
              {image.georeferenced === null ? (
                <StatusBadge kind="active" label="GEOTIFF / METADATA SYNC" />
              ) : (
                <StatusBadge kind="proposed" label="MONOCULAR CALIBRATION" />
              )}
            </div>
          </div>
        )}
      </Panel>

      <Panel eyebrow="PROCESSING" title="DepthWizard End-to-End Pipeline">
        <Pipeline nodes={nodes} showStatus className="lg:flex-col" />

        {isRunning && (
          <div className="mt-4 flex items-center gap-3 rounded-sm border border-primary/40 bg-primary/10 p-3">
            <Loader2 className="size-4 animate-spin text-primary" />
            <div className="text-xs">
              <p className="font-semibold text-primary">Inference & 3D Reconstruction in progress...</p>
              <p className="text-muted-foreground">Running HTC-DC Net, SegFormer, and generating 3D GLB mesh.</p>
            </div>
          </div>
        )}

        {isComplete && (
          <div className="mt-4 space-y-3">
            <div className="flex items-center gap-2.5 rounded-sm border border-emerald-500/40 bg-emerald-500/10 p-3">
              <CheckCircle2 className="size-4 text-emerald-400" />
              <p className="text-xs text-emerald-300">
                Height map, segmentation, JSON metadata, and 3D GLB model successfully generated!
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              <a
                href={`http://127.0.0.1:8000/download/${baseName}_dsm.tif`}
                download
                className="flex items-center justify-between rounded-sm border border-border bg-background/50 px-2.5 py-1.5 text-[11px] hover:border-primary"
              >
                <span>Height DSM (.tif)</span>
                <Download className="size-3 text-primary" />
              </a>
              <a
                href={`http://127.0.0.1:8000/download/${baseName}_metadata.json`}
                download
                className="flex items-center justify-between rounded-sm border border-border bg-background/50 px-2.5 py-1.5 text-[11px] hover:border-primary"
              >
                <span>Height Grid (.json)</span>
                <Download className="size-3 text-primary" />
              </a>
              <a
                href={`http://127.0.0.1:8000/download/${baseName}_segmentation.tif`}
                download
                className="flex items-center justify-between rounded-sm border border-border bg-background/50 px-2.5 py-1.5 text-[11px] hover:border-primary"
              >
                <span>Segmentation (.tif)</span>
                <Download className="size-3 text-primary" />
              </a>
            </div>

            <div className="flex flex-wrap gap-2 pt-2">
              <a href="/flythrough">
                <HudButton variant="primary">
                  <Rocket className="mr-1.5 size-3.5" /> Launch 3D Flythrough
                </HudButton>
              </a>
              <a
                href={
                  glbUrl
                    ? `http://localhost:5174/?model=${encodeURIComponent(glbUrl)}&_t=${Date.now()}`
                    : `http://localhost:5174/?model=http://127.0.0.1:8000/download/imgg_fresh.glb&_t=${Date.now()}`
                }
                target="_blank"
                rel="noreferrer"
              >
                <HudButton variant="outline">
                  <Plane className="mr-1.5 size-3.5" /> Open 3D Viewer Flythrough <ExternalLink className="ml-1 size-3" />
                </HudButton>
              </a>
            </div>
          </div>
        )}

        {!isComplete && !isRunning && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <HudButton
              variant="primary"
              disabled={!image}
              onClick={handleManualRun}
            >
              <Rocket className="mr-1.5 size-3.5" /> Run 3D Pipeline
            </HudButton>
            <StatusBadge
              kind={image ? "active" : "integration-ready"}
              label={image ? "READY TO EXECUTE" : "WAITING FOR IMAGE"}
              className="self-center"
            />
          </div>
        )}
      </Panel>
    </div>
  );
}
