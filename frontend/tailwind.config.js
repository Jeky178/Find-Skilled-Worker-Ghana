/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#EEF3FF", 100: "#DCE7FF", 200: "#B9CEFF", 600: "#1E4DB7",
          700: "#153C94", 800: "#0F2D74", 900: "#0B2259",
        },
        accent: { 100: "#FFE9DA", 400: "#FF8A3D", 500: "#F26B1D", 600: "#C74A09", 700: "#A53C05" },
        ink: "#16213E",
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', "system-ui", "sans-serif"],
        sans: ['"Source Sans 3"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
