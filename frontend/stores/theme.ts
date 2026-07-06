import { defineStore } from "pinia";

export type ThemeMode = "light" | "dark";

export const useThemeStore = defineStore("theme", {
  state: () => ({
    mode: "light" as ThemeMode,
  }),
  getters: {
    icon: (s) => (s.mode === "light" ? "🌙" : "☀️"),
    label: (s) => (s.mode === "light" ? "다크" : "라이트"),
  },
  actions: {
    apply() {
      if (import.meta.client) {
        document.documentElement.setAttribute("data-theme", this.mode);
      }
    },
    toggle() {
      this.mode = this.mode === "light" ? "dark" : "light";
      if (import.meta.client) localStorage.setItem("theme", this.mode);
      this.apply();
    },
    init() {
      if (import.meta.client) {
        const saved = localStorage.getItem("theme") as ThemeMode | null;
        if (saved === "light" || saved === "dark") this.mode = saved;
      }
      this.apply();
    },
  },
});
