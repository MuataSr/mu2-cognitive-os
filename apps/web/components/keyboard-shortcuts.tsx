"use client";

import { useState, useEffect } from "react";
import { useMode } from "./providers/mode-provider";

interface KeyboardShortcutsProps {
  onShow: boolean;
}

export function KeyboardShortcuts({ onShow }: KeyboardShortcutsProps) {
  const { mode } = useMode();
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Show shortcuts on first visit
    const hasSeenShortcuts = localStorage.getItem("mu2-seen-shortcuts");
    if (!hasSeenShortcuts) {
      setIsVisible(true);
      localStorage.setItem("mu2-seen-shortcuts", "true");
    }
  }, []);

  useEffect(() => {
    if (onShow) {
      setIsVisible(true);
    }
  }, [onShow]);

  if (!isVisible) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={() => setIsVisible(false)}
      role="dialog"
      aria-modal="true"
      aria-labelledby="shortcuts-title"
    >
      <div
        className={`
          max-w-md w-full p-6 rounded-lg shadow-xl
          ${mode === "focus" ? "bg-black border border-white" : "bg-[color:var(--bg-primary)] border border-[color:var(--border)]"}
        `}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 id="shortcuts-title" className="text-xl font-semibold">
            Keyboard Shortcuts
          </h2>
          <button
            onClick={() => setIsVisible(false)}
            className="p-2 hover:bg-[color:var(--border)] rounded focus:outline-none focus:ring-2 focus:ring-[color:var(--accent)]"
            aria-label="Close keyboard shortcuts"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[color:var(--text-secondary)]">Switch panes</span>
            <kbd
              className={`
                px-2 py-1 text-sm rounded
                ${mode === "focus" ? "bg-white text-black" : "bg-[color:var(--border)]"}
              `}
            >
              Ctrl + Tab
            </kbd>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[color:var(--text-secondary)]">Focus on chat input</span>
            <kbd
              className={`
                px-2 py-1 text-sm rounded
                ${mode === "focus" ? "bg-white text-black" : "bg-[color:var(--border)]"}
              `}
            >
              /
            </kbd>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[color:var(--text-secondary)]">Scroll to top</span>
            <kbd
              className={`
                px-2 py-1 text-sm rounded
                ${mode === "focus" ? "bg-white text-black" : "bg-[color:var(--border)]"}
              `}
            >
              Home
            </kbd>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[color:var(--text-secondary)]">Scroll to bottom</span>
            <kbd
              className={`
                px-2 py-1 text-sm rounded
                ${mode === "focus" ? "bg-white text-black" : "bg-[color:var(--border)]"}
              `}
            >
              End
            </kbd>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[color:var(--text-secondary)]">Navigate citations</span>
            <kbd
              className={`
                px-2 py-1 text-sm rounded
                ${mode === "focus" ? "bg-white text-black" : "bg-[color:var(--border)]"}
              `}
            >
              Tab
            </kbd>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[color:var(--text-secondary)]">Show shortcuts</span>
            <kbd
              className={`
                px-2 py-1 text-sm rounded
                ${mode === "focus" ? "bg-white text-black" : "bg-[color:var(--border)]"}
              `}
            >
              ?
            </kbd>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-[color:var(--border)]">
          <p className="text-sm text-[color:var(--text-secondary)]">
            Tip: Click on any citation [para-X] in the AI response to jump to that paragraph in the textbook.
          </p>
        </div>
      </div>
    </div>
  );
}

export function KeyboardShortcutsButton() {
  const [showShortcuts, setShowShortcuts] = useState(false);

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === "?" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        setShowShortcuts(true);
      }
    };

    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, []);

  return (
    <>
      <button
        onClick={() => setShowShortcuts(true)}
        className="fixed bottom-6 right-6 w-12 h-12 rounded-full bg-[color:var(--accent)] text-[color:var(--bg-primary)] flex items-center justify-center shadow-lg hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[color:var(--accent)] z-40"
        aria-label="Show keyboard shortcuts"
        title="Keyboard shortcuts (Ctrl+?)"
      >
        ?
      </button>
      <KeyboardShortcuts onShow={showShortcuts} />
    </>
  );
}
