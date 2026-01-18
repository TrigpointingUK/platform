interface BadgeProps {
  children: React.ReactNode;
  variant?: "good" | "damaged" | "missing" | "unknown" | "default";
  className?: string;
}

export default function Badge({ children, variant = "default", className = "" }: BadgeProps) {
  const variantClasses = {
    good: "bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300",
    damaged: "bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-300",
    missing: "bg-red-100 dark:bg-red-900/50 text-red-800 dark:text-red-300",
    unknown: "bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300",
    default: "bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300",
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variantClasses[variant]} ${className}`}>
      {children}
    </span>
  );
}

