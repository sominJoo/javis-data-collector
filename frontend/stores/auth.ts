import { defineStore } from "pinia";
import type { Session } from "~/types";

const STORAGE_KEY = "session";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    session: null as Session | null,
  }),
  getters: {
    isAuthenticated: (s) => s.session !== null,
    isAdmin: (s) => s.session?.role === "admin",
    displayName: (s) => s.session?.displayName ?? "",
    initial: (s) => s.session?.displayName?.charAt(0) ?? "U",
  },
  actions: {
    init() {
      if (import.meta.client) {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
          try {
            this.session = JSON.parse(raw) as Session;
          } catch {
            this.session = null;
          }
        }
      }
    },
    setSession(session: Session) {
      this.session = session;
      if (import.meta.client) localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    },
    logout() {
      this.session = null;
      if (import.meta.client) localStorage.removeItem(STORAGE_KEY);
    },
  },
});
