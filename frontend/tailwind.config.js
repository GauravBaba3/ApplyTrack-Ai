/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      colors: {
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b',
        },
        accent: {
          cyan: '#06b6d4',
          violet: '#8b5cf6',
          emerald: '#10b981',
          amber: '#f59e0b',
          rose: '#ef4444',
        },
        navy: {
          950: '#040711',
          900: '#070b18',
          850: '#0b1124',
          800: '#0f172a',
          700: '#1e293b',
          600: '#334155',
        },
        dark: {
          bg: '#080c14',
          surface: '#0d131f',
          card: '#111928',
          elevated: '#162032',
          border: 'rgba(255, 255, 255, 0.08)',
          muted: '#334155',
        }
      },
      boxShadow: {
        'subtle': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        'premium': '0 4px 20px -2px rgba(0, 0, 0, 0.05), 0 2px 6px -1px rgba(0, 0, 0, 0.02)',
        'glass-1': '0 2px 10px 0 rgba(0, 0, 0, 0.15)',
        'glass-2': '0 8px 30px 0 rgba(0, 0, 0, 0.25)',
        'glass-3': '0 16px 48px -8px rgba(0, 0, 0, 0.45)',
        'glass-4': '0 20px 60px -10px rgba(0, 0, 0, 0.60)',
        'glow-primary': '0 0 28px -4px rgba(79, 70, 229, 0.40)',
        'glow-cyan': '0 0 28px -4px rgba(6, 182, 212, 0.35)',
        'glow-violet': '0 0 28px -4px rgba(139, 92, 246, 0.35)',
        'glow-emerald': '0 0 28px -4px rgba(16, 185, 129, 0.35)',
      },
      animation: {
        'toast-drop': 'toastDrop 0.32s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'toast-rise': 'toastRise 0.24s cubic-bezier(0.4, 0, 1, 1) forwards',
        'fade-in': 'fadeIn 0.2s ease-out forwards',
        'scale-in': 'scaleIn 0.24s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'pulse-subtle': 'pulseSubtle 3s infinite ease-in-out',
        'shimmer': 'shimmer 2.5s infinite linear',
      },
      keyframes: {
        toastDrop: {
          '0%': { transform: 'translateY(-120%) scale(0.95)', opacity: '0' },
          '100%': { transform: 'translateY(0) scale(1)', opacity: '1' },
        },
        toastRise: {
          '0%': { transform: 'translateY(0) scale(1)', opacity: '1' },
          '100%': { transform: 'translateY(-120%) scale(0.95)', opacity: '0' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.96)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        }
      }
    },
  },
  plugins: [],
}
