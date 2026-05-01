/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0a0a0a',
        foreground: '#f5f5f5',
        card: {
          DEFAULT: '#141414',
          hover: '#1a1a1a',
        },
        primary: {
          DEFAULT: '#7c3aed',
          hover: '#6d28d9',
        },
        secondary: '#06b6d4',
        accent: '#f59e0b',
        border: '#262626',
        input: {
          DEFAULT: '#1a1a1a',
          text: '#f5f5f5',
          placeholder: '#737373'
        },
        text: {
          primary: '#f5f5f5',
          secondary: '#a1a1a1',
          muted: '#737373',
        }
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-in': 'slideIn 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [],
}