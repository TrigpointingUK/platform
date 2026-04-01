/**
 * Survey Timeline Visualisation - Experimental Page
 *
 * Displays an animated visualisation of when trigpoints were triangulated
 * and levelled by the Ordnance Survey.
 */

import { useRef, useEffect, useState, useCallback, useMemo } from "react";
import {
  Play,
  Pause,
  SkipBack,
  Volume2,
  VolumeX,
  ChevronsLeft,
  ChevronsRight,
  ChevronLeft,
  ChevronRight,
  SkipForward,
  FlaskConical,
} from "lucide-react";
import {
  useSurveyTimeline,
  type SurveyTimelineEntry,
} from "../hooks/useSurveyTimeline";
import { latLonToScaledPixel, MAP_DIMENSIONS } from "../lib/mapCalibration";
import { useTheme } from "../hooks/useTheme";
import Spinner from "../components/ui/Spinner";


/** Map colour schemes for light and dark modes */
const MAP_COLOURS = {
  light: {
    sea: "#ffffff",
    land: "#d9d2ca",
    coastline: "#a0998f",
    coastlineWidth: 1,
  },
  dark: {
    sea: "#1f2937",
    land: "#374151",
    coastline: "#4b5563",
    coastlineWidth: 0.5,
  },
};

/** Survey colour definitions - green for triangulation, blue for levelling */
const SURVEY_COLOURS = {
  green: "#22c55e", // Triangulation (final colour)
  greenLight: "#86efac", // Triangulation (initial lighter colour)
  blue: "#3b82f6", // Levelling
};

/** Playback speed options */
const SPEED_OPTIONS = [
  { label: "0.1x", value: 0.1 },
  { label: "1x", value: 1 },
  { label: "10x", value: 10 },
];

/** Month name abbreviations */
const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** Dot configuration */
const DOT_SIZE = 2;
const PULSE_SIZE = 6;
const PULSE_DURATION = 200;
const HEAT_TRAIL_LENGTH = 50;
const FADE_OPACITY = 0.6;
const BASE_DELAY = 50;
const BLUE_TO_GREEN_FADE_DURATION = 2000; // ms for blue dots to fade to green

interface DisplayedDot {
  x: number;
  y: number;
  colourType: "green" | "blue"; // Original colour type
  addedAt: number;
}

/** Interpolate between two hex colours */
function interpolateColour(colour1: string, colour2: string, t: number): string {
  // Parse hex colours
  const r1 = parseInt(colour1.slice(1, 3), 16);
  const g1 = parseInt(colour1.slice(3, 5), 16);
  const b1 = parseInt(colour1.slice(5, 7), 16);
  const r2 = parseInt(colour2.slice(1, 3), 16);
  const g2 = parseInt(colour2.slice(3, 5), 16);
  const b2 = parseInt(colour2.slice(5, 7), 16);

  // Interpolate
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);

  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}

/** Get the current display colour for a dot based on age */
function getDotColour(dot: DisplayedDot, now: number): string {
  const age = now - dot.addedAt;
  const fadeProgress = Math.min(1, age / BLUE_TO_GREEN_FADE_DURATION);
  
  if (dot.colourType === "green") {
    // Green dots fade from light green to dark green
    return interpolateColour(SURVEY_COLOURS.greenLight, SURVEY_COLOURS.green, fadeProgress);
  }
  // Blue dots fade to green over time
  return interpolateColour(SURVEY_COLOURS.blue, SURVEY_COLOURS.green, fadeProgress);
}

export default function SurveyTimeline() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mapImageRef = useRef<HTMLImageElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  // Theme
  const { resolvedTheme } = useTheme();
  const mapColours = MAP_COLOURS[resolvedTheme];

  // State
  const [isPlaying, setIsPlaying] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [speed, setSpeed] = useState(10);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [displayedDots, setDisplayedDots] = useState<DisplayedDot[]>([]);
  const [currentDate, setCurrentDate] = useState<string | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [overlaysVisible, setOverlaysVisible] = useState(true);
  const overlayFadeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fixed height for the map
  const height = 600;

  // Start overlay fade timer
  const startOverlayFade = useCallback(() => {
    if (overlayFadeTimerRef.current) {
      clearTimeout(overlayFadeTimerRef.current);
    }
    overlayFadeTimerRef.current = setTimeout(() => {
      setOverlaysVisible(false);
    }, 3000);
  }, []);

  // Cancel overlay fade and show overlays
  const cancelOverlayFade = useCallback(() => {
    if (overlayFadeTimerRef.current) {
      clearTimeout(overlayFadeTimerRef.current);
      overlayFadeTimerRef.current = null;
    }
    setOverlaysVisible(true);
  }, []);

  // Fetch timeline data
  const { data: timeline, isLoading, error } = useSurveyTimeline();

  // Calculate canvas dimensions maintaining aspect ratio
  const canvasWidth = useMemo(() => {
    return Math.round((height * MAP_DIMENSIONS.width) / MAP_DIMENSIONS.height);
  }, [height]);

  // Group entries by date for batching
  const entriesByDate = useMemo(() => {
    if (!timeline) return new Map<string, SurveyTimelineEntry[]>();
    const grouped = new Map<string, SurveyTimelineEntry[]>();
    for (const entry of timeline) {
      const dateKey = entry.date || "unknown";
      const existing = grouped.get(dateKey) || [];
      existing.push(entry);
      grouped.set(dateKey, existing);
    }
    return grouped;
  }, [timeline]);

  // Get unique dates in order
  const orderedDates = useMemo(() => {
    if (!timeline) return [];
    const dates = new Set<string>();
    for (const entry of timeline) {
      dates.add(entry.date || "unknown");
    }
    return Array.from(dates);
  }, [timeline]);

  // Current year and month for display
  const currentYearMonth = useMemo(() => {
    if (!currentDate || currentDate === "unknown") return null;
    const parts = currentDate.split("-");
    const year = parts[0];
    const monthNum = parseInt(parts[1], 10);
    const month = MONTH_NAMES[monthNum - 1] || "";
    return month ? `${month} ${year}` : year;
  }, [currentDate]);

  // Load map image
  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      mapImageRef.current = img;
      setMapLoaded(true);
    };
    img.onerror = () => {
      console.error("Failed to load map image");
    };
    img.src = "/ukmap.png";
  }, []);

  // Play tick sound - different pitches for triangulation vs levelling
  const playTick = useCallback((hasTriangulation: boolean, hasLevelling: boolean) => {
    if (!soundEnabled) return;

    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext();
      }
      const ctx = audioContextRef.current;

      // Play triangulation sound (lower pitch)
      if (hasTriangulation) {
        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);
        oscillator.frequency.value = 600; // Lower pitch for triangulation
        oscillator.type = "sine";
        gainNode.gain.setValueAtTime(0.1, ctx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);
        oscillator.start(ctx.currentTime);
        oscillator.stop(ctx.currentTime + 0.05);
      }

      // Play levelling sound (higher pitch)
      if (hasLevelling) {
        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);
        oscillator.frequency.value = 1000; // Higher pitch for levelling
        oscillator.type = "sine";
        gainNode.gain.setValueAtTime(0.1, ctx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);
        oscillator.start(ctx.currentTime);
        oscillator.stop(ctx.currentTime + 0.05);
      }
    } catch {
      // Audio not available
    }
  }, [soundEnabled]);

  // Create coloured version of map on an offscreen canvas
  const createColouredMap = useCallback(
    (
      image: HTMLImageElement,
      width: number,
      height: number,
      colour: string
    ): HTMLCanvasElement => {
      const offscreen = document.createElement("canvas");
      offscreen.width = width;
      offscreen.height = height;
      const offCtx = offscreen.getContext("2d");
      if (!offCtx) return offscreen;

      offCtx.drawImage(image, 0, 0, width, height);
      offCtx.globalCompositeOperation = "source-in";
      offCtx.fillStyle = colour;
      offCtx.fillRect(0, 0, width, height);

      return offscreen;
    },
    []
  );

  // Draw the map and dots
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    const mapImage = mapImageRef.current;

    if (!canvas || !ctx || !mapImage) return;

    // Clear canvas and fill with sea colour
    ctx.fillStyle = mapColours.sea;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw coastline
    if (mapColours.coastlineWidth > 0) {
      const coastlineMap = createColouredMap(
        mapImage,
        canvas.width,
        canvas.height,
        mapColours.coastline
      );
      const expand = mapColours.coastlineWidth * 2;
      ctx.drawImage(
        coastlineMap,
        -expand / 2,
        -expand / 2,
        canvas.width + expand,
        canvas.height + expand
      );
    }

    // Draw land on top
    const landMap = createColouredMap(
      mapImage,
      canvas.width,
      canvas.height,
      mapColours.land
    );
    ctx.drawImage(landMap, 0, 0);

    const now = Date.now();

    // Draw all dots
    displayedDots.forEach((dot, index) => {
      const age = now - dot.addedAt;
      const isRecent = index >= displayedDots.length - HEAT_TRAIL_LENGTH;
      const isPulsing = age < PULSE_DURATION;

      let size = DOT_SIZE;
      if (isPulsing) {
        const progress = age / PULSE_DURATION;
        size = PULSE_SIZE - (PULSE_SIZE - DOT_SIZE) * progress;
      }

      let opacity = isRecent ? 1 : FADE_OPACITY;
      if (isPulsing) {
        opacity = 1;
      }

      ctx.globalAlpha = opacity;
      ctx.fillStyle = getDotColour(dot, now);
      ctx.fillRect(dot.x - size / 2, dot.y - size / 2, size, size);

      if (isPulsing) {
        ctx.globalAlpha = 0.3 * (1 - age / PULSE_DURATION);
        ctx.fillRect(dot.x - size, dot.y - size, size * 2, size * 2);
      }
    });

    ctx.globalAlpha = 1;
  }, [displayedDots, mapColours, createColouredMap]);

  // Redraw when dots change or theme changes
  useEffect(() => {
    if (mapLoaded) {
      draw();
    }
  }, [draw, mapLoaded, displayedDots, mapColours]);

  // Animation loop - process next batch of entries
  const processNextBatch = useCallback(() => {
    if (!timeline || currentIndex >= orderedDates.length) {
      return false;
    }

    const dateKey = orderedDates[currentIndex];
    const entriesForDate = entriesByDate.get(dateKey) || [];

    const newDots: DisplayedDot[] = entriesForDate.map((entry) => {
      const pixel = latLonToScaledPixel(
        entry.lat,
        entry.lon,
        canvasWidth,
        height
      );
      return {
        x: pixel.x,
        y: pixel.y,
        colourType: entry.colour,
        addedAt: Date.now(),
      };
    });

    if (newDots.length > 0) {
      setDisplayedDots((prev) => [...prev, ...newDots]);
      setCurrentDate(dateKey);
      const hasTriangulation = newDots.some(d => d.colourType === "green");
      const hasLevelling = newDots.some(d => d.colourType === "blue");
      playTick(hasTriangulation, hasLevelling);
    }

    setCurrentIndex((prev) => prev + 1);
    return true;
  }, [timeline, currentIndex, orderedDates, entriesByDate, canvasWidth, height, playTick]);

  // Animation timer
  useEffect(() => {
    if (!isPlaying) return;

    if (currentIndex >= orderedDates.length) {
      setTimeout(() => {
        setIsPlaying(false);
        setIsComplete(true);
      }, 0);
      return;
    }

    const delay = BASE_DELAY / speed;
    const timeoutId = setTimeout(() => {
      processNextBatch();
    }, delay);

    return () => clearTimeout(timeoutId);
  }, [isPlaying, currentIndex, orderedDates.length, speed, processNextBatch]);

  // Trigger overlay fade when sequence completes
  useEffect(() => {
    if (isComplete) {
      startOverlayFade();
    }
    return () => {
      if (overlayFadeTimerRef.current) {
        clearTimeout(overlayFadeTimerRef.current);
      }
    };
  }, [isComplete, startOverlayFade]);

  // Continuous redraw for pulse animations
  useEffect(() => {
    if (!mapLoaded) return;

    let animationId: number;
    const animate = () => {
      draw();
      animationId = requestAnimationFrame(animate);
    };

    const hasRecentDots = displayedDots.some(
      (dot) => Date.now() - dot.addedAt < PULSE_DURATION
    );

    // Also keep animating if there are dots still fading
    const hasFadingDots = displayedDots.some(
      (dot) => Date.now() - dot.addedAt < BLUE_TO_GREEN_FADE_DURATION
    );

    if (hasRecentDots || hasFadingDots || isPlaying) {
      animationId = requestAnimationFrame(animate);
    }

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, [draw, displayedDots, isPlaying, mapLoaded]);

  // Handlers
  const handlePlayPause = () => {
    cancelOverlayFade();
    if (isComplete) {
      setDisplayedDots([]);
      setCurrentIndex(0);
      setCurrentDate(null);
      setIsComplete(false);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const handleReplay = () => {
    cancelOverlayFade();
    setDisplayedDots([]);
    setCurrentIndex(0);
    setCurrentDate(null);
    setIsComplete(false);
    setIsPlaying(true);
  };

  const handleSpeedChange = (newSpeed: number) => {
    setSpeed(newSpeed);
  };

  const handleScrub = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timeline || orderedDates.length === 0) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const progress = x / rect.width;
    const targetIndex = Math.floor(progress * orderedDates.length);

    const newDots: DisplayedDot[] = [];
    for (let i = 0; i <= targetIndex && i < orderedDates.length; i++) {
      const dateKey = orderedDates[i];
      const entriesForDate = entriesByDate.get(dateKey) || [];
      for (const entry of entriesForDate) {
        const pixel = latLonToScaledPixel(
          entry.lat,
          entry.lon,
          canvasWidth,
          height
        );
        newDots.push({
          x: pixel.x,
          y: pixel.y,
          colourType: entry.colour,
          addedAt: Date.now() - BLUE_TO_GREEN_FADE_DURATION, // Already faded
        });
      }
    }

    setDisplayedDots(newDots);
    setCurrentIndex(targetIndex + 1);
    setCurrentDate(orderedDates[targetIndex] || null);
    setIsComplete(targetIndex >= orderedDates.length - 1);
    setIsPlaying(false);
  };

  // Jump to a specific index
  const jumpToIndex = useCallback(
    (targetIndex: number, overrideDate?: string) => {
      if (!timeline || orderedDates.length === 0) return;

      const clampedIndex = Math.max(0, Math.min(targetIndex, orderedDates.length - 1));

      const newDots: DisplayedDot[] = [];
      for (let i = 0; i <= clampedIndex && i < orderedDates.length; i++) {
        const dateKey = orderedDates[i];
        const entriesForDate = entriesByDate.get(dateKey) || [];
        for (const entry of entriesForDate) {
          const pixel = latLonToScaledPixel(
            entry.lat,
            entry.lon,
            canvasWidth,
            height
          );
          newDots.push({
            x: pixel.x,
            y: pixel.y,
            colourType: entry.colour,
            addedAt: Date.now() - BLUE_TO_GREEN_FADE_DURATION, // Already faded
          });
        }
      }

      setDisplayedDots(newDots);
      setCurrentIndex(clampedIndex + 1);
      setCurrentDate(overrideDate || orderedDates[clampedIndex] || null);
      setIsComplete(clampedIndex >= orderedDates.length - 1);
      setIsPlaying(false);
    },
    [timeline, orderedDates, entriesByDate, canvasWidth, height]
  );

  // Skip by year
  const skipByYear = useCallback(
    (direction: number) => {
      if (!orderedDates.length) return;

      const baseDateKey = currentDate || orderedDates[0];
      if (!baseDateKey || baseDateKey === "unknown") return;

      const [yearStr, monthStr] = baseDateKey.split("-");
      const baseYear = parseInt(yearStr, 10);
      const baseMonth = monthStr || "01";

      const targetYear = baseYear + direction;
      const targetDateKey = `${targetYear}-${baseMonth}`;

      let targetIdx = -1;
      for (let i = orderedDates.length - 1; i >= 0; i--) {
        const d = orderedDates[i];
        if (d && d !== "unknown" && d <= targetDateKey + "-31") {
          targetIdx = i;
          break;
        }
      }

      if (targetIdx !== -1) {
        jumpToIndex(targetIdx, targetDateKey);
      } else if (direction < 0) {
        jumpToIndex(0, targetDateKey);
      } else {
        setDisplayedDots([]);
        setCurrentIndex(0);
        setCurrentDate(targetDateKey);
        setIsComplete(false);
        setIsPlaying(false);
      }
    },
    [orderedDates, currentDate, jumpToIndex]
  );

  // Skip by month
  const skipByMonth = useCallback(
    (direction: number) => {
      if (!orderedDates.length) return;

      const baseDateKey = currentDate || orderedDates[0];
      if (!baseDateKey || baseDateKey === "unknown") return;

      const [yearStr, monthStr] = baseDateKey.split("-");
      let baseYear = parseInt(yearStr, 10);
      let baseMonth = parseInt(monthStr || "1", 10);

      baseMonth += direction;
      if (baseMonth > 12) {
        baseMonth = 1;
        baseYear += 1;
      } else if (baseMonth < 1) {
        baseMonth = 12;
        baseYear -= 1;
      }

      const targetDateKey = `${baseYear}-${String(baseMonth).padStart(2, "0")}`;

      let targetIdx = -1;
      for (let i = orderedDates.length - 1; i >= 0; i--) {
        const d = orderedDates[i];
        if (d && d !== "unknown" && d <= targetDateKey + "-31") {
          targetIdx = i;
          break;
        }
      }

      if (targetIdx !== -1) {
        jumpToIndex(targetIdx, targetDateKey);
      } else {
        setDisplayedDots([]);
        setCurrentIndex(0);
        setCurrentDate(targetDateKey);
        setIsComplete(false);
        setIsPlaying(false);
      }
    },
    [orderedDates, currentDate, jumpToIndex]
  );

  // Skip to end
  const skipToEnd = useCallback(() => {
    if (orderedDates.length > 0) {
      jumpToIndex(orderedDates.length - 1);
      startOverlayFade();
    }
  }, [orderedDates, jumpToIndex, startOverlayFade]);

  // Count stats
  const triangulationCount = displayedDots.filter(d => d.colourType === "green").length;
  const levellingCount = displayedDots.filter(d => d.colourType === "blue").length;

  // Calculate progress
  const progress =
    orderedDates.length > 0 ? currentIndex / orderedDates.length : 0;

  // Date range for display
  const firstDate = orderedDates[0];
  const lastDate = orderedDates[orderedDates.length - 1];

  return (
    <>
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <FlaskConical className="w-8 h-8 text-amber-500" />
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              Survey Timeline
            </h1>
            <span className="px-2 py-1 text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200 rounded">
              Experimental
            </span>
          </div>
          <p className="text-gray-600 dark:text-gray-400">
            Watch the Ordnance Survey's triangulation and levelling work unfold across the UK.
            <span className="ml-2 inline-flex items-center gap-2">
              <span className="inline-block w-3 h-3 bg-green-500 rounded-sm"></span>
              <span>Triangulation</span>
              <span className="inline-block w-3 h-3 bg-blue-500 rounded-sm ml-2"></span>
              <span>Levelling</span>
            </span>
          </p>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div
            className="flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg"
            style={{ height, width: canvasWidth }}
          >
            <Spinner size="lg" />
          </div>
        )}

        {/* Error state */}
        {error && (
          <div
            className="flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg text-red-500"
            style={{ height, width: canvasWidth }}
          >
            Failed to load timeline data
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && (!timeline || timeline.length === 0) && (
          <div
            className="flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg text-gray-500 dark:text-gray-400"
            style={{ height, width: canvasWidth }}
          >
            No survey data to display
          </div>
        )}

        {/* Map and controls */}
        {!isLoading && !error && timeline && timeline.length > 0 && (
          <div className="relative" style={{ width: canvasWidth }}>
            {/* Canvas */}
            <canvas
              ref={canvasRef}
              width={canvasWidth}
              height={height}
              className="rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900"
            />

            {/* Year/Month overlay */}
            {currentYearMonth && (
              <div
                className="absolute top-3 left-3 bg-black/60 text-white px-3 py-1 rounded-md font-mono text-2xl font-bold transition-opacity duration-[2000ms]"
                style={{ opacity: overlaysVisible ? 1 : 0 }}
              >
                {currentYearMonth}
              </div>
            )}

            {/* Stats overlay */}
            <div
              className="absolute top-3 right-3 bg-black/60 text-white px-3 py-1 rounded-md text-sm transition-opacity duration-[2000ms]"
              style={{ opacity: overlaysVisible ? 1 : 0 }}
            >
              <div className="flex items-center gap-2">
                <span className="inline-block w-2 h-2 bg-green-500 rounded-sm"></span>
                <span className="font-bold">{triangulationCount}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-block w-2 h-2 bg-blue-500 rounded-sm"></span>
                <span className="font-bold">{levellingCount}</span>
              </div>
              <div className="text-gray-300 text-xs mt-1">
                / {timeline.length} total
              </div>
            </div>

            {/* Timeline scrubber */}
            <div
              className="mt-2 h-2 bg-gray-200 dark:bg-gray-700 rounded-full cursor-pointer overflow-hidden"
              onClick={handleScrub}
            >
              <div
                className="h-full bg-trig-green-600 transition-all duration-100"
                style={{ width: `${progress * 100}%` }}
              />
            </div>

            {/* Date range labels */}
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
              <span>{firstDate !== "unknown" ? firstDate : "—"}</span>
              <span>{lastDate !== "unknown" ? lastDate : "—"}</span>
            </div>

            {/* Controls */}
            <div className="flex items-center justify-between mt-3 gap-2 flex-wrap">
              {/* Play/Pause */}
              <div className="flex items-center gap-1">
                <button
                  onClick={handlePlayPause}
                  className="p-2 rounded-full bg-trig-green-600 text-white hover:bg-trig-green-700 transition-colors"
                  aria-label={isPlaying ? "Pause" : isComplete ? "Replay" : "Play"}
                >
                  {isPlaying ? (
                    <Pause className="w-5 h-5" />
                  ) : (
                    <Play className="w-5 h-5" />
                  )}
                </button>
              </div>

              {/* Skip controls */}
              <div className="flex items-center gap-0.5">
                <button
                  onClick={handleReplay}
                  className="p-1.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                  aria-label="Skip to start"
                  title="Skip to start"
                >
                  <SkipBack className="w-4 h-4" />
                </button>
                <button
                  onClick={() => skipByYear(-1)}
                  className="p-1.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                  aria-label="Skip back one year"
                  title="Year back"
                >
                  <ChevronsLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => skipByMonth(-1)}
                  className="p-1.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                  aria-label="Skip back one month"
                  title="Month back"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => skipByMonth(1)}
                  className="p-1.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                  aria-label="Skip forward one month"
                  title="Month forward"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
                <button
                  onClick={() => skipByYear(1)}
                  className="p-1.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                  aria-label="Skip forward one year"
                  title="Year forward"
                >
                  <ChevronsRight className="w-4 h-4" />
                </button>
                <button
                  onClick={skipToEnd}
                  className="p-1.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                  aria-label="Skip to end"
                  title="Skip to present"
                >
                  <SkipForward className="w-4 h-4" />
                </button>
              </div>

              {/* Speed selector */}
              <div className="flex items-center gap-1">
                {SPEED_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => handleSpeedChange(option.value)}
                    className={`px-2 py-1 text-sm rounded transition-colors ${
                      speed === option.value
                        ? "bg-trig-green-600 text-white"
                        : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>

              {/* Sound toggle */}
              <button
                onClick={() => setSoundEnabled(!soundEnabled)}
                className={`p-2 rounded-full transition-colors ${
                  soundEnabled
                    ? "bg-trig-green-600 text-white"
                    : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
                }`}
                aria-label={soundEnabled ? "Mute" : "Unmute"}
              >
                {soundEnabled ? (
                  <Volume2 className="w-5 h-5" />
                ) : (
                  <VolumeX className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
        )}

        {/* Info section */}
        <div className="mt-8 prose dark:prose-invert max-w-none">
          <h2>About this visualisation</h2>
          <p>
            This experimental visualisation shows the dates when trigpoints were surveyed
            by the Ordnance Survey. The data comes from OS records indicating:
          </p>
          <ul>
            <li>
              <strong className="text-green-600 dark:text-green-400">Triangulation dates</strong> (green dots)
              — when the trigpoint was used for horizontal position fixing
            </li>
            <li>
              <strong className="text-blue-600 dark:text-blue-400">Levelling dates</strong> (blue dots)
              — when the trigpoint was used for height determination
            </li>
          </ul>
          <p>
            Note: Not all trigpoints have recorded survey dates. This visualisation shows
            approximately {timeline?.length?.toLocaleString() || "—"} records from the OS dataset.
          </p>
        </div>
      </div>
    </>
  );
}

