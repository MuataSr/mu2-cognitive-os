"use client";

import { useState, useRef, useEffect } from "react";
import { useMode } from "@/components/providers/mode-provider";

interface Citation {
  source_id: string;
  paragraph_id: string;
  relevance_score: number;
  text_snippet: string;
}

interface CitationTooltipProps {
  citation: Citation;
  onClick: () => void;
}

export function CitationTooltip({ citation, onClick }: CitationTooltipProps) {
  const { mode } = useMode();
  const [showTooltip, setShowTooltip] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => {
      setShowTooltip(true);
    }, 300);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setShowTooltip(false);
  };

  const handleClick = () => {
    onClick();
    setShowTooltip(false);
  };

  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Calculate relevance color
  const getRelevanceColor = (score: number) => {
    if (score >= 0.8) return "bg-green-500";
    if (score >= 0.6) return "bg-yellow-500";
    return "bg-orange-500";
  };

  return (
    <div className="relative inline-block">
      <button
        ref={buttonRef}
        onClick={handleClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onFocus={() => setShowTooltip(true)}
        onBlur={() => setShowTooltip(false)}
        className={`
          inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full
          transition-all duration-200
          ${mode === "focus"
            ? "bg-[color:var(--focus-accent)] text-black"
            : "bg-[color:var(--accent)]/20 text-[color:var(--accent)]"
          }
          hover:opacity-80
          focus:outline-none focus:ring-2 focus:ring-[color:var(--accent)]
          cursor-pointer
        `}
        aria-label={`View source: ${citation.text_snippet.slice(0, 50)}...`}
        aria-describedby={showTooltip ? "citation-tooltip" : undefined}
      >
        <span className="font-bold">[{citation.paragraph_id}]</span>
        <div
          className={`w-1.5 h-1.5 rounded-full ${getRelevanceColor(citation.relevance_score)}`}
          aria-hidden="true"
        />
      </button>

      {/* Tooltip */}
      {showTooltip && (
        <div
          id="citation-tooltip"
          role="tooltip"
          className={`
            absolute bottom-full left-1/2 -translate-x-1/2 mb-2
            w-64 p-3 rounded-lg shadow-lg z-50
            ${mode === "focus"
              ? "bg-black border border-white"
              : "bg-[color:var(--bg-primary)] border border-[color:var(--border)]"
            }
            animate-fadeIn
          `}
          style={{
            animation: "fadeIn 0.2s ease-out"
          }}
        >
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[color:var(--accent)]">
                Source {citation.paragraph_id}
              </span>
              <span className="text-xs text-[color:var(--text-secondary)]">
                {Math.round(citation.relevance_score * 100)}% match
              </span>
            </div>
            <p className="text-sm text-[color:var(--text-secondary)] line-clamp-3">
              {citation.text_snippet}
            </p>
            <p className="text-xs text-[color:var(--accent)] font-medium">
              Click to view in textbook →
            </p>
          </div>

          {/* Tooltip arrow */}
          <div
            className={`
              absolute top-full left-1/2 -translate-x-1/2 -mt-px
              w-2 h-2 rotate-45
              ${mode === "focus"
                ? "bg-black border-r border-b border-white"
                : "bg-[color:var(--bg-primary)] border-r border-b border-[color:var(--border)]"
              }
            `}
            aria-hidden="true"
          />
        </div>
      )}

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateX(-50%) translateY(4px);
          }
          to {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
          }
        }

        .line-clamp-3 {
          display: -webkit-box;
          -webkit-line-clamp: 3;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        /* Respect prefers-reduced-motion */
        @media (prefers-reduced-motion: reduce) {
          .animate-fadeIn {
            animation: none;
          }
        }
      `}</style>
    </div>
  );
}
