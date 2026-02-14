"use client";

import { Component, ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary Component
 *
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI instead of crashing
 * the entire application.
 *
 * WCAG 2.1 AA Compliance:
 * - Proper error announcement to screen readers
 * - Clear error messaging
 * - Recovery mechanism available
 */
export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log the error to console (in production, send to error tracking service)
    console.error("Error Boundary caught an error:", error, errorInfo);

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div
          className="min-h-screen flex items-center justify-center p-6 bg-[color:var(--kd-black)]"
          role="alert"
          aria-live="assertive"
        >
          <div className="kd-card p-8 max-w-md w-full text-center">
            <div
              className="text-6xl mb-4"
              role="img"
              aria-label="Warning icon"
            >
              ⚠️
            </div>
            <h1 className="kd-title text-2xl mb-4 text-[color:var(--kd-red)]">
              Something Went Wrong
            </h1>
            <p className="text-[color:var(--kd-text-muted)] mb-6">
              We encountered an unexpected error. You can try refreshing the page,
              or return to the home screen.
            </p>

            {/* Show error details in development */}
            {process.env.NODE_ENV === "development" && this.state.error && (
              <details className="mb-6 text-left">
                <summary className="cursor-pointer text-sm text-[color:var(--kd-text-muted)] hover:text-[color:var(--kd-white)] mb-2">
                  Error Details (Development Only)
                </summary>
                <pre className="text-xs bg-[color:var(--kd-black)] p-4 rounded-kd overflow-auto max-h-40 text-red-400">
                  {this.state.error.toString()}
                  {"\n"}
                  {this.state.error.stack}
                </pre>
              </details>
            )}

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={this.handleReset}
                className="kd-btn"
                aria-label="Try again"
              >
                Try Again
              </button>
              <a
                href="/"
                className="px-6 py-3 bg-[color:var(--kd-dark-grey)] border border-[color:var(--kd-slate)] rounded-kd text-[color:var(--kd-white)] font-semibold hover:bg-[color:var(--kd-slate)] focus:outline-none focus:ring-2 focus:ring-[color:var(--kd-red)] transition-colors"
                aria-label="Return to home page"
              >
                Go Home
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Hook version for functional components
 * Note: Error boundaries must be class components, but this wrapper
 * makes it easier to use in functional component patterns.
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, "children">
): React.ComponentType<P> {
  return function WithErrorBoundaryWrapper(props: P) {
    return (
      <ErrorBoundary {...errorBoundaryProps}>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
}
