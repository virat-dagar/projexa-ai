const THEME_STORAGE_KEY = "writetrace-theme";
const root = document.documentElement;
const themeToggle = document.getElementById("themeToggle");

function getStoredTheme() {
  const value = localStorage.getItem(THEME_STORAGE_KEY);
  return value === "dark" || value === "light" ? value : null;
}

function applyTheme(theme) {
  root.dataset.theme = theme;
  if (themeToggle) {
    themeToggle.textContent = theme === "dark" ? "Light mode" : "Dark mode";
    themeToggle.setAttribute("aria-pressed", String(theme === "dark"));
  }
}

function initTheme() {
  const storedTheme = getStoredTheme();
  const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(storedTheme || (systemPrefersDark ? "dark" : "light"));
}

function toggleTheme() {
  const current = root.dataset.theme === "dark" ? "dark" : "light";
  const next = current === "dark" ? "light" : "dark";
  localStorage.setItem(THEME_STORAGE_KEY, next);
  applyTheme(next);
}

if (themeToggle) {
  themeToggle.addEventListener("click", toggleTheme);
}

initTheme();
