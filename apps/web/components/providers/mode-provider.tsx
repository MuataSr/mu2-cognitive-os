"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";

type Mode = "standard" | "focus";

interface ModeContextType {
  mode: Mode;
  setMode: (mode: Mode) => void;
  toggleMode: () => void;
}

const ModeContext = createContext<ModeContextType | undefined>(undefined);

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<Mode>("standard");
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize mode from localStorage on mount
  useEffect(() => {
    const savedMode = localStorage.getItem("mu2-mode") as Mode | null;
    if (savedMode === "focus" || savedMode === "standard") {
      setModeState(savedMode);
    }
    setIsInitialized(true);
  }, []);

  // Apply mode to document and localStorage
  useEffect(() => {
    if (!isInitialized) return;

    document.documentElement.setAttribute("data-mode", mode);
    localStorage.setItem("mu2-mode", mode);

    // Announce mode change to screen readers (WCAG 2.1 AA)
    const announcement = document.createElement("div");
    announcement.setAttribute("role", "status");
    announcement.setAttribute("aria-live", "polite");
    announcement.setAttribute("aria-atomic", "true");
    announcement.className = "sr-only";
    announcement.textContent = `Mode changed to ${mode}`;
    document.body.appendChild(announcement);

    // Clean up announcement after it's read
    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  }, [mode, isInitialized]);

  const setMode = (newMode: Mode) => {
    setModeState(newMode);
  };

  const toggleMode = () => {
    setModeState((prev) => (prev === "standard" ? "focus" : "standard"));
  };

  return (
    <ModeContext.Provider value={{ mode, setMode, toggleMode }}>
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
