"use client";

import { useState } from "react";
import {
  getStatusColor,
  formatMasteryPercentage,
  maskStudentId,
  formatLastActive,
  type StudentSkillsOutput,
  type LiveFeedEvent,
} from "@/lib/api/mastery";

/**
 * StudentDetailModal - Modal showing detailed student information
 *
 * Displays two tabs:
 * - Skills: Current skill breakdown with mastery levels
 * - Citations: List of learning events with source text
 */

interface StudentDetailModalProps {
  studentId: string;
  studentDetails: StudentSkillsOutput | null;
  onClose: () => void;
  userRole: "teacher" | "researcher";
}

type TabType = "skills" | "citations";

export function StudentDetailModal({
  studentId,
  studentDetails,
  onClose,
  userRole,
}: StudentDetailModalProps) {
  const [activeTab, setActiveTab] = useState<TabType>("skills");

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-[color:var(--bg-primary)] rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">{maskStudentId(studentId, userRole)}</h2>
          <button
            onClick={onClose}
            className="text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)] transition-colors"
            aria-label="Close details"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Loading Details */}
        {!studentDetails && (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[color:var(--accent)]"></div>
            <p className="mt-4 text-[color:var(--text-secondary)]">Loading details...</p>
          </div>
        )}

        {/* Student Details */}
        {studentDetails && (
          <>
            {/* Summary */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-[color:var(--bg-secondary)] rounded-lg p-4 text-center">
                <div className="text-3xl font-bold text-green-500">
                  {studentDetails.mastered_count}
                </div>
                <div className="text-sm text-[color:var(--text-secondary)]">Mastered</div>
              </div>
              <div className="bg-[color:var(--bg-secondary)] rounded-lg p-4 text-center">
                <div className="text-3xl font-bold text-yellow-500">
                  {studentDetails.learning_count}
                </div>
                <div className="text-sm text-[color:var(--text-secondary)]">Learning</div>
              </div>
              <div className="bg-[color:var(--bg-secondary)] rounded-lg p-4 text-center">
                <div className="text-3xl font-bold text-red-500">
                  {studentDetails.struggling_count}
                </div>
                <div className="text-sm text-[color:var(--text-secondary)]">Struggling</div>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 mb-4 border-b border-[color:var(--border)]">
              <button
                onClick={() => setActiveTab("skills")}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === "skills"
                    ? "text-[color:var(--accent)] border-b-2 border-[color:var(--accent)]"
                    : "text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)]"
                }`}
              >
                Skills
              </button>
              <button
                onClick={() => setActiveTab("citations")}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === "citations"
                    ? "text-[color:var(--accent)] border-b-2 border-[color:var(--accent)]"
                    : "text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)]"
                }`}
              >
                Citations
              </button>
            </div>

            {/* Skills Tab */}
            {activeTab === "skills" && (
              <div className="space-y-3">
                <h3 className="text-lg font-semibold mb-4">Skill Breakdown</h3>
                {studentDetails.skills.map((skill) => (
                  <div
                    key={skill.skill_id}
                    className="bg-[color:var(--bg-secondary)] rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-2 h-2 rounded-full ${getStatusColor(skill.status.status)}`}
                        />
                        <span className="font-medium">{skill.skill_name}</span>
                      </div>
                      <span className="text-sm font-semibold">
                        {formatMasteryPercentage(skill.probability_mastery)}
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-gray-700 rounded-full h-2 mb-2">
                      <div
                        className={`h-2 rounded-full transition-all duration-500 ${
                          skill.status.status === "MASTERED"
                            ? "bg-green-500"
                            : skill.status.status === "STRUGGLING"
                            ? "bg-red-500"
                            : "bg-yellow-500"
                        }`}
                        style={{ width: formatMasteryPercentage(skill.probability_mastery) }}
                      />
                    </div>

                    {/* Stats */}
                    <div className="flex items-center justify-between text-sm text-[color:var(--text-secondary)]">
                      <span>
                        {skill.correct_attempts}/{skill.total_attempts} correct
                      </span>
                      <span>{skill.status.suggested_action}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Citations Tab */}
            {activeTab === "citations" && (
              <div className="space-y-3">
                <h3 className="text-lg font-semibold mb-4">Learning Events</h3>
                {studentDetails.recent_events.length === 0 ? (
                  <p className="text-[color:var(--text-secondary)] text-center py-8">
                    No recent events available
                  </p>
                ) : (
                  studentDetails.recent_events.map((event, index) => (
                    <div
                      key={`${event.timestamp}-${index}`}
                      className="bg-[color:var(--bg-secondary)] rounded-lg p-4"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          {event.source_text && (
                            <p className="font-medium mb-1">{event.source_text}</p>
                          )}
                          <div className="flex items-center gap-3 text-sm text-[color:var(--text-secondary)]">
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded ${
                              event.event_type === "AGENT_ACTION"
                                ? "bg-[color:var(--accent)]/20 text-[color:var(--accent)]"
                                : "bg-blue-500/20 text-blue-400"
                            }`}>
                              {event.event_type === "AGENT_ACTION" ? "🤖 Agent" : "👤 Student"}
                            </span>
                            <span>{formatLastActive(event.timestamp)}</span>
                          </div>
                        </div>
                      </div>

                      {/* Metadata */}
                      {Object.keys(event.metadata).length > 0 && (
                        <div className="mt-2 pt-2 border-t border-[color:var(--border)]">
                          <p className="text-xs text-[color:var(--text-secondary)]">
                            Metadata: {JSON.stringify(event.metadata)}
                          </p>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
