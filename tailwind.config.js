module.exports = {
  content: [
    "./examples/**/*.html",
    "./templates/**/*.html",
    "./src/**/*.css",
  ],
  theme: {
    extend: {
      colors: {
        paper: {
          bg: "#f4f3ef",
          card: "#ffffff",
          text: "#252422",
          muted: "#9a9a9a",
          border: "#e3e3e3",
          sidebar: "#66615b",
          sidebarDark: "#403d39",
          primary: "#51cbce",
          info: "#51bcda",
          success: "#6bd098",
          warning: "#fbc658",
          danger: "#ef8157",
          orange: "#f96332",
        },
      },
      boxShadow: {
        paper: "0 6px 10px -4px rgba(0, 0, 0, 0.15)",
      },
      borderRadius: {
        paper: "12px",
      },
      fontFamily: {
        sans: ["Montserrat", "Helvetica Neue", "Arial", "sans-serif"],
      },
    },
  },
  plugins: [],
};
