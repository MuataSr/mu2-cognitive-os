import { z } from "zod";

/**
 * Zod Schemas for Runtime Validation
 *
 * These schemas provide runtime type safety for API responses.
 * All API responses should be validated before use to prevent
 * runtime errors and potential security issues.
 */

// ============================================================================
// Mastery API Schemas (from /api/v1/mastery)
// ============================================================================

export const MasteryStatusSchema = z.enum(["MASTERED", "LEARNING", "STRUGGLING"]);

export const MasteryStatusOutputSchema = z.object({
  status: MasteryStatusSchema,
  probability_mastery: z.number().min(0).max(1),
  attempts: z.number().int().nonnegative(),
  suggested_action: z.string().optional(),
  confidence: z.number().min(0).max(1),
});

export const StudentSkillOutputSchema = z.object({
  skill_id: z.string(),
  skill_name: z.string(),
  probability_mastery: z.number().min(0).max(1),
  total_attempts: z.number().int().nonnegative(),
  correct_attempts: z.number().int().nonnegative(),
  status: MasteryStatusOutputSchema,
});

export const LiveFeedEventSchema = z.object({
  user_id: z.string(),
  event_type: z.enum(["STUDENT_ACTION", "AGENT_ACTION"]),
  timestamp: z.string(), // ISO datetime string
  source_text: z.string().optional(),
  metadata: z.record(z.unknown()),
});

export const StudentSkillsOutputSchema = z.object({
  user_id: z.string(),
  skills: z.array(StudentSkillOutputSchema),
  total_skills: z.number().int().nonnegative(),
  mastered_count: z.number().int().nonnegative(),
  learning_count: z.number().int().nonnegative(),
  struggling_count: z.number().int().nonnegative(),
  recent_events: z.array(LiveFeedEventSchema),
});

export const StudentCardOutputSchema = z.object({
  user_id: z.string(),
  masked_id: z.string(),
  total_skills: z.number().int().nonnegative(),
  mastered_count: z.number().int().nonnegative(),
  learning_count: z.number().int().nonnegative(),
  struggling_count: z.number().int().nonnegative(),
  avg_mastery: z.number().min(0).max(1),
  overall_status: MasteryStatusSchema,
  last_active: z.string(), // ISO datetime string
});

export const ClassOverviewOutputSchema = z.object({
  students: z.array(StudentCardOutputSchema),
  total_students: z.number().int().nonnegative(),
  struggling_students: z.number().int().nonnegative(),
  class_avg_mastery: z.number().min(0).max(1),
  count_ready: z.number().int().nonnegative(),
  count_distracted: z.number().int().nonnegative(),
  count_intervention: z.number().int().nonnegative(),
});

export const MasteryUpdateOutputSchema = z.object({
  user_id: z.string(),
  skill_id: z.string(),
  previous_mastery: z.number().min(0).max(1),
  new_mastery: z.number().min(0).max(1),
  status: MasteryStatusOutputSchema,
  predicted_next: z.number().min(0).max(1),
});

export const SkillRegistryEntrySchema = z.object({
  skill_id: z.string(),
  skill_name: z.string(),
  subject: z.string(),
  grade_level: z.number().int().positive(),
  description: z.string(),
});

export const SkillsListOutputSchema = z.object({
  skills: z.array(SkillRegistryEntrySchema),
  count: z.number().int().nonnegative(),
  filters: z.object({
    subject: z.string().optional(),
    grade_level: z.number().int().positive().optional(),
  }),
});

// Recent events can be returned as either a direct array or wrapped in an object
export const RecentEventsArraySchema = z.array(LiveFeedEventSchema);

export const RecentEventsObjectSchema = z.object({
  events: z.array(LiveFeedEventSchema),
});

// ============================================================================
// Chat API Schemas (from /api/v2/query)
// ============================================================================

export const CitationSchema = z.object({
  source_id: z.string(),
  paragraph_id: z.string(),
  relevance_score: z.number().min(0).max(1),
  text_snippet: z.string(),
});

export const TranslationSchema = z.object({
  simplified: z.string(),
  metaphor: z.string().optional(),
  grade_level: z.string(),
});

export const QueryResponseSchema = z.object({
  answer: z.string(),
  sources: z.array(CitationSchema),
  translation: TranslationSchema,
  confidence: z.number().min(0).max(1),
  follow_up_questions: z.array(z.string()),
});

export const QueryRequestSchema = z.object({
  query: z.string().min(1).max(10000),
  context: z.object({
    chapter_id: z.string().optional(),
    mode: z.enum(["standard", "focus"]).optional(),
  }).optional(),
});

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Validate API response with Zod schema
 * Throws detailed error if validation fails
 */
export function validateApiResponse<T>(
  data: unknown,
  schema: z.ZodSchema<T>,
  context: string
): T {
  try {
    return schema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error(`[Validation Error] ${context}:`, error.errors);
      throw new Error(
        `Invalid API response for ${context}: ${error.errors.map(
          (e) => `${e.path.join(".")}: ${e.message}`
        ).join(", ")}`
      );
    }
    throw error;
  }
}

/**
 * Safely parse API response with fallback
 * Returns fallback data if validation fails
 */
export function safeParseApiResponse<T>(
  data: unknown,
  schema: z.ZodSchema<T>,
  fallback: T,
  context: string
): T {
  try {
    return schema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.warn(`[Validation Warning] ${context}:`, error.errors);
    }
    return fallback;
  }
}

// ============================================================================
// Type Exports (inference from schemas)
// ============================================================================

export type MasteryStatus = z.infer<typeof MasteryStatusSchema>;
export type MasteryStatusOutput = z.infer<typeof MasteryStatusOutputSchema>;
export type StudentSkillOutput = z.infer<typeof StudentSkillOutputSchema>;
export type LiveFeedEvent = z.infer<typeof LiveFeedEventSchema>;
export type StudentSkillsOutput = z.infer<typeof StudentSkillsOutputSchema>;
export type StudentCardOutput = z.infer<typeof StudentCardOutputSchema>;
export type ClassOverviewOutput = z.infer<typeof ClassOverviewOutputSchema>;
export type MasteryUpdateOutput = z.infer<typeof MasteryUpdateOutputSchema>;
export type SkillRegistryEntry = z.infer<typeof SkillRegistryEntrySchema>;
export type SkillsListOutput = z.infer<typeof SkillsListOutputSchema>;

export type Citation = z.infer<typeof CitationSchema>;
export type Translation = z.infer<typeof TranslationSchema>;
export type QueryResponse = z.infer<typeof QueryResponseSchema>;
export type QueryRequest = z.infer<typeof QueryRequestSchema>;
