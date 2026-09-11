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
    metadata.units === "meters" &&
    Number.isFinite(metadata.metersPerUnit) &&
    metadata.metersPerUnit > 0,
  );
  const scale = absoluteAvailable ? metadata.metersPerUnit : DEFAULT_METERS_PER_UNIT;
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

export function createDimensionOverlay(scene) {
  const group = new THREE.Group();
  group.visible = false;
  scene.add(group);

  return {
    show(dimensions, view) {
      group.clear();
      const { box, size } = dimensions;

      group.add(new THREE.Box3Helper(box, GUIDE_COLOR));

      group.visible = true;
    },
    hide() {
      group.visible = false;
      group.clear();
    },
  };
}
