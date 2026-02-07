/**
 * Mastery Tracking API Client
 * FERPA-compliant local-only API calls for student mastery tracking
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1/mastery";

// ============================================================================
// Types
// ============================================================================

export type MasteryStatus = "MASTERED" | "LEARNING" | "STRUGGLING";

export interface LearningEventInput {
  user_id: string;
  skill_id: string;
  is_correct: boolean;
  attempts?: number;
  time_spent_seconds?: number;
  metadata?: Record<string, unknown>;
}

export interface MasteryStatusOutput {
  status: MasteryStatus;
  probability_mastery: number;
  attempts: number;
  suggested_action?: string;
  confidence: number;
}

export interface MasteryUpdateOutput {
  user_id: string;
  skill_id: string;
  previous_mastery: number;
  new_mastery: number;
  status: MasteryStatusOutput;
  predicted_next: number;
}

export interface StudentSkillOutput {
  skill_id: string;
  skill_name: string;
  probability_mastery: number;
  total_attempts: number;
  correct_attempts: number;
  status: MasteryStatusOutput;
}

export interface StudentSkillsOutput {
  user_id: string;
  skills: StudentSkillOutput[];
  total_skills: number;
  mastered_count: number;
  learning_count: number;
  struggling_count: number;
  recent_events: LiveFeedEvent[];
}

export interface StudentCardOutput {
  user_id: string;
  masked_id: string;
  total_skills: number;
  mastered_count: number;
  learning_count: number;
  struggling_count: number;
  avg_mastery: number;
  overall_status: MasteryStatus;
  last_active: string;
}

export interface ClassOverviewOutput {
  students: StudentCardOutput[];
  total_students: number;
  struggling_students: number;
  class_avg_mastery: number;
  count_ready: number;
  count_distracted: number;
  count_intervention: number;
}

export interface SkillRegistryEntry {
  skill_id: string;
  skill_name: string;
  subject: string;
  grade_level: number;
  description: string;
}

export interface SkillsListOutput {
  skills: SkillRegistryEntry[];
  count: number;
  filters: {
    subject?: string;
    grade_level?: number;
  };
}

export interface LiveFeedEvent {
  user_id: string;
  event_type: "STUDENT_ACTION" | "AGENT_ACTION";
  timestamp: string;
  source_text?: string;
  metadata: Record<string, unknown>;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Record a learning event and update mastery probability
 */
export async function recordLearningEvent(
  data: LearningEventInput
): Promise<MasteryUpdateOutput> {
  const res = await fetch(`${API_BASE}/record`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(`Failed to record learning event: ${res.statusText}`);
  }

  return res.json();
}

/**
 * Get all mastery states for a specific student
 */
export async function getStudentMastery(userId: string): Promise<StudentSkillsOutput> {
  const res = await fetch(`${API_BASE}/student/${encodeURIComponent(userId)}`);

  if (!res.ok) {
    throw new Error(`Failed to get student mastery: ${res.statusText}`);
  }

  return res.json();
}

/**
 * Get class mastery overview (Teacher Dashboard)
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

  return res.json();
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

  return res.json();
}

/**
 * Get recent learning events for the Live Feed sidebar
 */
export async function getRecentEvents(limit: number = 20): Promise<LiveFeedEvent[]> {
  const res = await fetch(`${API_BASE}/recent-events?limit=${limit}`);

  if (!res.ok) {
    throw new Error(`Failed to get recent events: ${res.statusText}`);
  }

  const data = await res.json();
  return data.events || [];
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get Tailwind color class for mastery status
 */
export function getStatusColor(status: MasteryStatus): string {
  switch (status) {
    case "MASTERED":
      return "bg-green-500";
    case "LEARNING":
      return "bg-yellow-500";
    case "STRUGGLING":
      return "bg-red-500";
    default:
      return "bg-gray-500";
  }
}

/**
 * Get text color for mastery status
 */
export function getStatusTextColor(status: MasteryStatus): string {
  switch (status) {
    case "MASTERED":
      return "text-green-500";
    case "LEARNING":
      return "text-yellow-500";
    case "STRUGGLING":
      return "text-red-500";
    default:
      return "text-gray-500";
  }
}

/**
 * Format mastery percentage for display
 */
export function formatMasteryPercentage(mastery: number): string {
  return `${Math.round(mastery * 100)}%`;
}

/**
 * Mask student ID based on user role (FERPA compliance)
 */
export function maskStudentId(userId: string, role: string): string {
  if (role === "researcher" || role === "external") {
    return userId.length > 8 ? `${userId.slice(0, 8)}...` : "***";
  }
  return userId;
}

/**
 * Calculate mastery percentage for progress bar
 */
export function getMasteryWidth(mastery: number): string {
  return `${mastery * 100}%`;
}

/**
 * Determine if a student needs intervention
 */
export function needsIntervention(status: MasteryStatus, mastery: number, attempts: number): boolean {
  return status === "STRUGGLING" && attempts > 3;
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

    // Set up polling
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
