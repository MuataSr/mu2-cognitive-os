"use client";

/**
 * useExplorationMode Hook - Mu2 Cognitive OS
 * =========================================
 *
 * React hook for managing the 3D Exploration Mode.
 *
 * Provides:
 * - Content loading for different 3D models
 * - Mode entry/exit handlers
 * - WebGL detection
 * - Keyboard shortcuts
 */

import { useState, useCallback, useEffect } from "react";
import { ExplorationLayout, LearningContent, ModelType, SAMPLE_CONTENT } from "@/components/modes/exploration-layout";

export interface UseExplorationModeOptions {
  onModeEnter?: () => void;
  onModeExit?: () => void;
  defaultContent?: LearningContent;
}

export interface UseExplorationModeReturn {
  /** Whether exploration mode is active */
  isActive: boolean;
  /** Current content being displayed */
  content: LearningContent | null;
  /** Enter exploration mode with specific content */
  enterMode: (content: LearningContent) => void;
  /** Exit exploration mode */
  exitMode: () => void;
  /** Load new content while in mode */
  loadContent: (contentKey: string) => void;
  /** Whether WebGL is supported */
  webglSupported: boolean;
  /** Available sample content */
  sampleContent: typeof SAMPLE_CONTENT;
}

/**
 * Hook for managing 3D Exploration Mode
 *
 * @example
 * ```tsx
 * const { isActive, content, enterMode, exitMode } = useExplorationMode();
 *
 * return (
 *   <>
 *     <button onClick={() => enterMode(SAMPLE_CONTENT.photosynthesis)}>
 *       View 3D Model
 *     </button>
 *
 *     {isActive && content && (
 *       <ExplorationLayout
 *         content={content}
 *         onModeExit={exitMode}
 *       />
 *     )}
 *   </>
 * );
 * ```
 */
export function useExplorationMode(options: UseExplorationModeOptions = {}): UseExplorationModeReturn {
  const [isActive, setIsActive] = useState(false);
  const [content, setContent] = useState<LearningContent | null>(options.defaultContent || null);
  const [webglSupported, setWebglSupported] = useState(true);

  // Check WebGL support on mount
  useEffect(() => {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
    setWebglSupported(!!gl);

    // Cleanup canvas
    canvas.remove();
  }, []);

  const enterMode = useCallback((newContent: LearningContent) => {
    setContent(newContent);
    setIsActive(true);
    options.onModeEnter?.();

    // Announce to screen readers
    const announcement = document.createElement("div");
    announcement.setAttribute("role", "status");
    announcement.setAttribute("aria-live", "polite");
    announcement.setAttribute("aria-atomic", "true");
    announcement.className = "sr-only";
    announcement.textContent = `3D Exploration mode activated. Viewing: ${newContent.title}`;
    document.body.appendChild(announcement);

    setTimeout(() => {
      if (announcement.parentNode) {
        document.body.removeChild(announcement);
      }
    }, 1000);
  }, [options]);

  const exitMode = useCallback(() => {
    setIsActive(false);
    options.onModeExit?.();

    // Announce exit
    const announcement = document.createElement("div");
    announcement.setAttribute("role", "status");
    announcement.setAttribute("aria-live", "polite");
    announcement.setAttribute("aria-atomic", "true");
    announcement.className = "sr-only";
    announcement.textContent = "Exiting 3D Exploration mode.";
    document.body.appendChild(announcement);

    setTimeout(() => {
      if (announcement.parentNode) {
        document.body.removeChild(announcement);
      }
    }, 1000);
  }, [options]);

  const loadContent = useCallback((contentKey: string) => {
    if (SAMPLE_CONTENT[contentKey]) {
      setContent(SAMPLE_CONTENT[contentKey]);
    } else {
      console.warn(`Content key "${contentKey}" not found in sample content`);
    }
  }, []);

  return {
    isActive,
    content,
    enterMode,
    exitMode,
    loadContent,
    webglSupported,
    sampleContent: SAMPLE_CONTENT,
  };
}

/**
 * Hook for quickly entering exploration mode with a specific model type
 */
export function useQuickExploration() {
  const exploration = useExplorationMode();

  const showMolecule = useCallback((title: string, labels?: string[]) => {
    exploration.enterMode({
      title,
      description: `Interactive 3D model of ${title.toLowerCase()}.`,
      modelType: "molecule" as ModelType,
      labels,
    });
  }, [exploration]);

  const showSolarSystem = useCallback((title = "Solar System", labels?: string[]) => {
    exploration.enterMode({
      title,
      description: "Interactive 3D model of our solar system showing planets orbiting the sun.",
      modelType: "solar-system" as ModelType,
      labels,
    });
  }, [exploration]);

  const showCell = useCallback((title = "Animal Cell", labels?: string[]) => {
    exploration.enterMode({
      title,
      description: "Interactive 3D model of an animal cell showing major organelles.",
      modelType: "cell" as ModelType,
      labels,
    });
  }, [exploration]);

  const showGeometry = useCallback((title = "Geometric Shapes", labels?: string[]) => {
    exploration.enterMode({
      title,
      description: "Interactive 3D geometric shapes for spatial learning.",
      modelType: "geometric" as ModelType,
      labels,
    });
  }, [exploration]);

  return {
    ...exploration,
    showMolecule,
    showSolarSystem,
    showCell,
    showGeometry,
  };
}

export default useExplorationMode;
