/**
 * TrigModelViewer – Interactive 3D viewer for the Hotine pillar model.
 *
 * Uses React Three Fiber with drei helpers to display a .glb model that
 * auto-rotates and supports orbit / pan / zoom via mouse interaction.
 */

import { Suspense, useRef, useCallback, useEffect, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import {
  OrbitControls,
  useGLTF,
  ContactShadows,
  Html,
  Center,
} from "@react-three/drei";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import Spinner from "../ui/Spinner";

const MODEL_PATH = "/models/trig.glb";

// ---------------------------------------------------------------------------
// Material palette — approximate the Blender procedural materials as flat PBR.
// Colours are taken from the Blender script's tuneable BASE_COLOUR values.
// ---------------------------------------------------------------------------

function makePBR(
  colour: [number, number, number],
  metalness: number,
  roughness: number,
): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: new THREE.Color().setRGB(...colour, THREE.LinearSRGBColorSpace),
    metalness,
    roughness,
  });
}

const MATERIALS: Record<string, THREE.MeshStandardMaterial> = {
  concrete:     makePBR([0.30, 0.28, 0.23], 0.0, 0.85),
  brass:        makePBR([0.25, 0.18, 0.06], 0.55, 0.50),
  rusted_steel: makePBR([0.14, 0.06, 0.02], 0.2, 0.75),
  aged_steel:   makePBR([0.12, 0.12, 0.13], 0.6, 0.55),
  wood:         makePBR([0.15, 0.08, 0.03], 0.0, 0.80),
  terrain:      makePBR([0.12, 0.20, 0.05], 0.0, 0.95),
};

/** Map Blender object names (or prefixes) to material keys. */
function materialForObject(name: string): THREE.MeshStandardMaterial | null {
  const n = name.toLowerCase();

  // Concrete parts
  if (
    n === "pillar" ||
    n === "concretefill" ||
    n === "baseslab" ||
    n === "lowerblock"
  )
    return MATERIALS.concrete;

  // Brass parts
  if (
    n === "spider" ||
    n === "plug" ||
    n === "innerplug" ||
    n.startsWith("brassloop") ||
    n === "flushbracket" ||
    n === "flushbracket_bead" ||
    n === "uppercentremark" ||
    n === "uppercentremark_spike" ||
    n === "lowercentremark"
  )
    return MATERIALS.brass;

  // Rusted steel — sighting tubes, centre pipe, angle irons
  if (
    n.startsWith("st_") ||
    n === "centrepipe" ||
    n.startsWith("angleiron")
  )
    return MATERIALS.rusted_steel;

  // Aged steel — screws, peg
  if (n.startsWith("screw") || n === "antirotationpeg")
    return MATERIALS.aged_steel;

  // Wood — boxes
  if (n === "upperbox" || n === "lowerbox") return MATERIALS.wood;

  // Terrain
  if (n === "terrain" || n === "grid") return MATERIALS.terrain;

  return null;
}

/** Inline loading indicator shown inside the Canvas while the model loads. */
function Loader() {
  return (
    <Html center>
      <div className="flex flex-col items-center gap-3">
        <Spinner size="lg" />
        <p className="text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">
          Loading 3D model…
        </p>
      </div>
    </Html>
  );
}

/** The GLTF model itself, centred at the origin with materials applied. */
function TrigModel() {
  const { scene } = useGLTF(MODEL_PATH);

  // Clone the scene so we don't mutate the cached original.
  const cloned = useMemo(() => scene.clone(true), [scene]);

  useEffect(() => {
    cloned.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        const mat = materialForObject(mesh.name);
        if (mat) {
          mesh.material = mat;
        }
      }
    });
  }, [cloned]);

  return (
    <Center>
      <primitive object={cloned} />
    </Center>
  );
}

/** Pre-load the model so it starts downloading as soon as this module is imported. */
useGLTF.preload(MODEL_PATH);

/** Pause duration (seconds) after user interaction before auto-rotate resumes. */
const PAUSE_DURATION = 5;

/**
 * OrbitControls wrapper that pauses auto-rotation for PAUSE_DURATION
 * seconds whenever the user interacts (drag / scroll / pinch).
 */
function AutoRotateControls() {
  const controlsRef = useRef<OrbitControlsImpl>(null);
  const resumeAtRef = useRef(0);

  const handleInteractionStart = useCallback(() => {
    // While the user is actively dragging, disable auto-rotate immediately
    // and cancel any pending resume timer from a previous interaction.
    if (controlsRef.current) {
      controlsRef.current.autoRotate = false;
    }
    resumeAtRef.current = 0;
  }, []);

  const handleInteractionEnd = useCallback(() => {
    // Schedule resume after the pause duration
    resumeAtRef.current = performance.now() + PAUSE_DURATION * 1000;
  }, []);

  useFrame(() => {
    const controls = controlsRef.current;
    if (!controls) return;
    if (!controls.autoRotate && resumeAtRef.current > 0 && performance.now() >= resumeAtRef.current) {
      controls.autoRotate = true;
      resumeAtRef.current = 0;
    }
  });

  return (
    <OrbitControls
      ref={controlsRef}
      autoRotate
      autoRotateSpeed={1.5}
      enablePan={true}
      enableZoom={true}
      minDistance={0.5}
      maxDistance={15}
      minPolarAngle={0}
      maxPolarAngle={Math.PI / 2 + 0.3}
      onStart={handleInteractionStart}
      onEnd={handleInteractionEnd}
    />
  );
}

export default function TrigModelViewer() {
  return (
    <div className="w-full h-full min-h-[60vh]">
      <Canvas
        camera={{ position: [3, 2.5, 3], fov: 40, near: 0.01, far: 100 }}
        gl={{ antialias: true }}
        dpr={[1, 2]}
      >
        {/* Lighting – multi-point setup for good hard-surface definition */}
        <ambientLight intensity={0.5} />
        <directionalLight position={[5, 8, 5]} intensity={1.4} castShadow />
        <directionalLight position={[-4, 3, -3]} intensity={0.5} />
        <directionalLight position={[0, -2, 5]} intensity={0.2} />
        <hemisphereLight
          color="#b1d8ff"
          groundColor="#665533"
          intensity={0.5}
        />

        {/* Model with suspense fallback */}
        <Suspense fallback={<Loader />}>
          <TrigModel />
          <ContactShadows
            position={[0, -0.01, 0]}
            opacity={0.4}
            scale={8}
            blur={2.5}
            far={4}
          />
        </Suspense>

        {/* Controls – auto-rotate with pause-on-interact behaviour */}
        <AutoRotateControls />
      </Canvas>
    </div>
  );
}

