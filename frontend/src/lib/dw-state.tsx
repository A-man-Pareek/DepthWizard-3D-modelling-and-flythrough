import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type PipelineStageId =
  | "loaded"
  | "preprocessing"
  | "height"
  | "dsm"
  | "ready";

export type StageStatus = "pending" | "running" | "complete" | "blocked";

export type ImageAsset = {
  name: string;
  type: string;
  sizeBytes: number;
  url: string;
  width: number;
  height: number;
  georeferenced: boolean | null;
  sourceFile?: File;
};

export type SceneStats = {
  label: string;
  source: "demo" | "upload";
  vertices: number;
  triangles: number;
  textured: boolean;
  minY: number;
  maxY: number;
  meanY: number;
};

export type Measurement = {
  id: number;
  x: number;
  y: number;
  z: number;
  elevation: number;
  distanceFromPrev: number | null;
};

export type Settings = {
  theme: "abyss" | "midnight" | "steel";
  grid: boolean;
  wireframe: boolean;
  exaggeration: number;
  motion: boolean;
};

export const defaultSettings: Settings = {
  theme: "abyss",
  grid: true,
  wireframe: false,
  exaggeration: 1,
  motion: true,
};

type DwState = {
  settings: Settings;
  updateSettings: (patch: Partial<Settings>) => void;
  resetSettings: () => void;
  image: ImageAsset | null;
  setImage: (img: ImageAsset | null) => void;
  stages: Record<PipelineStageId, StageStatus>;
  runPreprocessing: () => void;
  processImageWithBackend: (file: File) => Promise<void>;
  glbFile: File | null;
  setGlbFile: (f: File | null) => void;
  glbUrl: string | null;
  setGlbUrl: (u: string | null) => void;
  heightMetadata: any;
  setHeightMetadata: (m: any) => void;
  demoRequested: boolean;
  setDemoRequested: (v: boolean) => void;
  scene: SceneStats | null;
  setScene: (s: SceneStats | null) => void;
  measurements: Measurement[];
  addMeasurement: (m: Omit<Measurement, "id" | "distanceFromPrev">) => void;
  clearMeasurements: () => void;
  beforeImage: string | null;
  afterImage: string | null;
  setBeforeImage: (u: string | null) => void;
  setAfterImage: (u: string | null) => void;
};

const initialStages: Record<PipelineStageId, StageStatus> = {
  loaded: "pending",
  preprocessing: "pending",
  height: "pending",
  dsm: "pending",
  ready: "pending",
};

const DwContext = createContext<DwState | null>(null);

export function DwProvider({ children }: { children: ReactNode }) {
  const [image, setImageRaw] = useState<ImageAsset | null>(null);
  const [stages, setStages] = useState(initialStages);
  const [glbFile, setGlbFile] = useState<File | null>(null);
  const [glbUrl, setGlbUrl] = useState<string | null>(null);
  const [heightMetadata, setHeightMetadata] = useState<any>(null);
  const [demoRequested, setDemoRequested] = useState(false);
  const [scene, setScene] = useState<SceneStats | null>(null);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [beforeImage, setBeforeImage] = useState<string | null>(null);
  const [afterImage, setAfterImage] = useState<string | null>(null);
  const [settings, setSettings] = useState<Settings>(defaultSettings);

  const updateSettings = useCallback(
    (patch: Partial<Settings>) => setSettings((s) => ({ ...s, ...patch })),
    [],
  );
  const resetSettings = useCallback(() => setSettings(defaultSettings), []);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("theme-abyss", "theme-midnight", "theme-steel");
    root.classList.add(`theme-${settings.theme}`);
    root.classList.toggle("no-motion", !settings.motion);
  }, [settings.theme, settings.motion]);

  const setImage = useCallback((img: ImageAsset | null) => {
    setImageRaw(img);
    setStages(
      img
        ? { ...initialStages, loaded: "complete", preprocessing: "running" }
        : initialStages,
    );
  }, []);

  const runPreprocessing = useCallback(() => {
    setStages((s) => ({
      ...s,
      preprocessing: "complete",
      height: "blocked",
      dsm: "blocked",
      ready: "blocked",
    }));
  }, []);

  const processImageWithBackend = useCallback(async (file: File) => {
    setStages({
      loaded: "complete",
      preprocessing: "running",
      height: "pending",
      dsm: "pending",
      ready: "pending",
    });

    try {
      setStages((s) => ({ ...s, preprocessing: "complete", height: "running" }));

      const formData = new FormData();
      formData.append("file", file);

      // Call Unified Backend: Height Estimation + SegFormer + 2D-to-3D GLB
      const res = await fetch("http://127.0.0.1:8000/process-3d", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Inference server error (${res.status}): ${errText}`);
      }

      const data = await res.json();
      setHeightMetadata(data);

      setStages((s) => ({
        ...s,
        height: "complete",
        dsm: "complete",
      }));

      if (data.glb_url) {
        const sep = data.glb_url.includes("?") ? "&" : "?";
        const fullGlbUrl = `http://127.0.0.1:8000${data.glb_url}${sep}_t=${Date.now()}`;
        setGlbUrl(fullGlbUrl);

        try {
          const glbRes = await fetch(fullGlbUrl);
          const glbBlob = await glbRes.blob();
          const glbFileObj = new File(
            [glbBlob],
            `${file.name.replace(/\.[^/.]+$/, "")}.glb`,
            { type: "model/gltf-binary" },
          );
          setGlbFile(glbFileObj);
          setDemoRequested(false);
        } catch (fetchErr) {
          console.warn("Could not download GLB blob, will load via URL:", fetchErr);
        }
      }

      setStages((s) => ({ ...s, ready: "complete" }));
    } catch (err: any) {
      console.warn("Backend processing note:", err);
      // If backend is unavailable, set height/dsm as blocked
      setStages((s) => ({
        ...s,
        preprocessing: "complete",
        height: "blocked",
        dsm: "blocked",
        ready: "blocked",
      }));
    }
  }, []);

  const addMeasurement = useCallback(
    (m: Omit<Measurement, "id" | "distanceFromPrev">) => {
      setMeasurements((prev) => {
        const last = prev[prev.length - 1];
        const distanceFromPrev = last
          ? Math.sqrt(
              (m.x - last.x) ** 2 + (m.y - last.y) ** 2 + (m.z - last.z) ** 2,
            )
          : null;
        return [...prev, { ...m, id: Date.now() + prev.length, distanceFromPrev }];
      });
    },
    [],
  );

  const clearMeasurements = useCallback(() => setMeasurements([]), []);

  const value = useMemo(
    () => ({
      settings,
      updateSettings,
      resetSettings,
      image,
      setImage,
      stages,
      runPreprocessing,
      processImageWithBackend,
      glbFile,
      setGlbFile,
      glbUrl,
      setGlbUrl,
      heightMetadata,
      setHeightMetadata,
      demoRequested,
      setDemoRequested,
      scene,
      setScene,
      measurements,
      addMeasurement,
      clearMeasurements,
      beforeImage,
      afterImage,
      setBeforeImage,
      setAfterImage,
    }),
    [
      settings,
      updateSettings,
      resetSettings,
      image,
      setImage,
      stages,
      runPreprocessing,
      processImageWithBackend,
      glbFile,
      glbUrl,
      heightMetadata,
      demoRequested,
      scene,
      measurements,
      addMeasurement,
      clearMeasurements,
      beforeImage,
      afterImage,
    ],
  );

  return <DwContext.Provider value={value}>{children}</DwContext.Provider>;
}

export function useDw() {
  const ctx = useContext(DwContext);
  if (!ctx) throw new Error("useDw must be used inside DwProvider");
  return ctx;
}

export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}
