/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bjc': {
          'bg': '#0b0b0b',
          'card': '#121212',
          'line': '#232323',
          'red': '#e00000',
          'red-dark': '#b80000',
          'muted': '#bdbdbd',
        },
      },
    },
  },
  plugins: [],
}
