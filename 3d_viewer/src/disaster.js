import * as THREE from "three";

/**
 * DepthWizard Photorealistic 3D Hazard & Disaster Simulation Visualizer FX Engine
 * High-fidelity animated 3D visual effects for Flood, Wildfire, Cyclone, Landslide, and Spatial Risk Tiers.
 */

let hazardGroup = null;
let waterMesh = null;
let waterMaterial = null;
let waveLine = null;
let riskBoxesGroup = null;
let terrainBounds = null;

// Dynamic 3D FX Particle Systems
let activeHazardType = "FLOOD";
let wildfireParticles = null;
let wildfireParticleGeo = null;
let cycloneGroup = null;
let cycloneParticles = null;
let landslideParticles = null;
let activeParams = {};

export function initHazardVisualizer(scene) {
  if (hazardGroup) scene.remove(hazardGroup);
  hazardGroup = new THREE.Group();
  hazardGroup.name = "hazardSimulationGroup";
  scene.add(hazardGroup);
  return hazardGroup;
}

export function updateTerrainBounds(bounds) {
  terrainBounds = bounds;
}

/**
 * Render 3D Flood Water Surface with wave animation
 */
export function setFloodLevel(levelPercent, sceneBounds = null) {
  if (!hazardGroup) return;

  const bounds = sceneBounds || terrainBounds;
  const minY = bounds ? bounds.min.y : 0;
  const maxY = bounds ? bounds.max.y : 10;
  const terrainHeightRange = Math.max(maxY - minY, 3.0);

  const targetY = minY + (levelPercent / 100.0) * (terrainHeightRange * 1.2);

  if (!waterMesh) {
    const planeWidth = bounds ? Math.max((bounds.max.x - bounds.min.x) * 1.5, 300) : 300;
    const planeDepth = bounds ? Math.max((bounds.max.z - bounds.min.z) * 1.5, 300) : 300;

    const geom = new THREE.PlaneGeometry(planeWidth, planeDepth, 64, 64);
    geom.rotateX(-Math.PI / 2);

    waterMaterial = new THREE.MeshStandardMaterial({
      color: 0x0284c7, // Azure cyan
      roughness: 0.10,
      metalness: 0.20,
      transparent: true,
      opacity: 0.72,
      side: THREE.DoubleSide,
      depthWrite: false,
    });

    waterMesh = new THREE.Mesh(geom, waterMaterial);
    waterMesh.position.y = targetY;
    hazardGroup.add(waterMesh);

    // Glowing wave boundary line
    const ringGeom = new THREE.RingGeometry(planeWidth * 0.48, planeWidth * 0.5, 64);
    ringGeom.rotateX(-Math.PI / 2);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.85,
    });
    waveLine = new THREE.Mesh(ringGeom, ringMat);
    waveLine.position.y = 0.05;
    waterMesh.add(waveLine);
  } else {
    waterMesh.position.y = targetY;
  }

  waterMesh.visible = levelPercent > 0;
}

/**
 * Clear existing dynamic hazard FX (particles, vortices, heatmaps)
 */
function clearHazardFX() {
  if (!hazardGroup) return;
  
  // Remove non-water hazard children
  const toRemove = [];
  hazardGroup.children.forEach((child) => {
    if (child !== waterMesh && child !== riskBoxesGroup) {
      toRemove.push(child);
    }
  });
  toRemove.forEach((child) => hazardGroup.remove(child));

  wildfireParticles = null;
  cycloneGroup = null;
  cycloneParticles = null;
  landslideParticles = null;
}

/**
 * Build 3D Wildfire Ember Particle System & Charred Terrain Front
 */
function buildWildfireFX(intensity = 50) {
  const bounds = terrainBounds || { min: { x: -100, y: 0, z: -100 }, max: { x: 100, y: 10, z: 100 } };
  const radius = Math.max(30, (intensity / 100) * 85);

  // 1. Dark Charred Ash Base Mesh
  const geom = new THREE.CircleGeometry(radius, 48);
  geom.rotateX(-Math.PI / 2);
  const mat = new THREE.MeshStandardMaterial({
    color: 0x18181b, // Dark charcoal ash
    roughness: 0.95,
    transparent: true,
    opacity: 0.80,
    side: THREE.DoubleSide,
  });
  const ashMesh = new THREE.Mesh(geom, mat);
  ashMesh.position.set(0, bounds.min.y + 0.18, 0);
  hazardGroup.add(ashMesh);

  // 2. Glowing Flame Front Ring
  const flameRingGeom = new THREE.RingGeometry(radius - 2.5, radius + 2.5, 48);
  flameRingGeom.rotateX(-Math.PI / 2);
  const flameRingMat = new THREE.MeshBasicMaterial({
    color: 0xf97316, // Vibrant neon orange
    side: THREE.DoubleSide,
    transparent: true,
    opacity: 0.90,
  });
  const flameRing = new THREE.Mesh(flameRingGeom, flameRingMat);
  flameRing.position.set(0, bounds.min.y + 0.22, 0);
  hazardGroup.add(flameRing);

  // 3. 3D Floating Glowing Ember Particles
  const particleCount = 250;
  const positions = new Float32Array(particleCount * 3);
  const speeds = new Float32Array(particleCount);

  for (let i = 0; i < particleCount; i++) {
    const angle = Math.random() * Math.PI * 2;
    const r = Math.random() * radius;
    positions[i * 3] = Math.cos(angle) * r;
    positions[i * 3 + 1] = bounds.min.y + Math.random() * 15;
    positions[i * 3 + 2] = Math.sin(angle) * r;
    speeds[i] = 0.05 + Math.random() * 0.12;
  }

  wildfireParticleGeo = new THREE.BufferGeometry();
  wildfireParticleGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));

  const particleMat = new THREE.PointsMaterial({
    color: 0xff4500,
    size: 0.8,
    transparent: true,
    opacity: 0.85,
    blending: THREE.AdditiveBlending,
  });

  wildfireParticles = new THREE.Points(wildfireParticleGeo, particleMat);
  wildfireParticles.userData = { speeds, minY: bounds.min.y, maxY: bounds.min.y + 18, radius };
  hazardGroup.add(wildfireParticles);
}

/**
 * Build 3D Cyclone Spinning Vortex & Gale-Force Wind Streamlines
 */
function buildCycloneFX(magnitude = 6.2) {
  const bounds = terrainBounds || { min: { x: -100, y: 0, z: -100 }, max: { x: 100, y: 10, z: 100 } };
  cycloneGroup = new THREE.Group();
  cycloneGroup.position.set(0, bounds.min.y + 0.3, 0);

  const radiusMax = Math.max(40, magnitude * 12);

  // 1. Concentric Pressure Shockwave Rings
  for (let r = 1; r <= 4; r++) {
    const radius = (r / 4) * radiusMax;
    const ringGeom = new THREE.RingGeometry(radius - 1.2, radius + 1.2, 64);
    ringGeom.rotateX(-Math.PI / 2);
    const ringMat = new THREE.MeshBasicMaterial({
      color: r === 1 ? 0xef4444 : r === 2 ? 0xf59e0b : 0x38bdf8,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.85 - r * 0.15,
    });
    const ring = new THREE.Mesh(ringGeom, ringMat);
    cycloneGroup.add(ring);
  }

  // 2. Swirling Vortex Wind Particle System
  const particleCount = 400;
  const positions = new Float32Array(particleCount * 3);
  const angles = new Float32Array(particleCount);
  const radii = new Float32Array(particleCount);

  for (let i = 0; i < particleCount; i++) {
    const angle = Math.random() * Math.PI * 2;
    const rad = 5 + Math.random() * (radiusMax - 5);
    angles[i] = angle;
    radii[i] = rad;
    positions[i * 3] = Math.cos(angle) * rad;
    positions[i * 3 + 1] = (rad / radiusMax) * 12.0;
    positions[i * 3 + 2] = Math.sin(angle) * rad;
  }

  const pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const pMat = new THREE.PointsMaterial({
    color: 0x38bdf8,
    size: 0.7,
    transparent: true,
    opacity: 0.75,
    blending: THREE.AdditiveBlending,
  });

  cycloneParticles = new THREE.Points(pGeo, pMat);
  cycloneParticles.userData = { angles, radii, radiusMax };
  cycloneGroup.add(cycloneParticles);

  hazardGroup.add(cycloneGroup);
}

/**
 * Build 3D Landslide Slope Susceptibility Heatmap & Cascading Debris
 */
function buildLandslideFX(slope = 28) {
  const bounds = terrainBounds || { min: { x: -100, y: 0, z: -100 }, max: { x: 100, y: 10, z: 100 } };

  // 1. Slope Hazard Gradient Zone (Red to Amber overlay)
  const geom = new THREE.PlaneGeometry(160, 160, 32, 32);
  geom.rotateX(-Math.PI / 2);
  const mat = new THREE.MeshStandardMaterial({
    color: slope > 35 ? 0xd97706 : 0xef4444,
    transparent: true,
    opacity: Math.min(0.60, (slope / 50.0) * 0.65),
    side: THREE.DoubleSide,
    roughness: 0.8,
  });
  const zone = new THREE.Mesh(geom, mat);
  zone.position.set(0, bounds.min.y + 0.25, 0);
  hazardGroup.add(zone);

  // 2. Cascading Falling Debris Particle System
  const particleCount = 200;
  const positions = new Float32Array(particleCount * 3);
  const speeds = new Float32Array(particleCount);

  for (let i = 0; i < particleCount; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 140;
    positions[i * 3 + 1] = bounds.min.y + Math.random() * 12;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 140;
    speeds[i] = 0.08 + Math.random() * 0.15;
  }

  const pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const pMat = new THREE.PointsMaterial({
    color: 0x78350f, // Earthy soil brown
    size: 0.9,
    transparent: true,
    opacity: 0.85,
  });

  landslideParticles = new THREE.Points(pGeo, pMat);
  landslideParticles.userData = { speeds, minY: bounds.min.y, maxY: bounds.min.y + 12 };
  hazardGroup.add(landslideParticles);
}

/**
 * Render High Risk Areas (Red) and Low Risk Areas (Green) bounding region overlays
 */
export function renderRiskAreaTiers(summaryStatistics, assessedBuildings = []) {
  if (!hazardGroup) return;

  if (riskBoxesGroup) {
    hazardGroup.remove(riskBoxesGroup);
  }
  riskBoxesGroup = new THREE.Group();
  riskBoxesGroup.name = "riskAreaTiersGroup";

  const bounds = terrainBounds || { min: { x: -100, y: 0, z: -100 }, max: { x: 100, y: 10, z: 100 } };
  const width = bounds.max.x - bounds.min.x;
  const depth = bounds.max.z - bounds.min.z;
  const minY = bounds.min.y;

  // High Risk Area Overlay (Red Translucent Plane on left/front quadrant)
  const highRiskGeom = new THREE.PlaneGeometry(width * 0.45, depth * 0.45);
  highRiskGeom.rotateX(-Math.PI / 2);
  const highRiskMat = new THREE.MeshStandardMaterial({
    color: 0xef4444, // Red
    transparent: true,
    opacity: 0.42,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const highRiskZone = new THREE.Mesh(highRiskGeom, highRiskMat);
  highRiskZone.position.set(bounds.min.x + width * 0.25, minY + 0.3, bounds.min.z + depth * 0.25);
  riskBoxesGroup.add(highRiskZone);

  // Low Risk Area Overlay (Green Translucent Plane on right/back quadrant)
  const lowRiskGeom = new THREE.PlaneGeometry(width * 0.45, depth * 0.45);
  lowRiskGeom.rotateX(-Math.PI / 2);
  const lowRiskMat = new THREE.MeshStandardMaterial({
    color: 0x22c55e, // Green
    transparent: true,
    opacity: 0.35,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const lowRiskZone = new THREE.Mesh(lowRiskGeom, lowRiskMat);
  lowRiskZone.position.set(bounds.min.x + width * 0.75, minY + 0.3, bounds.min.z + depth * 0.75);
  riskBoxesGroup.add(lowRiskZone);

  hazardGroup.add(riskBoxesGroup);
}

/**
 * Render complete 3D hazard visualization overlays: FLOOD, WILDFIRE, CYCLONE, LANDSLIDE
 */
export function renderHazardOverlay(type, params = {}) {
  if (!hazardGroup) return;

  activeHazardType = (type || "FLOOD").toUpperCase();
  activeParams = params;
  clearHazardFX();

  if (activeHazardType === "FLOOD") {
    const level = params.level !== undefined ? params.level : (params.intensity === "high" ? 75 : params.intensity === "low" ? 25 : 45);
    setFloodLevel(level);
    renderRiskAreaTiers(params.summaryStatistics, params.assessedBuildings);
  } else if (activeHazardType === "WILDFIRE") {
    setFloodLevel(0);
    const intensity = params.level !== undefined ? params.level : 50;
    buildWildfireFX(intensity);
    renderRiskAreaTiers(params.summaryStatistics, params.assessedBuildings);
  } else if (activeHazardType === "CYCLONE") {
    setFloodLevel(0);
    const mag = params.magnitude || (params.level ? (params.level / 100) * 5 + 4 : 6.2);
    buildCycloneFX(mag);
    renderRiskAreaTiers(params.summaryStatistics, params.assessedBuildings);
  } else if (activeHazardType === "LANDSLIDE") {
    setFloodLevel(0);
    const slope = params.slope || (params.level ? (params.level / 100) * 45 + 10 : 28);
    buildLandslideFX(slope);
    renderRiskAreaTiers(params.summaryStatistics, params.assessedBuildings);
  }
}

/**
 * Continuous 3D Animation Loop for ALL Hazard FX (Waves, Wildfire Embers, Cyclone Spinning Vortex, Landslide Debris)
 */
export function animateWater(elapsedTime, delta = 0.016) {
  // 1. Flood Water Wave Animation
  if (waterMesh && waterMesh.visible) {
    const pos = waterMesh.geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const u = pos.getX(i);
      const v = pos.getZ(i);
      const wave = Math.sin(u * 0.1 + elapsedTime * 2.5) * Math.cos(v * 0.1 + elapsedTime * 2.0) * 0.15;
      pos.setY(i, wave);
    }
    pos.needsUpdate = true;
  }

  // 2. Wildfire Rising Ember Particles Animation
  if (wildfireParticles) {
    const pos = wildfireParticles.geometry.attributes.position;
    const { speeds, minY, maxY } = wildfireParticles.userData;
    for (let i = 0; i < pos.count; i++) {
      let y = pos.getY(i) + speeds[i];
      if (y > maxY) y = minY;
      // Brownian swirl drift
      const x = pos.getX(i) + Math.sin(elapsedTime * 3 + i) * 0.05;
      const z = pos.getZ(i) + Math.cos(elapsedTime * 3 + i) * 0.05;
      pos.setXYZ(i, x, y, z);
    }
    pos.needsUpdate = true;
  }

  // 3. Cyclone Spinning Vortex & Wind Orbit Animation
  if (cycloneGroup) {
    cycloneGroup.rotation.y += delta * 1.8; // Rotate storm eye vortex
  }
  if (cycloneParticles) {
    const pos = cycloneParticles.geometry.attributes.position;
    const { angles, radii } = cycloneParticles.userData;
    for (let i = 0; i < pos.count; i++) {
      angles[i] += delta * (3.0 / Math.sqrt(radii[i]));
      const x = Math.cos(angles[i]) * radii[i];
      const z = Math.sin(angles[i]) * radii[i];
      pos.setX(i, x);
      pos.setZ(i, z);
    }
    pos.needsUpdate = true;
  }

  // 4. Landslide Cascading Debris Particle Animation
  if (landslideParticles) {
    const pos = landslideParticles.geometry.attributes.position;
    const { speeds, minY, maxY } = landslideParticles.userData;
    for (let i = 0; i < pos.count; i++) {
      let y = pos.getY(i) - speeds[i];
      let z = pos.getZ(i) - speeds[i] * 0.5; // Flow down hill
      if (y < minY) {
        y = maxY;
        z = (Math.random() - 0.5) * 140;
      }
      pos.setY(i, y);
      pos.setZ(i, z);
    }
    pos.needsUpdate = true;
  }
}
