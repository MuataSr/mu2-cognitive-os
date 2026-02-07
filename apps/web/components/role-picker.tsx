"use client";

import Link from "next/link";
import { Users, BookOpen, Sparkles } from "lucide-react";

/**
 * Role Picker Landing Page Component
 *
 * WCAG 2.1 AA Compliance:
 * - Semantic HTML with proper heading hierarchy
 * - Full keyboard navigation support
 * - ARIA labels for screen readers
 * - Focus-visible indicators
 * - High contrast colors in both modes
 */

export function RolePicker() {
  const roles = [
    {
      id: "teacher",
      title: "Teacher",
      description: "Command Center for real-time student mastery tracking",
      href: "/teacher",
      icon: Users,
      color: "from-blue-500/20 to-blue-600/20",
      borderColor: "border-blue-500/30",
      hoverBorder: "hover:border-blue-500",
    },
    {
      id: "student",
      title: "Student",
      description: "Personalized learning with AI-powered textbook assistance",
      href: "/student",
      icon: BookOpen,
      color: "from-green-500/20 to-green-600/20",
      borderColor: "border-green-500/30",
      hoverBorder: "hover:border-green-500",
    },
  ];

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6 bg-[color:var(--bg-primary)]">
      {/* Hero Section */}
      <div className="text-center mb-16 max-w-3xl">
        <div className="flex items-center justify-center gap-3 mb-6">
          <Sparkles className="w-10 h-10 text-[color:var(--accent)]" aria-hidden="true" />
          <h1 className="text-5xl font-bold tracking-tight">Mu2 Cognitive OS</h1>
        </div>
        <p className="text-xl text-[color:var(--text-secondary)] leading-relaxed">
          A FERPA-compliant, local-only adaptive learning platform with intelligent
          comprehension tracking and AI-powered assistance.
        </p>
      </div>

      {/* Role Selection */}
      <div className="w-full max-w-4xl">
        <h2 className="text-2xl font-semibold text-center mb-8">
          I am a...
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {roles.map((role) => {
            const Icon = role.icon;
            return (
              <Link
                key={role.id}
                href={role.href}
                className={`
                  group relative bg-gradient-to-br ${role.color}
                  border-2 ${role.borderColor} ${role.hoverBorder}
                  rounded-2xl p-8 transition-all duration-300
                  hover:shadow-2xl hover:scale-[1.02]
                  focus:outline-none focus:ring-2 focus:ring-[color:var(--accent)]
                  focus:ring-offset-2 focus:ring-offset-[color:var(--bg-primary)]
                `}
                onKeyDown={(e) => {
                  // Enhance keyboard navigation
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    window.location.href = role.href;
                  }
                }}
                aria-label={`Continue as ${role.title}`}
              >
                {/* Icon */}
                <div className="mb-6">
                  <div className="w-16 h-16 rounded-xl bg-[color:var(--bg-primary)] border border-[color:var(--border)] flex items-center justify-center group-hover:border-[color:var(--accent)] transition-colors">
                    <Icon className="w-8 h-8 text-[color:var(--accent)]" aria-hidden="true" />
                  </div>
                </div>

                {/* Title */}
                <h3 className="text-2xl font-bold mb-3">
                  {role.title}
                </h3>

                {/* Description */}
                <p className="text-[color:var(--text-secondary)] leading-relaxed">
                  {role.description}
                </p>

                {/* Arrow indicator */}
                <div className="mt-6 flex items-center gap-2 text-[color:var(--accent)] font-medium group-hover:gap-3 transition-all">
                  <span>Enter</span>
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 7l5 5m0 0l-5 5m5-5H6"
                    />
                  </svg>
                </div>

                {/* Focus Mode indicator */}
                <div className="sr-only">
                  Press Enter to continue as {role.title}
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Footer Info */}
      <div className="mt-16 text-center text-sm text-[color:var(--text-secondary)]">
        <p className="mb-2">
          All data stays local • No external connections • FERPA compliant
        </p>
        <p className="flex items-center justify-center gap-2">
          <span>Press</span>
          <kbd className="px-2 py-1 rounded bg-[color:var(--bg-secondary)] border border-[color:var(--border)] text-xs">
            Tab
          </kbd>
          <span>to navigate, </span>
          <kbd className="px-2 py-1 rounded bg-[color:var(--bg-secondary)] border border-[color:var(--border)] text-xs">
            Enter
          </kbd>
          <span>to select</span>
        </p>
      </div>
    </main>
  );
}
