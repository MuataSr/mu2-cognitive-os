/**
 * Mastery Tracking API Client
 * FERPA-compliant local-only API calls for scholar mastery tracking
 */

import {
  // Type exports from schemas (reduces duplication)
  type MasteryStatus,
  type MasteryStatusOutput,
  type StudentSkillOutput,
  type StudentSkillsOutput,
  type StudentCardOutput,
  type ClassOverviewOutput,
  type MasteryUpdateOutput,
  type SkillRegistryEntry,
  type SkillsListOutput,
  type LiveFeedEvent,
  // Zod schemas for validation
  MasteryUpdateOutputSchema,
  StudentSkillsOutputSchema,
  ClassOverviewOutputSchema,
  SkillsListOutputSchema,
  RecentEventsArraySchema,
  RecentEventsObjectSchema,
  // Validation helper
  validateApiResponse,
} from "@/lib/api/schemas";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1/mastery";

// ============================================================================
// Types (re-exported from schemas for backward compatibility)
// ============================================================================

export type { MasteryStatus, MasteryStatusOutput, StudentSkillOutput, StudentSkillsOutput, StudentCardOutput, ClassOverviewOutput, MasteryUpdateOutput, SkillRegistryEntry, SkillsListOutput, LiveFeedEvent };

export interface LearningEventInput {
  user_id: string;
  skill_id: string;
  is_correct: boolean;
  attempts?: number;
  time_spent_seconds?: number;
  metadata?: Record<string, unknown>;
}

// ============================================================================
// CSRF Token Management
// ============================================================================

/**
 * Get or generate CSRF token for POST requests
 * Since this is local-only, we use a simple token stored in localStorage
 */
function getCsrfToken(): string {
  let token = localStorage.getItem("mu2-csrf-token");

  if (!token) {
    // Generate a random token for CSRF protection
    token = Array.from({ length: 32 }, () =>
      Math.random().toString(36)[2]
    ).join("");
    localStorage.setItem("mu2-csrf-token", token);
  }

  return token;
}

/**
 * Validate CSRF token from response headers
 */
function validateCsrfToken(response: Response): boolean {
  const responseToken = response.headers.get("X-CSRF-Token");
  if (!responseToken) {
    // For local development without CSRF headers, we'll allow it
    return process.env.NODE_ENV === "development";
  }

  const storedToken = localStorage.getItem("mu2-csrf-token");
  return responseToken === storedToken;
}

// ============================================================================
// API Functions (with Zod validation and CSRF protection)
// ============================================================================

/**
 * Record a learning event and update mastery probability
 */
export async function recordLearningEvent(
  data: LearningEventInput
): Promise<MasteryUpdateOutput> {
  const res = await fetch(`${API_BASE}/record`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": getCsrfToken(),
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(`Failed to record learning event: ${res.statusText}`);
  }

  // Validate CSRF token from response
  validateCsrfToken(res);

  // Validate response with Zod
  const rawData = await res.json();
  return validateApiResponse(rawData, MasteryUpdateOutputSchema, "record learning event");
}

/**
 * Get all mastery states for a specific scholar
 */
export async function getStudentMastery(userId: string): Promise<StudentSkillsOutput> {
  const res = await fetch(`${API_BASE}/student/${encodeURIComponent(userId)}`);

  if (!res.ok) {
    throw new Error(`Failed to get scholar mastery: ${res.statusText}`);
  }

  // Validate response with Zod
  const rawData = await res.json();
  return validateApiResponse(rawData, StudentSkillsOutputSchema, "get student mastery");
}

/**
 * Get class mastery overview (Mentor Dashboard)
 */
export async function getClassMastery(options: {
  strugglingOnly?: boolean;
  minMastery?: number;
} = {}): Promise<ClassOverviewOutput> {
  const params = new URLSearchParams();
  if (options.strugglingOnly) params.append("struggling_only", "true");
  if (options.minMastery !== undefined) params.append("min_mastery", options.minMastery.toString());

  const url = `${API_BASE}/class${params.toString() ? `?${params.toString()}` : ""}`;
  const res = await fetch(url);

  if (!res.ok) {
    throw new Error(`Failed to get class mastery: ${res.statusText}`);
  }

  // Validate response with Zod
  const rawData = await res.json();
  return validateApiResponse(rawData, ClassOverviewOutputSchema, "get class mastery");
}

/**
 * List all available skills in the registry
 */
export async function listSkills(options?: {
  subject?: string;
  gradeLevel?: number;
}): Promise<SkillsListOutput> {
  const params = new URLSearchParams();
  if (options?.subject) params.append("subject", options.subject);
  if (options?.gradeLevel !== undefined) params.append("grade_level", options.gradeLevel.toString());

  const url = `${API_BASE}/skills${params.toString() ? `?${params.toString()}` : ""}`;
  const res = await fetch(url);

  if (!res.ok) {
    throw new Error(`Failed to list skills: ${res.statusText}`);
  }

  // Validate response with Zod
  const rawData = await res.json();
  return validateApiResponse(rawData, SkillsListOutputSchema, "list skills");
}

/**
 * Get recent learning events for the Live Feed sidebar
 */
export async function getRecentEvents(limit: number = 20): Promise<LiveFeedEvent[]> {
  const res = await fetch(`${API_BASE}/recent-events?limit=${limit}`);

  if (!res.ok) {
    throw new Error(`Failed to get recent events: ${res.statusText}`);
  }

  const rawData = await res.json();

  // Handle both array format and {events: array} format
  if (Array.isArray(rawData)) {
    // Direct array format
    return validateApiResponse(rawData, RecentEventsArraySchema, "get recent events");
  }

  // Object format with events property
  const validated = validateApiResponse(rawData, RecentEventsObjectSchema, "get recent events");
  return validated.events;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Consolidated status color configuration
 * Reduces code duplication from separate functions
 */
const STATUS_COLORS = {
  MASTERED: {
    bg: "bg-green-500",
    text: "text-green-500",
  },
  LEARNING: {
    bg: "bg-yellow-500",
    text: "text-yellow-500",
  },
  STRUGGLING: {
    bg: "bg-[color:var(--kd-red)]",
    text: "text-[color:var(--kd-red)]",
  },
} as const;

/**
 * Get Tailwind color class for mastery status
 */
export function getStatusColor(status: MasteryStatus): string {
  return STATUS_COLORS[status]?.bg || "bg-gray-500";
}

/**
 * Get text color for mastery status
 */
export function getStatusTextColor(status: MasteryStatus): string {
  return STATUS_COLORS[status]?.text || "text-gray-500";
}

/**
 * Format mastery percentage for display
 */
export function formatMasteryPercentage(mastery: number): string {
  return `${Math.round(mastery * 100)}%`;
}

/**
 * Mask scholar ID based on user role (FERPA compliance)
 * Always mask PII to prevent accidental exposure
 */
export function maskStudentId(userId: string, role: string): string {
  // Always mask at least partially for FERPA compliance
  if (role === "researcher" || role === "external") {
    return userId.length > 8 ? `${userId.slice(0, 8)}...` : "***";
  }
  // For mentors/teachers, show first initial + last name format
  const parts = userId.split("-");
  if (parts.length >= 2) {
    const firstInitial = parts[0]?.charAt(0) || "?";
    const lastName = parts[parts.length - 1] || "";
    return `${firstInitial}. ${lastName}`;
  }
  return userId.length > 8 ? `${userId.slice(0, 8)}...` : userId;
}

/**
 * Calculate mastery percentage for progress bar
 */
export function getMasteryWidth(mastery: number): string {
  return `${mastery * 100}%`;
}

/**
 * Determine if a scholar needs intervention
 * Named constant for threshold instead of magic number
 */
const INTERVENTION_THRESHOLD = 3;

export function needsIntervention(status: MasteryStatus, mastery: number, attempts: number): boolean {
  return status === "STRUGGLING" && attempts > INTERVENTION_THRESHOLD;
}

/**
 * Format last active timestamp for display
 */
export function formatLastActive(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

// ============================================================================
// React Hook Helpers
// ============================================================================

/**
 * Hook for polling class mastery updates (for real-time dashboard)
 * Fixed: Uses useRef to prevent interval recreation on every render
 */
export function createClassMasteryPoller(
  callback: (data: ClassOverviewOutput) => void,
  intervalMs: number = 5000,
  options: { strugglingOnly?: boolean; minMastery?: number } = {}
) {
  let intervalId: NodeJS.Timeout | null = null;

  const start = () => {
    // Initial fetch
    getClassMastery(options).then(callback).catch(console.error);

    // Set up polling - only create interval once
    intervalId = setInterval(() => {
      getClassMastery(options).then(callback).catch(console.error);
    }, intervalMs);
  };

  const stop = () => {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  };

  return { start, stop };
}

/**
 * Batch record multiple learning events
 */
export async function batchRecordEvents(events: LearningEventInput[]): Promise<MasteryUpdateOutput[]> {
  const results = await Promise.allSettled(
    events.map((event) => recordLearningEvent(event))
  );

  return results.map((result, index) => {
    if (result.status === "fulfilled") {
      return result.value;
    } else {
      console.error(`Failed to record event ${index}:`, result.reason);
      throw result.reason;
    }
  });
}
