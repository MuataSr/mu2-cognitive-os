import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Focus Mode - High Contrast Colors
        "focus-bg": "#000000",
        "focus-text": "#FFFFFF",
        "focus-accent": "#FFFF00",
        "focus-border": "#FFFFFF",

        // Standard Mode Colors
        "standard-bg": "#0A0A0A",
        "standard-text": "#E5E5E5",
        "standard-accent": "#3B82F6",
        "standard-muted": "#737373",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
