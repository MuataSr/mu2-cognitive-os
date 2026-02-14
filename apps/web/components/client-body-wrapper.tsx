"use client";

import { ErrorBoundary } from "@/components/error-boundary";
import { FocusModeToggle } from "@/components/focus-mode-toggle";
import { KeyboardShortcutsButton } from "@/components/keyboard-shortcuts";

interface ClientBodyProps {
  children: React.ReactNode;
}

/**
 * ClientBodyWrapper - Client component wrapper for root layout
 *
 * Wraps the application content with error boundaries and other
 * client-only functionality.
 */
export function ClientBodyWrapper({ children }: ClientBodyProps) {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        // Log to console in development
        if (process.env.NODE_ENV === "development") {
          console.error("Error Boundary caught:", error, errorInfo);
        }
        // In production, send to error tracking service
        // Example: sendToSentry(error, errorInfo);
      }}
    >
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <FocusModeToggle />
      <main id="main-content">{children}</main>
      <KeyboardShortcutsButton />
    </ErrorBoundary>
  );
}
