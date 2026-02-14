"use client";

/**
 * Behavioral Status Indicator - Mu2 Cognitive OS
 * =====================================
 *
 * Displays real-time behavioral status from backend:
 * - Current/suggested mode
 * - Frustration level
 * - Engagement status
 *
 * FERPA Compliance:
 * - All data stays local
 * - No PII in status signals
 */

import { useState, useEffect } from "react";
import { Clock } from "lucide-react";

// API base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Behavioral signal types
interface FrustrationLevel {
  none: "none";
  attention: "attention";
  intervention: "intervention";
}

interface BehavioralStatus {
  user_id: string;
  is_frustrated: boolean;
  is_engaged: boolean;
  is_struggling: boolean;
  consecutive_errors: number;
  time_on_task_seconds: number;
  suggested_mode: string | null;
  urgency: FrustrationLevel;
  confidence: number;
  last_activity_seconds_ago: number;
  reasoning: string[];
}

interface BehavioralStatusResponse {
  status: "success" | "error";
  user_id: string;
  suggested_mode: string | null;
  urgency: FrustrationLevel;
  confidence: number;
  reasoning?: string;
}

/**
 * Hook for displaying and managing behavioral status
 *
 * @param userId - User identifier to track
 * @param refreshInterval - How often to poll (default: 10000ms)
 * @param enabled - Enable/disable the status indicator
 *
 * @returns - Object with status and control methods
 *
 * Usage:
 * ```typescript
 * const indicator = useBehavioralStatusIndicator({
 *   userId: 'student-123',
 *   refreshInterval: 5000,
 *   enabled: true
 * });
 *
 * // Get current status
 * indicator.getStatus();
 * // Refresh status
 * indicator.refresh();
 *
 * // Cleanup on unmount
 * indicator.cleanup(); // Only call this if enabled
 * ```
 */
export function useBehavioralStatusIndicator(config: {
  userId?: string;
  refreshInterval?: number;
  enabled?: boolean;
}) {
  const {
    userId = "current-user",
    refreshInterval = 10000,
    enabled = true
  } = config;
  // State for status data
  const [status, setStatus] = useState<BehavioralStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastFetch, setLastFetch] = useState<number>(0);

  /**
   * Fetch behavioral status from backend
   */
  const fetchStatus = async () => {
    if (!enabled) return;

    // Rate limiting
    const now = Date.now();
    const timeSinceLastFetch = now - lastFetch;

    if (timeSinceLastFetch < 1000) {  // Minimum 1 second between fetches
      console.warn("[Behavioral] Rate limit: Fetching too frequently. Please wait.");
      return;
    }

    setLastFetch(now);

    try {
      const response = await fetch(`${API_BASE}/api/v1/behavioral/status/${userId}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch behavioral status: ${response.status}`);
      }

      const data: BehavioralStatusResponse = await response.json();

      if (data.status === "error") {
        setError(data.reasoning || "Unknown error");
        return;
      }

      setStatus(data);
      setLastFetch(Date.now());

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      setError(errorMessage);
      console.error("[Behavioral] Error fetching status:", error);
      setStatus(null);
    }
  };

  /**
   * Refresh status (force fetch from backend)
   */
  const refreshStatus = async () => {
    setLastFetch(0); // Reset rate limit
    await fetchStatus();
  };

  /**
   * Get current status
   */
  const getStatus = () => status;

  /**
   * Clear any error state
   */
  const clearError = () => setError(null);

  /**
   * Cleanup on unmount
   */
  const cleanup = () => {
    // Only cleanup if enabled
    if (!enabled) return;

    // Clear any pending timeout
    if (lastFetch) {
      clearTimeout(lastFetch);
      setLastFetch(0);
    }

    // Clear all intervals
    // Note: In production, this would also clear database connections
  };

  // Auto-refresh on mount
  useEffect(() => {
    if (!enabled) return;

    // Initial fetch
    fetchStatus();

    // Set up polling interval
    const intervalId = setInterval(async () => {
      await fetchStatus();
    }, refreshInterval);

    return () => {
      clearInterval(intervalId);
    };
  }, [userId, enabled, refreshInterval]);

  // Watch for userId changes
  useEffect(() => {
    // Cleanup interval on userId change
    return cleanup;
  }, [userId, enabled, refreshInterval, cleanup]);
};

/**
 * Component for displaying behavioral status in the UI
 *
 * Shows a compact status indicator with:
 * - Current mode badge
 * - Frustration level indicator
 * - Last update time
 * - Error/success indicator
 *
 * FERPA Compliance: No PII, local-only data
 */
interface BehavioralStatusIndicatorProps {
  userId?: string;
  enabled?: boolean;
  refreshInterval?: number;
}

export function BehavioralStatusIndicator(props: BehavioralStatusIndicatorProps) {
  const {
    userId = "current-user",
    enabled = true,
    refreshInterval = 5000,
  } = props;

  const status = useBehavioralStatusIndicator({ userId, enabled, refreshInterval });
  const currentStatus = getStatus();

  return (
    <div className="behavioral-status-indicator" aria-live="polite">
      {/* Status Badge */}
      <div
        className="behavioral-status-badge"
        aria-label={`Current mode: ${currentStatus?.suggested_mode || 'standard'}`}
        title={currentStatus?.suggested_mode || 'Standard'}
      >
        {currentStatus?.suggested_mode || 'Standard'}
      </div>

      {/* Last Update */}
      <div className="behavioral-status-meta">
        <span className="behavioral-status-time">
          Updated: {status.lastFetch ? new Date(status.lastFetch).toLocaleTimeString() : "Never"}
        </span>
      </div>

      {/* Error */}
      {status.error && (
        <div className="behavioral-status-error" aria-live="assertive" role="alert">
          <span className="behavioral-status-error-text">Error: {status.error}</span>
        </div>
      )}
    </div>
  );
}
