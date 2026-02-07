"use client";

/**
 * High Contrast Focus Layout - Mu2 Cognitive OS
 * ============================================
 *
 * WCAG AAA compliant layout with maximum contrast.
 * Designed for students who are struggling or have visual impairments.
 *
 * Features:
 * - 7:1+ contrast ratio (exceeds WCAG AAA)
 * - Large, scalable fonts
 * - Generous spacing
 * - Clear focus indicators
 * - Reduced motion by default
 */

import { useEffect } from "react";
import { BookOpen, AlertCircle } from "lucide-react";

interface HighContrastLayoutProps {
  children: React.ReactNode;
  onModeExit?: () => void;
}

export function HighContrastFocusLayout({ children, onModeExit }: HighContrastLayoutProps) {
  useEffect(() => {
    // Apply WCAG AAA contrast styles
    document.documentElement.style.setProperty("--bg-primary", "#000000");
    document.documentElement.style.setProperty("--text-primary", "#FFFFFF");
    document.documentElement.style.setProperty("--border", "#FFFFFF");
    document.documentElement.style.setProperty("--accent", "#FFFF00");

    // Force reduced motion
    document.documentElement.classList.add("force-reduced-motion");

    // Announce to screen readers
    const announcement = document.createElement("div");
    announcement.setAttribute("role", "status");
    announcement.setAttribute("aria-live", "polite");
    announcement.setAttribute("aria-atomic", "true");
    announcement.className = "sr-only";
    announcement.textContent =
      "High contrast focus mode activated. Maximum contrast enabled for better readability.";
    document.body.appendChild(announcement);

    setTimeout(() => {
      if (announcement.parentNode) {
        document.body.removeChild(announcement);
      }
    }, 3000);

    return () => {
      // Cleanup on unmount
      document.documentElement.classList.remove("force-reduced-motion");
    };
  }, []);

  return (
    <div
      className="high-contrast-focus-layout"
      style={{
        backgroundColor: "#000000",
        color: "#FFFFFF",
        minHeight: "100vh",
        padding: "2rem",
        lineHeight: 2,
      }}
    >
      {/* Mode Header */}
      <header
        className="mode-header"
        style={{
          borderBottom: "3px solid #FFFF00",
          paddingBottom: "1.5rem",
          marginBottom: "2rem",
        }}
        role="banner"
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <h1
              style={{
                fontSize: "2rem",
                fontWeight: 700,
                margin: 0,
                letterSpacing: "0.02em",
              }}
            >
              <AlertCircle style={{ display: "inline", marginRight: "0.5rem" }} aria-hidden="true" />
              High Contrast Focus Mode
            </h1>
            <p
              style={{
                fontSize: "1.25rem",
                marginTop: "0.5rem",
                color: "#FFFF00",
              }}
            >
              Maximum contrast for better readability
            </p>
          </div>

          {onModeExit && (
            <button
              onClick={onModeExit}
              style={{
                padding: "1rem 2rem",
                fontSize: "1.125rem",
                fontWeight: 700,
                backgroundColor: "#FFFF00",
                color: "#000000",
                border: "3px solid #FFFFFF",
                cursor: "pointer",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
              aria-label="Exit high contrast focus mode"
            >
              Exit Focus Mode
            </button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main
        role="main"
        style={{
          maxWidth: "80ch",
          margin: "0 auto",
          fontSize: "1.25rem",
        }}
      >
        {/* Help Banner */}
        <div
          role="alert"
          style={{
            backgroundColor: "#FFFF00",
            color: "#000000",
            padding: "1.5rem",
            marginBottom: "2rem",
            border: "3px solid #FFFFFF",
            fontSize: "1.125rem",
            fontWeight: 600,
          }}
        >
          <BookOpen style={{ display: "inline", marginRight: "0.5rem" }} aria-hidden="true" />
          Need help? Your teacher has been notified.
        </div>

        {/* Content */}
        <div style={{ minHeight: "50vh" }}>
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer
        role="contentinfo"
        style={{
          marginTop: "3rem",
          paddingTop: "2rem",
          borderTop: "3px solid #FFFF00",
          fontSize: "1rem",
          textAlign: "center",
        }}
      >
        <p style={{ margin: 0, color: "#CCCCCC" }}>
          AI generated. Always verify with source text.
        </p>
      </footer>
    </div>
  );
}

/**
 * High contrast text input component
 */
export function HighContrastInput({
  label,
  value,
  onChange,
  placeholder = "",
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  type?: string;
}) {
  const inputId = `hc-input-${label.toLowerCase().replace(/\s+/g, "-")}`;

  return (
    <div style={{ marginBottom: "1.5rem" }}>
      <label
        htmlFor={inputId}
        style={{
          display: "block",
          fontSize: "1.25rem",
          fontWeight: 700,
          marginBottom: "0.75rem",
        }}
      >
        {label}
      </label>
      <input
        id={inputId}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        style={{
          width: "100%",
          padding: "1rem",
          fontSize: "1.25rem",
          backgroundColor: "#000000",
          color: "#FFFFFF",
          border: "3px solid #FFFFFF",
          outline: "none",
        }}
        onFocus={(e) => {
          e.target.style.borderColor = "#FFFF00";
          e.target.style.borderWidth = "4px";
        }}
        onBlur={(e) => {
          e.target.style.borderColor = "#FFFFFF";
          e.target.style.borderWidth = "3px";
        }}
      />
    </div>
  );
}

/**
 * High contrast button component
 */
export function HighContrastButton({
  children,
  onClick,
  variant = "primary",
  disabled = false,
}: {
  children: React.ReactNode;
  onClick: () => void;
  variant?: "primary" | "secondary";
  disabled?: boolean;
}) {
  const baseStyles = {
    padding: "1rem 2rem",
    fontSize: "1.125rem",
    fontWeight: 700,
    cursor: disabled ? "not-allowed" : "pointer",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
    border: "3px solid",
    transition: "none", // No transitions for reduced motion
  };

  const primaryStyles = {
    ...baseStyles,
    backgroundColor: "#FFFF00",
    color: "#000000",
    borderColor: "#FFFFFF",
    opacity: disabled ? 0.5 : 1,
  };

  const secondaryStyles = {
    ...baseStyles,
    backgroundColor: "#000000",
    color: "#FFFFFF",
    borderColor: "#FFFF00",
    opacity: disabled ? 0.5 : 1,
  };

  const styles = variant === "primary" ? primaryStyles : secondaryStyles;

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={styles}
      aria-disabled={disabled}
    >
      {children}
    </button>
  );
}

/**
 * High contrast card component
 */
export function HighContrastCard({
  title,
  children,
  warning = false,
}: {
  title: string;
  children: React.ReactNode;
  warning?: boolean;
}) {
  return (
    <div
      style={{
        backgroundColor: "#000000",
        border: warning ? "4px solid #FFFF00" : "3px solid #FFFFFF",
        padding: "2rem",
        marginBottom: "1.5rem",
      }}
      role="article"
    >
      <h2
        style={{
          fontSize: "1.5rem",
          fontWeight: 700,
          marginTop: 0,
          marginBottom: "1rem",
          color: warning ? "#FFFF00" : "#FFFFFF",
        }}
      >
        {title}
      </h2>
      <div style={{ fontSize: "1.125rem", lineHeight: 1.8 }}>
        {children}
      </div>
    </div>
  );
}

export default HighContrastFocusLayout;
