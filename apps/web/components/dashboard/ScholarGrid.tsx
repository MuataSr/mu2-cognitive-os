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
 * ScholarCard - Individual scholar display card
 * Memoized to prevent unnecessary re-renders during polling
 */
interface ScholarCardProps {
  student: StudentCardOutput;
  onClick: () => void;
  userRole: "teacher" | "researcher";
}

const ScholarCard = memo(function ScholarCard({ student, onClick, userRole }: ScholarCardProps) {
  const getBorderClass = (status: MasteryStatus): string => {
    switch (status) {
      case "MASTERED":
        return "border-green-500";
      case "STRUGGLING":
        return "border-[color:var(--kd-red)] animate-pulse";
      default:
        return "border-[color:var(--kd-slate)]";
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

  // Determine if scholar is "active" (online/engaged)
  const isActive = student.overall_status === "LEARNING" || student.overall_status === "MASTERED";

  return (
    <div
      className={`kd-card p-4 border-2 hover:border-[color:var(--kd-red)] hover:shadow-[0_0_20px_var(--kd-red-glow)] transition-all cursor-pointer ${getBorderClass(
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
      {/* Scholar Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {/* Pulse dot for active scholars */}
          <div className="flex items-center gap-2">
            {isActive ? (
              <span className="kd-pulse-dot kd-pulse-active" aria-label="Active" />
            ) : (
              <span className="kd-pulse-dot bg-gray-500" aria-label="Inactive" />
            )}
            <span className="kd-title font-semibold text-sm">
              {maskStudentId(student.user_id, userRole)}
            </span>
          </div>
        </div>
        <span className="text-xs text-[color:var(--kd-text-muted)]">
          {formatLastActive(student.last_active)}
        </span>
      </div>

      {/* Current Focus (mock) */}
      <div className="text-xs text-[color:var(--kd-text-muted)] mb-3">
        Current Focus: <span className="text-[color:var(--kd-white)]">Quadratic Equations</span>
      </div>

      {/* Mastery Progress */}
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-[color:var(--kd-text-muted)]">MASTERY</span>
          <span className="font-semibold text-[color:var(--kd-red)]">
            {formatMasteryPercentage(student.avg_mastery)}
          </span>
        </div>
        <div className="h-1 bg-[color:var(--kd-slate)] rounded-full overflow-hidden">
          <div
            className="h-full bg-[color:var(--kd-red)] transition-all duration-500"
            style={{ width: formatMasteryPercentage(student.avg_mastery) }}
          />
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-[color:var(--kd-black)] rounded-kd p-2">
          <div className="text-xs text-[color:var(--kd-text-muted)]">Mastered</div>
          <div className="text-sm font-bold text-green-500">{student.mastered_count}</div>
        </div>
        <div className="bg-[color:var(--kd-black)] rounded-kd p-2">
          <div className="text-xs text-[color:var(--kd-text-muted)]">Learning</div>
          <div className="text-sm font-bold text-yellow-500">{student.learning_count}</div>
        </div>
        <div className="bg-[color:var(--kd-black)] rounded-kd p-2">
          <div className="text-xs text-[color:var(--kd-text-muted)]">Struggling</div>
          <div className="text-sm font-bold text-[color:var(--kd-red)]">{student.struggling_count}</div>
        </div>
      </div>

      {/* Overall Status Badge */}
      <div className="mt-3 text-center">
        <span
          className={`inline-block px-2 py-1 rounded-kd text-xs font-semibold ${
            student.overall_status === "MASTERED"
              ? "bg-green-500/20 text-green-500"
              : student.overall_status === "STRUGGLING"
              ? "bg-[color:var(--kd-red)]/20 text-[color:var(--kd-red)]"
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
 * ScholarGrid - Responsive grid of scholar cards
 *
 * Displays scholars in a responsive grid layout (1-4 columns based on screen size).
 * Filtered by the selected status filter from MasteryStatsBar.
 */
interface ScholarGridProps {
  students: StudentCardOutput[];
  onStudentClick: (userId: string) => void;
  filter: "all" | "ready" | "distracted" | "intervention";
  userRole: "teacher" | "researcher";
}

export function ScholarGrid({ students, onStudentClick, filter, userRole }: ScholarGridProps) {
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
        <p className="text-[color:var(--kd-text-muted)]">
          {filter === "all"
            ? "No scholars found"
            : `No scholars matching the ${filter} filter`}
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {filteredStudents.map((student) => (
        <ScholarCard
          key={student.user_id}
          student={student}
          onClick={() => onStudentClick(student.user_id)}
          userRole={userRole}
        />
      ))}
    </div>
  );
}
