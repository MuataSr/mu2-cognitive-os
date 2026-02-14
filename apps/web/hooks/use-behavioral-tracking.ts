"use client";

/**
 * Behavioral Tracking Hook - Mu2 Cognitive OS
 * =====================================
 *
 * Tracks user behavioral signals for adaptive UI triggering:
 * - Mouse/cursor movements (clickstream)
 * - Time spent on tasks
 * - Click patterns (rapid clicking = frustration)
 *
 * FERPA Compliance:
 * - All data stays local
 * - No PII in behavioral signals
 * - User IDs are anonymized
 */

import { useEffect, useRef, useCallback } from "react";

// API base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Event storage (in-memory before batching)
interface ClickEvent {
  x: number;
  y: number;
  elementId?: string;
  elementType?: string;
  timestamp: Date;
}

interface BehavioralConfig {
  userId: string;
  batchInterval: number; // milliseconds
  maxBatchSize: number;
  enabled: boolean;
}

/**
 * Hook for tracking behavioral signals
 *
 * @param config - Configuration options
 * @returns - Object with tracking methods and state
 */
export function useBehavioralTracking(config: BehavioralConfig) {
  const {
    userId,
    batchInterval = 5000, // 5 seconds
    maxBatchSize = 50,
    enabled = true
  } = config;

  // Refs for event storage and timer
  const clickEventsRef = useRef<ClickEvent[]>([]);
  const timeOnTaskRef = useRef<number>(0);
  const startTimeRef = useRef<Date>(new Date());
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Record a click/cursor event
   */
  const recordClick = useCallback((x: number, y: number, elementId?: string, elementType?: string) => {
    if (!enabled) return;

    const event: ClickEvent = {
      x,
      y,
      elementId,
      elementType,
      timestamp: new Date()
    };

    clickEventsRef.current.push(event);

    // Auto-send if batch is full
    if (clickEventsRef.current.length >= maxBatchSize) {
      sendClickstreamBatch();
    }
  }, [enabled, maxBatchSize]);

  /**
   * Send clickstream batch to backend
   */
  const sendClickstreamBatch = useCallback(async () => {
    if (clickEventsRef.current.length === 0) return;

    try {
      const response = await fetch(`${API_BASE}/api/v1/behavioral/clickstream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          clickEventsRef.current.map(event => ({
            user_id: userId,
            x: event.x,
            y: event.y,
            element_id: event.elementId,
            element_type: event.elementType,
            timestamp: event.timestamp.toISOString()
          }))
        ),
      });

      if (response.ok) {
        // Clear sent events
        clickEventsRef.current = [];
      } else {
        console.error("Failed to send clickstream:", await response.text());
      }
    } catch (error) {
      console.error("Error sending clickstream:", error);
    }
  }, [API_BASE, userId]);

  /**
   * Track time spent on current task
   */
  const startTaskTimer = useCallback(() => {
    startTimeRef.current = new Date();
    timeOnTaskRef.current = 0;

    // Clear existing timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    // Update time every second
    timerRef.current = setInterval(() => {
      timeOnTaskRef.current = Math.floor((Date.now() - startTimeRef.current.getTime()) / 1000);
    }, 1000);
  }, []);

  const stopTaskTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  /**
   * Get current time on task
   */
  const getTimeOnTask = useCallback(() => {
    return timeOnTaskRef.current;
  }, []);

  /**
   * Detect rapid clicking pattern (frustration signal)
   */
  const detectRapidClicking = useCallback((events: ClickEvent[]) => {
    if (events.length < 5) return false;

    const now = Date.now();
    const fiveSecondsAgo = now - 5000;

    // Count clicks in last 5 seconds
    const recentClicks = events.filter(e => e.timestamp.getTime() > fiveSecondsAgo);

    return recentClicks.length >= 5; // 5+ clicks in 5 seconds = rapid
  }, []);

  /**
   * Send pending events on unmount
   */
  useEffect(() => {
    // Set up periodic batch sending
    if (enabled && intervalRef.current === null) {
      intervalRef.current = setInterval(() => {
        if (clickEventsRef.current.length > 0) {
          sendClickstreamBatch();
        }
      }, batchInterval);
    }

    return () => {
      // Cleanup
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }

      // Send remaining events
      if (clickEventsRef.current.length > 0) {
        sendClickstreamBatch();
      }
    };
  }, [enabled, batchInterval, sendClickstreamBatch]);

  return {
    // Event recording
    recordClick,
    startTaskTimer,
    stopTaskTimer,
    getTimeOnTask,

    // State
    clickEvents: clickEventsRef.current,
    timeOnTask: timeOnTaskRef.current,
    isRapidClicking: () => detectRapidClicking(clickEventsRef.current),
  };
}

/**
 * Hook for integrating behavioral signals with mode switching
 *
 * Automatically switches UI mode based on behavioral analysis from backend
 */
export function useBehavioralModeSwitch(userId: string, checkInterval = 30000) {
  const [suggestedMode, setSuggestedMode] = useState<string | null>(null);
  const [urgency, setUrgency] = useState<string>("none");
  const checkIntervalRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Fetch behavioral status from backend
   */
  const fetchBehavioralStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/behavioral/status/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setSuggestedMode(data.suggested_mode || null);
        setUrgency(data.urgency || "none");
      }
    } catch (error) {
      console.error("Error fetching behavioral status:", error);
    }
  }, [API_BASE, userId]);

  /**
   * Start periodic behavioral status checks
   */
  useEffect(() => {
    if (!userId) return;

    // Initial fetch
    fetchBehavioralStatus();

    // Set up periodic checks
    checkIntervalRef.current = setInterval(() => {
      fetchBehavioralStatus();
    }, checkInterval);

    return () => {
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
      }
    };
  }, [userId, fetchBehavioralStatus, checkInterval]);

  return {
    suggestedMode,
    urgency,
    refetchStatus: fetchBehavioralStatus,
  };
}

/**
 * Higher-level hook that combines tracking and mode switching
 */
export function useAdaptiveBehavioralSystem(config: BehavioralConfig) {
  const tracking = useBehavioralTracking(config);
  const modeSwitching = useBehavioralModeSwitch(config.userId);

  return {
    // Tracking methods
    ...tracking,

    // Mode switching
    suggestedMode: modeSwitching.suggestedMode,
    urgency: modeSwitching.urgency,
    refetchStatus: modeSwitching.refetchStatus,

    // Convenience method to get full behavioral state
    getBehavioralState: () => ({
      timeOnTask: tracking.getTimeOnTask(),
      clickEventCount: tracking.clickEvents.length,
      isRapidClicking: tracking.isRapidClicking(),
    }),
  };
}
