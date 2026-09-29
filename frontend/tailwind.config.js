/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        display: ["Space Grotesk", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      colors: {
        bg: "var(--c-bg)",
        surface: "var(--c-surface)",
        surface2: "var(--c-surface2)",
        surface3: "var(--c-surface3)",
        border: "var(--c-border)",
        borderSoft: "var(--c-border-soft)",
        text: "var(--c-text)",
        textDim: "var(--c-text-dim)",
        textFaint: "var(--c-text-faint)",
        accent: "#5b5fef",
        accent2: "#22d3aa",
        warn: "#f5a623",
        danger: "#ef5a6f",
      },
    },
  },
  plugins: [],
};
