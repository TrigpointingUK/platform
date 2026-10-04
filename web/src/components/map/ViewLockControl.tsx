import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useMap } from "react-leaflet";
import { Control, DomEvent } from "leaflet";
import { Lock, LockOpen } from "lucide-react";

interface ViewLockControlProps {
  locked: boolean;
  onChange: (locked: boolean) => void;
}

/**
 * Padlock button in the top-left control stack. While locked, the map keeps
 * its current view instead of zooming to fit when the filters change.
 */
export default function ViewLockControl({ locked, onChange }: ViewLockControlProps) {
  const map = useMap();
  const [container, setContainer] = useState<HTMLElement | null>(null);

  // A Leaflet control in the top-left corner, so it stacks under the other
  // buttons; React renders into it through a portal
  useEffect(() => {
    const control = new Control({ position: "topleft" });
    control.onAdd = () => {
      const div = document.createElement("div");
      div.className = "leaflet-bar leaflet-control";
      DomEvent.disableClickPropagation(div);
      return div;
    };
    control.addTo(map);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Portal target only exists once Leaflet has added the control
    setContainer(control.getContainer() ?? null);
    return () => {
      control.remove();
    };
  }, [map]);

  if (!container) return null;

  const label = locked
    ? "View locked - unlock to zoom to fit when the filters change"
    : "Lock the view so changing the filters doesn't move the map";

  return createPortal(
    // An <a>, like Leaflet's own zoom buttons, so it picks up their styling.
    // The colours need ! to beat Leaflet's (and our dark mode) .leaflet-bar a.
    <a
      href="#"
      role="button"
      title={label}
      aria-label={label}
      aria-pressed={locked}
      onClick={(e) => {
        e.preventDefault();
        onChange(!locked);
      }}
      className={`flex! items-center justify-center ${
        locked ? "bg-trig-green-600! text-white! hover:bg-trig-green-700!" : ""
      }`}
    >
      {locked ? <Lock className="w-4 h-4" /> : <LockOpen className="w-4 h-4" />}
    </a>,
    container,
  );
}
