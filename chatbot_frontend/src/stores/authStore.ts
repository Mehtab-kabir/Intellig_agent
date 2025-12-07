import { create } from "zustand";
import { authApi, User, LoginCredentials, RegisterData } from "../api/auth";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem("access_token"),
  isLoading: false,
  error: null,

  login: async (credentials) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authApi.login(credentials);
      localStorage.setItem("access_token", response.tokens.access);
      localStorage.setItem("refresh_token", response.tokens.refresh);
      set({ user: response.user, isAuthenticated: true, isLoading: false });
    } catch (error: any) {
      const message =
        error.response?.data?.error?.message ||
        error.response?.data?.detail ||
        "Login failed";
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  register: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authApi.register(data);
      localStorage.setItem("access_token", response.tokens.access);
      localStorage.setItem("refresh_token", response.tokens.refresh);
      set({ user: response.user, isAuthenticated: true, isLoading: false });
    } catch (error: any) {
      const message =
        error.response?.data?.email?.[0] ||
        error.response?.data?.password?.[0] ||
        error.response?.data?.error?.message ||
        "Registration failed";
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  logout: async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    try {
      if (refreshToken) await authApi.logout(refreshToken);
    } catch {
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      set({ user: null, isAuthenticated: false });
    }
  },

  checkAuth: async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }
    try {
      const user = await authApi.getProfile();
      set({ user, isAuthenticated: true });
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      set({ user: null, isAuthenticated: false });
    }
  },

  clearError: () => set({ error: null }),
}));
