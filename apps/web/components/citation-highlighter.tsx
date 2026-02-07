"use client";

/**
 * Citation Highlighter - Mu2 Cognitive OS
 * ======================================
 *
 * Displays AI response citations and highlights corresponding sections
 * in the textbook viewer.
 *
 * Features:
 * - Clickable citation links
 * - Automatic paragraph highlighting
 * - Source validation
 * - ARIA live announcements for accessibility
 */

import { useState, useCallback } from "react";
import { BookOpen, AlertTriangle, CheckCircle } from "lucide-react";

export interface Citation {
  source_id: string;
  chapter?: string;
  paragraph?: number;
  confidence: number;
  excerpt?: string;
}

export interface CitationLockData {
  response: string;
  citations: Citation[];
  validated: boolean;
  disclaimer: string;
  timestamp: string;
}

interface CitationHighlighterProps {
  citations: Citation[];
  validated: boolean;
  disclaimer?: string;
  onCitationClick?: (sourceId: string, paragraph?: number) => void;
  className?: string;
}

export function CitationHighlighter({
  citations,
  validated,
  disclaimer = "AI generated. Always verify with source text.",
  onCitationClick,
  className = "",
}: CitationHighlighterProps) {
  const [highlightedId, setHighlightedId] = useState<string | null>(null);

  const handleCitationClick = useCallback(
    (citation: Citation, index: number) => {
      const sourceId = citation.source_id;
      setHighlightedId(sourceId);

      // Announce to screen readers
      const announcement = document.createElement("div");
      announcement.setAttribute("role", "status");
      announcement.setAttribute("aria-live", "polite");
      announcement.setAttribute("aria-atomic", "true");
      announcement.className = "sr-only";
      announcement.textContent = `Highlighting citation ${index + 1}: ${sourceId}`;
      document.body.appendChild(announcement);

      setTimeout(() => {
        document.body.removeChild(announcement);
      }, 1000);

      // Trigger highlight in textbook viewer
      if (onCitationClick) {
        onCitationClick(sourceId, citation.paragraph);
      }

      // Clear highlight after animation
      setTimeout(() => {
        setHighlightedId(null);
      }, 3000);
    },
    [onCitationClick]
  );

  const formatCitationLabel = (citation: Citation, index: number) => {
    const parts = [`[${index + 1}]`];

    if (citation.chapter) {
      // Format chapter nicely
      const chapterLabel = citation.chapter.replace(/[_\-]/g, " ");
      parts.push(`Ch. ${chapterLabel}`);
    }

    if (citation.paragraph) {
      parts.push(`§${citation.paragraph}`);
    }

    return parts.join(" ");
  };

  const getValidationIcon = () => {
    if (!validated) {
      return <AlertTriangle className="w-4 h-4 text-yellow-500" aria-hidden="true" />;
    }
    return <CheckCircle className="w-4 h-4 text-green-500" aria-hidden="true" />;
  };

  if (citations.length === 0) {
    return (
      <div className={`citation-warning ${className}`} role="alert">
        <AlertTriangle className="w-4 h-4 text-yellow-500" aria-hidden="true" />
        <span className="text-sm text-yellow-300">
          No citations provided. Response may not be grounded in source material.
        </span>
      </div>
    );
  }

  return (
    <div className={`citation-highlighter ${className}`}>
      {/* Validation Status */}
      <div className="flex items-center gap-2 mb-2" role="status" aria-live="polite">
        {getValidationIcon()}
        <span className="text-sm text-gray-400">
          {validated ? "Verified with sources" : "Citations pending verification"}
        </span>
        <span className="text-gray-600">•</span>
        <span className="text-sm text-gray-400">{citations.length} source{citations.length !== 1 ? "s" : ""} cited</span>
      </div>

      {/* Citation List */}
      <div className="flex flex-wrap gap-2" role="list" aria-label="Citations">
        {citations.map((citation, index) => (
          <button
            key={citation.source_id}
            onClick={() => handleCitationClick(citation, index)}
            className={`
              citation-link inline-flex items-center gap-2 px-3 py-1.5 rounded
              text-sm font-medium transition-all duration-200
              ${highlightedId === citation.source_id
                ? "bg-accent text-black scale-105"
                : "bg-gray-800 text-gray-300 hover:bg-gray-700"
              }
              focus-visible:outline-2 focus-visible:outline-accent
            `}
            role="listitem"
            aria-label={`Citation ${index + 1}: ${formatCitationLabel(citation, index)}`}
            aria-pressed={highlightedId === citation.source_id}
          >
            <BookOpen className="w-3.5 h-3.5" aria-hidden="true" />
            <span>{formatCitationLabel(citation, index)}</span>
          </button>
        ))}
      </div>

      {/* Disclaimer */}
      <p className="mt-3 text-xs text-gray-500 italic" role="note">
        {disclaimer}
      </p>
    </div>
  );
}

/**
 * Hook to manage citation highlighting state across components
 */
export function useCitationHighlight() {
  const [activeCitation, setActiveCitation] = useState<string | null>(null);

  const highlightCitation = useCallback((sourceId: string) => {
    setActiveCitation(sourceId);

    // Find and highlight the paragraph in textbook
    const paragraph = document.querySelector(`[data-source-id="${sourceId}"]`);
    if (paragraph) {
      paragraph.scrollIntoView({ behavior: "smooth", block: "center" });
      paragraph.classList.add("highlighted-paragraph");

      setTimeout(() => {
        paragraph.classList.remove("highlighted-paragraph");
        setActiveCitation(null);
      }, 3000);
    }
  }, []);

  const clearHighlight = useCallback(() => {
    setActiveCitation(null);
    document.querySelectorAll(".highlighted-paragraph").forEach((el) => {
      el.classList.remove("highlighted-paragraph");
    });
  }, []);

  return {
    activeCitation,
    highlightCitation,
    clearHighlight,
  };
}

/**
 * Component to display inline citations within AI responses
 */
interface InlineCitationProps {
  sourceId: string;
  index: number;
  onClick?: () => void;
}

export function InlineCitation({ sourceId, index, onClick }: InlineCitationProps) {
  return (
    <sup>
      <button
        onClick={onClick}
        className="inline-citation-link text-accent hover:text-white underline text-xs font-bold ml-1"
        aria-label={`View source ${index + 1}`}
      >
        [{index + 1}]
      </button>
    </sup>
  );
}

/**
 * Component to display citation footer on AI messages
 */
interface CitationFooterProps {
  citations: Citation[];
  validated: boolean;
  onCitationClick?: (citation: Citation, index: number) => void;
}

export function CitationFooter({ citations, validated, onCitationClick }: CitationFooterProps) {
  if (citations.length === 0) {
    return (
      <footer className="mt-2 pt-2 border-t border-gray-800">
        <p className="text-xs text-yellow-500 flex items-center gap-2">
          <AlertTriangle className="w-3 h-3" aria-hidden="true" />
          <span>No sources cited. Please verify with textbook.</span>
        </p>
      </footer>
    );
  }

  return (
    <footer className="mt-2 pt-2 border-t border-gray-800">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-gray-500">Sources:</span>
        {citations.map((citation, index) => (
          <button
            key={citation.source_id}
            onClick={() => onCitationClick?.(citation, index)}
            className="text-xs text-accent hover:text-white underline"
            aria-label={`View source ${index + 1}`}
          >
            [{index + 1}]
          </button>
        ))}
        {!validated && (
          <span className="text-xs text-yellow-500 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" aria-hidden="true" />
            <span>Unverified</span>
          </span>
        )}
      </div>
    </footer>
  );
}

export default CitationHighlighter;
