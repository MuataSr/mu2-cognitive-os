"use client";

import { memo } from "react";
import {
  getStatusColor,
  formatLastActive,
  maskStudentId,
  formatMasteryPercentage,
  type StudentCardOutput,
  type MasteryStatus,
} from "@/lib/api/mastery";

/**
 * StudentCard - Individual student display card
 * Memoized to prevent unnecessary re-renders during polling
 */
interface StudentCardProps {
  student: StudentCardOutput;
  onClick: () => void;
  userRole: "teacher" | "researcher";
}

const StudentCard = memo(function StudentCard({ student, onClick, userRole }: StudentCardProps) {
  const getBorderClass = (status: MasteryStatus): string => {
    switch (status) {
      case "MASTERED":
        return "border-green-500";
      case "STRUGGLING":
        return "border-red-500 animate-pulse";
      default:
        return "border-[color:var(--border)]";
    }
  };

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
    <div
      className={`bg-[color:var(--bg-secondary)] rounded-lg p-4 border-2 hover:shadow-lg hover:border-[color:var(--accent)] transition-all cursor-pointer ${getBorderClass(
        student.overall_status
      )}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          onClick();
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
          <span className="font-semibold">{maskStudentId(student.user_id, userRole)}</span>
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
  );
});

/**
 * StudentGrid - Responsive grid of student cards
 *
 * Displays students in a responsive grid layout (1-4 columns based on screen size).
 * Filtered by the selected status filter from ClassPulseBar.
 */
interface StudentGridProps {
  students: StudentCardOutput[];
  onStudentClick: (userId: string) => void;
  filter: "all" | "ready" | "distracted" | "intervention";
  userRole: "teacher" | "researcher";
}

export function StudentGrid({ students, onStudentClick, filter, userRole }: StudentGridProps) {
  // Filter students based on selected filter
  const filteredStudents = students.filter((student) => {
    switch (filter) {
      case "ready":
        return student.overall_status === "MASTERED";
      case "distracted":
        return student.overall_status === "LEARNING";
      case "intervention":
        return student.overall_status === "STRUGGLING";
      default:
        return true;
    }
  });

  if (filteredStudents.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-[color:var(--text-secondary)]">
          {filter === "all"
            ? "No students found"
            : `No students matching the ${filter} filter`}
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {filteredStudents.map((student) => (
        <StudentCard
          key={student.user_id}
          student={student}
          onClick={() => onStudentClick(student.user_id)}
          userRole={userRole}
        />
      ))}
    </div>
  );
}
