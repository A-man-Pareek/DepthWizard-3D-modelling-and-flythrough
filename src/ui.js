import * as THREE from "three";
import "./style.css";

const enterButton = document.querySelector("#enter-button");
const status = document.querySelector("#status");
const selection = document.querySelector("#selection");
const modeBadge = document.querySelector("#mode-badge");
const hint = document.querySelector("#measurement-hint");
const flythroughControls = document.querySelector("#flythrough-controls");
const measurementControls = document.querySelector("#measurement-controls");
const dimensionToggle = document.querySelector("#dimension-toggle");
const absoluteButton = document.querySelector("#absolute-button");
const relativeButton = document.querySelector("#relative-button");

export function bindLockControls(controls, onLock, onUnlock) {
  enterButton.addEventListener("click", () => controls.lock());
  controls.addEventListener("lock", () => {
    enterButton.textContent = "Flythrough active";
    enterButton.disabled = true;
    enterButton.style.display = "none";
    onLock();
  });
  controls.addEventListener("unlock", () => {
    enterButton.textContent = "Resume Flythrough";
    enterButton.disabled = false;
    enterButton.style.display = "block";
    onUnlock();
  });
}

export function showMode(mode, dimensionView = "relative", absoluteAvailable = false, metadataMode = "relative") {
  const measurement = mode === "measurement";
  const badge = dimensionView === "absolute"
    ? metadataMode === "absolute-geo" ? "ABSOLUTE - GEOREFERENCED" : "ABSOLUTE - ESTIMATED"
    : metadataMode === "relative" ? "RELATIVE ONLY" : "RELATIVE - NO REAL-WORLD SCALE";
  modeBadge.textContent = measurement ? badge : "Mode: FLYTHROUGH";
  modeBadge.classList.toggle("measurement", measurement);
  hint.style.display = measurement ? "block" : "none";
  flythroughControls.style.display = measurement ? "none" : "grid";
  measurementControls.style.display = measurement ? "grid" : "none";
  dimensionToggle.style.display = "none";
  enterButton.textContent = measurement ? "Resume Flythrough" : "Click to enter Flythrough";
  absoluteButton.disabled = !absoluteAvailable;
  absoluteButton.classList.toggle("active", dimensionView === "absolute");
  relativeButton.classList.toggle("active", dimensionView === "relative");
}

export function showLoading(message) {
  status.className = "";
  status.textContent = message;
  status.hidden = false;
}

export function showReady() {
  status.textContent = "Environment ready.";
  status.hidden = false;
}

export function showError(message) {
  status.className = "error";
  status.textContent = message;
  status.hidden = false;
}

export function showSelection(result) {
  if (!result) {
    selection.style.display = "none";
    return;
  }

  const values = result.dimensions;
  selection.innerHTML = `<div class="panel-title">${result.name}</div><strong>Height:</strong> ${values.height.toFixed(2)} ${result.measurementUnit}<br><strong>Width:</strong> ${values.width.toFixed(2)} ${result.measurementUnit}`;
  selection.style.display = "block";
}

export function updateSelectionPosition(result, camera, renderer) {
  if (!result) return;

  const box = result.dimensions.box;
  const anchor = new THREE.Vector3(
    (box.min.x + box.max.x) / 2,
    box.max.y,
    (box.min.z + box.max.z) / 2,
  ).project(camera);
  const bounds = renderer.domElement.getBoundingClientRect();
  const x = bounds.left + (anchor.x + 1) * bounds.width / 2;
  const y = bounds.top + (1 - anchor.y) * bounds.height / 2;
  const margin = 12;
  const clampedX = Math.max(margin, Math.min(window.innerWidth - margin, x));
  const clampedY = Math.max(72, Math.min(window.innerHeight - margin, y));
  selection.style.left = `${clampedX}px`;
  selection.style.top = `${clampedY}px`;
}