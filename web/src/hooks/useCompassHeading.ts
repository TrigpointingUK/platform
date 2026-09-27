import { useCallback, useEffect, useRef, useState } from "react";

// iOS adds these to the standard types
interface IOSDeviceOrientationEvent extends DeviceOrientationEvent {
  webkitCompassHeading?: number;
}
type OrientationEventWithPermission = typeof DeviceOrientationEvent & {
  requestPermission?: () => Promise<"granted" | "denied">;
};

// How much each new reading moves the smoothed heading (0-1). Lower is
// steadier but lags more.
const SMOOTHING = 0.2;
// Ignore changes smaller than this, in degrees, to save redraws
const MIN_CHANGE = 1;

function screenAngle(): number {
  return screen.orientation?.angle ?? 0;
}

/** Heading of the top of the screen, in degrees clockwise from north, or null */
function readHeading(event: IOSDeviceOrientationEvent): number | null {
  // iOS: already a compass heading
  if (typeof event.webkitCompassHeading === "number" && event.webkitCompassHeading >= 0) {
    return (event.webkitCompassHeading + screenAngle()) % 360;
  }
  // Others: alpha runs anticlockwise from north, but only when absolute
  if (event.absolute && event.alpha !== null) {
    return (360 - event.alpha + screenAngle()) % 360;
  }
  return null;
}

/**
 * The direction the device is pointing, from its compass where it has one.
 *
 * `heading` stays null on devices without a compass (most desktops). On iOS
 * the compass needs permission, which can only be asked for from a tap:
 * call `requestPermission` from a click handler.
 */
export function useCompassHeading() {
  const orientationEvent =
    typeof window !== "undefined" && "DeviceOrientationEvent" in window
      ? (window.DeviceOrientationEvent as OrientationEventWithPermission)
      : null;
  const needsPermission = typeof orientationEvent?.requestPermission === "function";

  const [permitted, setPermitted] = useState(!needsPermission);
  const [heading, setHeading] = useState<number | null>(null);

  // Smoothed as a unit vector, so 359° and 1° average to 0°, not 180°
  const smoothed = useRef<{ x: number; y: number } | null>(null);
  const frame = useRef(0);

  useEffect(() => {
    if (!orientationEvent || !permitted) return;

    const onOrientation = (event: Event) => {
      const raw = readHeading(event as IOSDeviceOrientationEvent);
      if (raw === null) return;
      const rad = (raw * Math.PI) / 180;
      const prev = smoothed.current;
      smoothed.current = prev
        ? {
            x: prev.x + (Math.sin(rad) - prev.x) * SMOOTHING,
            y: prev.y + (Math.cos(rad) - prev.y) * SMOOTHING,
          }
        : { x: Math.sin(rad), y: Math.cos(rad) };

      if (frame.current) return;
      frame.current = requestAnimationFrame(() => {
        frame.current = 0;
        const s = smoothed.current;
        if (!s) return;
        const next = ((Math.atan2(s.x, s.y) * 180) / Math.PI + 360) % 360;
        setHeading((current) => {
          if (current === null) return next;
          const diff = Math.abs(((next - current + 540) % 360) - 180);
          return diff < MIN_CHANGE ? current : next;
        });
      });
    };

    // Android Chrome reports true compass readings only on the absolute event
    const eventName =
      "ondeviceorientationabsolute" in window ? "deviceorientationabsolute" : "deviceorientation";
    window.addEventListener(eventName, onOrientation);
    return () => {
      window.removeEventListener(eventName, onOrientation);
      cancelAnimationFrame(frame.current);
      frame.current = 0;
    };
  }, [orientationEvent, permitted]);

  const requestPermission = useCallback(() => {
    if (permitted || !orientationEvent?.requestPermission) return;
    orientationEvent
      .requestPermission()
      .then((result) => setPermitted(result === "granted"))
      .catch(() => {
        // Declined or not allowed here - just no compass
      });
  }, [permitted, orientationEvent]);

  return { heading, requestPermission };
}
