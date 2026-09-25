/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      colors: {
        surface: '#F7F8FA',
        raised: '#FFFFFF',
        ink: '#0F172A',
        muted: '#64748B',
        line: '#E2E8F0',
        accent: '#2563EB',
        'accent-soft': '#EFF6FF',
        danger: '#DC2626',
        'danger-bg': '#FEF2F2',
        'danger-border': '#FECACA',
        warn: '#B45309',
        'warn-bg': '#FFFBEB',
        'warn-border': '#FDE68A',
        skeleton: '#E8ECF1',
      },
      fontFamily: {
        display: ['Geist', 'Inter', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
      },
      maxWidth: {
        content: '960px',
        search: '720px',
      },
      boxShadow: {
        search: '0 8px 28px rgba(37, 99, 235, 0.08)',
      },
    },
  },
  plugins: [],
}
