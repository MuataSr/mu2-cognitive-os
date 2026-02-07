/**
 * ADAPT API Client - Mu2 Cognitive OS
 * ===================================
 *
 * Frontend API client for LibreTexts ADAPT integration.
 *
 * Features:
 * - Import questions from ADAPT
 * - Search local question store
 * - Get imported topics and statistics
 * - TypeScript types for all responses
 */

// ============================================================================
// Types
// ============================================================================

export interface ImportQuestionsInput {
  topic: string;
  subject?: string;
  difficulty?: "easy" | "medium" | "hard";
  count?: number;
}

export interface ImportQuestionsResult {
  status: "success" | "partial";
  total_fetched: number;
  successfully_imported: number;
  failed: number;
  errors: string[];
  imported_ids: string[];
  duration_seconds: number;
}

export interface SearchQuestionsInput {
  query: string;
  subject?: string;
  topic?: string;
  top_k?: number;
}

export interface Question {
  question_id: string;
  text: string;
  subject: string;
  topic: string;
  difficulty: string;
  type: string;
  explanation: string | null;
  score: number;
}

export interface SearchQuestionsResult {
  query: string;
  count: number;
  questions: Question[];
}

export interface TopicsResult {
  topics: string[];
  count: number;
  subject: string | null;
}

export interface QuestionStatistics {
  total: number;
  by_subject: Record<string, number>;
  by_topic: Record<string, number>;
  by_difficulty: Record<string, number>;
}

export interface AdaptHealthStatus {
  status: "healthy" | "unhealthy";
  local_store: {
    status: string;
    total_questions: number;
    subjects: string[];
    topics: string[];
  };
  adapt_api: {
    status: string;
    api_available: boolean;
    endpoint: string;
    timestamp: string;
  };
  error?: string;
  timestamp: string;
}

// ============================================================================
// API Client
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ADAPTAPIClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Unknown error" }));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Import questions from LibreTexts ADAPT
   */
  async importQuestions(input: ImportQuestionsInput): Promise<ImportQuestionsResult> {
    return this.request<ImportQuestionsResult>("/api/v1/adapt/import", {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  /**
   * Search for similar questions in local store
   */
  async searchQuestions(input: SearchQuestionsInput): Promise<SearchQuestionsResult> {
    const params = new URLSearchParams();
    if (input.subject) params.append("subject", input.subject);
    if (input.topic) params.append("topic", input.topic);
    if (input.top_k) params.append("top_k", input.top_k.toString());

    return this.request<SearchQuestionsResult>(
      `/api/v1/adapt/search?query=${encodeURIComponent(input.query)}&${params.toString()}`
    );
  }

  /**
   * Get list of imported topics
   */
  async getTopics(subject?: string): Promise<TopicsResult> {
    const params = subject ? `?subject=${encodeURIComponent(subject)}` : "";
    return this.request<TopicsResult>(`/api/v1/adapt/topics${params}`);
  }

  /**
   * Get question statistics
   */
  async getStatistics(): Promise<QuestionStatistics> {
    return this.request<QuestionStatistics>("/api/v1/adapt/statistics");
  }

  /**
   * Check ADAPT integration health
   */
  async getHealth(): Promise<AdaptHealthStatus> {
    return this.request<AdaptHealthStatus>("/api/v1/adapt/health");
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

const adaptApiClient = new ADAPTAPIClient();

export default adaptApiClient;

// ============================================================================
// React Hooks
// ============================================================================

import { useState, useCallback, useEffect } from "react";

/**
 * Hook for importing questions from ADAPT
 */
export function useImportQuestions() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportQuestionsResult | null>(null);

  const importQuestions = useCallback(async (input: ImportQuestionsInput) => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await adaptApiClient.importQuestions(input);
      setResult(data);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { importQuestions, isLoading, error, result };
}

/**
 * Hook for searching questions
 */
export function useSearchQuestions() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SearchQuestionsResult | null>(null);

  const searchQuestions = useCallback(async (input: SearchQuestionsInput) => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await adaptApiClient.searchQuestions(input);
      setResult(data);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { searchQuestions, isLoading, error, result };
}

/**
 * Hook for getting imported topics
 */
export function useAdaptTopics(subject?: string) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [topics, setTopics] = useState<string[]>([]);

  const fetchTopics = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await adaptApiClient.getTopics(subject);
      setTopics(data.topics);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [subject]);

  useEffect(() => {
    fetchTopics();
  }, [fetchTopics]);

  return { topics, isLoading, error, refetch: fetchTopics };
}

/**
 * Hook for getting ADAPT statistics
 */
export function useAdaptStatistics() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<QuestionStatistics | null>(null);

  const fetchStats = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await adaptApiClient.getStatistics();
      setStats(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return { stats, isLoading, error, refetch: fetchStats };
}

/**
 * Hook for checking ADAPT health
 */
export function useAdaptHealth() {
  const [isLoading, setIsLoading] = useState(false);
  const [health, setHealth] = useState<AdaptHealthStatus | null>(null);

  const checkHealth = useCallback(async () => {
    setIsLoading(true);

    try {
      const data = await adaptApiClient.getHealth();
      setHealth(data);
    } catch (err) {
      setHealth({
        status: "unhealthy",
        local_store: {
          status: "unavailable",
          total_questions: 0,
          subjects: [],
          topics: [],
        },
        adapt_api: {
          status: "unavailable",
          api_available: false,
          endpoint: "",
          timestamp: new Date().toISOString(),
        },
        error: err instanceof Error ? err.message : "Unknown error",
        timestamp: new Date().toISOString(),
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  return { health, isLoading, checkHealth };
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Predefined topics for quick import
 */
export const PREDEFINED_TOPICS = {
  biology: [
    "Photosynthesis",
    "Cellular Respiration",
    "Genetics",
    "Evolution",
    "Ecology",
    "Cell Structure",
    "DNA Replication",
    "Mitosis",
    "Meiosis",
    "Enzymes",
  ],
  chemistry: [
    "Atomic Structure",
    "Chemical Bonding",
    "Stoichiometry",
    "Acids and Bases",
    "Redox Reactions",
    "Organic Chemistry",
    "Periodic Table",
    "Chemical Equilibrium",
  ],
  physics: [
    "Newton's Laws",
    "Energy and Work",
    "Waves and Sound",
    "Light and Optics",
    "Electricity",
    "Magnetism",
    "Thermodynamics",
  ],
  mathematics: [
    "Algebra",
    "Geometry",
    "Trigonometry",
    "Calculus",
    "Statistics",
    "Probability",
  ],
} as const;

/**
 * Get available subjects
 */
export function getAvailableSubjects(): string[] {
  return Object.keys(PREDEFINED_TOPICS);
}

/**
 * Get topics for a subject
 */
export function getTopicsForSubject(subject: string): string[] {
  return PREDEFINED_TOPICS[subject as keyof typeof PREDEFINED_TOPICS] || [];
}
