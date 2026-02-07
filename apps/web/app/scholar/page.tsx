"use client";

import { SplitBookLayout } from "@/components/split-book-layout";
import Link from "next/link";
import { ArrowLeft, Home } from "lucide-react";

/**
 * Scholar Quest - Learning Page
 *
 * Displays the split-screen textbook + chat interface for scholars.
 * Includes a navigation link back to the role picker landing page.
 */
export default function ScholarPage() {
  return (
    <div className="relative">
      {/* Home Navigation */}
      <Link
        href="/"
        className="kd-card fixed top-4 left-4 z-50 flex items-center gap-2 px-4 py-2 hover:border-[color:var(--kd-red)] transition-colors focus:outline-none focus:ring-2 focus:ring-[color:var(--kd-red)]"
        aria-label="Return to home"
      >
        <Home className="w-4 h-4" aria-hidden="true" />
        <span className="text-sm font-medium">Home</span>
      </Link>

      {/* Scholar Learning View */}
      <SplitBookLayout chapterId="photosynthesis-101" />
    </div>
  );
}
