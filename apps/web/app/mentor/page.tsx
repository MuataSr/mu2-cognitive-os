"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  getClassMastery,
  getStudentMastery,
  type StudentCardOutput,
  type StudentSkillsOutput,
  type ClassOverviewOutput,
} from "@/lib/api/mastery";
import { MasteryStatsBar } from "@/components/dashboard/MasteryStatsBar";
import { ScholarGrid } from "@/components/dashboard/ScholarGrid";
import { LiveFeedSidebar } from "@/components/dashboard/LiveFeedSidebar";
import { ScholarDetailModal } from "@/components/dashboard/ScholarDetailModal";

/**
 * Mentor Command Center - Real-Time Monitoring Dashboard
 *
 * "Air Traffic Control" view for real-time scholar mastery tracking
 * - MasteryStatsBar: Horizontal stacked bar showing class status distribution
 * - ScholarGrid: Filterable grid of scholar cards
 * - LiveFeedSidebar: Real-time event timeline
 * - FERPA-compliant data masking
 */

type FilterType = "all" | "ready" | "distracted" | "intervention";

export default function MentorDashboard() {
  const [students, setStudents] = useState<StudentCardOutput[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<string | null>(null);
  const [studentDetails, setStudentDetails] = useState<StudentSkillsOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterType>("all");
  const [userRole, setUserRole] = useState<"teacher" | "researcher">("teacher");
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Class statistics from the API
  const [countReady, setCountReady] = useState(0);
  const [countDistracted, setCountDistracted] = useState(0);
  const [countIntervention, setCountIntervention] = useState(0);

  // Fetch students data
  const fetchStudents = useCallback(async () => {
    try {
      setError(null);
      const data: ClassOverviewOutput = await getClassMastery({
        strugglingOnly: false,
      });
      setStudents(data.students);

      // Update statistics from API response
      setCountReady(data.count_ready);
      setCountDistracted(data.count_distracted);
      setCountIntervention(data.count_intervention);

      setLastUpdate(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load scholars");
      console.error("Error fetching scholars:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch student details
  const fetchStudentDetails = useCallback(async (userId: string) => {
    try {
      const data: StudentSkillsOutput = await getStudentMastery(userId);
      setStudentDetails(data);
    } catch (err) {
      console.error("Error fetching scholar details:", err);
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

  // Clear details when modal closes
  const handleCloseModal = () => {
    setSelectedStudent(null);
    setStudentDetails(null);
  };

  // Calculate statistics if API doesn't provide them
  const calculatedStats = {
    ready: students.filter((s) => s.overall_status === "MASTERED").length,
    distracted: students.filter((s) => s.overall_status === "LEARNING").length,
    intervention: students.filter((s) => s.overall_status === "STRUGGLING").length,
  };

  // Use API stats if available, otherwise calculate from students
  const displayReady = countReady || calculatedStats.ready;
  const displayDistracted = countDistracted || calculatedStats.distracted;
  const displayIntervention = countIntervention || calculatedStats.intervention;

  return (
    <div className="min-h-screen bg-[color:var(--kd-black)] p-6">
      {/* Header */}
      <header className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="kd-title text-3xl mb-1">Mentor Command Center</h1>
            <p className="text-[color:var(--kd-text-muted)]">
              Real-Time Monitoring Dashboard
            </p>
          </div>
          <Link
            href="/"
            className="kd-btn"
            aria-label="Return to home"
          >
            Back to Home
          </Link>
        </div>
      </header>

      {/* MasteryStatsBar */}
      <MasteryStatsBar
        countReady={displayReady}
        countDistracted={displayDistracted}
        countIntervention={displayIntervention}
        activeFilter={filter}
        onFilterChange={setFilter}
      />

      {/* Main Layout: Grid + Sidebar */}
      <div className="flex gap-6">
        {/* Scholar Grid (Main Area) */}
        <div className="flex-1">
          {/* Status Bar */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-6 text-sm text-[color:var(--kd-text-muted)]">
              <span>Showing: {filter === "all" ? "All Scholars" : filter.charAt(0).toUpperCase() + filter.slice(1)}</span>
              <span>Total: {students.length}</span>
              <span>Last updated: {lastUpdate.toLocaleTimeString()}</span>
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[color:var(--kd-red)]"></div>
              <p className="mt-4 text-[color:var(--kd-text-muted)]">Loading scholars...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-500/10 border border-red-500 rounded-kd p-4 mb-6">
              <p className="text-red-500">Error: {error}</p>
            </div>
          )}

          {/* Scholars Grid */}
          {!loading && !error && (
            <ScholarGrid
              students={students}
              onStudentClick={setSelectedStudent}
              filter={filter}
              userRole={userRole}
            />
          )}
        </div>

        {/* Live Feed Sidebar (Right) */}
        <div className="w-80 flex-shrink-0">
          <LiveFeedSidebar refreshInterval={5000} maxVisible={10} />
        </div>
      </div>

      {/* Scholar Detail Modal */}
      {selectedStudent && (
        <ScholarDetailModal
          studentId={selectedStudent}
          studentDetails={studentDetails}
          onClose={handleCloseModal}
          userRole={userRole}
        />
      )}
    </div>
  );
}
