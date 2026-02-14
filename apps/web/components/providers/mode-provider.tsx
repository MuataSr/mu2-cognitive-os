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

import React, { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";

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
  // Behavioral state
  backendSuggestedMode: Mode | null;
  behavioralUrgency: string;
}

// Type guard to validate Mode values
function isValidMode(value: unknown): value is Mode {
  return typeof value === "string" && AVAILABLE_MODES.includes(value as Mode);
}

const ModeContext = createContext<ModeContextType | undefined>(undefined);

const MODE_STORAGE_KEY = "mu2-mode";
const ADAPTIVE_MODE_KEY = "mu2-adaptive-enabled";

// API base URL for behavioral status
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<Mode>("standard");
  const [isAdaptive, setIsAdaptiveState] = useState(true); // Adaptive mode enabled by default
  const [isInitialized, setIsInitialized] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  // Behavioral integration state
  const [userId] = useState("current-user"); // TODO: Get from auth
  const [backendSuggestedMode, setBackendSuggestedMode] = useState<Mode | null>(null);
  const [behavioralUrgency, setBehavioralUrgency] = useState<string>("none");
  const pollIntervalRef = React.useRef<NodeJS.Timeout | null>(null);

  // Initialize mode from localStorage on mount and check reduced motion preference
  useEffect(() => {
    try {
      const savedMode = localStorage.getItem(MODE_STORAGE_KEY);
      const savedAdaptive = localStorage.getItem(ADAPTIVE_MODE_KEY);

      // Check for reduced motion preference
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
      setPrefersReducedMotion(mediaQuery.matches);

      // Listen for changes to reduced motion preference
      const handleChange = (e: MediaQueryListEvent) => {
        setPrefersReducedMotion(e.matches);
      };
      mediaQuery.addEventListener('change', handleChange);

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

      // Cleanup listener on unmount
      return () => {
        mediaQuery.removeEventListener('change', handleChange);
      };
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
  }, [mode, isInitialized, prefersReducedMotion]);

  // Behavioral API polling - Auto-switch mode based on backend suggestions
  useEffect(() => {
    // Only poll if:
    // 1. Component is initialized
    // 2. Adaptive mode is enabled
    // 3. We have a userId
    if (!isInitialized || !isAdaptive || !userId) {
      return;
    }

    /**
     * Fetch behavioral status from backend and auto-switch if needed
     */
    const fetchBehavioralStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/v1/behavioral/status/${userId}`);

        if (!response.ok) {
          console.warn(`[Behavioral] Failed to fetch status: ${response.status}`);
          return;
        }

        const data = await response.json();

        // Update urgency for UI display
        if (data.urgency) {
          setBehavioralUrgency(data.urgency);
        }

        // Check if backend suggests a different mode
        const suggested = data.suggested_mode;
        if (suggested && isValidMode(suggested) && suggested !== mode) {
          console.log(`[Behavioral] Auto-switching to ${suggested} (urgency: ${data.urgency})`);

          // Auto-switch to suggested mode
          setModeState(suggested);

          // Enhanced ARIA announcement for automatic mode changes
          const announcement = document.createElement("div");
          announcement.setAttribute("role", "status");
          announcement.setAttribute("aria-live", "polite");
          announcement.setAttribute("aria-atomic", "true");
          announcement.className = "sr-only";

          const urgencyMessages: Record<string, string> = {
            none: "based on your learning patterns",
            attention: "to help you focus",
            intervention: "to provide additional support"
          };

          announcement.textContent = `Mode automatically changed to ${suggested} ${urgencyMessages[data.urgency] || urgencyMessages.none}`;
          document.body.appendChild(announcement);

          setTimeout(() => {
            if (announcement.parentNode) {
              document.body.removeChild(announcement);
            }
          }, 1000);
        }

        // Store backend suggestion for reference
        setBackendSuggestedMode(suggested);

      } catch (error) {
        console.error("[Behavioral] Error fetching status:", error);
        // Don't switch mode on error - keep current mode
      }
    };

    // Initial fetch
    fetchBehavioralStatus();

    // Set up polling interval (every 10 seconds)
    pollIntervalRef.current = setInterval(() => {
      fetchBehavioralStatus();
    }, 10000);

    // Cleanup on unmount or when adaptive mode changes
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [isInitialized, isAdaptive, userId, mode]);

  // Apply mode-specific CSS variables
  const applyModeStyles = useCallback((currentMode: Mode) => {
    const root = document.documentElement;

    // Reset base styles
    root.style.removeProperty("--font-scale");
    root.style.removeProperty("--line-height");

    // Force snap transition if user prefers reduced motion
    if (prefersReducedMotion) {
      root.style.setProperty("--transition-style", "snap");
      document.body.classList.add("force-reduced-motion");
    } else {
      root.style.setProperty("--transition-style", "morph");
      document.body.classList.remove("force-reduced-motion");
    }

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
  }, [prefersReducedMotion]);

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
        backendSuggestedMode,
        behavioralUrgency,
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
