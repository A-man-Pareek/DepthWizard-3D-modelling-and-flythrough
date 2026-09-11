import * as THREE from "three";
import { calculateDimensions } from "./dimensions.js";

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let camera = null;
let environment = null;
let canvas = null;
let highlightedMesh = null;
let originalMaterials = null;
let team1Metadata = null;
let nextObjectId = 1;
const objectIds = new WeakMap();

export function configureRaycasting(nextCamera, nextEnvironment, nextCanvas) {
  camera = nextCamera;
  environment = nextEnvironment;
  canvas = nextCanvas;
}

export function setTeam1Metadata(metadata) {
  team1Metadata = metadata;
}

function setHighlight(mesh) {
  if (highlightedMesh === mesh) return;
  clearHighlight();
  highlightedMesh = mesh;
  originalMaterials = mesh.material;
  const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  mesh.material = materials.map((material) => {
    const highlighted = material.clone();
    if ("emissive" in highlighted) highlighted.emissive.set(0xf7d27d);
    if ("emissiveIntensity" in highlighted) highlighted.emissiveIntensity = 0.65;
    return highlighted;
  });
  if (!Array.isArray(originalMaterials)) mesh.material = mesh.material[0];
}

export function clearHighlight() {
  if (!highlightedMesh) return;
  highlightedMesh.material = originalMaterials;
  highlightedMesh = null;
  originalMaterials = null;
}

function raycast(screenX, screenY) {
  if (!camera || !environment || !canvas) return null;

  const bounds = canvas.getBoundingClientRect();
  pointer.x = ((screenX - bounds.left) / bounds.width) * 2 - 1;
  pointer.y = -((screenY - bounds.top) / bounds.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);

  const intersections = raycaster.intersectObject(environment, true);
  if (intersections.length === 0) return null;

  const hit = intersections[0];
  if (!hit.object.isMesh) return null;
  setHighlight(hit.object);
  const worldPosition = hit.point.clone();
  const dimensions = calculateDimensions(hit.object, team1Metadata);
  return {
    mesh: hit.object,
    objectName: hit.object.name || "",
    worldPosition,
    position: dimensions.center,
    width: dimensions.size.x,
    height: dimensions.size.y,
    depth: dimensions.size.z,
    dimensions,
    height_value: null,
    units: null,
    height_lookup_connected: false,
  };
}

function raycastMeshes(screenX, screenY) {
  if (!camera || !environment || !canvas) return [];

  const bounds = canvas.getBoundingClientRect();
  pointer.x = ((screenX - bounds.left) / bounds.width) * 2 - 1;
  pointer.y = -((screenY - bounds.top) / bounds.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);

  const seen = new Set();
  return raycaster
    .intersectObject(environment, true)
    .filter((intersection) => intersection.object.isMesh)
    .filter((intersection) => {
      if (seen.has(intersection.object)) return false;
      seen.add(intersection.object);
      return true;
    })
    .map((intersection) => {
      const dimensions = calculateDimensions(intersection.object, team1Metadata);
      return {
        mesh: intersection.object,
        objectName: intersection.object.name || "",
        worldPosition: intersection.point.clone(),
        position: dimensions.center,
        width: dimensions.size.x,
        height: dimensions.size.y,
        depth: dimensions.size.z,
        dimensions,
        height_value: null,
        units: null,
        height_lookup_connected: false,
      };
    });
}

export function inspectTerrain(screenX, screenY, preserveHighlight = false) {
  const result = raycast(screenX, screenY);
  if (!result && !preserveHighlight) clearHighlight();
  return result;
}

export function inspectTerrainCandidates(screenX, screenY) {
  return raycastMeshes(screenX, screenY);
}

export function highlightTerrainResult(result) {
  if (result?.mesh) setHighlight(result.mesh);
}

function getObjectType(mesh) {
  const label = `${mesh.name || ""} ${mesh.parent?.name || ""}`.toLowerCase();
  if (label.includes("house")) return "house";
  if (label.includes("tree")) return "tree";
  if (label.includes("road")) return "road";
  if (label.includes("structure")) return "structure";
  return "building";
}

export function createSelectedObject(result) {
  if (!result?.mesh) return null;

  if (!objectIds.has(result.mesh)) objectIds.set(result.mesh, `object-${String(nextObjectId++).padStart(3, "0")}`);
  const meters = result.dimensions.meters;
  const hasSpecificName = result.objectName && !/^(mesh|object|node|model)[ _-]?\d*$/i.test(result.objectName);
  return {
    id: objectIds.get(result.mesh),
    type: getObjectType(result.mesh),
    name: hasSpecificName ? result.objectName : "Building",
    object3D: result.mesh,
    position: {
      x: result.position.x,
      y: result.position.y,
      z: result.position.z,
    },
    dimensions: {
      height: meters.height,
      width: meters.width,
    },
    measurementUnit: "m",
    isSelected: true,
  };
}

// Team 1 integration point. Return null until height_grid data is connected.
export function onTerrainClick(screenX, screenY) {
  const result = raycast(screenX, screenY);
  if (!result) clearHighlight();
  return result ? { height_value: null, units: null } : null;
}