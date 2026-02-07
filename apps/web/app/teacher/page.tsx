"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  getClassMastery,
  getStudentMastery,
  getStatusColor,
  formatLastActive,
  maskStudentId,
  formatMasteryPercentage,
  type MasteryStatus,
  type StudentCardOutput,
  type StudentSkillsOutput,
  type ClassOverviewOutput,
} from "@/lib/api/mastery";

/**
 * Teacher Command Center (Dashboard)
 *
 * "Air Traffic Control" view for real-time student mastery tracking
 * - Red/Yellow/Green status indicators
 * - Real-time updates (5-second polling)
 * - FERPA-compliant data masking
 */

export default function TeacherDashboard() {
  const [students, setStudents] = useState<StudentCardOutput[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<string | null>(null);
  const [studentDetails, setStudentDetails] = useState<StudentSkillsOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "struggling">("all");
  const [userRole, setUserRole] = useState<"teacher" | "researcher">("teacher");
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Fetch students data
  const fetchStudents = useCallback(async () => {
    try {
      setError(null);
      const data: ClassOverviewOutput = await getClassMastery({
        strugglingOnly: filter === "struggling",
      });
      setStudents(data.students);
      setLastUpdate(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load students");
      console.error("Error fetching students:", err);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  // Fetch student details
  const fetchStudentDetails = useCallback(async (userId: string) => {
    try {
      const data: StudentSkillsOutput = await getStudentMastery(userId);
      setStudentDetails(data);
    } catch (err) {
      console.error("Error fetching student details:", err);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchStudents();
  }, [fetchStudents]);

  // Real-time updates via polling (5-second interval)
  useEffect(() => {
    const interval = setInterval(() => {
      fetchStudents();
    }, 5000);

    return () => clearInterval(interval);
  }, [fetchStudents]);

  // Fetch details when student is selected
  useEffect(() => {
    if (selectedStudent) {
      fetchStudentDetails(selectedStudent);
    }
  }, [selectedStudent, fetchStudentDetails]);

  const getStatusLabel = (status: MasteryStatus): string => {
    switch (status) {
      case "MASTERED":
        return "Mastered";
      case "LEARNING":
        return "In Progress";
      case "STRUGGLING":
        return "Needs Help";
      default:
        return "Unknown";
    }
  };

  return (
    <div className="min-h-screen bg-[color:var(--bg-primary)] p-6">
      {/* Header */}
      <header className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold mb-2">Teacher Command Center</h1>
            <p className="text-[color:var(--text-secondary)]">
              Air Traffic Control for Student Learning
            </p>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="px-4 py-2 rounded-lg bg-[color:var(--accent)] text-[color:var(--bg-primary)] hover:opacity-90 transition-opacity"
            >
              Back to Learning
            </Link>
          </div>
        </div>

        {/* Status Bar */}
        <div className="flex items-center gap-6 text-sm text-[color:var(--text-secondary)]">
          <span>Total Students: {students.length}</span>
          <span className="text-red-500">
            Struggling: {students.filter((s) => s.overall_status === "STRUGGLING").length}
          </span>
          <span className="text-yellow-500">
            Learning: {students.filter((s) => s.overall_status === "LEARNING").length}
          </span>
          <span className="text-green-500">
            Mastered: {students.filter((s) => s.overall_status === "MASTERED").length}
          </span>
          <span>
            Last updated: {lastUpdate.toLocaleTimeString()}
          </span>
        </div>
      </header>

      {/* Filters */}
      <div className="mb-6 flex items-center gap-4">
        <div className="flex gap-2">
          <button
            onClick={() => setFilter("all")}
            className={`px-4 py-2 rounded-lg transition-colors ${
              filter === "all"
                ? "bg-[color:var(--accent)] text-[color:var(--bg-primary)]"
                : "bg-[color:var(--bg-secondary)] hover:bg-[color:var(--border)]"
            }`}
          >
            All Students
          </button>
          <button
            onClick={() => setFilter("struggling")}
            className={`px-4 py-2 rounded-lg transition-colors ${
              filter === "struggling"
                ? "bg-red-600 text-white"
                : "bg-[color:var(--bg-secondary)] hover:bg-[color:var(--border)]"
            }`}
          >
            Needs Help Only
          </button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[color:var(--accent)]"></div>
          <p className="mt-4 text-[color:var(--text-secondary)]">Loading students...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500 rounded-lg p-4 mb-6">
          <p className="text-red-500">Error: {error}</p>
        </div>
      )}

      {/* Students Grid */}
      {!loading && !error && students.length === 0 && (
        <div className="text-center py-12">
          <p className="text-[color:var(--text-secondary)]">No students found</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {students.map((student) => (
          <div
            key={student.user_id}
            className="bg-[color:var(--bg-secondary)] rounded-lg p-4 border border-[color:var(--border)] hover:shadow-lg hover:border-[color:var(--accent)] transition-all cursor-pointer"
            onClick={() => setSelectedStudent(student.user_id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                setSelectedStudent(student.user_id);
              }
            }}
            aria-label={`View details for ${student.masked_id}`}
          >
            {/* Student Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div
                  className={`w-3 h-3 rounded-full ${getStatusColor(student.overall_status)}`}
                  aria-label={`Status: ${getStatusLabel(student.overall_status)}`}
                />
                <span className="font-semibold">
                  {maskStudentId(student.user_id, userRole)}
                </span>
              </div>
              <span className="text-xs text-[color:var(--text-secondary)]">
                {formatLastActive(student.last_active)}
              </span>
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-3 gap-2 mb-3 text-center">
              <div className="bg-[color:var(--bg-primary)] rounded p-2">
                <div className="text-xs text-[color:var(--text-secondary)]">Mastered</div>
                <div className="text-lg font-bold text-green-500">{student.mastered_count}</div>
              </div>
              <div className="bg-[color:var(--bg-primary)] rounded p-2">
                <div className="text-xs text-[color:var(--text-secondary)]">Learning</div>
                <div className="text-lg font-bold text-yellow-500">{student.learning_count}</div>
              </div>
              <div className="bg-[color:var(--bg-primary)] rounded p-2">
                <div className="text-xs text-[color:var(--text-secondary)]">Struggling</div>
                <div className="text-lg font-bold text-red-500">{student.struggling_count}</div>
              </div>
            </div>

            {/* Average Mastery */}
            <div className="mb-2">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-[color:var(--text-secondary)]">Average Mastery</span>
                <span className="font-semibold">{formatMasteryPercentage(student.avg_mastery)}</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className="bg-[color:var(--accent)] h-2 rounded-full transition-all duration-500"
                  style={{ width: formatMasteryPercentage(student.avg_mastery) }}
                />
              </div>
            </div>

            {/* Overall Status Badge */}
            <div className="mt-2 text-center">
              <span
                className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                  student.overall_status === "MASTERED"
                    ? "bg-green-500/20 text-green-500"
                    : student.overall_status === "STRUGGLING"
                    ? "bg-red-500/20 text-red-500"
                    : "bg-yellow-500/20 text-yellow-500"
                }`}
              >
                {getStatusLabel(student.overall_status)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Student Detail Modal */}
      {selectedStudent && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedStudent(null)}
        >
          <div
            className="bg-[color:var(--bg-primary)] rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold">
                {maskStudentId(selectedStudent, userRole)}
              </h2>
              <button
                onClick={() => setSelectedStudent(null)}
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

                {/* Skills List */}
                <h3 className="text-lg font-semibold mb-4">Skill Breakdown</h3>
                <div className="space-y-3">
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
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
