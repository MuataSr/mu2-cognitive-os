"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useMode } from "@/components/providers/mode-provider";
import { TextbookViewer } from "./textbook-viewer";
import { ChatInterface } from "./chat-interface";

interface SplitBookLayoutProps {
  chapterId?: string;
}

export function SplitBookLayout({ chapterId = "photosynthesis-101" }: SplitBookLayoutProps) {
  const { mode } = useMode();
  const [activePane, setActivePane] = useState<"left" | "right">("left");
  const [highlightedParagraph, setHighlightedParagraph] = useState<string | null>(null);
  const leftPaneRef = useRef<HTMLDivElement>(null);
  const rightPaneRef = useRef<HTMLDivElement>(null);

  // Handle citation clicks - scroll to paragraph and highlight
  const handleCitationClick = useCallback((paragraphId: string) => {
    setHighlightedParagraph(paragraphId);
    setActivePane("left");

    // Scroll to the paragraph
    const element = document.getElementById(`para-${paragraphId}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });

      // Focus on the left pane for accessibility
      leftPaneRef.current?.focus();

      // Remove highlight after animation
      setTimeout(() => {
        setHighlightedParagraph(null);
      }, 2000);
    }
  }, []);

  // Keyboard navigation between panes
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + Tab to switch panes
      if ((e.ctrlKey || e.metaKey) && e.key === "Tab") {
        e.preventDefault();
        setActivePane((prev) => (prev === "left" ? "right" : "left"));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Focus management
  useEffect(() => {
    if (activePane === "left") {
      leftPaneRef.current?.focus();
    } else {
      rightPaneRef.current?.focus();
    }
  }, [activePane]);

  return (
    <div className="flex h-screen">
      {/* Left Pane - Source of Truth (Textbook) */}
      <div
        ref={leftPaneRef}
        className="w-1/2 border-r border-[color:var(--border)] overflow-y-auto"
        tabIndex={0}
        role="region"
        aria-label="Textbook content"
        aria-live="polite"
        onFocus={() => setActivePane("left")}
      >
        <TextbookViewer
          chapterId={chapterId}
          highlightedParagraph={highlightedParagraph}
        />
      </div>

      {/* Right Pane - AI Co-Pilot */}
      <div
        ref={rightPaneRef}
        className="w-1/2 overflow-y-auto"
        tabIndex={0}
        role="region"
        aria-label="AI assistant"
        aria-live="polite"
        onFocus={() => setActivePane("right")}
      >
        <ChatInterface onCitationClick={handleCitationClick} />
      </div>

      {/* Screen reader announcement for pane switching */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        Active pane: {activePane === "left" ? "Textbook content" : "AI assistant"}
      </div>
    </div>
  );
}
