export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          50:  '#1e2235',
          100: '#181c2e',
          200: '#12152a',
          300: '#0d1021',
          400: '#252a40',
          500: '#2e3450',
          600: '#363d5c',
        },
        beige: {
          50:  '#faf8f4',
          100: '#f5f0e8',
          200: '#ede6d6',
          300: '#ddd3be',
          400: '#c4b49a',
          500: '#9c8872',
          600: '#7a6a57',
        },
        accent: {
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
        },
      },
      fontFamily: { sans: ['Inter', 'sans-serif'] },
      boxShadow: {
        'dark-card':   '0 4px 24px rgba(0,0,0,0.45)',
        'light-card':  '0 2px 12px rgba(0,0,0,0.07)',
        'glow-accent': '0 0 24px rgba(99,102,241,0.25)',
      },
    },
  },
  plugins: [],
}
