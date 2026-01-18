import { ReactNode } from "react";

interface ButtonProps {
  children: ReactNode;
  onClick?: (e?: React.MouseEvent<HTMLButtonElement>) => void;
  variant?: "primary" | "secondary" | "ghost" | "outline" | "danger";
  size?: "sm" | "md" | "lg";
  type?: "button" | "submit" | "reset";
  disabled?: boolean;
  className?: string;
}

export default function Button({
  children,
  onClick,
  variant = "primary",
  size = "md",
  type = "button",
  disabled = false,
  className = "",
}: ButtonProps) {
  const baseClasses = "rounded-md font-medium transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2";
  
  const sizeClasses = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2",
    lg: "px-6 py-3 text-lg",
  };
  
  const variantClasses = {
    primary: "bg-trig-green-600 text-white hover:bg-trig-green-500 focus:ring-trig-green-500 disabled:bg-gray-300 dark:disabled:bg-gray-600",
    secondary: "bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-600 focus:ring-gray-500 disabled:bg-gray-100 dark:disabled:bg-gray-800",
    ghost: "bg-transparent text-trig-green-600 dark:text-trig-green-400 hover:bg-trig-green-50 dark:hover:bg-trig-green-900/30 focus:ring-trig-green-500",
    outline: "border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 focus:ring-gray-500 disabled:bg-gray-50 dark:disabled:bg-gray-800 disabled:text-gray-400",
    danger: "bg-red-800 text-white hover:bg-red-700 focus:ring-red-500 disabled:bg-gray-300 dark:disabled:bg-gray-600",
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

