/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#2E3F8F",
        sky: "#D4E2FF",
        sun: "#EEE772",
        coral: "#E47A59",
        coralink: "#A8442A", // coral darkened for text (AA on white)
        ink: "#111111",
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
