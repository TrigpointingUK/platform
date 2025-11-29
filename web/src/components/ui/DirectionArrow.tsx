interface DirectionArrowProps {
  bearing: number;
  size?: number;
  className?: string;
}

/**
 * Renders a directional arrow rotated to the specified bearing angle.
 * 0° = North (up), 90° = East (right), 180° = South (down), 270° = West (left)
 */
export default function DirectionArrow({ bearing, size = 16, className = "" }: DirectionArrowProps) {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ transform: `rotate(${bearing}deg)`, display: 'inline-block' }}
      className={className}
      aria-label={`Bearing: ${bearing.toFixed(0)}°`}
    >
      <path d="M12 5l0 14M12 5l-4 4M12 5l4 4" />
    </svg>
  );
}
