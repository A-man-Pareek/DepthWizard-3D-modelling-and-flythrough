import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

export function loadEnvironment(scene, onProgress) {
  const loader = new GLTFLoader();
  return new Promise((resolve, reject) => {
    loader.load(
      "/street.glb",
      (gltf) => {
        const environment = gltf.scene;
        scene.add(environment);

        environment.traverse((object) => {
          if (!object.isMesh) return;
          object.castShadow = true;
          object.receiveShadow = true;
        });

        const initialBox = new THREE.Box3().setFromObject(environment);
        const initialSize = initialBox.getSize(new THREE.Vector3());
        const initialMax = Math.max(initialSize.x, initialSize.y, initialSize.z);
        if (!Number.isFinite(initialMax) || initialMax <= 0) {
          reject(new Error("The GLB contains no visible geometry."));
          return;
        }

        // Keep unusually large or tiny exports navigable without changing normal-scale assets.
        if (initialMax > 500 || initialMax < 0.1) {
          const factor = 100 / initialMax;
          environment.scale.multiplyScalar(factor);
        }

        const box = new THREE.Box3().setFromObject(environment);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        environment.position.x -= center.x;
        environment.position.z -= center.z;
        environment.position.y -= box.min.y;
        const adjustedBox = new THREE.Box3().setFromObject(environment);
        const adjustedSize = adjustedBox.getSize(new THREE.Vector3());
        resolve({ environment, bounds: adjustedBox, size: adjustedSize });
      },
      (event) => {
        if (event.total) onProgress(Math.round((event.loaded / event.total) * 100));
      },
      reject,
    );
  });
}

export function placeCamera(camera, bounds, size) {
  const maxDimension = Math.max(size.x, size.y, size.z);
  camera.position.set(
    0,
    Math.max(1.7, size.y * 0.08),
    Math.max(5, size.z / 2 + maxDimension * 0.25),
  );
  camera.lookAt(new THREE.Vector3(0, Math.max(1, size.y * 0.35), 0));
}