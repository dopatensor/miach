/** @type {import('tailwindcss').Config} */
// All colours are theme tokens defined in src/index.css (warm dark = default, light via data-theme).
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        fg: "var(--fg)",
        mute: "var(--mute)",
        line: "var(--line)",
        raise: "var(--raise)",
        "raise-2": "var(--raise-2)",
        accsoft: "var(--acc-soft)",
        acc: "var(--acc)",
        accfg: "var(--acc-fg)",
        warn: "var(--warn)",
      },
      fontFamily: {
        sans: ['"DM Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
