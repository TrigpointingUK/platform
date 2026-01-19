import { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}

export default function Card({ 
  children, 
  className = "", 
  onClick,
  onMouseEnter,
  onMouseLeave 
}: CardProps) {
  return (
    <div 
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-md dark:shadow-gray-900/50 p-4 transition-colors duration-200 ${className}`}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {children}
    </div>
  );
}

