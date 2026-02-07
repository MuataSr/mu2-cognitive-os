/**
 * Chameleon Orchestrator - Mu2 Cognitive OS
 * =========================================
 *
 * Receives signals from LangGraph and hot-swaps UI modes.
 *
 * This is the "engine" that:
 * 1. Evaluates behavioral signals from backend
 * 2. Selects appropriate UI mode from registry
 * 3. Executes smooth transition with ARIA announcements
 * 4. Respects user preferences (reduced motion, etc.)
 */

import { UIMode, TransitionStyle, UI_MODE_REGISTRY, getModeById, isValidModeId } from "./registry";

// ============================================================================
// Behavioral Signal Types
// ============================================================================

export interface BehavioralSignal {
  type: string;
  value?: any;
  confidence: number;
  timestamp: number;
}

export interface BehavioralState {
  user_id: string;
  is_frustrated: boolean;
  is_engaged: boolean;
  is_struggling: boolean;
  consecutive_errors: number;
  time_on_task_seconds: number;
  suggested_mode: string;
  urgency: "none" | "attention" | "intervention";
  confidence: number;
  reasoning: string[];
}

// ============================================================================
// Orchestrator Configuration
// ============================================================================

export interface OrchestratorConfig {
  respect_reduced_motion: boolean;
  transition_duration_ms: number;
  announcement_delay_ms: number;
  enable_auto_switch: boolean;
  min_confidence_threshold: number;
}

const DEFAULT_CONFIG: OrchestratorConfig = {
  respect_reduced_motion: true,
  transition_duration_ms: 300,
  announcement_delay_ms: 100,
  enable_auto_switch: true,
  min_confidence_threshold: 0.5
};

// ============================================================================
// Transition Types
// ============================================================================

export type ModeTransition = {
  from: UIMode | null;
  to: UIMode;
  transition_style: TransitionStyle;
  reason: string;
  timestamp: number;
};

export type TransitionListener = (transition: ModeTransition) => void;

// ============================================================================
// Chameleon Orchestrator Class
// ============================================================================

export class ChameleonOrchestrator {
  private currentMode: UIMode;
  private registry: UIMode[];
  private config: OrchestratorConfig;
  private listeners: Set<TransitionListener>;
  private transitionHistory: ModeTransition[];
  private readonly MAX_HISTORY = 50;

  constructor(
    initialMode: UIMode = UI_MODE_REGISTRY[0],
    config: Partial<OrchestratorConfig> = {}
  ) {
    this.currentMode = initialMode;
    this.registry = UI_MODE_REGISTRY;
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.listeners = new Set();
    this.transitionHistory = [];
  }

  /**
   * Evaluate trigger conditions and select appropriate mode
   */
  async evaluateMode(signals: BehavioralState): Promise<UIMode> {
    // If auto-switch is disabled, return current mode
    if (!this.config.enable_auto_switch) {
      return this.currentMode;
    }

    // Check confidence threshold
    if (signals.confidence < this.config.min_confidence_threshold) {
      return this.currentMode; // Not confident enough to switch
    }

    // Check for urgent intervention
    if (signals.urgency === "intervention") {
      const interventionMode = this.findModeById("intervention") || this.findModeById("high_contrast_focus");
      if (interventionMode && interventionMode.id !== this.currentMode.id) {
        return interventionMode;
      }
    }

    // Check suggested mode from backend
    if (signals.suggested_mode && signals.suggested_mode !== this.currentMode.id) {
      const suggested = this.findModeById(signals.suggested_mode);
      if (suggested) {
        return suggested;
      }
    }

    // Evaluate each mode's trigger conditions
    for (const mode of this.registry) {
      if (mode.id === this.currentMode.id) continue; // Skip current mode

      if (this.matchesTriggers(mode, signals)) {
        return mode;
      }
    }

    // Default: stay in current mode
    return this.currentMode;
  }

  /**
   * Transition to new mode with ARIA announcement
   */
  async transitionTo(
    newMode: UIMode,
    reason: string = "Manual mode change"
  ): Promise<void> {
    if (newMode.id === this.currentMode.id) {
      return; // Already in this mode
    }

    const transition: ModeTransition = {
      from: this.currentMode,
      to: newMode,
      transition_style: this.selectTransitionStyle(newMode),
      reason,
      timestamp: Date.now()
    };

    // Store in history
    this.transitionHistory.push(transition);
    if (this.transitionHistory.length > this.MAX_HISTORY) {
      this.transitionHistory.shift();
    }

    // Announce to screen readers
    this.announceModeChange(newMode, reason);

    // Apply mode to document
    this.applyModeToDocument(newMode);

    // Check reduced motion preference
    const prefersReduced = this.config.respect_reduced_motion &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Add transition class
    const transitionClass = prefersReduced
      ? 'snap-transition'
      : `${newMode.transition_style}-transition`;

    document.documentElement.classList.add(transitionClass);

    // Remove transition class after animation
    setTimeout(() => {
      document.documentElement.classList.remove(transitionClass);
    }, this.config.transition_duration_ms);

    // Update current mode
    const previousMode = this.currentMode;
    this.currentMode = newMode;

    // Notify listeners
    this.notifyListeners(transition);
  }

  /**
   * Get current mode
   */
  getCurrentMode(): UIMode {
    return this.currentMode;
  }

  /**
   * Get transition history
   */
  getTransitionHistory(): ModeTransition[] {
    return [...this.transitionHistory];
  }

  /**
   * Add transition listener
   */
  addListener(listener: TransitionListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Update configuration
   */
  updateConfig(updates: Partial<OrchestratorConfig>): void {
    this.config = { ...this.config, ...updates };
  }

  // ==========================================================================
  // Private Methods
  // ==========================================================================

  private matchesTriggers(mode: UIMode, signals: BehavioralState): boolean {
    return mode.trigger_conditions.some(condition => {
      switch (condition.type) {
        case "frustration_detected":
          return signals.is_frustrated;

        case "consecutive_errors":
          return signals.consecutive_errors >= (condition.threshold || 3);

        case "time_spent":
          return signals.time_on_task_seconds >= (condition.threshold || 120);

        case "struggling":
          return signals.is_struggling;

        case "low_engagement":
          return !signals.is_engaged;

        case "default":
        case "manual_toggle":
        case "manual_request":
          return false; // These require explicit action

        default:
          return false;
      }
    });
  }

  private selectTransitionStyle(newMode: UIMode): TransitionStyle {
    // Respect user's reduced motion preference
    if (this.config.respect_reduced_motion) {
      const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (prefersReduced) {
        return "snap";
      }
    }

    // Use the mode's preferred transition style
    return newMode.transition_style;
  }

  private announceModeChange(newMode: UIMode, reason: string): void {
    // Create announcement element
    const announcement = document.createElement("div");
    announcement.setAttribute("role", "status");
    announcement.setAttribute("aria-live", "polite");
    announcement.setAttribute("aria-atomic", "true");
    announcement.className = "sr-only";

    // Build announcement message
    const message = `Switching to ${newMode.name}. ${newMode.description}`;
    announcement.textContent = message;

    // Add to DOM
    document.body.appendChild(announcement);

    // Remove after announcement
    setTimeout(() => {
      if (announcement.parentNode) {
        document.body.removeChild(announcement);
      }
    }, this.config.announcement_delay_ms + 1000);
  }

  private applyModeToDocument(mode: UIMode): void {
    // Set data-mode attribute
    document.documentElement.setAttribute("data-mode", mode.id);

    // Set color scheme
    document.documentElement.setAttribute("data-color-scheme", mode.color_scheme);

    // Apply font scale
    document.documentElement.style.setProperty("--font-scale", mode.font_scale.toString());

    // Apply line height
    document.documentElement.style.setProperty("--line-height", mode.line_height.toString());

    // Apply accessibility classes
    if (mode.reduced_motion) {
      document.documentElement.classList.add("force-reduced-motion");
    } else {
      document.documentElement.classList.remove("force-reduced-motion");
    }

    // Store in localStorage for persistence
    try {
      localStorage.setItem("mu2-current-mode", mode.id);
    } catch (e) {
      // Silently fail if localStorage is not available
    }
  }

  private notifyListeners(transition: ModeTransition): void {
    this.listeners.forEach(listener => {
      try {
        listener(transition);
      } catch (e) {
        console.error("Error in transition listener:", e);
      }
    });
  }

  private findModeById(id: string): UIMode | undefined {
    return this.registry.find(mode => mode.id === id);
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

let orchestratorInstance: ChameleonOrchestrator | null = null;

export function getOrchestrator(config?: Partial<OrchestratorConfig>): ChameleonOrchestrator {
  if (!orchestratorInstance) {
    // Try to restore saved mode from localStorage
    let initialMode = UI_MODE_REGISTRY[0]; // Default to standard

    try {
      const savedModeId = localStorage.getItem("mu2-current-mode");
      if (savedModeId && isValidModeId(savedModeId)) {
        const savedMode = getModeById(savedModeId);
        if (savedMode) {
          initialMode = savedMode;
        }
      }
    } catch (e) {
      // Silently fail, use default mode
    }

    orchestratorInstance = new ChameleonOrchestrator(initialMode, config);
  }

  return orchestratorInstance;
}

export function resetOrchestrator(): void {
  orchestratorInstance = null;
}

// ============================================================================
// React Hook Integration
// ============================================================================

/**
 * Hook to access the orchestrator in React components
 */
export function useChameleonOrchestrator() {
  const orchestrator = getOrchestrator();

  return {
    currentMode: orchestrator.getCurrentMode(),
    transitionTo: async (modeId: string, reason?: string) => {
      const mode = getModeById(modeId);
      if (mode) {
        await orchestrator.transitionTo(mode, reason);
      }
    },
    evaluateMode: async (signals: BehavioralState) => {
      const suggestedMode = await orchestrator.evaluateMode(signals);
      if (suggestedMode.id !== orchestrator.getCurrentMode().id) {
        await orchestrator.transitionTo(
          suggestedMode,
          signals.reasoning.join("; ")
        );
      }
    },
    getHistory: () => orchestrator.getTransitionHistory(),
    addListener: orchestrator.addListener.bind(orchestrator)
  };
}

export default ChameleonOrchestrator;
