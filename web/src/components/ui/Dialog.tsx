import { ReactNode, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cx } from "../../lib/utils";

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}

interface DialogContentProps {
  children: ReactNode;
  className?: string;
  title?: string;
  description?: string;
}

interface DialogHeaderProps {
  children: ReactNode;
  className?: string;
}

interface DialogTitleProps {
  children: ReactNode;
  className?: string;
}

interface DialogDescriptionProps {
  children: ReactNode;
  className?: string;
}

interface DialogFooterProps {
  children: ReactNode;
  className?: string;
}

interface DialogCloseProps {
  children: ReactNode;
  className?: string;
  asChild?: boolean;
}

// Context for dialog state
import { createContext, useContext } from "react";

interface DialogContextValue {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const DialogContext = createContext<DialogContextValue | null>(null);

function useDialogContext() {
  const context = useContext(DialogContext);
  if (!context) {
    throw new Error("Dialog components must be used within a Dialog");
  }
  return context;
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  return (
    <DialogContext.Provider value={{ open, onOpenChange }}>
      {children}
    </DialogContext.Provider>
  );
}

export function DialogTrigger({
  children,
  asChild,
}: {
  children: ReactNode;
  asChild?: boolean;
}) {
  const { onOpenChange } = useDialogContext();

  if (asChild) {
    return <span onClick={() => onOpenChange(true)}>{children}</span>;
  }

  return (
    <button type="button" onClick={() => onOpenChange(true)}>
      {children}
    </button>
  );
}

export function DialogContent({
  children,
  className,
  title,
  description,
}: DialogContentProps) {
  const { open, onOpenChange } = useDialogContext();
  const dialogRef = useRef<HTMLDivElement>(null);

  const handleEscape = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onOpenChange(false);
      }
    },
    [onOpenChange]
  );

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        onOpenChange(false);
      }
    },
    [onOpenChange]
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";

      // Focus the dialog
      dialogRef.current?.focus();

      return () => {
        document.removeEventListener("keydown", handleEscape);
        document.body.style.overflow = "";
      };
    }
  }, [open, handleEscape]);

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={handleBackdropClick}
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 dark:bg-black/70" />

      {/* Dialog */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? "dialog-title" : undefined}
        aria-describedby={description ? "dialog-description" : undefined}
        tabIndex={-1}
        className={cx(
          "relative z-50 w-full max-w-lg max-h-[90vh] overflow-y-auto",
          "bg-white dark:bg-gray-800 rounded-lg shadow-xl",
          "p-6 mx-4",
          "animate-in fade-in-0 zoom-in-95",
          className
        )}
      >
        {/* Close button */}
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          className="absolute top-4 right-4 p-1 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-trig-green-500"
          aria-label="Close"
        >
          <X className="h-5 w-5" />
        </button>

        {children}
      </div>
    </div>,
    document.body
  );
}

export function DialogHeader({ children, className }: DialogHeaderProps) {
  return (
    <div className={cx("mb-4 pr-8", className)}>
      {children}
    </div>
  );
}

export function DialogTitle({ children, className }: DialogTitleProps) {
  return (
    <h2
      id="dialog-title"
      className={cx(
        "text-xl font-semibold text-gray-900 dark:text-gray-100",
        className
      )}
    >
      {children}
    </h2>
  );
}

export function DialogDescription({
  children,
  className,
}: DialogDescriptionProps) {
  return (
    <p
      id="dialog-description"
      className={cx("text-sm text-gray-600 dark:text-gray-400 mt-1", className)}
    >
      {children}
    </p>
  );
}

export function DialogFooter({ children, className }: DialogFooterProps) {
  return (
    <div
      className={cx(
        "mt-6 flex flex-col-reverse sm:flex-row sm:justify-end sm:gap-3 gap-2",
        className
      )}
    >
      {children}
    </div>
  );
}

export function DialogClose({ children, className, asChild }: DialogCloseProps) {
  const { onOpenChange } = useDialogContext();

  if (asChild) {
    return (
      <span onClick={() => onOpenChange(false)} className={className}>
        {children}
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onOpenChange(false)}
      className={className}
    >
      {children}
    </button>
  );
}

