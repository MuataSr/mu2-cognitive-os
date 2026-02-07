/**
 * OpenTDB API Client - Mu2 Cognitive OS
 * ======================================
 *
 * Free API client for OpenTDB - No API key required!
 *
 * OpenTDB provides:
 * - Free JSON API (no registration needed)
 * - Science & Nature questions (Category 17)
 * - Math questions (Category 19)
 * - Computer Science (Category 18)
 * - No rate limiting for development
 * - Creative Commons licensed
 *
 * Documentation: https://opentdb.com/api_config.php
 */

// ============================================================================
// Types
// ============================================================================

export interface OpenTDBQuestion {
  id: string;
  question: string;
  correct_answer: string;
  incorrect_answers: string[];
  type: "multiple" | "boolean";
  difficulty: "easy" | "medium" | "hard";
  category: string;
}

export interface FetchQuestionsInput {
  amount?: number;
  category?: number;
  difficulty?: "easy" | "medium" | "hard";
  type?: "multiple" | "boolean";
  science_only?: boolean;
}

export interface FetchQuestionsResult {
  count: number;
  questions: OpenTDBQuestion[];
}

export interface OpenTDBCategory {
  id: number;
  name: string;
}

export interface CategoriesResult {
  categories: OpenTDBCategory[];
  count: number;
  science_categories: Record<number, string>;
}

export interface ImportResult {
  status: string;
  total_fetched: number;
  successfully_imported: number;
  failed: number;
  timestamp: string;
}

// ============================================================================
// OpenTDB Category IDs
// ============================================================================

export const OPENTDB_CATEGORIES: Record<number, string> = {
  9: "General Knowledge",
  10: "Entertainment: Books",
  11: "Entertainment: Film",
  12: "Entertainment: Music",
  13: "Entertainment: Musicals & Theatres",
  14: "Entertainment: Television",
  15: "Entertainment: Video Games",
  16: "Entertainment: Board Games",
  17: "Science & Nature", // <-- Main science category
  18: "Science: Computers",
  19: "Science: Mathematics",
  20: "Mythology",
  21: "Sports",
  22: "Geography",
  23: "History",
  24: "Politics",
  25: "Art",
  26: "Celebrities",
  27: "Animals",
  28: "Vehicles",
  29: "Entertainment: Comics",
  30: "Science: Gadgets",
  31: "Anime & Manga",
  32: "Cartoon & Animations",
};

export const SCIENCE_CATEGORIES: Record<number, string> = {
  17: "Science & Nature",
  18: "Science: Computers",
  19: "Science: Mathematics",
  27: "Animals",
  30: "Science: Gadgets",
};

// ============================================================================
// API Client
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class OpenTDBClient {
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
   * Fetch questions from OpenTDB
   */
  async fetchQuestions(input: FetchQuestionsInput): Promise<FetchQuestionsResult> {
    return this.request<FetchQuestionsResult>("/api/v1/opentdb/fetch", {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  /**
   * Get all available categories
   */
  async getCategories(): Promise<CategoriesResult> {
    return this.request<CategoriesResult>("/api/v1/opentdb/categories");
  }

  /**
   * Check API health
   */
  async getHealth(): Promise<any> {
    return this.request<any>("/api/v1/opentdb/health");
  }

  /**
   * Import OpenTDB questions into local vector store
   */
  async importQuestions(input: FetchQuestionsInput): Promise<ImportResult> {
    return this.request<ImportResult>("/api/v1/opentdb/import", {
      method: "POST",
      body: JSON.stringify(input),
    });
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

const opentdbClient = new OpenTDBClient();

export default opentdbClient;

// ============================================================================
// React Hooks
// ============================================================================

import { useState, useCallback } from "react";

/**
 * Hook for fetching questions from OpenTDB
 */
export function useOpenTDBQuestions() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FetchQuestionsResult | null>(null);

  const fetchQuestions = useCallback(async (input: FetchQuestionsInput) => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await opentdbClient.fetchQuestions(input);
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

  return { fetchQuestions, isLoading, error, result };
}

/**
 * Hook for getting OpenTDB categories
 */
export function useOpenTDBCategories() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [categories, setCategories] = useState<CategoriesResult | null>(null);

  const fetchCategories = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await opentdbClient.getCategories();
      setCategories(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Auto-fetch on mount
  useCallback(() => {
    fetchCategories();
  }, [fetchCategories])();

  return { categories, isLoading, error, refetch: fetchCategories };
}

/**
 * Hook for importing OpenTDB questions
 */
export function useImportOpenTDB() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);

  const importQuestions = useCallback(async (input: FetchQuestionsInput) => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await opentdbClient.importQuestions(input);
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
 * Hook for checking OpenTDB health
 */
export function useOpenTDBHealth() {
  const [isLoading, setIsLoading] = useState(false);
  const [health, setHealth] = useState<any>(null);

  const checkHealth = useCallback(async () => {
    setIsLoading(true);

    try {
      const data = await opentdbClient.getHealth();
      setHealth(data);
    } catch (err) {
      setHealth({
        status: "unhealthy",
        api_available: false,
        error: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Auto-check on mount
  useCallback(() => {
    checkHealth();
  }, [checkHealth])();

  return { health, isLoading, checkHealth };
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Pre-configured fetch inputs for common use cases
 */
export const OpenTDBPresets = {
  scienceMedium: {
    amount: 20,
    difficulty: "medium" as const,
    science_only: true,
  },
  scienceEasy: {
    amount: 20,
    difficulty: "easy" as const,
    science_only: true,
  },
  scienceHard: {
    amount: 20,
    difficulty: "hard" as const,
    science_only: true,
  },
  mathQuestions: {
    amount: 20,
    category: 19, // Science: Mathematics
    difficulty: "medium" as const,
    science_only: false,
  },
  biologyQuestions: {
    amount: 20,
    category: 17, // Science & Nature (includes biology)
    difficulty: "medium" as const,
    science_only: false,
  },
  allScience: {
    amount: 50,
    science_only: true,
  },
} as const;

/**
 * Get a nice display name for a category
 */
export function getCategoryName(categoryId: number): string {
  return OPENTDB_CATEGORIES[categoryId] || `Category ${categoryId}`;
}

/**
 * Get all science category IDs
 */
export function getScienceCategoryIds(): number[] {
  return Object.keys(SCIENCE_CATEGORIES).map(Number);
}

/**
 * Format a question for display
 */
export function formatQuestion(question: OpenTDBQuestion): string {
  if (question.type === "boolean") {
    // True/False questions
    return `${question.question} (True/False)`;
  } else {
    // Multiple choice
    const allAnswers = [
      question.correct_answer,
      ...question.incorrect_answers
    ];
    return `${question.question}\n\nOptions: ${allAnswers.join(", ")}`;
  }
}

/**
 * Check if an answer is correct
 */
export function checkAnswer(question: OpenTDBQuestion, answer: string): boolean {
  // Normalize for comparison (case-insensitive, trim whitespace)
  const normalize = (str: string) => str.trim().toLowerCase();
  return normalize(answer) === normalize(question.correct_answer);
}

export default OpenTDBPresets;
