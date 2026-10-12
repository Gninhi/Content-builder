/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class', '[data-mode="dark"]'],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        /* Semantic Surface & Background Tokens */
        app: 'var(--bg-app)',
        surface: {
          DEFAULT: 'var(--bg-surface)',
          elevated: 'var(--bg-surface-raised)',
          raised: 'var(--bg-surface-raised)',
          subtle: 'var(--bg-subtle)',
          hover: 'var(--bg-hover)',
          active: 'var(--bg-active)',
        },
        /* Semantic Border Tokens */
        border: {
          DEFAULT: 'var(--border-default)',
          default: 'var(--border-default)',
          subtle: 'var(--border-subtle)',
          hover: 'var(--border-hover)',
          focus: 'var(--border-focus)',
        },
        /* Semantic Text Tokens */
        txt: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
          inverse: 'var(--text-inverse)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
          inverse: 'var(--text-inverse)',
        },
        /* Semantic Accent Tokens */
        accent: {
          DEFAULT: 'var(--accent-solid)',
          hover: 'var(--accent-hover)',
          active: 'var(--accent-active)',
          subtle: 'var(--accent-subtle)',
          border: 'var(--accent-border)',
          txt: 'var(--accent-text)',
          text: 'var(--accent-text)',
          foreground: 'var(--text-inverse)',
        },
        /* Decoupled State & Status Tokens */
        status: {
          success: {
            bg: 'var(--status-success-bg)',
            border: 'var(--status-success-border)',
            text: 'var(--status-success-text)',
          },
          warning: {
            bg: 'var(--status-warning-bg)',
            border: 'var(--status-warning-border)',
            text: 'var(--status-warning-text)',
          },
          danger: {
            bg: 'var(--status-danger-bg)',
            border: 'var(--status-danger-border)',
            text: 'var(--status-danger-text)',
          },
          info: {
            bg: 'var(--status-info-bg)',
            border: 'var(--status-info-border)',
            text: 'var(--status-info-text)',
          },
        },
        /* Backwards-compatible aliases bridging to CSS variables */
        obsidian: {
          950: 'var(--bg-app)',
          900: 'var(--bg-surface)',
          850: 'var(--bg-surface-raised)',
          800: 'var(--bg-subtle)',
        },
        titanium: {
          900: 'var(--bg-app)',
          800: 'var(--border-default)',
          700: 'var(--border-hover)',
          600: 'var(--text-muted)',
          500: 'var(--text-muted)',
          400: 'var(--text-secondary)',
          300: 'var(--border-subtle)',
          200: 'var(--bg-hover)',
          100: 'var(--text-primary)',
        },
        brass: {
          900: 'var(--accent-active)',
          800: 'var(--accent-active)',
          700: 'var(--accent-border)',
          600: 'var(--accent-border)',
          500: 'var(--accent-solid)',
          400: 'var(--accent-text)',
          300: 'var(--accent-text)',
          200: 'var(--accent-subtle)',
          100: 'var(--accent-subtle)',
          50: 'var(--accent-subtle)',
        },
      },
      fontFamily: {
        sans: ['Geist Sans', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['Geist Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      borderRadius: {
        xs: 'var(--radius-xs)',
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
      },
      boxShadow: {
        subtle: 'var(--shadow-sm)',
        elevated: 'var(--shadow-md)',
        vault: 'var(--shadow-md)',
        surface: 'var(--shadow-sm)',
        raised: 'var(--shadow-lg)',
      },
    },
  },
  plugins: [],
}
