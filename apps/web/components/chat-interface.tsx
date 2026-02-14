"use client";

import { useState } from "react";
import { useMode } from "@/components/providers/mode-provider";
import { CitationTooltip } from "./citation-tooltip";
import { getDemoResponse, type DemoQueryResponse } from "@/lib/demo-data";
import {
  QueryResponseSchema,
  type QueryResponse,
  type Citation,
  type Translation,
  validateApiResponse,
} from "@/lib/api/schemas";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  translation?: Translation;
  isDemo?: boolean;
}

interface ChatInterfaceProps {
  onCitationClick: (paragraphId: string) => void;
}

export function ChatInterface({ onCitationClick }: ChatInterfaceProps) {
  const { mode } = useMode();
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usingDemoData, setUsingDemoData] = useState(false);

  // Use environment variable for API URL with secure default
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    // Sanitize user input to prevent XSS
    const sanitizedMessage = message.trim().replace(/<[^>]*>/g, "");

    const userMessage: ChatMessage = {
      role: "user",
      content: sanitizedMessage,
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentMessage = sanitizedMessage;
    setMessage("");
    setError(null);
    setIsLoading(true);

    // Create abort controller for request cancellation
    const abortController = new AbortController();

    try {
      // Generate CSRF token for this request
      const csrfToken = crypto.randomUUID();

      const res = await fetch(`${API_BASE}/api/v2/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({
          query: currentMessage,
          context: {
            chapter_id: "photosynthesis-101",
            mode,
          },
        }),
        signal: abortController.signal,
      });

      if (!res.ok) {
        throw new Error(`API returned ${res.status}: ${res.statusText}`);
      }

      const rawData = await res.json();

      // Validate API response with Zod schema
      const data = validateApiResponse(rawData, QueryResponseSchema, "query response");

      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: data.answer,
        citations: data.sources,
        translation: data.translation,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setUsingDemoData(false);
    } catch (err) {
      // Handle abort separately
      if (err instanceof Error && err.name === "AbortError") {
        console.log("Request was cancelled");
        return;
      }

      // Fallback to demo data if API fails
      console.log("API unavailable, using demo data");
      const demoResponse = getDemoResponse(currentMessage);

      if (demoResponse) {
        const assistantMessage: ChatMessage = {
          role: "assistant",
          content: demoResponse.answer,
          citations: demoResponse.sources,
          translation: demoResponse.translation,
          isDemo: true,
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setUsingDemoData(true);
      } else {
        const errorMessage = err instanceof Error ? err.message : "Unknown error";
        setError(`Failed to connect to API: ${errorMessage}. Make sure the backend is running on ${API_BASE}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Chat Header */}
      <header className="sticky top-0 z-10 bg-[color:var(--bg-primary)] border-b border-[color:var(--border)] p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">AI Co-Pilot</h2>
            <p className="text-sm text-[color:var(--text-secondary)]">
              Your learning assistant
            </p>
          </div>
          <div
            className="text-xs px-3 py-1 bg-[color:var(--accent)]/10 text-[color:var(--accent)] rounded-full"
            aria-label="AI assistant"
          >
            AI
          </div>
        </div>
      </header>

      {/* Chat Messages */}
      <div
        className="flex-1 overflow-y-auto p-6 space-y-6"
        role="log"
        aria-live="polite"
        aria-atomic="false"
      >
        {/* Demo Data Notice */}
        {usingDemoData && (
          <div
            className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-sm text-yellow-500"
            role="alert"
            aria-live="polite"
          >
            <p>Demo Mode: Using sample data. Connect to the backend API at {API_BASE} for live responses.</p>
          </div>
        )}

        {/* Welcome Message */}
        {messages.length === 0 && !usingDemoData && (
          <div className="text-center py-12">
            <div className="text-4xl mb-4" role="img" aria-label="Robot face">
              🤖
            </div>
            <h3 className="text-lg font-semibold mb-2">
              Hello! I'm your AI learning assistant
            </h3>
            <p className="text-[color:var(--text-secondary)] max-w-md mx-auto">
              Ask me anything about the textbook content on the left. I'll provide answers with citations to help you learn better.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {[
                "What is photosynthesis?",
                "How does light energy get converted?",
                "What factors affect photosynthesis?",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setMessage(suggestion)}
                  className="text-sm px-4 py-2 bg-[color:var(--border)] hover:bg-[color:var(--accent)]/10 rounded-full transition-colors"
                  aria-label={`Ask: ${suggestion}`}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            role="article"
            aria-label={`${msg.role === "user" ? "Your" : "Assistant's"} message`}
          >
            <div
              className={`max-w-[85%] rounded-2xl p-4 ${
                msg.role === "user"
                  ? "bg-[color:var(--accent)] text-[color:var(--bg-primary)]"
                  : "bg-[color:var(--border)] text-[color:var(--text-primary)]"
              }`}
            >
              {/* Safely render content - prevent XSS */}
              <p className="leading-relaxed">{msg.content}</p>

              {/* Citations */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-black/10" role="group" aria-label="Sources">
                  <p className="text-xs font-semibold mb-2 opacity-70">
                    Sources:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {msg.citations.map((citation) => (
                      <CitationTooltip
                        key={citation.source_id}
                        citation={citation}
                        onClick={() => onCitationClick(citation.paragraph_id)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Translation (Simplified + Metaphor) */}
              {msg.translation && (
                <div className="mt-3 pt-3 border-t border-black/10 space-y-2">
                  <p className="text-xs font-semibold opacity-70">
                    Simplified explanation:
                  </p>
                  <p className="text-sm italic opacity-90">
                    {msg.translation.simplified}
                  </p>
                  {msg.translation.metaphor && (
                    <>
                      <p className="text-xs font-semibold opacity-70 mt-2">
                        Metaphor:
                      </p>
                      <p className="text-sm opacity-90">
                        {msg.translation.metaphor}
                      </p>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Error Message */}
        {error && (
          <div
            className="p-4 border border-red-500/50 rounded-lg bg-red-500/10"
            role="alert"
            aria-live="assertive"
          >
            <p className="font-semibold text-red-500">Error</p>
            <p className="text-sm text-[color:var(--text-secondary)] mt-1">{error}</p>
          </div>
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-[color:var(--border)] rounded-2xl p-4">
              <div className="flex items-center gap-2">
                <div
                  className="w-2 h-2 bg-[color:var(--accent)] rounded-full animate-bounce"
                  style={{ animationDelay: "0ms" }}
                  aria-hidden="true"
                />
                <div
                  className="w-2 h-2 bg-[color:var(--accent)] rounded-full animate-bounce"
                  style={{ animationDelay: "150ms" }}
                  aria-hidden="true"
                />
                <div
                  className="w-2 h-2 bg-[color:var(--accent)] rounded-full animate-bounce"
                  style={{ animationDelay: "300ms" }}
                  aria-hidden="true"
                />
                <span className="sr-only">Loading response...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Chat Input */}
      <form onSubmit={handleSubmit} className="p-6 border-t border-[color:var(--border)]">
        <div className="flex gap-3">
          <label htmlFor="chat-input" className="sr-only">
            Your question
          </label>
          <input
            id="chat-input"
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask about photosynthesis..."
            className="flex-1 px-4 py-3 bg-[color:var(--bg-primary)] border border-[color:var(--border)] rounded-full focus:outline-none focus:ring-2 focus:ring-[color:var(--accent)]"
            disabled={isLoading}
            autoComplete="off"
          />
          <button
            type="submit"
            disabled={isLoading || !message.trim()}
            className="px-6 py-3 bg-[color:var(--accent)] text-[color:var(--bg-primary)] font-semibold rounded-full hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[color:var(--accent)] disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            aria-label="Send message"
          >
            Send
          </button>
        </div>
        <p className="text-xs text-[color:var(--text-secondary)] mt-2 text-center">
          Press Ctrl+Tab to switch between textbook and chat
        </p>
      </form>
    </div>
  );
}
