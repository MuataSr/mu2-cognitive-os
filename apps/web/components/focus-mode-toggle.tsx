"use client";

import { useMode } from "./providers/mode-provider";
import { Sun, Moon } from "lucide-react";

/**
 * Focus Mode Toggle Component - Kut Different Branding
 *
 * WCAG 2.1 AA Compliance:
 * - aria-live="polite" announces mode changes to screen readers
 * - aria-pressed indicates button state
 * - aria-label provides accessible name
 * - Full keyboard navigation support
 * - High contrast colors in both modes
 */
export function FocusModeToggle() {
  const { mode, toggleMode } = useMode();
  const isFocus = mode === "focus";

  return (
    <button
      onClick={toggleMode}
      aria-pressed={isFocus}
      aria-label={`Switch to ${isFocus ? "Standard" : "Focus"} mode`}
      className="kd-card fixed top-4 right-4 p-3 hover:border-[color:var(--kd-red)] focus:outline-none focus:ring-2 focus:ring-[color:var(--kd-red)] transition-all z-50"
      aria-live="polite"
      aria-atomic="true"
    >
      <span className="sr-only">
        {isFocus ? "Focus mode enabled" : "Standard mode enabled"}
      </span>
      {isFocus ? (
        <Sun className="w-5 h-5 text-[color:var(--focus-accent)]" aria-hidden="true" />
      ) : (
        <Moon className="w-5 h-5 text-[color:var(--kd-red)]" aria-hidden="true" />
      )}
    </button>
  );
}
