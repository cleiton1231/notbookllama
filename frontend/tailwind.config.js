/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#191919',
        sidebar: '#141414',
        card: '#222222',
        input: '#202020',
        'surface-hover': '#2a2a2a',
        border: 'rgba(255, 255, 255, 0.08)',
        coral: {
          300: '#f0a38b',
          400: '#e58b6e',
          500: '#da7756',
          600: '#c66545',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
