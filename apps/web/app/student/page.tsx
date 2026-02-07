"use client";

import { SplitBookLayout } from "@/components/split-book-layout";
import Link from "next/link";
import { ArrowLeft, Home } from "lucide-react";

/**
 * Student Learning Page
 *
 * Displays the split-screen textbook + chat interface for students.
 * Includes a navigation link back to the role picker landing page.
 */
export default function StudentPage() {
  return (
    <div className="relative">
      {/* Home Navigation */}
      <Link
        href="/"
        className="fixed top-4 left-4 z-50 flex items-center gap-2 px-4 py-2 rounded-lg bg-[color:var(--bg-primary)] border border-[color:var(--border)] hover:border-[color:var(--accent)] transition-colors focus:outline-none focus:ring-2 focus:ring-[color:var(--accent)]"
        aria-label="Return to home"
      >
        <Home className="w-4 h-4" aria-hidden="true" />
        <span className="text-sm font-medium">Home</span>
      </Link>

      {/* Student Learning View */}
      <SplitBookLayout chapterId="photosynthesis-101" />
    </div>
  );
}
