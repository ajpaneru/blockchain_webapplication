/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",  // Scan all HTML files in the templates folder
    "./static/**/*.js"        // Scan all JS files in the static folder
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

