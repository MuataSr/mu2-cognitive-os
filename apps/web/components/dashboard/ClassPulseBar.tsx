"use client";

import { type MasteryStatus } from "@/lib/api/mastery";

/**
 * ClassPulseBar - Horizontal stacked bar chart showing class status distribution
 *
 * Displays three segments:
 * - GREEN: Ready (MASTERED)
 * - YELLOW: Distracted (LEARNING)
 * - RED: Intervention (STRUGGLING)
 *
 * Clickable segments allow filtering the student grid by status.
 */

interface ClassPulseBarProps {
  countReady: number;
  countDistracted: number;
  countIntervention: number;
  activeFilter: "all" | "ready" | "distracted" | "intervention";
  onFilterChange: (filter: "all" | "ready" | "distracted" | "intervention") => void;
}

export function ClassPulseBar({
  countReady,
  countDistracted,
  countIntervention,
  activeFilter,
  onFilterChange,
}: ClassPulseBarProps) {
  const total = countReady + countDistracted + countIntervention;

  if (total === 0) {
    return (
      <div className="bg-[color:var(--bg-secondary)] rounded-lg p-4 mb-6">
        <p className="text-[color:var(--text-secondary)] text-center">No student data available</p>
      </div>
    );
  }

  const readyPercent = (countReady / total) * 100;
  const distractedPercent = (countDistracted / total) * 100;
  const interventionPercent = (countIntervention / total) * 100;

  const getFilterClass = (filter: "all" | "ready" | "distracted" | "intervention") => {
    return activeFilter === filter
      ? "ring-2 ring-[color:var(--accent)] ring-offset-2 ring-offset-[color:var(--bg-primary)]"
      : "hover:opacity-80";
  };

  return (
    <div className="bg-[color:var(--bg-secondary)] rounded-lg p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Class Pulse</h2>
        <div className="flex gap-2 text-sm">
          <button
            onClick={() => onFilterChange("all")}
            className={`px-3 py-1 rounded transition-colors ${
              activeFilter === "all"
                ? "bg-[color:var(--accent)] text-[color:var(--bg-primary)]"
                : "bg-[color:var(--bg-primary)] text-[color:var(--text-secondary)] hover:bg-[color:var(--border)]"
            }`}
          >
            All ({total})
          </button>
        </div>
      </div>

      {/* Stacked Bar */}
      <div className="relative h-12 rounded-lg overflow-hidden flex cursor-pointer">
        {/* Ready (Green) */}
        <button
          onClick={() => onFilterChange("ready")}
          className={`bg-green-500 hover:bg-green-600 transition-colors flex items-center justify-center text-sm font-medium ${getFilterClass(
            "ready"
          )}`}
          style={{ width: `${readyPercent}%` }}
          aria-label={`Filter by ready students (${countReady})`}
        >
          {readyPercent > 10 && <span className="text-white drop-shadow">{countReady}</span>}
        </button>

        {/* Distracted (Yellow) */}
        <button
          onClick={() => onFilterChange("distracted")}
          className={`bg-yellow-500 hover:bg-yellow-600 transition-colors flex items-center justify-center text-sm font-medium ${getFilterClass(
            "distracted"
          )}`}
          style={{ width: `${distractedPercent}%` }}
          aria-label={`Filter by learning students (${countDistracted})`}
        >
          {distractedPercent > 10 && <span className="text-white drop-shadow">{countDistracted}</span>}
        </button>

        {/* Intervention (Red) */}
        <button
          onClick={() => onFilterChange("intervention")}
          className={`bg-red-500 hover:bg-red-600 transition-colors flex items-center justify-center text-sm font-medium ${getFilterClass(
            "intervention"
          )}`}
          style={{ width: `${interventionPercent}%` }}
          aria-label={`Filter by students needing intervention (${countIntervention})`}
        >
          {interventionPercent > 10 && <span className="text-white drop-shadow">{countIntervention}</span>}
        </button>
      </div>

      {/* Legend */}
      <div className="flex gap-4 mt-3 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500" aria-hidden="true" />
          <span className="text-[color:var(--text-secondary)]">Ready</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-yellow-500" aria-hidden="true" />
          <span className="text-[color:var(--text-secondary)]">Distracted</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500" aria-hidden="true" />
          <span className="text-[color:var(--text-secondary)]">Needs Help</span>
        </div>
      </div>
    </div>
  );
}
