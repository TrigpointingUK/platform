import { useState, useRef, useCallback } from "react";

interface InteractiveStarRatingProps {
  rating: number;
  onRate?: (score: number) => void;
  readonly?: boolean;
  size?: "sm" | "md" | "lg";
  maxStars?: number;
  showLabel?: boolean;
  label?: string;
  colour?: "amber" | "green";
}

const STAR_PATH =
  "M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z";

const SIZE_CLASSES = {
  sm: "w-3.5 h-3.5",
  md: "w-5 h-5",
  lg: "w-6 h-6",
};

const COLOUR_CLASSES = {
  amber: "text-amber-400",
  green: "text-green-700",
};

export default function InteractiveStarRating({
  rating,
  onRate,
  readonly = false,
  size = "md",
  maxStars = 5,
  showLabel = false,
  label,
  colour = "amber",
}: InteractiveStarRatingProps) {
  const [hoverScore, setHoverScore] = useState<number | null>(null);
  const starRefs = useRef<(HTMLDivElement | null)[]>([]);

  const displayScore = hoverScore ?? rating;
  const displayRating = displayScore / 2;
  const maxScore = maxStars * 2;

  const filledClass = COLOUR_CLASSES[colour];
  const emptyClass = "text-gray-300 dark:text-gray-500";

  const getScoreFromEvent = useCallback(
    (e: React.MouseEvent, starIndex: number): number => {
      const el = starRefs.current[starIndex];
      if (!el) return (starIndex + 1) * 2;
      const rect = el.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const isLeftHalf = x < rect.width / 2;
      return starIndex * 2 + (isLeftHalf ? 1 : 2);
    },
    []
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent, starIndex: number) => {
      if (readonly) return;
      setHoverScore(getScoreFromEvent(e, starIndex));
    },
    [readonly, getScoreFromEvent]
  );

  const handleClick = useCallback(
    (e: React.MouseEvent, starIndex: number) => {
      if (readonly || !onRate) return;
      const score = getScoreFromEvent(e, starIndex);
      if (score === rating) {
        onRate(0);
      } else {
        onRate(score);
      }
    },
    [readonly, onRate, getScoreFromEvent, rating]
  );

  const handleMouseLeave = useCallback(() => {
    if (!readonly) setHoverScore(null);
  }, [readonly]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (readonly || !onRate) return;
      if (e.key === "ArrowRight" || e.key === "ArrowUp") {
        e.preventDefault();
        const next = Math.min(rating + 1, maxScore);
        onRate(next);
      } else if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
        e.preventDefault();
        const prev = Math.max(rating - 1, 0);
        onRate(prev);
      } else if (e.key === "Delete" || e.key === "Backspace") {
        e.preventDefault();
        onRate(0);
      }
    },
    [readonly, onRate, rating, maxScore]
  );

  const getStarFill = (index: number): "full" | "half" | "empty" => {
    if (index < Math.floor(displayRating)) return "full";
    if (index < displayRating && displayRating % 1 >= 0.5) return "half";
    return "empty";
  };

  const titleText =
    label ??
    (rating > 0 ? `${rating}/${maxScore}` : readonly ? "Not rated" : "Rate this photo");

  return (
    <div className="flex items-center gap-1">
      <div
        className={`flex items-center gap-0.5 ${!readonly ? "cursor-pointer" : ""}`}
        onMouseLeave={handleMouseLeave}
        onKeyDown={handleKeyDown}
        role={readonly ? "img" : "slider"}
        aria-label={titleText}
        aria-valuenow={rating}
        aria-valuemin={0}
        aria-valuemax={maxScore}
        tabIndex={readonly ? -1 : 0}
        title={titleText}
      >
        {Array.from({ length: maxStars }).map((_, index) => {
          const fill = getStarFill(index);
          return (
            <div
              key={index}
              ref={(el) => {
                starRefs.current[index] = el;
              }}
              className="relative"
              onMouseMove={(e) => handleMouseMove(e, index)}
              onClick={(e) => handleClick(e, index)}
            >
              <svg
                className={`${SIZE_CLASSES[size]} ${emptyClass} transition-colors duration-100`}
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path d={STAR_PATH} />
              </svg>
              {fill !== "empty" && (
                <svg
                  className={`${SIZE_CLASSES[size]} ${filledClass} absolute top-0 left-0 transition-colors duration-100`}
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  style={
                    fill === "half" ? { clipPath: "inset(0 50% 0 0)" } : undefined
                  }
                >
                  <path d={STAR_PATH} />
                </svg>
              )}
            </div>
          );
        })}
      </div>
      {showLabel && (
        <span className="text-xs text-gray-500 dark:text-gray-400 ml-0.5">
          {rating > 0 ? `${rating}/${maxScore}` : readonly ? "" : "Rate"}
        </span>
      )}
    </div>
  );
}
