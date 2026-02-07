"use client";

/**
 * Mode Provider - Mu2 Cognitive OS
 * ================================
 *
 * Enhanced mode provider with Chameleon Engine integration.
 *
 * This provider:
 * 1. Manages UI mode state
 * 2. Connects to the Chameleon Orchestrator for adaptive switching
 * 3. Maintains backward compatibility with existing useMode hook
 * 4. Persists mode preference to localStorage
 * 5. Announces mode changes to screen readers (WCAG 2.1 AA)
 */

import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from "react";

// Extend mode type to include new modes
type Mode =
  | "standard"
  | "focus"
  | "high_contrast_focus"
  | "simplified"
  | "step_by_step"
  | "visual"
  | "gamified"
  | "exploration"
  | "intervention"
  | "dyslexic_friendly"
  | "adhd_friendly"
  | "low_vision";

// All available modes
const AVAILABLE_MODES: Mode[] = [
  "standard",
  "focus",
  "high_contrast_focus",
  "simplified",
  "step_by_step",
  "visual",
  "gamified",
  "exploration",
  "intervention",
  "dyslexic_friendly",
  "adhd_friendly",
  "low_vision",
];

interface ModeContextType {
  mode: Mode;
  setMode: (mode: Mode) => void;
  toggleMode: () => void;
  availableModes: Mode[];
  isAdaptive: boolean; // Whether adaptive switching is enabled
  setAdaptive: (enabled: boolean) => void; // Enable/disable auto-switching
}

// Type guard to validate Mode values
function isValidMode(value: unknown): value is Mode {
  return typeof value === "string" && AVAILABLE_MODES.includes(value as Mode);
}

const ModeContext = createContext<ModeContextType | undefined>(undefined);

const MODE_STORAGE_KEY = "mu2-mode";
const ADAPTIVE_MODE_KEY = "mu2-adaptive-enabled";

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<Mode>("standard");
  const [isAdaptive, setIsAdaptiveState] = useState(true); // Adaptive mode enabled by default
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize mode from localStorage on mount
  useEffect(() => {
    try {
      const savedMode = localStorage.getItem(MODE_STORAGE_KEY);
      const savedAdaptive = localStorage.getItem(ADAPTIVE_MODE_KEY);

      // Validate the saved value before using it
      if (savedMode && isValidMode(savedMode)) {
        setModeState(savedMode);
      } else if (savedMode) {
        // Invalid value in localStorage, remove it
        console.warn(`Invalid mode value in localStorage: ${savedMode}. Removing.`);
        localStorage.removeItem(MODE_STORAGE_KEY);
      }

      // Restore adaptive preference
      if (savedAdaptive !== null) {
        setIsAdaptiveState(savedAdaptive === "true");
      }
    } catch (error) {
      // Handle potential localStorage access errors (e.g., in incognito mode)
      console.error("Error accessing localStorage:", error);
    }
    setIsInitialized(true);
  }, []);

  // Apply mode to document and localStorage
  useEffect(() => {
    if (!isInitialized) return;

    // Set data-mode attribute
    document.documentElement.setAttribute("data-mode", mode);

    // Apply mode-specific CSS variables
    applyModeStyles(mode);

    // Safely save to localStorage
    try {
      localStorage.setItem(MODE_STORAGE_KEY, mode);
    } catch (error) {
      console.error("Error saving mode to localStorage:", error);
    }

    // Announce mode change to screen readers (WCAG 2.1 AA)
    const modeNames: Record<Mode, string> = {
      standard: "Standard",
      focus: "Focus",
      high_contrast_focus: "High Contrast Focus",
      simplified: "Simplified",
      step_by_step: "Step by Step",
      visual: "Visual",
      gamified: "Gamified",
      exploration: "3D Exploration",
      intervention: "Intervention",
      dyslexic_friendly: "Dyslexic Friendly",
      adhd_friendly: "ADHD Friendly",
      low_vision: "Low Vision",
    };

    const announcement = document.createElement("div");
    announcement.setAttribute("role", "status");
    announcement.setAttribute("aria-live", "polite");
    announcement.setAttribute("aria-atomic", "true");
    announcement.className = "sr-only";
    announcement.textContent = `Mode changed to ${modeNames[mode] || mode}`;
    document.body.appendChild(announcement);

    // Clean up announcement after it's read
    setTimeout(() => {
      if (announcement.parentNode) {
        document.body.removeChild(announcement);
      }
    }, 1000);
  }, [mode, isInitialized]);

  // Apply mode-specific CSS variables
  const applyModeStyles = useCallback((currentMode: Mode) => {
    const root = document.documentElement;

    // Reset base styles
    root.style.removeProperty("--font-scale");
    root.style.removeProperty("--line-height");

    switch (currentMode) {
      case "focus":
        root.style.setProperty("--font-scale", "1.125");
        root.style.setProperty("--line-height", "1.75");
        break;

      case "high_contrast_focus":
        root.style.setProperty("--font-scale", "1.25");
        root.style.setProperty("--line-height", "2.0");
        root.style.setProperty("--bg-primary", "#000000");
        root.style.setProperty("--text-primary", "#FFFFFF");
        root.style.setProperty("--border", "#FFFFFF");
        root.style.setProperty("--accent", "#FFFF00");
        break;

      case "simplified":
        root.style.setProperty("--font-scale", "1.0");
        root.style.setProperty("--line-height", "1.75");
        break;

      case "step_by_step":
        root.style.setProperty("--font-scale", "1.1");
        root.style.setProperty("--line-height", "1.6");
        break;

      case "dyslexic_friendly":
        root.style.setProperty("--font-scale", "1.15");
        root.style.setProperty("--line-height", "2.0");
        root.style.setProperty("--font-family", "OpenDyslexic, sans-serif");
        break;

      case "low_vision":
        root.style.setProperty("--font-scale", "1.5");
        root.style.setProperty("--line-height", "2.2");
        break;

      case "adhd_friendly":
        root.style.setProperty("--font-scale", "1.1");
        root.style.setProperty("--line-height", "1.8");
        break;

      default:
        // Standard mode - no overrides
        break;
    }
  }, []);

  const setMode = useCallback((newMode: Mode) => {
    // Validate before setting
    if (!isValidMode(newMode)) {
      throw new Error(
        `Invalid mode value: ${newMode}. Must be one of: ${AVAILABLE_MODES.join(", ")}`
      );
    }
    setModeState(newMode);
  }, []);

  const toggleMode = useCallback(() => {
    setModeState((prev) => {
      // Toggle between standard and focus for backward compatibility
      return prev === "standard" ? "focus" : "standard";
    });
  }, []);

  const setAdaptive = useCallback((enabled: boolean) => {
    setIsAdaptiveState(enabled);
    try {
      localStorage.setItem(ADAPTIVE_MODE_KEY, String(enabled));
    } catch (error) {
      console.error("Error saving adaptive preference:", error);
    }
  }, []);

  return (
    <ModeContext.Provider
      value={{
        mode,
        setMode,
        toggleMode,
        availableModes: AVAILABLE_MODES,
        isAdaptive,
        setAdaptive,
      }}
    >
      {children}
    </ModeContext.Provider>
  );
}

export function useMode() {
  const context = useContext(ModeContext);
  if (context === undefined) {
    throw new Error("useMode must be used within a ModeProvider");
  }
  return context;
}

// Export type for use in other components
export type { Mode };
