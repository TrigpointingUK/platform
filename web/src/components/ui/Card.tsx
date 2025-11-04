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
      className={`bg-white rounded-lg shadow-md p-4 ${className}`}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {children}
    </div>
  );
}

