/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        covered: "#16a34a",
        partial: "#d97706",
        missing: "#dc2626",
        superseded: "#6b7280",
      },
    },
  },
  plugins: [],
};
