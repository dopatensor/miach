/** @type {import('tailwindcss').Config} */
// All colours are theme tokens defined in src/index.css (dark = default, light via data-theme).
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
        acc: "var(--acc)",
        accfg: "var(--acc-fg)",
        warn: "var(--warn)",
      },
      fontFamily: { mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"] },
      borderRadius: { DEFAULT: "2px" },
    },
  },
  plugins: [],
};
