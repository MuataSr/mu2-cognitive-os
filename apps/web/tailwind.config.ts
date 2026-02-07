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
        /* Kut Different Signature Palette */
        "kd-red": "#E62121",
        "kd-red-glow": "rgba(230, 33, 33, 0.4)",
        "kd-black": "#0F0F0F",
        "kd-dark-grey": "#1A1A1A",
        "kd-slate": "#2A2A2A",
        "kd-white": "#FFFFFF",
        "kd-text-muted": "#A0A0A0",

        // Focus Mode - High Contrast Colors
        "focus-bg": "#000000",
        "focus-text": "#FFFFFF",
        "focus-accent": "#FFFF00",
        "focus-border": "#FFFFFF",

        // Legacy color names for compatibility
        "standard-bg": "#0F0F0F",
        "standard-text": "#FFFFFF",
        "standard-accent": "#E62121",
        "standard-muted": "#A0A0A0",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        display: ["var(--font-montserrat)", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "monospace"],
      },
      borderRadius: {
        "kd": "4px", // Diamond Kut sharp corners
      },
      transitionTimingFunction: {
        "kd": "cubic-bezier(0.4, 0, 0.2, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
