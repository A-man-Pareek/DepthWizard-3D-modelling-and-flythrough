import * as THREE from "three";
import { PointerLockControls } from "three/addons/controls/PointerLockControls.js";
import { createDimensionOverlay } from "./dimensions.js";
import { loadEnvironment, placeCamera } from "./flythrough.js";
import { clearHighlight, configureRaycasting, createSelectedObject, highlightTerrainResult, inspectTerrain, inspectTerrainCandidates, setTeam1Metadata } from "./raycasting.js";
import { bindLockControls, showError, showLoading, showMode, showReady, showSelection, updateSelectionPosition } from "./ui.js";

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x8db9c1);
scene.fog = new THREE.Fog(0x8db9c1, 150, 900);

const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.05, 2000);
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
document.querySelector("#app").appendChild(renderer.domElement);

scene.add(new THREE.HemisphereLight(0xe4f5ff, 0x4a5543, 2.2));
const sun = new THREE.DirectionalLight(0xfff3d6, 2.4);
sun.position.set(-80, 140, 60);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.near = 1;
sun.shadow.camera.far = 500;
scene.add(sun);

const controls = new PointerLockControls(camera, renderer.domElement);
const dimensionOverlay = createDimensionOverlay(scene);
let mode = "flythrough";
let selectedResult = null;
let selectedObject = null;
let dimensionView = "relative";
let cursorPosition = null;
// Team 1 can provide this object later. metersPerUnit is required for real-world dimensions.
const team1Metadata = null;
setTeam1Metadata(team1Metadata);

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
    showMode(mode);
  },
);
const keys = new Set();
const clock = new THREE.Clock();
let moveSpeed = 5;
let environment = null;

const speedSlider = document.querySelector("#speed-slider");
const speedValue = document.querySelector("#speed-value");
speedSlider.addEventListener("input", () => {
  moveSpeed = Number(speedSlider.value);
  speedValue.textContent = `${moveSpeed} units/s`;
});

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
  showMode(mode, dimensionView, false, "relative");
  if (selectedResult) showDimensions({ ...selectedResult, selected: true });
});

document.querySelector("#absolute-button").addEventListener("click", () => {
  if (!team1Metadata || team1Metadata.units !== "meters" || !team1Metadata.metersPerUnit) return;
  dimensionView = "absolute";
  showMode(mode, dimensionView, true, team1Metadata.mode);
  if (selectedResult) showDimensions({ ...selectedResult, selected: true });
});

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
  try {
    const result = await loadEnvironment(scene, (percent) => showLoading(`Loading environment... ${percent}%`));
    environment = result.environment;
    configureRaycasting(camera, environment, renderer.domElement);
    placeCamera(camera, result.bounds, result.size);
    showReady();
    showMode(mode, dimensionView, false, "relative");
  } catch (error) {
    console.error("DepthWizard could not load /street.glb:", error);
    showError("Could not load street.glb. Add it to public/ and reload.");
  }
}

function animate() {
  requestAnimationFrame(animate);
  updateMovement(Math.min(clock.getDelta(), 0.1));
  if (selectedResult) updateSelectionPosition(selectedResult, camera, renderer);
  renderer.render(scene, camera);
}

start();
animate();