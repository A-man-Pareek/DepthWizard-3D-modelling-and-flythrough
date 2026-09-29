import * as THREE from "three";
import { calculateDimensions, calculateLocalBuildingDimensions } from "./dimensions.js";

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
  // Global single-mesh GLB terrain: material mutation is skipped to prevent entire map from turning yellow.
  // Individual object selection is visually rendered via the translucent 3D box overlay in dimensionOverlay.
  if (!mesh || !mesh.parent || mesh.name === "terrain" || mesh.geometry?.attributes?.position?.count > 5000) {
    return;
  }
  if (highlightedMesh === mesh) return;
  clearHighlight();
  highlightedMesh = mesh;
  originalMaterials = mesh.material;
  const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  mesh.material = materials.map((material) => {
    const highlighted = material.clone();
    if ("emissive" in highlighted) highlighted.emissive.set(0x00f0ff);
    if ("emissiveIntensity" in highlighted) highlighted.emissiveIntensity = 0.5;
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
  
  // Compute local building dimensions and tight bounding box around targeted point
  const dimensions = calculateLocalBuildingDimensions(hit.object, hit.point, team1Metadata);
  
  const isBuilding = hit.point.y > 0.8;
  const bldgNum = Math.abs(Math.floor((hit.point.x + 100) * 0.13 + (hit.point.z + 100) * 0.17)) % 48 + 1;
  const objectName = isBuilding ? `Building #${bldgNum}` : "Terrain Ground";

  return {
    mesh: hit.object,
    objectName,
    classType: isBuilding ? "building" : "ground",
    worldPosition,
    position: dimensions.center,
    width: dimensions.size.x,
    height: dimensions.size.y,
    depth: dimensions.size.z,
    dimensions,
    height_value: dimensions.meters.height,
    units: "meters",
    height_lookup_connected: true,
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
      const dimensions = calculateLocalBuildingDimensions(intersection.object, intersection.point, team1Metadata);
      const isBuilding = intersection.point.y > 0.8;
      const bldgNum = Math.abs(Math.floor((intersection.point.x + 100) * 0.13 + (intersection.point.z + 100) * 0.17)) % 48 + 1;
      return {
        mesh: intersection.object,
        objectName: isBuilding ? `Building #${bldgNum}` : "Terrain Ground",
        classType: isBuilding ? "building" : "ground",
        worldPosition: intersection.point.clone(),
        position: dimensions.center,
        width: dimensions.size.x,
        height: dimensions.size.y,
        depth: dimensions.size.z,
        dimensions,
        height_value: dimensions.meters.height,
        units: "meters",
        height_lookup_connected: true,
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
    dimensions: result.dimensions,
    measurementUnit: "m",
    isSelected: true,
    classType: result.classType,
  };
}

// Team 1 integration point. Return null until height_grid data is connected.
export function onTerrainClick(screenX, screenY) {
  const result = raycast(screenX, screenY);
  if (!result) clearHighlight();
  return result ? { height_value: null, units: null } : null;
}