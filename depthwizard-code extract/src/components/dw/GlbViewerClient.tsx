import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  Box,
  Crosshair,
  Eye,
  Gauge,
  Grid3x3,
  Layers,
  Maximize2,
  Mountain,
  Move3d,
  RotateCcw,
  Sun,
  Trash2,
} from "lucide-react";
import { useDw } from "@/lib/dw-state";
import { HudButton, StatusBadge } from "./primitives";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const COL_TERRAIN_LOW = 0x0e2a3a;
const COL_TERRAIN_MID = 0x1c7293;
const COL_TERRAIN_HIGH = 0x9be7ff;
const COL_MARKER = 0x5ee9ff;

type Flight = "orbit" | "fp";

export default function GlbViewerClient({
  file,
  demo,
  className,
}: {
  file: File | null;
  demo: boolean;
  className?: string;
}) {
  const { setScene, addMeasurement, measurements, clearMeasurements, settings } = useDw();
  const mountRef = useRef<HTMLDivElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  const [flight, setFlight] = useState<Flight>("orbit");
  const [wireframe, setWireframe] = useState(settings.wireframe);
  const [grid, setGrid] = useState(settings.grid);
  const [shadows, setShadows] = useState(true);
  const [lighting, setLighting] = useState(true);
  const [texture, setTexture] = useState(true);
  const [exaggeration, setExaggeration] = useState(settings.exaggeration);
  const [speed, setSpeed] = useState(22);
  const [hud, setHud] = useState({ alt: 0, heading: 0, pitch: 0, fps: 0 });
  const [progress, setProgress] = useState<number | null>(null);
  const [empty, setEmpty] = useState(true);

  // mutable engine refs
  const api = useRef<{
    renderer?: THREE.WebGLRenderer;
    scene?: THREE.Scene;
    camera?: THREE.PerspectiveCamera;
    orbit?: OrbitControls;
    modelGroup?: THREE.Group;
    markerGroup?: THREE.Group;
    gridHelper?: THREE.GridHelper;
    dirLight?: THREE.DirectionalLight;
    hemiLight?: THREE.HemisphereLight;
    meshes: THREE.Mesh[];
    keys: Set<string>;
    flight: Flight;
    speed: number;
    yaw: number;
    pitch: number;
    dragging: boolean;
    radius: number;
  }>({ meshes: [], keys: new Set(), flight: "orbit", speed: 22, yaw: 0, pitch: 0, dragging: false, radius: 60 });

  /* ---------------- engine bootstrap ---------------- */
  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a1016);
    scene.fog = new THREE.Fog(0x0a1016, 180, 460);

    const camera = new THREE.PerspectiveCamera(
      55,
      mount.clientWidth / Math.max(mount.clientHeight, 1),
      0.1,
      3000,
    );
    camera.position.set(70, 55, 90);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mount.appendChild(renderer.domElement);

    const hemi = new THREE.HemisphereLight(0x9fd8ff, 0x0a1016, 0.55);
    scene.add(hemi);
    const dir = new THREE.DirectionalLight(0xdff4ff, 1.5);
    dir.position.set(90, 130, 60);
    dir.castShadow = true;
    dir.shadow.mapSize.set(2048, 2048);
    dir.shadow.camera.near = 1;
    dir.shadow.camera.far = 600;
    (dir.shadow.camera as THREE.OrthographicCamera).left = -160;
    (dir.shadow.camera as THREE.OrthographicCamera).right = 160;
    (dir.shadow.camera as THREE.OrthographicCamera).top = 160;
    (dir.shadow.camera as THREE.OrthographicCamera).bottom = -160;
    scene.add(dir);
    scene.add(new THREE.AmbientLight(0x22405a, 0.6));

    const gridHelper = new THREE.GridHelper(400, 80, 0x1c7293, 0x11212c);
    (gridHelper.material as THREE.Material).opacity = 0.5;
    (gridHelper.material as THREE.Material).transparent = true;
    gridHelper.position.y = -0.02;
    scene.add(gridHelper);

    const modelGroup = new THREE.Group();
    scene.add(modelGroup);
    const markerGroup = new THREE.Group();
    scene.add(markerGroup);

    const orbit = new OrbitControls(camera, renderer.domElement);
    orbit.enableDamping = true;
    orbit.dampingFactor = 0.08;
    orbit.maxPolarAngle = Math.PI * 0.495;
    orbit.target.set(0, 6, 0);

    Object.assign(api.current, {
      renderer,
      scene,
      camera,
      orbit,
      modelGroup,
      markerGroup,
      gridHelper,
      dirLight: dir,
      hemiLight: hemi,
    });

    const onResize = () => {
      if (!mount.clientWidth) return;
      camera.aspect = mount.clientWidth / Math.max(mount.clientHeight, 1);
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    };
    window.addEventListener("resize", onResize);
    const ro = new ResizeObserver(onResize);
    ro.observe(mount);

    const onKeyDown = (e: KeyboardEvent) => {
      api.current.keys.add(e.code);
      if (e.code === "Escape" && api.current.flight === "fp") setFlight("orbit");
      if (["Space", "ShiftLeft"].includes(e.code) && api.current.flight === "fp") e.preventDefault();
    };
    const onKeyUp = (e: KeyboardEvent) => api.current.keys.delete(e.code);
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);

    const onMouseMove = (e: MouseEvent) => {
      if (api.current.flight !== "fp" || document.pointerLockElement !== renderer.domElement) return;
      api.current.yaw -= e.movementX * 0.0022;
      api.current.pitch = THREE.MathUtils.clamp(
        api.current.pitch - e.movementY * 0.0022,
        -Math.PI / 2.2,
        Math.PI / 2.2,
      );
    };
    document.addEventListener("mousemove", onMouseMove);

    const clock = new THREE.Clock();
    let raf = 0;
    let frames = 0;
    let acc = 0;

    const tick = () => {
      raf = requestAnimationFrame(tick);
      const dt = Math.min(clock.getDelta(), 0.1);
      const s = api.current;

      if (s.flight === "fp") {
        const dirVec = new THREE.Vector3();
        const forward = new THREE.Vector3(
          Math.sin(s.yaw) * Math.cos(s.pitch),
          Math.sin(s.pitch),
          Math.cos(s.yaw) * Math.cos(s.pitch),
        ).negate();
        const right = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), forward).negate();
        if (s.keys.has("KeyW")) dirVec.add(forward);
        if (s.keys.has("KeyS")) dirVec.sub(forward);
        if (s.keys.has("KeyD")) dirVec.add(right);
        if (s.keys.has("KeyA")) dirVec.sub(right);
        if (s.keys.has("Space")) dirVec.y += 1;
        if (s.keys.has("ShiftLeft") || s.keys.has("ShiftRight")) dirVec.y -= 1;
        if (dirVec.lengthSq() > 0) {
          dirVec.normalize().multiplyScalar(s.speed * dt);
          camera.position.add(dirVec);
        }
        camera.lookAt(camera.position.clone().add(forward));
      } else {
        orbit.update();
      }

      frames++;
      acc += dt;
      if (acc > 0.25) {
        const e = new THREE.Euler().setFromQuaternion(camera.quaternion, "YXZ");
        setHud({
          alt: camera.position.y,
          heading: (THREE.MathUtils.radToDeg(-e.y) + 360) % 360,
          pitch: THREE.MathUtils.radToDeg(e.x),
          fps: Math.round(frames / acc),
        });
        frames = 0;
        acc = 0;
      }

      markerGroup.children.forEach((m, i) => {
        m.rotation.y += dt * 1.2;
        const pulse = 1 + Math.sin(clock.elapsedTime * 3 + i) * 0.12;
        m.scale.setScalar(pulse);
      });

      renderer.render(scene, camera);
    };
    tick();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      document.removeEventListener("mousemove", onMouseMove);
      ro.disconnect();
      orbit.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) mount.removeChild(renderer.domElement);
    };
  }, []);

  /* ---------------- model loading ---------------- */
  useEffect(() => {
    const s = api.current;
    if (!s.scene || !s.modelGroup) return;
    if (!file && !demo) return;

    const clearModel = () => {
      s.modelGroup!.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.isMesh) {
          m.geometry.dispose();
          const mat = m.material as THREE.Material | THREE.Material[];
          if (Array.isArray(mat)) mat.forEach((x) => x.dispose());
          else mat.dispose();
        }
      });
      s.modelGroup!.clear();
      s.meshes = [];
      clearMeasurements();
      s.markerGroup?.clear();
    };

    const finalize = (label: string, source: "demo" | "upload") => {
      const meshes: THREE.Mesh[] = [];
      s.modelGroup!.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.isMesh) {
          m.castShadow = true;
          m.receiveShadow = true;
          meshes.push(m);
        }
      });
      s.meshes = meshes;

      // fit to a ~100 unit footprint
      const box = new THREE.Box3().setFromObject(s.modelGroup!);
      const size = box.getSize(new THREE.Vector3());
      const maxDim = Math.max(size.x, size.z, size.y) || 1;
      const scale = 100 / maxDim;
      s.modelGroup!.scale.setScalar(scale);
      const box2 = new THREE.Box3().setFromObject(s.modelGroup!);
      const center = box2.getCenter(new THREE.Vector3());
      s.modelGroup!.position.x -= center.x;
      s.modelGroup!.position.z -= center.z;
      s.modelGroup!.position.y -= box2.min.y;

      let vertices = 0;
      let triangles = 0;
      let textured = false;
      let minY = Infinity;
      let maxY = -Infinity;
      let sumY = 0;
      let count = 0;

      s.modelGroup!.updateMatrixWorld(true);
      meshes.forEach((m) => {
        const pos = m.geometry.getAttribute("position");
        vertices += pos.count;
        triangles += m.geometry.index ? m.geometry.index.count / 3 : pos.count / 3;
        const mat = m.material as THREE.MeshStandardMaterial;
        if (mat && "map" in mat && mat.map) textured = true;
        const v = new THREE.Vector3();
        const step = Math.max(1, Math.floor(pos.count / 40000));
        for (let i = 0; i < pos.count; i += step) {
          v.fromBufferAttribute(pos, i).applyMatrix4(m.matrixWorld);
          minY = Math.min(minY, v.y);
          maxY = Math.max(maxY, v.y);
          sumY += v.y;
          count++;
        }
      });

      const radius = Math.max(new THREE.Box3().setFromObject(s.modelGroup!).getSize(new THREE.Vector3()).length(), 40);
      s.radius = radius;
      resetCamera();

      setScene({
        label,
        source,
        vertices,
        triangles: Math.round(triangles),
        textured,
        minY: count ? minY : 0,
        maxY: count ? maxY : 0,
        meanY: count ? sumY / count : 0,
      });
      setEmpty(false);
      applyVisuals();
    };

    if (file) {
      clearModel();
      setProgress(0);
      const url = URL.createObjectURL(file);
      const loader = new GLTFLoader();
      loader.load(
        url,
        (gltf) => {
          s.modelGroup!.add(gltf.scene);
          setProgress(null);
          URL.revokeObjectURL(url);
          finalize(file.name, "upload");
          toast.success("GLB LOADED", { description: file.name });
        },
        (evt) => {
          if (evt.total) setProgress(Math.round((evt.loaded / evt.total) * 100));
        },
        (err) => {
          console.error(err);
          setProgress(null);
          URL.revokeObjectURL(url);
          toast.error("GLB LOAD FAILED", { description: "File could not be parsed as GLB/glTF." });
        },
      );
      return;
    }

    // Procedural demo terrain — explicitly labelled as synthetic reference geometry.
    clearModel();
    const seg = 190;
    const geo = new THREE.PlaneGeometry(120, 120, seg, seg);
    geo.rotateX(-Math.PI / 2);
    const pos = geo.getAttribute("position") as THREE.BufferAttribute;
    const colors = new Float32Array(pos.count * 3);
    const noise = (x: number, z: number) =>
      Math.sin(x * 0.06) * Math.cos(z * 0.05) * 9 +
      Math.sin(x * 0.14 + z * 0.09) * 4.5 +
      Math.cos(x * 0.31 - z * 0.22) * 1.6 +
      Math.sin((x + z) * 0.02) * 6;
    let lo = Infinity;
    let hi = -Infinity;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      const h = noise(x, z) + 10;
      pos.setY(i, h);
      lo = Math.min(lo, h);
      hi = Math.max(hi, h);
    }
    const cLow = new THREE.Color(COL_TERRAIN_LOW);
    const cMid = new THREE.Color(COL_TERRAIN_MID);
    const cHigh = new THREE.Color(COL_TERRAIN_HIGH);
    for (let i = 0; i < pos.count; i++) {
      const t = (pos.getY(i) - lo) / Math.max(hi - lo, 0.0001);
      const c = t < 0.5 ? cLow.clone().lerp(cMid, t * 2) : cMid.clone().lerp(cHigh, (t - 0.5) * 2);
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    geo.computeVertexNormals();
    const mat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.85,
      metalness: 0.08,
    });
    const mesh = new THREE.Mesh(geo, mat);
    s.modelGroup.add(mesh);
    finalize("DEMO TERRAIN (PROCEDURAL)", "demo");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file, demo]);

  /* ---------------- visual toggles ---------------- */
  const applyVisuals = () => {
    const s = api.current;
    s.meshes.forEach((m) => {
      const mats = Array.isArray(m.material) ? m.material : [m.material];
      mats.forEach((mm) => {
        const mat = mm as THREE.MeshStandardMaterial & { userData: { origMap?: THREE.Texture | null } };
        mat.wireframe = wireframe;
        if (mat.map !== undefined) {
          if (mat.userData.origMap === undefined) mat.userData.origMap = mat.map ?? null;
          mat.map = texture ? (mat.userData.origMap ?? null) : null;
        }
        mat.needsUpdate = true;
      });
      m.castShadow = shadows;
      m.receiveShadow = shadows;
    });
    if (s.gridHelper) s.gridHelper.visible = grid;
    if (s.renderer) s.renderer.shadowMap.enabled = shadows;
    if (s.dirLight) s.dirLight.intensity = lighting ? 1.5 : 0.15;
    if (s.hemiLight) s.hemiLight.intensity = lighting ? 0.55 : 0.9;
    if (s.modelGroup) s.modelGroup.scale.y = s.modelGroup.scale.x * exaggeration;
  };

  useEffect(applyVisuals, [wireframe, grid, shadows, lighting, texture, exaggeration]);

  // Global console settings drive the viewer defaults.
  useEffect(() => {
    setWireframe(settings.wireframe);
    setGrid(settings.grid);
    setExaggeration(settings.exaggeration);
  }, [settings.wireframe, settings.grid, settings.exaggeration]);

  useEffect(() => {
    api.current.flight = flight;
    api.current.speed = speed;
    const s = api.current;
    if (!s.orbit || !s.renderer) return;
    if (flight === "fp") {
      s.orbit.enabled = false;
      const e = new THREE.Euler().setFromQuaternion(s.camera!.quaternion, "YXZ");
      s.yaw = e.y + Math.PI;
      s.pitch = e.x;
      s.renderer.domElement.requestPointerLock?.();
    } else {
      s.orbit.enabled = true;
      if (document.pointerLockElement) document.exitPointerLock();
    }
  }, [flight, speed]);

  useEffect(() => {
    if (measurements.length === 0) api.current.markerGroup?.clear();
  }, [measurements.length]);

  const resetCamera = () => {
    const s = api.current;
    if (!s.camera || !s.orbit) return;
    const d = s.radius * 0.85;
    s.camera.position.set(d * 0.7, d * 0.55, d * 0.9);
    s.orbit.target.set(0, s.radius * 0.08, 0);
    s.orbit.update();
  };

  /* ---------------- raycast measurement ---------------- */
  const onCanvasClick = (e: React.MouseEvent) => {
    const s = api.current;
    if (!s.camera || !s.renderer || s.meshes.length === 0 || flight === "fp") return;
    const rect = s.renderer.domElement.getBoundingClientRect();
    const ndc = new THREE.Vector2(
      ((e.clientX - rect.left) / rect.width) * 2 - 1,
      -((e.clientY - rect.top) / rect.height) * 2 + 1,
    );
    const ray = new THREE.Raycaster();
    ray.setFromCamera(ndc, s.camera);
    const hits = ray.intersectObjects(s.meshes, true);
    if (!hits.length) return;
    const p = hits[0]!.point;

    const marker = new THREE.Group();
    const core = new THREE.Mesh(
      new THREE.SphereGeometry(s.radius * 0.006, 16, 16),
      new THREE.MeshBasicMaterial({ color: COL_MARKER }),
    );
    const halo = new THREE.Mesh(
      new THREE.RingGeometry(s.radius * 0.012, s.radius * 0.017, 32),
      new THREE.MeshBasicMaterial({
        color: COL_MARKER,
        transparent: true,
        opacity: 0.55,
        side: THREE.DoubleSide,
      }),
    );
    halo.rotation.x = -Math.PI / 2;
    const beam = new THREE.Mesh(
      new THREE.CylinderGeometry(s.radius * 0.0012, s.radius * 0.0012, s.radius * 0.08, 8),
      new THREE.MeshBasicMaterial({ color: COL_MARKER, transparent: true, opacity: 0.5 }),
    );
    beam.position.y = s.radius * 0.04;
    marker.add(core, halo, beam);
    marker.position.copy(p);
    s.markerGroup?.add(marker);

    // Undo the visual height exaggeration so the reported elevation stays true to the mesh.
    const yScale = Math.max(s.modelGroup?.scale.y ?? 1, 0.0001);
    addMeasurement({ x: p.x, y: p.y, z: p.z, elevation: p.y / yScale });
  };

  const toggleFullscreen = () => {
    const el = wrapRef.current;
    if (!el) return;
    if (document.fullscreenElement) document.exitFullscreen();
    else el.requestFullscreen?.();
  };

  const Toggle = ({
    on,
    onClick,
    icon: Icon,
    label,
  }: {
    on: boolean;
    onClick: () => void;
    icon: typeof Grid3x3;
    label: string;
  }) => (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 rounded-sm border px-2.5 py-1.5 font-mono text-[10px] tracking-[0.12em] uppercase transition-colors",
        on
          ? "border-primary/50 bg-primary/12 text-primary"
          : "border-border bg-surface/60 text-muted-foreground hover:text-foreground",
      )}
    >
      <Icon className="size-3" />
      {label}
    </button>
  );

  return (
    <div ref={wrapRef} className={cn("relative overflow-hidden rounded-lg border border-border bg-background", className)}>
      <div ref={mountRef} onClick={onCanvasClick} className="size-full [&>canvas]:block [&>canvas]:size-full" />

      {/* top-left readouts */}
      <div className="pointer-events-none absolute top-3 left-3 flex flex-col gap-2">
        <div className="hud-panel px-3 py-2 font-mono text-[10px] tracking-[0.12em] text-muted-foreground">
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            <span>
              MODE <span className="text-primary">{flight === "fp" ? "FLIGHT" : "ORBIT"}</span>
            </span>
            <span>
              SPD <span className="text-primary">{speed}</span>
            </span>
            <span>
              ALT <span className="text-primary">{hud.alt.toFixed(1)}</span>
            </span>
            <span>
              HDG <span className="text-primary">{hud.heading.toFixed(0)}°</span>
            </span>
            <span>
              PIT <span className="text-primary">{hud.pitch.toFixed(0)}°</span>
            </span>
            <span>
              FPS <span className="text-primary">{hud.fps}</span>
            </span>
          </div>
        </div>
        {flight === "fp" && (
          <div className="hud-panel px-3 py-2 font-mono text-[10px] leading-relaxed tracking-[0.12em] text-muted-foreground">
            <p>WASD — MOVE</p>
            <p>SPACE — ASCEND</p>
            <p>SHIFT — DESCEND</p>
            <p>MOUSE — LOOK</p>
            <p className="text-warning">ESC — EXIT FLYTHROUGH</p>
          </div>
        )}
      </div>

      {/* crosshair */}
      {flight === "fp" && (
        <Crosshair className="pointer-events-none absolute top-1/2 left-1/2 size-5 -translate-x-1/2 -translate-y-1/2 text-primary/70" />
      )}

      {/* loading */}
      {progress !== null && (
        <div className="absolute inset-0 grid place-items-center bg-background/80 backdrop-blur-sm">
          <div className="w-64 text-center">
            <p className="label-mono">LOADING GLB · {progress}%</p>
            <div className="mt-3 h-1 overflow-hidden rounded-full bg-surface-2">
              <div
                className="h-full bg-primary transition-all duration-200"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* empty state */}
      {empty && progress === null && (
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <div className="hud-panel pointer-events-auto max-w-sm p-6 text-center">
            <Mountain className="mx-auto size-6 text-primary" />
            <p className="mt-3 font-display text-sm tracking-[0.14em]">NO SCENE LOADED</p>
            <p className="mt-2 text-xs text-muted-foreground">
              Upload a .glb / .gltf model or load the procedural demo terrain to begin.
            </p>
          </div>
        </div>
      )}

      {/* control dock */}
      <div className="absolute inset-x-3 bottom-3 flex flex-wrap items-end gap-2">
        <div className="hud-panel flex flex-wrap items-center gap-2 p-2.5">
          <div className="flex rounded-sm border border-border p-0.5">
            {(["orbit", "fp"] as Flight[]).map((f) => (
              <button
                key={f}
                onClick={() => setFlight(f)}
                className={cn(
                  "rounded-sm px-2.5 py-1 font-mono text-[10px] tracking-[0.12em] uppercase transition-colors",
                  flight === f ? "bg-primary text-primary-foreground" : "text-muted-foreground",
                )}
              >
                {f === "orbit" ? "Orbit" : "First Person"}
              </button>
            ))}
          </div>
          <Toggle on={grid} onClick={() => setGrid((v) => !v)} icon={Grid3x3} label="Grid" />
          <Toggle on={wireframe} onClick={() => setWireframe((v) => !v)} icon={Box} label="Wire" />
          <Toggle on={lighting} onClick={() => setLighting((v) => !v)} icon={Sun} label="Light" />
          <Toggle on={shadows} onClick={() => setShadows((v) => !v)} icon={Layers} label="Shadow" />
          <Toggle on={texture} onClick={() => setTexture((v) => !v)} icon={Eye} label="Texture" />
          <HudButton variant="outline" onClick={resetCamera} className="px-2.5 py-1.5">
            <RotateCcw className="size-3" /> Reset
          </HudButton>
          <HudButton variant="outline" onClick={toggleFullscreen} className="px-2.5 py-1.5">
            <Maximize2 className="size-3" /> Full
          </HudButton>
          {measurements.length > 0 && (
            <HudButton variant="danger" onClick={clearMeasurements} className="px-2.5 py-1.5">
              <Trash2 className="size-3" /> Clear ({measurements.length})
            </HudButton>
          )}
        </div>

        <div className="hud-panel flex min-w-[220px] flex-col gap-2 p-3">
          <label className="flex items-center justify-between gap-3">
            <span className="label-mono flex items-center gap-1.5">
              <Move3d className="size-3" /> Height Exag.
            </span>
            <span className="font-mono text-[10px] text-primary">{exaggeration.toFixed(1)}×</span>
          </label>
          <input
            type="range"
            min={0.2}
            max={4}
            step={0.1}
            value={exaggeration}
            onChange={(e) => setExaggeration(Number(e.target.value))}
            className="h-1 w-full cursor-pointer appearance-none rounded-full bg-surface-2 accent-primary"
          />
          <label className="flex items-center justify-between gap-3">
            <span className="label-mono flex items-center gap-1.5">
              <Gauge className="size-3" /> Flight Speed
            </span>
            <span className="font-mono text-[10px] text-primary">{speed}</span>
          </label>
          <input
            type="range"
            min={4}
            max={90}
            step={1}
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
            className="h-1 w-full cursor-pointer appearance-none rounded-full bg-surface-2 accent-primary"
          />
        </div>

        <div className="ml-auto hidden sm:block">
          <StatusBadge kind="active" label="WEBGL RENDERER ACTIVE" />
        </div>
      </div>
    </div>
  );
}
