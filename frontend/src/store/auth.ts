import { create } from "zustand";
import { api } from "../lib/api";
import { tokenStore } from "../lib/tokenStore";
import type { User } from "../types";

interface AuthState {
  user: User | null;
  status: "idle" | "loading" | "authenticated" | "unauthenticated";
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  hydrate: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  status: "idle",
  error: null,

  login: async (username, password) => {
    set({ status: "loading", error: null });
    try {
      const tokens = await api.auth.login(username, password);
      tokenStore.set(tokens.access_token, tokens.refresh_token);
      const user = await api.auth.me();
      set({ user, status: "authenticated" });
    } catch (e) {
      set({ status: "unauthenticated", error: e instanceof Error ? e.message : "Login failed" });
      throw e;
    }
  },

  register: async (username, email, password) => {
    set({ status: "loading", error: null });
    try {
      await api.auth.register(username, email, password);
      const tokens = await api.auth.login(username, password);
      tokenStore.set(tokens.access_token, tokens.refresh_token);
      const user = await api.auth.me();
      set({ user, status: "authenticated" });
    } catch (e) {
      set({ status: "unauthenticated", error: e instanceof Error ? e.message : "Registration failed" });
      throw e;
    }
  },

  logout: () => {
    tokenStore.clear();
    set({ user: null, status: "unauthenticated" });
  },

  hydrate: async () => {
    if (!tokenStore.getAccess()) {
      set({ status: "unauthenticated" });
      return;
    }
    set({ status: "loading" });
    try {
      const user = await api.auth.me();
      set({ user, status: "authenticated" });
    } catch {
      tokenStore.clear();
      set({ status: "unauthenticated", user: null });
    }
  },
}));
