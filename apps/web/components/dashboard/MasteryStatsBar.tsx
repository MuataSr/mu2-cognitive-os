"use client";

import { type MasteryStatus } from "@/lib/api/mastery";

/**
 * MasteryStatsBar - Kut Different styled stats bar showing class overview
 *
 * Displays four stat cards:
 * - Active Scholars (total count)
 * - Connectedness % (average)
 * - Motivation Index % (average)
 * - Need Intervention (count)
 *
 * Also includes a horizontal stacked bar for filtering:
 * - GREEN: Mastered
 * - YELLOW: Learning
 * - RED: Struggling
 */

interface MasteryStatsBarProps {
  countReady: number;
  countDistracted: number;
  countIntervention: number;
  activeFilter: "all" | "ready" | "distracted" | "intervention";
  onFilterChange: (filter: "all" | "ready" | "distracted" | "intervention") => void;
}

export function MasteryStatsBar({
  countReady,
  countDistracted,
  countIntervention,
  activeFilter,
  onFilterChange,
}: MasteryStatsBarProps) {
  const total = countReady + countDistracted + countIntervention;

  // Calculate average metrics (mock data for now - would come from API)
  const avgConnectedness = 89;
  const avgMotivation = 94;

  if (total === 0) {
    return (
      <div className="kd-card p-4 mb-6">
        <p className="text-[color:var(--kd-text-muted)] text-center">No scholar data available</p>
      </div>
    );
  }

  const readyPercent = (countReady / total) * 100;
  const distractedPercent = (countDistracted / total) * 100;
  const interventionPercent = (countIntervention / total) * 100;

  const getFilterClass = (filter: "all" | "ready" | "distracted" | "intervention") => {
    return activeFilter === filter
      ? "ring-2 ring-[color:var(--kd-red)] ring-offset-2 ring-offset-[color:var(--kd-black)]"
      : "hover:opacity-80";
  };

  return (
    <div className="mb-6">
      {/* Stats Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {/* Active Scholars */}
        <div className="kd-card p-5 border-l-4 border-l-[color:var(--kd-red)]">
          <div className="text-3xl font-bold text-[color:var(--kd-red)] mb-1">
            {total}
          </div>
          <div className="text-xs uppercase text-[color:var(--kd-text-muted)] tracking-wider">
            Active Scholars
          </div>
        </div>

        {/* Connectedness */}
        <div className="kd-card p-5 border-l-4 border-l-[color:var(--kd-red)]">
          <div className="text-3xl font-bold text-[color:var(--kd-red)] mb-1">
            {avgConnectedness}%
          </div>
          <div className="text-xs uppercase text-[color:var(--kd-text-muted)] tracking-wider">
            Avg. Connectedness
          </div>
        </div>

        {/* Motivation Index */}
        <div className="kd-card p-5 border-l-4 border-l-[color:var(--kd-red)]">
          <div className="text-3xl font-bold text-[color:var(--kd-red)] mb-1">
            {avgMotivation}%
          </div>
          <div className="text-xs uppercase text-[color:var(--kd-text-muted)] tracking-wider">
            Motivation Index
          </div>
        </div>

        {/* Need Intervention */}
        <div className="kd-card p-5 border-l-4 border-l-[color:var(--kd-red)]">
          <div className="text-3xl font-bold text-[color:var(--kd-red)] mb-1">
            {countIntervention}
          </div>
          <div className="text-xs uppercase text-[color:var(--kd-text-muted)] tracking-wider">
            Need Intervention
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="kd-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="kd-title text-lg">Filter by Status</h2>
          <div className="flex gap-2 text-sm">
            <button
              onClick={() => onFilterChange("all")}
              className={`px-3 py-1 rounded-kd transition-colors ${
                activeFilter === "all"
                  ? "bg-[color:var(--kd-red)] text-white"
                  : "bg-[color:var(--kd-dark-grey)] text-[color:var(--kd-text-muted)] hover:bg-[color:var(--kd-slate)]"
              }`}
            >
              All ({total})
            </button>
          </div>
        </div>

        {/* Stacked Bar */}
        <div className="relative h-12 rounded-kd overflow-hidden flex cursor-pointer">
          {/* Mastered (Green) */}
          <button
            onClick={() => onFilterChange("ready")}
            className={`bg-green-500 hover:bg-green-600 transition-colors flex items-center justify-center text-sm font-semibold ${getFilterClass(
              "ready"
            )}`}
            style={{ width: `${readyPercent}%` }}
            aria-label={`Filter by mastered scholars (${countReady})`}
          >
            {readyPercent > 10 && <span className="text-white drop-shadow">{countReady}</span>}
          </button>

          {/* Learning (Yellow) */}
          <button
            onClick={() => onFilterChange("distracted")}
            className={`bg-yellow-500 hover:bg-yellow-600 transition-colors flex items-center justify-center text-sm font-semibold ${getFilterClass(
              "distracted"
            )}`}
            style={{ width: `${distractedPercent}%` }}
            aria-label={`Filter by learning scholars (${countDistracted})`}
          >
            {distractedPercent > 10 && <span className="text-white drop-shadow">{countDistracted}</span>}
          </button>

          {/* Struggling (Red) */}
          <button
            onClick={() => onFilterChange("intervention")}
            className={`bg-[color:var(--kd-red)] hover:bg-red-600 transition-colors flex items-center justify-center text-sm font-semibold ${getFilterClass(
              "intervention"
            )}`}
            style={{ width: `${interventionPercent}%` }}
            aria-label={`Filter by scholars needing intervention (${countIntervention})`}
          >
            {interventionPercent > 10 && <span className="text-white drop-shadow">{countIntervention}</span>}
          </button>
        </div>

        {/* Legend */}
        <div className="flex gap-4 mt-3 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500" aria-hidden="true" />
            <span className="text-[color:var(--kd-text-muted)]">Mastered</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500" aria-hidden="true" />
            <span className="text-[color:var(--kd-text-muted)]">Learning</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[color:var(--kd-red)]" aria-hidden="true" />
            <span className="text-[color:var(--kd-text-muted)]">Needs Help</span>
          </div>
        </div>
      </div>
    </div>
  );
}
