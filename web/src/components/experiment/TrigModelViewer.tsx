/**
 * TrigModelViewer – Interactive 3D viewer for the Hotine pillar model.
 *
 * Uses React Three Fiber with drei helpers to display a .glb model that
 * auto-rotates and supports orbit / pan / zoom via mouse interaction.
 *
 * Material-group toggle buttons let the user hide/show structural layers
 * (concrete, brass, steel, wood, fixings) so the pillar's interior can
 * be inspected.
 */

import {
  Suspense,
  useRef,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
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
  concrete: makePBR([0.3, 0.28, 0.23], 0.0, 0.85),
  brass: makePBR([0.25, 0.18, 0.06], 0.55, 0.5),
  rusted_steel: makePBR([0.14, 0.06, 0.02], 0.2, 0.75),
  aged_steel: makePBR([0.12, 0.12, 0.13], 0.6, 0.55),
  wood: makePBR([0.15, 0.08, 0.03], 0.0, 0.8),
  terrain: makePBR([0.12, 0.2, 0.05], 0.0, 0.95),
};

// ---------------------------------------------------------------------------
// Object → material-group mapping (used for both material assignment and
// layer-visibility toggling).
// ---------------------------------------------------------------------------

/** Return the material-group key for a Blender object name. */
function materialGroupForObject(name: string): string | null {
  const n = name.toLowerCase();

  if (
    n === "pillar" ||
    n === "concretefill" ||
    n === "baseslab" ||
    n === "lowerblock"
  )
    return "concrete";

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
    return "brass";

  if (
    n.startsWith("st_") ||
    n === "centrepipe" ||
    n.startsWith("angleiron")
  )
    return "rusted_steel";

  if (n.startsWith("screw") || n === "antirotationpeg") return "aged_steel";

  if (n === "upperbox" || n === "lowerbox") return "wood";

  if (n === "terrain" || n === "grid") return "terrain";

  return null;
}

/** Return the PBR material for a Blender object name. */
function materialForObject(name: string): THREE.MeshStandardMaterial | null {
  const group = materialGroupForObject(name);
  return group ? (MATERIALS[group] ?? null) : null;
}

// ---------------------------------------------------------------------------
// Layer toggle definitions
// ---------------------------------------------------------------------------

/** Material groups the user can toggle on/off. */
const LAYER_GROUPS = [
  { key: "concrete", label: "Concrete" },
  { key: "brass", label: "Brass" },
  { key: "rusted_steel", label: "Steel" },
  { key: "wood", label: "Wood" },
  { key: "aged_steel", label: "Fixings" },
] as const;

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

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
function TrigModel({ hidden }: { hidden: Set<string> }) {
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
        // Toggle visibility based on the hidden set
        const group = materialGroupForObject(mesh.name);
        mesh.visible = group ? !hidden.has(group) : true;
      }
    });
  }, [cloned, hidden]);

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
    if (
      !controls.autoRotate &&
      resumeAtRef.current > 0 &&
      performance.now() >= resumeAtRef.current
    ) {
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

// ---------------------------------------------------------------------------
// Colour swatch for each material group (matches the PBR palette above)
// ---------------------------------------------------------------------------

const SWATCH_COLOURS: Record<string, string> = {
  concrete: "#4d4840",
  brass: "#9e7520",
  rusted_steel: "#5c2810",
  aged_steel: "#3a3a40",
  wood: "#5c3010",
};

// ---------------------------------------------------------------------------
// Main exported component
// ---------------------------------------------------------------------------

export default function TrigModelViewer() {
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const toggle = useCallback((key: string) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  return (
    <div className="relative w-full h-full min-h-[60vh]">
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
          <TrigModel hidden={hidden} />
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

      {/* Layer toggle buttons — overlaid bottom-right */}
      <div className="absolute bottom-3 right-3 flex flex-col gap-1.5">
        {LAYER_GROUPS.map(({ key, label }) => {
          const isHidden = hidden.has(key);
          return (
            <button
              key={key}
              onClick={() => toggle(key)}
              className={`
                flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium
                backdrop-blur-sm transition-all shadow-sm cursor-pointer
                ${
                  isHidden
                    ? "bg-gray-800/60 text-gray-400 line-through"
                    : "bg-white/80 dark:bg-gray-800/80 text-gray-700 dark:text-gray-200"
                }
                hover:scale-105 active:scale-95
              `}
            >
              <span
                className="inline-block w-3 h-3 rounded-full shrink-0 border border-white/30"
                style={{
                  backgroundColor: SWATCH_COLOURS[key],
                  opacity: isHidden ? 0.3 : 1,
                }}
              />
              <span>{label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
