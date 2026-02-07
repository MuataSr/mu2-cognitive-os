"use client";

import { useMemo } from "react";
import { useMode } from "@/components/providers/mode-provider";

interface Paragraph {
  id: string;
  text: string;
}

interface Chapter {
  id: string;
  title: string;
  paragraphs: Paragraph[];
}

interface TextbookViewerProps {
  chapterId: string;
  highlightedParagraph?: string | null;
}

// Sample OpenStax content - Photosynthesis chapter
const sampleChapter: Chapter = {
  id: "photosynthesis-101",
  title: "Introduction to Photosynthesis",
  paragraphs: [
    {
      id: "para-1",
      text: "Photosynthesis is the process by which plants convert light energy from the sun into chemical energy stored in glucose. This fundamental biological process is essential for life on Earth, as it produces oxygen and forms the base of most food chains."
    },
    {
      id: "para-2",
      text: "The process occurs primarily in the leaves of plants, within specialized cellular structures called chloroplasts. These chloroplasts contain chlorophyll, the green pigment that captures light energy and gives plants their characteristic color."
    },
    {
      id: "para-3",
      text: "Photosynthesis can be summarized by the chemical equation: 6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂. This means that carbon dioxide and water, in the presence of light, produce glucose and oxygen."
    },
    {
      id: "para-4",
      text: "The process consists of two main stages: the light-dependent reactions and the Calvin cycle (light-independent reactions). During the light-dependent reactions, energy from sunlight is captured and used to produce ATP and NADPH, energy-carrying molecules."
    },
    {
      id: "para-5",
      text: "The Calvin cycle uses the ATP and NADPH from the light-dependent reactions to convert carbon dioxide into glucose. This cycle is named after Melvin Calvin, who discovered it in 1950 and was awarded the Nobel Prize for this work."
    },
    {
      id: "para-6",
      text: "Several factors affect the rate of photosynthesis, including light intensity, carbon dioxide concentration, temperature, and water availability. Plants have evolved various adaptations to optimize photosynthesis under different environmental conditions."
    },
    {
      id: "para-7",
      text: "Chlorophyll absorbs light most efficiently in the blue and red parts of the electromagnetic spectrum, while reflecting green light. This is why plants appear green to our eyes – we see the reflected light, not the absorbed light."
    },
    {
      id: "para-8",
      text: "The oxygen produced during photosynthesis is a byproduct of the light-dependent reactions, where water molecules are split. This oxygen is released into the atmosphere and is essential for the survival of most organisms on Earth."
    },
    {
      id: "para-9",
      text: "Photosynthesis not only produces oxygen but also removes carbon dioxide from the atmosphere. This makes plants crucial in mitigating climate change and maintaining the Earth's atmospheric balance."
    },
    {
      id: "para-10",
      text: "Understanding photosynthesis is fundamental to many fields, including agriculture, bioenergy, and climate science. Scientists continue to study this process to develop more efficient crops and sustainable energy solutions."
    }
  ]
};

export function TextbookViewer({ chapterId, highlightedParagraph }: TextbookViewerProps) {
  const { mode } = useMode();

  const chapter = useMemo(() => {
    // In a real app, this would fetch from the API
    return sampleChapter.id === chapterId ? sampleChapter : null;
  }, [chapterId]);

  if (!chapter) {
    return (
      <div className="p-8 text-center text-[color:var(--text-secondary)]">
        <p>Chapter not found</p>
      </div>
    );
  }

  return (
    <div className={`h-full ${mode === "focus" ? "focus-mode-enhanced" : ""}`}>
      {/* Chapter Header */}
      <header className="sticky top-0 z-10 bg-[color:var(--bg-primary)] border-b border-[color:var(--border)] p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-[color:var(--text-secondary)] mb-1">
              OpenStax Biology
            </p>
            <h1 className="text-2xl font-bold">
              {chapter.title}
            </h1>
          </div>
          <div
            className="text-xs px-3 py-1 bg-[color:var(--border)] rounded-full"
            aria-label="Source type"
          >
            Source
          </div>
        </div>
      </header>

      {/* Chapter Content - Academic/Paper-like styling */}
      <article className="p-8 max-w-3xl mx-auto">
        <div className="space-y-6 textbook-content paper-texture">
          {chapter.paragraphs.map((paragraph, index) => (
            <p
              key={paragraph.id}
              id={`para-${paragraph.id}`}
              className={`
                leading-relaxed text-lg
                ${mode === "focus" ? "text-[color:var(--text-primary)]" : "text-[color:var(--text-secondary)]"}
                transition-all duration-300 rounded
                ${highlightedParagraph === paragraph.id
                  ? "highlighted-paragraph"
                  : ""
                }
                ${index === 0 ? "first-paragraph-dropcap" : ""}
              `}
              style={{
                fontFamily: mode === "focus" ? "Georgia, serif" : "var(--font-geist-sans), system-ui, sans-serif",
                textIndent: mode === "standard" && index > 0 ? "2em" : "0",
                textAlign: "justify"
              }}
              tabIndex={0}
              role="text"
              aria-label={`Paragraph ${index + 1} of ${chapter.paragraphs.length}`}
            >
              {paragraph.text}
            </p>
          ))}
        </div>

        {/* Chapter Metadata */}
        <footer className="mt-12 pt-8 border-t border-[color:var(--border)]">
          <div className="flex items-center justify-between text-sm text-[color:var(--text-secondary)]">
            <span aria-label={`${chapter.paragraphs.length} paragraphs in this chapter`}>
              {chapter.paragraphs.length} paragraphs
            </span>
            <span>OpenStax Biology 2e</span>
          </div>
        </footer>
      </article>

      <style jsx>{`
        .paper-texture {
          background-image: url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100' height='100' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
        }

        .first-paragraph-dropcap::first-letter {
          font-size: 3em;
          font-weight: bold;
          float: left;
          line-height: 1;
          margin-right: 0.1em;
          color: var(--accent);
        }

        /* Smooth scrolling with reduced motion support */
        @media (prefers-reduced-motion: no-preference) {
          html {
            scroll-behavior: smooth;
          }
        }
      `}</style>
    </div>
  );
}
