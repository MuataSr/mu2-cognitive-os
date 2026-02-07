"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

/**
 * Role Picker Landing Page Component - Kut Different Branding
 *
 * WCAG 2.1 AA Compliance:
 * - Semantic HTML with proper heading hierarchy
 * - Full keyboard navigation support
 * - ARIA labels for screen readers
 * - Focus-visible indicators
 * - High contrast colors
 */

export function RolePicker() {
  const roles = [
    {
      id: "mentor",
      title: "MENTOR",
      description: "Command center for real-time scholarship tracking and scholar support.",
      href: "/mentor",
      enterText: "ENTER HUB",
    },
    {
      id: "scholar",
      title: "SCHOLAR",
      description: "Own your journey. Access your personal AI-powered knowledge base.",
      href: "/scholar",
      enterText: "OWN YOUR GREATNESS",
    },
  ];

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6 bg-[color:var(--kd-black)]">
      {/* Hero Section */}
      <div className="text-center mb-16 max-w-3xl">
        <h1 className="kd-title text-5xl md:text-6xl mb-4 text-[color:var(--kd-red)]">
          KUT DIFFERENT
        </h1>
        <p className="text-lg md:text-xl text-[color:var(--kd-text-muted)] leading-relaxed max-w-2xl mx-auto">
          MU2 COGNITIVE OS: Guiding young men to own their greatness through local, adaptive intelligence.
        </p>
      </div>

      {/* Role Selection */}
      <div className="w-full max-w-4xl">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {roles.map((role) => (
            <Link
              key={role.id}
              href={role.href}
              className={`
                kd-card p-10 md:p-14 relative overflow-hidden group
                transition-all duration-300
                hover:shadow-[0_0_30px_var(--kd-red-glow)]
                focus:outline-none focus:ring-2 focus:ring-[color:var(--kd-red)]
                focus:ring-offset-2 focus:ring-offset-[color:var(--kd-black)]
              `}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  window.location.href = role.href;
                }
              }}
              aria-label={`Continue as ${role.title}`}
            >
              {/* Watermark - shows on hover */}
              <div className="absolute bottom-[-10px] right-[-10px] opacity-0 group-hover:opacity-[0.03] transition-opacity duration-300 pointer-events-none">
                <span className="kd-title text-4xl md:text-5xl whitespace-nowrap">
                  OWN YOUR GREATNESS
                </span>
              </div>

              {/* Title */}
              <h3 className="kd-title text-3xl md:text-4xl mb-4 text-[color:var(--kd-white)]">
                {role.title}
              </h3>

              {/* Description */}
              <p className="text-[color:var(--kd-text-muted)] leading-relaxed mb-8 min-h-[3rem]">
                {role.description}
              </p>

              {/* Arrow indicator */}
              <div className="flex items-center gap-3 text-[color:var(--kd-red)] font-bold uppercase tracking-wider group-hover:gap-4 transition-all">
                <span className="text-sm">{role.enterText}</span>
                <ArrowRight className="w-5 h-5" aria-hidden="true" />
              </div>

              {/* Screen reader text */}
              <div className="sr-only">
                Press Enter to continue as {role.title}
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Footer Info */}
      <div className="mt-16 text-center text-sm text-[color:var(--kd-text-muted)]">
        <p className="mb-2">
          All data stays local • No external connections • FERPA compliant
        </p>
        <p className="flex items-center justify-center gap-2">
          <span>Press</span>
          <kbd className="px-2 py-1 rounded-kd bg-[color:var(--kd-dark-grey)] border border-[color:var(--kd-slate)] text-xs">
            Tab
          </kbd>
          <span>to navigate, </span>
          <kbd className="px-2 py-1 rounded-kd bg-[color:var(--kd-dark-grey)] border border-[color:var(--kd-slate)] text-xs">
            Enter
          </kbd>
          <span>to select</span>
        </p>
      </div>
    </main>
  );
}
