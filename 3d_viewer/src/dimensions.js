import * as THREE from "three";

const GUIDE_COLOR = 0xf7d27d;
const DEFAULT_METERS_PER_UNIT = 1;

export function normalizeDimensions(size) {
  const maxDimension = Math.max(size.x, size.y, size.z);
  if (!Number.isFinite(maxDimension) || maxDimension <= 0) {
    return { height: 0, width: 0, depth: 0 };
  }
  return {
    height: size.y / maxDimension,
    width: size.x / maxDimension,
    depth: size.z / maxDimension,
  };
}

export function calculateDimensions(object, metadata = null) {
  const box = new THREE.Box3().setFromObject(object);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const normalized = normalizeDimensions(size);

  const absoluteAvailable = Boolean(
    metadata &&
    (metadata.units === "meters" || metadata.mode?.startsWith("absolute")),
  );

  const scale = Number.isFinite(metadata?.metersPerUnit) && metadata.metersPerUnit > 0
    ? metadata.metersPerUnit
    : (absoluteAvailable ? 1.0 : DEFAULT_METERS_PER_UNIT);

  const meters = {
    height: size.y * scale,
    width: size.x * scale,
    depth: size.z * scale,
  };

  return {
    box,
    center,
    size,
    normalized,
    absoluteAvailable,
    meters,
    absolute: meters,
  };
}

/**
 * Calculates LOCAL building dimensions & tight bounding box around raycasted point.
 * Prevents raycasting from selecting the whole 200m terrain mesh.
 */
export function calculateLocalBuildingDimensions(mesh, hitPoint, metadata = null) {
  if (!mesh || !mesh.geometry || !hitPoint) {
    return calculateDimensions(mesh, metadata);
  }

  const posAttr = mesh.geometry.attributes.position;
  if (!posAttr) return calculateDimensions(mesh, metadata);

  const isGroundClick = hitPoint.y < 0.4;
  const searchRadius = isGroundClick ? 3.0 : 8.0; // Search radius around raycast click

  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;
  let minZ = Infinity, maxZ = -Infinity;
  let count = 0;

  const matrixWorld = mesh.matrixWorld;
  const vertex = new THREE.Vector3();
  const step = posAttr.count > 40000 ? 2 : 1;

  for (let i = 0; i < posAttr.count; i += step) {
    vertex.fromBufferAttribute(posAttr, i);
    vertex.applyMatrix4(matrixWorld);

    const dx = vertex.x - hitPoint.x;
    const dz = vertex.z - hitPoint.z;
    const distSq = dx * dx + dz * dz;

    if (distSq <= searchRadius * searchRadius) {
      if (isGroundClick) {
        if (vertex.x < minX) minX = vertex.x;
        if (vertex.x > maxX) maxX = vertex.x;
        if (vertex.y < minY) minY = vertex.y;
        if (vertex.y > maxY) maxY = vertex.y;
        if (vertex.z < minZ) minZ = vertex.z;
        if (vertex.z > maxZ) maxZ = vertex.z;
        count++;
      } else if (vertex.y >= 0.25) {
        // Elevated building / structure vertices
        if (vertex.x < minX) minX = vertex.x;
        if (vertex.x > maxX) maxX = vertex.x;
        if (vertex.y < minY) minY = vertex.y;
        if (vertex.y > maxY) maxY = vertex.y;
        if (vertex.z < minZ) minZ = vertex.z;
        if (vertex.z > maxZ) maxZ = vertex.z;
        count++;
      }
    }
  }

  // Fallback bounding box if sparse vertices around click point
  if (count < 4 || !Number.isFinite(minX)) {
    const halfWidth = isGroundClick ? 1.5 : 3.5;
    minX = hitPoint.x - halfWidth;
    maxX = hitPoint.x + halfWidth;
    minY = 0;
    maxY = Math.max(0.5, hitPoint.y);
    minZ = hitPoint.z - halfWidth;
    maxZ = hitPoint.z + halfWidth;
  }

  const boxMinY = isGroundClick ? Math.max(0, minY - 0.1) : 0;
  const box = new THREE.Box3(
    new THREE.Vector3(minX, boxMinY, minZ),
    new THREE.Vector3(maxX, Math.max(boxMinY + 0.4, maxY), maxZ)
  );

  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const normalized = normalizeDimensions(size);

  const scale = Number.isFinite(metadata?.metersPerUnit) && metadata.metersPerUnit > 0
    ? metadata.metersPerUnit
    : 1.0;

  const meters = {
    height: size.y * scale,
    width: size.x * scale,
    depth: size.z * scale,
  };

  return {
    box,
    center,
    size,
    normalized,
    absoluteAvailable: true,
    meters,
    absolute: meters,
  };
}

export function createDimensionOverlay(scene) {
  const group = new THREE.Group();
  group.visible = false;
  scene.add(group);

  const boxMaterial = new THREE.MeshBasicMaterial({
    color: 0x00f0ff,
    transparent: true,
    opacity: 0.32,
    depthWrite: false,
    side: THREE.DoubleSide,
  });

  return {
    show(dimensions, view) {
      group.clear();
      const { box, center, size } = dimensions;

      // 1. Translucent solid 3D highlight box
      const geo = new THREE.BoxGeometry(size.x, size.y, size.z);
      const highlightMesh = new THREE.Mesh(geo, boxMaterial);
      highlightMesh.position.copy(center);
      group.add(highlightMesh);

      // 2. Wireframe cyan border box helper
      const boxHelper = new THREE.Box3Helper(box, 0x00f0ff);
      group.add(boxHelper);

      group.visible = true;
    },
    hide() {
      group.visible = false;
      group.clear();
    },
  };
}
