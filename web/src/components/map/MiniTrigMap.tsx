import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import Spinner from "../ui/Spinner";
import {
  clampToPixelBBox,
  getBaseDimensions,
  loadMiniMapCalibration,
  lonLatToPixel,
  MINI_MAP_IMAGE_URL,
  type CalibrationResult,
} from "../../lib/mapCalibration";

type MiniTrigMapProps = {
  trigId?: number | null;
  trigName?: string | null;
  lat?: number | null;
  lon?: number | null;
  className?: string;
};

const DOT_DIAMETER = 10;

export default function MiniTrigMap({
  trigId,
  trigName,
  lat,
  lon,
  className = "",
}: MiniTrigMapProps) {
  const [calibration, setCalibration] = useState<CalibrationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [containerSize, setContainerSize] = useState<{ width: number; height: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadMiniMapCalibration()
      .then((cal) => {
        if (!cancelled) {
          setCalibration(cal);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load map calibration");
          setIsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return;
    }

    const updateSize = () => {
      setContainerSize({
        width: element.clientWidth,
        height: element.clientHeight,
      });
    };

    updateSize();

    if (typeof ResizeObserver === "undefined") {
      return;
    }

    const observer = new ResizeObserver(() => updateSize());
    observer.observe(element);

    return () => observer.disconnect();
  }, []);

  const dotPoint = useMemo(() => {
    if (!calibration || lat == null || lon == null) {
      return null;
    }
    const projected = lonLatToPixel(calibration, lon, lat);
    return clampToPixelBBox(calibration.pixel_bbox, projected.x, projected.y);
  }, [calibration, lat, lon]);

  const dotStyle: CSSProperties | null = useMemo(() => {
    if (!dotPoint || !calibration) {
      return null;
    }
    const base = getBaseDimensions(calibration);
    const width = containerSize?.width ?? base.width;
    const height = containerSize?.height ?? base.height;
    const [bboxLeft, bboxTop] = calibration.pixel_bbox;
    const xRatio = (dotPoint.x - bboxLeft) / base.width;
    const yRatio = (dotPoint.y - bboxTop) / base.height;
    return {
      width: DOT_DIAMETER,
      height: DOT_DIAMETER,
      left: xRatio * width - DOT_DIAMETER / 2,
      top: yRatio * height - DOT_DIAMETER / 2,
    };
  }, [dotPoint, calibration, containerSize]);

  const label =
    trigName ??
    (typeof trigId === "number" ? `Trig ${trigId.toLocaleString("en-GB")}` : "Trigpoint");

  const showDot = !!dotStyle && !isLoading && !error;
  const missingCoords = lat == null || lon == null;

  return (
    <div className={`relative ${className}`} ref={containerRef}>
      <img
        src={MINI_MAP_IMAGE_URL}
        alt={label}
        className="w-full h-full object-cover select-none"
        draggable={false}
      />
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/80">
          <Spinner size="sm" />
        </div>
      )}
      {error && !isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-red-50 text-red-600 text-xs text-center px-2">
          {error}
        </div>
      )}
      {missingCoords && !isLoading && !error && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/75 text-gray-600 text-xs px-2 text-center">
          No coordinates
        </div>
      )}
      {showDot && (
        <div
          className="absolute rounded-full bg-trig-green-500 border-2 border-white shadow"
          style={dotStyle as CSSProperties}
          data-testid="mini-trig-dot"
        />
      )}
      <div className="absolute top-2 left-2 bg-white/90 px-2 py-1 rounded text-xs font-mono text-gray-700 max-w-[calc(100%-1rem)] truncate shadow-sm">
        {label}
      </div>
    </div>
  );
}

