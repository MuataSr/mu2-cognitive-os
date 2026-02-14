"use client";

import { useEffect, useState } from "react";
import { getRecentEvents, formatLastActive, maskStudentId, type LiveFeedEvent } from "@/lib/api/mastery";

/**
 * LiveFeedSidebar - Vertical timeline of recent learning events
 * Kut Different Branding
 *
 * Displays the most recent learning events across all scholars.
 * Shows robot icon for agent actions and user icon for scholar actions.
 * Auto-refreshes every 5 seconds.
 */

interface LiveFeedSidebarProps {
  refreshInterval?: number; // Default 5000ms (5 seconds)
  maxVisible?: number; // Default 10 visible events
}

export function LiveFeedSidebar({
  refreshInterval = 5000,
  maxVisible = 10,
}: LiveFeedSidebarProps) {
  const [events, setEvents] = useState<LiveFeedEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchEvents = async () => {
    try {
      setError(null);
      const data = await getRecentEvents(20);
      setEvents(data);
      setLastUpdate(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load events");
      console.error("Error fetching events:", err);
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchEvents();
  }, []);

  // Poll for updates
  useEffect(() => {
    const interval = setInterval(fetchEvents, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  const visibleEvents = events.slice(0, maxVisible);
  const hiddenCount = Math.max(0, events.length - maxVisible);

  return (
    <div className="kd-card p-4 h-fit sticky top-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="kd-title text-lg">Live Feed</h2>
        <div className="flex items-center gap-2">
          <div
            className={`kd-pulse-dot ${loading ? "bg-yellow-500 animate-pulse" : "kd-pulse-active"}`}
            aria-label={loading ? "Loading" : "Live"}
          />
          <span className="text-xs text-[color:var(--kd-text-muted)]">
            {lastUpdate.toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500 rounded-kd p-3 mb-4">
          <p className="text-red-500 text-sm">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && events.length === 0 && (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-[color:var(--kd-red)]"></div>
          <p className="mt-2 text-sm text-[color:var(--kd-text-muted)]">Loading events...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && events.length === 0 && (
        <div className="text-center py-8">
          <p className="text-[color:var(--kd-text-muted)]">No recent events</p>
        </div>
      )}

      {/* Events List */}
      <div className="space-y-3">
        {visibleEvents.map((event, index) => (
          <div
            key={`${event.user_id}-${event.timestamp}-${index}`}
            className="flex items-start gap-3 p-2 rounded-kd bg-[color:var(--kd-black)] hover:bg-[color:var(--kd-slate)] transition-colors"
          >
            {/* Icon */}
            <div className="flex-shrink-0 mt-0.5">
              {event.event_type === "AGENT_ACTION" ? (
                // Robot icon for agent actions
                <svg
                  className="w-4 h-4 text-[color:var(--kd-red)]"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  aria-label="Agent action"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 2a1 1 0 00-1 1v1a1 1 0 002 0V3a1 1 0 00-1-1zM4 4h3a3 3 0 006 0h3a2 2 0 012 2v9a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2zm2.5 7a1.5 1.5 0 100-3 1.5 1.5 0 000 3zm2.45 4a2.5 2.5 0 10-4.9 0h4.9zM12 9a1 1 0 100 2h3a1 1 0 100-2h-3zm-1 4a1 1 0 011-1h2a1 1 0 110 2h-2a1 1 0 01-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                // User/hand icon for scholar actions
                <svg
                  className="w-4 h-4 text-blue-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  aria-label="Scholar action"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {event.source_text || "Learning activity"}
              </p>
              <p className="text-xs text-[color:var(--kd-text-muted)]">
                {/* Mask user ID for FERPA compliance */}
                {maskStudentId(event.user_id, "mentor")} • {formatLastActive(event.timestamp)}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Hidden Count */}
      {hiddenCount > 0 && (
        <div className="mt-4 text-center">
          <p className="text-sm text-[color:var(--kd-text-muted)]">
            +{hiddenCount} more events
          </p>
        </div>
      )}
    </div>
  );
}
