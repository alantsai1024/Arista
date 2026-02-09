/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#edf5ff',
          100: '#d9e8ff',
          500: '#2f7ed9',
          600: '#155fb8',
        },
      },
      boxShadow: {
        card: '0 10px 30px rgba(26, 75, 130, 0.09)',
      },
    },
  },
  plugins: [],
}
