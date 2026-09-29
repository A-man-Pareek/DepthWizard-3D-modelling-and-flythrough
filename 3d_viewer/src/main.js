import * as THREE from "three";
import { PointerLockControls } from "three/addons/controls/PointerLockControls.js";
import { createDimensionOverlay } from "./dimensions.js";
import { loadEnvironment, placeCamera } from "./flythrough.js";
import { clearHighlight, configureRaycasting, createSelectedObject, highlightTerrainResult, inspectTerrain, inspectTerrainCandidates, setTeam1Metadata } from "./raycasting.js";
import { bindLockControls, showError, showLoading, showMode, showReady, showSelection, updateSelectionPosition } from "./ui.js";
import { initHazardVisualizer, updateTerrainBounds, setFloodLevel, animateWater, renderHazardOverlay } from "./disaster.js";

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x8db9c1);
scene.fog = new THREE.Fog(0x8db9c1, 150, 900);

const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.05, 2000);
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
document.querySelector("#app").appendChild(renderer.domElement);

scene.add(new THREE.HemisphereLight(0xe4f5ff, 0x4a5543, 1.8));
const sun = new THREE.DirectionalLight(0xfff5e4, 2.2);
sun.position.set(-80, 140, 60);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.near = 1;
sun.shadow.camera.far = 600;
scene.add(sun);
scene.add(new THREE.AmbientLight(0xffffff, 0.65));

// Initialize 3D Hazard Simulation Group
initHazardVisualizer(scene);

const controls = new PointerLockControls(camera, renderer.domElement);
const dimensionOverlay = createDimensionOverlay(scene);
let mode = "flythrough";
let selectedResult = null;
let selectedObject = null;
let dimensionView = "relative";
let cursorPosition = null;

// Parse dynamic model URL and metadata from query parameters
const urlParams = new URLSearchParams(window.location.search);
const modelUrl = urlParams.get("model") || urlParams.get("glb") || "/terrain.glb";
let team1Metadata = null;
const metaParam = urlParams.get("metadata");
if (metaParam) {
  try {
    team1Metadata = JSON.parse(decodeURIComponent(metaParam));
  } catch (e) {
    console.warn("Could not parse metadata param:", e);
  }
}
setTeam1Metadata(team1Metadata);

// Listen for postMessage from parent UI if embedded
window.addEventListener("message", (event) => {
  if (event.data?.type === "SET_METADATA" && event.data.metadata) {
    team1Metadata = event.data.metadata;
    setTeam1Metadata(team1Metadata);
    const isAbs = Boolean(team1Metadata?.units === "meters" || team1Metadata?.mode?.startsWith("absolute"));
    showMode(mode, dimensionView, isAbs, team1Metadata?.mode || "relative");
    if (selectedResult) showDimensions({ ...selectedResult, selected: true });
  }
  if (event.data?.type === "SIMULATE_DISASTER" || event.data?.type === "SET_FLOOD_LEVEL") {
    const level = event.data.level !== undefined ? event.data.level : 35;
    const floodSlider = document.querySelector("#flood-slider");
    const floodValue = document.querySelector("#flood-value");
    if (floodSlider) floodSlider.value = String(level);
    if (floodValue) floodValue.textContent = `${level}%`;
    renderHazardOverlay(event.data.disasterType || "FLOOD", { level, ...event.data });
  }
});

function showDimensions(result) {
  if (!result) {
    selectedObject = null;
    dimensionOverlay.hide();
    showSelection(null);
    return;
  }
  selectedObject = createSelectedObject(result);
  result.view = dimensionView;
  dimensionOverlay.show(result.dimensions, dimensionView);
  showSelection(selectedObject);
  updateSelectionPosition(result, camera, renderer);
}

bindLockControls(
  controls,
  () => {
    mode = "flythrough";
    selectedResult = null;
    selectedObject = null;
    dimensionOverlay.hide();
    clearHighlight();
    showSelection(null);
    showMode(mode);
  },
  () => {
    mode = "measurement";
    keys.clear();
    selectedResult = null;
    selectedObject = null;
    dimensionOverlay.hide();
    clearHighlight();
    showSelection(null);
    const isAbs = Boolean(team1Metadata?.units === "meters" || team1Metadata?.mode?.startsWith("absolute"));
    showMode(mode, dimensionView, isAbs, team1Metadata?.mode || "relative");
  },
);

const keys = new Set();
const clock = new THREE.Clock();
let moveSpeed = 5;
let environment = null;

const speedSlider = document.querySelector("#speed-slider");
const speedValue = document.querySelector("#speed-value");
if (speedSlider) {
  speedSlider.addEventListener("input", () => {
    moveSpeed = Number(speedSlider.value);
    if (speedValue) speedValue.textContent = `${moveSpeed} units/s`;
  });
}

const hazardSelect = document.querySelector("#hazard-select");
const floodSlider = document.querySelector("#flood-slider");
const floodValue = document.querySelector("#flood-value");

function updateHazardSimulation() {
  const selectedType = hazardSelect ? hazardSelect.value : "FLOOD";
  const val = floodSlider ? Number(floodSlider.value) : 0;
  if (floodValue) floodValue.textContent = `${val}%`;
  renderHazardOverlay(selectedType, { level: val, magnitude: 6.2, slope: 28 });
}

if (hazardSelect) hazardSelect.addEventListener("change", updateHazardSimulation);
if (floodSlider) floodSlider.addEventListener("input", updateHazardSimulation);

window.addEventListener("keydown", (event) => keys.add(event.code));
window.addEventListener("keyup", (event) => keys.delete(event.code));
window.addEventListener("blur", () => keys.clear());

renderer.domElement.addEventListener("pointermove", (event) => {
  if (mode !== "measurement") return;
  cursorPosition = { x: event.clientX, y: event.clientY };
  const result = inspectTerrain(event.clientX, event.clientY);
  if (!result) {
    selectedResult = null;
    showDimensions(null);
    return;
  }
  selectedResult = result;
  result.selected = true;
  showDimensions(result);
});

renderer.domElement.addEventListener("pointerdown", (event) => {
  if (mode !== "measurement") return;
  cursorPosition = { x: event.clientX, y: event.clientY };
  const result = inspectTerrain(event.clientX, event.clientY);
  selectedResult = result;
  if (result) result.selected = true;
  showDimensions(result);
});

window.addEventListener("keydown", (event) => {
  if (mode !== "measurement" || !cursorPosition) return;
  if (event.code !== "ArrowLeft" && event.code !== "ArrowRight") return;

  const candidates = inspectTerrainCandidates(cursorPosition.x, cursorPosition.y);
  if (candidates.length === 0) {
    selectedResult = null;
    clearHighlight();
    showDimensions(null);
    return;
  }

  const currentIndex = candidates.findIndex((candidate) => candidate.mesh === selectedResult?.mesh);
  const direction = event.code === "ArrowRight" ? 1 : -1;
  const nextIndex = currentIndex < 0
    ? 0
    : (currentIndex + direction + candidates.length) % candidates.length;
  selectedResult = candidates[nextIndex];
  selectedResult.selected = true;
  highlightTerrainResult(selectedResult);
  showDimensions(selectedResult);
  event.preventDefault();
});

document.querySelector("#relative-button").addEventListener("click", () => {
  dimensionView = "relative";
  const isAbs = Boolean(team1Metadata?.units === "meters" || team1Metadata?.mode?.startsWith("absolute"));
  showMode(mode, dimensionView, isAbs, "relative");
  if (selectedResult) showDimensions({ ...selectedResult, selected: true });
});

document.querySelector("#absolute-button").addEventListener("click", () => {
  if (!team1Metadata || (team1Metadata.units !== "meters" && !team1Metadata.mode?.startsWith("absolute"))) return;
  dimensionView = "absolute";
  showMode(mode, dimensionView, true, team1Metadata.mode || "absolute");
  if (selectedResult) showDimensions({ ...selectedResult, selected: true });
});

const downloadBtn = document.querySelector("#download-glb-button");
if (downloadBtn) {
  downloadBtn.addEventListener("click", () => {
    const candidate = modelUrl || "/terrain.glb";
    const downloadName = candidate.split("/").pop().split("?")[0] || "depthwizard_model.glb";
    const link = document.createElement("a");
    link.href = candidate;
    link.download = downloadName;
    link.target = "_blank";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });
}

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

function updateMovement(delta) {
  if (!controls.isLocked) return;
  const forward = keys.has("KeyW") || keys.has("ArrowUp");
  const backward = keys.has("KeyS") || keys.has("ArrowDown");
  const left = keys.has("KeyA") || keys.has("ArrowLeft");
  const right = keys.has("KeyD") || keys.has("ArrowRight");
  const vertical = Number(keys.has("Space")) - Number(keys.has("ShiftLeft") || keys.has("ShiftRight"));
  const distance = moveSpeed * delta;
  if (forward) controls.moveForward(distance);
  if (backward) controls.moveForward(-distance);
  if (left) controls.moveRight(-distance);
  if (right) controls.moveRight(distance);
  camera.position.y += vertical * distance;
}

async function start() {
  showLoading("Loading environment... 0%");
  let loaded = false;
  const candidates = [
    modelUrl,
    "http://127.0.0.1:8000/download/imgg_height_model.glb",
    "http://127.0.0.1:8000/download/imgg_fresh.glb",
    "/terrain.glb",
    "http://127.0.0.1:8000/download/depthwizard_final.glb"
  ];
  const tryUrls = [...new Set(candidates.filter(Boolean))];

  for (const rawUrl of tryUrls) {
    const cacheBustUrl = rawUrl + (rawUrl.includes("?") ? "&" : "?") + `_t=${Date.now()}`;
    try {
      showLoading(`Loading model from ${rawUrl}... 0%`);
      const result = await loadEnvironment(
        scene,
        (percent) => showLoading(`Loading model... ${percent}%`),
        cacheBustUrl
      );
      environment = result.environment;
      updateTerrainBounds(result.bounds);
      configureRaycasting(camera, environment, renderer.domElement);
      placeCamera(camera, result.bounds, result.size);
      showReady();
      loaded = true;

      // Check initial flood or disaster parameters in query string
      const initialDisaster = urlParams.get("disaster") || "FLOOD";
      const initialLevel = urlParams.get("level") || urlParams.get("flood");
      if (initialLevel !== null) {
        const lvl = Number(initialLevel);
        const fSlider = document.querySelector("#flood-slider");
        const fValue = document.querySelector("#flood-value");
        if (fSlider) fSlider.value = String(lvl);
        if (fValue) fValue.textContent = `${lvl}%`;
        renderHazardOverlay(initialDisaster, { level: lvl });
      }
      break;
    } catch (err) {
      console.warn(`Failed loading model from ${rawUrl}:`, err);
    }
  }

  if (!loaded) {
    showError(`Could not load GLB model. Ensure backend or public folder has terrain.glb.`);
    return;
  }

  // Attempt to fetch /metadata.json if not already passed
  if (!team1Metadata) {
    try {
      const resp = await fetch("/metadata.json");
      if (resp.ok) {
        team1Metadata = await resp.json();
        setTeam1Metadata(team1Metadata);
      }
    } catch (e) {
      console.warn("No local metadata.json found:", e);
    }
  }

  const isAbsoluteAvail = Boolean(
    team1Metadata && (team1Metadata.units === "meters" || team1Metadata.mode?.startsWith("absolute"))
  );
  showMode(mode, dimensionView, isAbsoluteAvail, team1Metadata?.mode || "relative");
}

function animate() {
  requestAnimationFrame(animate);
  const delta = Math.min(clock.getDelta(), 0.1);
  updateMovement(delta);
  animateWater(clock.getElapsedTime(), delta);
  if (selectedResult) updateSelectionPosition(selectedResult, camera, renderer);
  renderer.render(scene, camera);
}

start();
animate();
