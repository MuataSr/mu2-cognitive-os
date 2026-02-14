/**
 * Supabase Database Types
 *
 * This file defines TypeScript types for the Supabase database schema.
 * These match the tables defined in the migration files:
 * - 001_initial_schema.sql
 * - 002_knowledge_vault.sql
 * - 003_mastery_tracking.sql
 * - 004_add_learning_events_fields.sql
 *
 * Generate this file using:
 * npx supabase gen types typescript --project-id YOUR_PROJECT_ID > lib/supabase/types.ts
 */

export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[]

export interface Database {
  public: {
    Tables: {
      // Cortex schema tables
      user_sessions: {
        Row: {
          id: string
          user_id: string
          session_start: string
          session_end: string | null
          current_mode: string
          focus_level: number
          context_vector: number[] | null
          metadata: Json
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          user_id: string
          session_start?: string
          session_end?: string | null
          current_mode?: string
          focus_level?: number
          context_vector?: number[] | null
          metadata?: Json
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          session_start?: string
          session_end?: string | null
          current_mode?: string
          focus_level?: number
          context_vector?: number[] | null
          metadata?: Json
          created_at?: string
          updated_at?: string
        }
      }
      textbook_chunks: {
        Row: {
          id: string
          chapter_id: string
          section_id: string
          content: string
          embedding: number[] | null
          grade_level: number
          subject: string
          metadata: Json
          created_at: string
        }
        Insert: {
          id?: string
          chapter_id: string
          section_id: string
          content: string
          embedding?: number[] | null
          grade_level?: number
          subject?: string
          metadata?: Json
          created_at?: string
        }
        Update: {
          id?: string
          chapter_id?: string
          section_id?: string
          content?: string
          embedding?: number[] | null
          grade_level?: number
          subject?: string
          metadata?: Json
          created_at?: string
        }
      }
      graph_nodes: {
        Row: {
          id: string
          graph_name: string
          node_id: number
          label: string
          properties: Json
          created_at: string
        }
        Insert: {
          id?: string
          graph_name?: string
          node_id: number
          label: string
          properties?: Json
          created_at?: string
        }
        Update: {
          id?: string
          graph_name?: string
          node_id?: number
          label?: string
          properties?: Json
          created_at?: string
        }
      }
      graph_edges: {
        Row: {
          id: string
          graph_name: string
          edge_id: number
          start_node_id: number
          end_node_id: number
          edge_label: string
          properties: Json
          created_at: string
        }
        Insert: {
          id?: string
          graph_name?: string
          edge_id: number
          start_node_id: number
          end_node_id: number
          edge_label: string
          properties?: Json
          created_at?: string
        }
        Update: {
          id?: string
          graph_name?: string
          edge_id?: number
          start_node_id?: number
          end_node_id?: number
          edge_label?: string
          properties?: Json
          created_at?: string
        }
      }
      chunk_concept_links: {
        Row: {
          id: string
          chunk_id: string
          node_id: number
          relevance_score: number
          created_at: string
        }
        Insert: {
          id?: string
          chunk_id: string
          node_id: number
          relevance_score?: number
          created_at?: string
        }
        Update: {
          id?: string
          chunk_id?: string
          node_id?: number
          relevance_score?: number
          created_at?: string
        }
      }
      skills_registry: {
        Row: {
          skill_id: string
          skill_name: string
          subject: string
          grade_level: number
          description: string | null
          metadata: Json
          created_at: string
          updated_at: string
        }
        Insert: {
          skill_id: string
          skill_name: string
          subject?: string
          grade_level?: number
          description?: string | null
          metadata?: Json
          created_at?: string
          updated_at?: string
        }
        Update: {
          skill_id?: string
          skill_name?: string
          subject?: string
          grade_level?: number
          description?: string | null
          metadata?: Json
          created_at?: string
          updated_at?: string
        }
      }
      learning_events: {
        Row: {
          id: string
          user_id: string
          skill_id: string
          is_correct: boolean
          attempts: number
          time_spent_seconds: number | null
          timestamp: string
          event_type: string
          source_text: string | null
          metadata: Json
          created_at: string
        }
        Insert: {
          id?: string
          user_id: string
          skill_id: string
          is_correct: boolean
          attempts?: number
          time_spent_seconds?: number | null
          timestamp?: string
          event_type?: string
          source_text?: string | null
          metadata?: Json
          created_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          skill_id?: string
          is_correct?: boolean
          attempts?: number
          time_spent_seconds?: number | null
          timestamp?: string
          event_type?: string
          source_text?: string | null
          metadata?: Json
          created_at?: string
        }
      }
      student_skills: {
        Row: {
          user_id: string
          skill_id: string
          probability_mastery: number
          total_attempts: number
          correct_attempts: number
          consecutive_correct: number
          consecutive_incorrect: number
          last_attempt_at: string
          last_updated_at: string
        }
        Insert: {
          user_id: string
          skill_id: string
          probability_mastery?: number
          total_attempts?: number
          correct_attempts?: number
          consecutive_correct?: number
          consecutive_incorrect?: number
          last_attempt_at?: string
          last_updated_at?: string
        }
        Update: {
          user_id?: string
          skill_id?: string
          probability_mastery?: number
          total_attempts?: number
          correct_attempts?: number
          consecutive_correct?: number
          consecutive_incorrect?: number
          last_attempt_at?: string
          last_updated_at?: string
        }
      }
    }
    Views: {
      active_sessions: {
        Row: {
          id: string
          user_id: string
          session_start: string
          current_mode: string
          focus_level: number
          duration_minutes: number
        }
      }
      chunk_with_concepts: {
        Row: {
          id: string
          chapter_id: string
          section_id: string
          content: string
          grade_level: number
          subject: string
          metadata: Json
          created_at: string
          related_concepts: Json | null
        }
      }
      graph_statistics: {
        Row: {
          graph_name: string
          node_count: number
          edge_count: number
          unique_labels: number
        }
      }
      struggling_students: {
        Row: {
          user_id: string
          skill_id: string
          skill_name: string
          probability_mastery: number
          total_attempts: number
          consecutive_incorrect: number
          last_attempt_at: string
          subject: string
          grade_level: number
        }
      }
      skill_mastery_summary: {
        Row: {
          skill_id: string
          skill_name: string
          subject: string
          grade_level: number
          total_students: number
          mastered_count: number
          struggling_count: number
          avg_mastery: number
          avg_attempts: number
        }
      }
    }
    Functions: {
      search_similar_chunks: {
        Args: {
          query_embedding: number[]
          p_grade_level: number | null
          p_subject: string | null
          p_limit: number
          p_threshold: number
        }
        Returns: {
          id: string
          chapter_id: string
          section_id: string
          content: string
          grade_level: number
          subject: string
          metadata: Json
          similarity: number
        }[]
      }
      get_concept_context: {
        Args: {
          concept_label: string
        }
        Returns: {
          related_concept: string
          relationship_type: string
          direction: string
        }[]
      }
      get_student_mastery_status: {
        Args: {
          p_user_id: string
        }
        Returns: {
          skill_id: string
          skill_name: string
          probability_mastery: number
          total_attempts: number
          correct_attempts: number
          status: string
          suggested_action: string
        }[]
      }
      get_class_mastery_overview: {
        Args: Record<PropertyKey, never>
        Returns: {
          user_id: string
          total_skills: number
          mastered_count: number
          learning_count: number
          struggling_count: number
          avg_mastery: number
          last_active: string
        }[]
      }
      record_learning: {
        Args: {
          p_user_id: string
          p_skill_id: string
          p_is_correct: boolean
          p_attempts: number
          p_time_spent_seconds: number | null
          p_metadata: Json
        }
        Returns: string
      }
      update_mastery_on_event: {
        Args: Record<PropertyKey, never>
        Returns: undefined
      }
      update_updated_at: {
        Args: Record<PropertyKey, never>
        Returns: undefined
      }
    }
    Enums: {
      [_ in never]: never
    }
  }
}
