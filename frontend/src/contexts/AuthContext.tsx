import React, { createContext, useContext, useState, useEffect } from "react";
import type { User, LoginResponse } from "../lib/types";
import {
  login as apiLogin,
  register as apiRegister,
  logout as logoutApi,
  getCurrentUser,
} from "../lib/api";
import { toast } from "sonner";
import { getErrorMessage } from "../lib/errors";
import { useQueryClient } from "@tanstack/react-query";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setAuthFromToken: (token: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing token on mount
  useEffect(() => {
    const token = localStorage.getItem("token");
    const storedUser = localStorage.getItem("user");

    if (token && storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (error) {
        console.error("Failed to parse stored user:", error);
        localStorage.removeItem("token");
        localStorage.removeItem("user");
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await apiLogin(email, password);
      const data: LoginResponse = response.data;

      // Store token and user
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      setUser(data.user);

      toast.success("Login successful!");
    } catch (error: unknown) {
      console.error("Login error:", error);
      const message = getErrorMessage(error);
      toast.error(message || "Login failed. Please try again.");
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      // Backend returns just User data (no token)
      await apiRegister(email, password);
      toast.success("Registration successful! Logging you in...");

      // Auto-login after successful registration
      await login(email, password);
    } catch (error: unknown) {
      console.error("Registration error:", error);

      // Use centralized error message extraction
      const message = getErrorMessage(error);
      toast.error(message || "Registration failed. Please try again.");
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      // Backend logout FIRST (to blacklist token)
      await logoutApi();

      // Then clear local state
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      setUser(null);
      queryClient.clear();

      toast.success("Logged out successfully");
    } catch (error) {
      // If backend fails, still clear local but warn user
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      setUser(null);
      queryClient.clear();

      toast.warning("Logged out locally, but server logout failed. Your session may still be active.");
      console.error("Backend logout failed:", error);
    }
  };

  const setAuthFromToken = async (token: string) => {
    setIsLoading(true);
    try {
      // Store token
      localStorage.setItem("token", token);

      // Fetch user profile using token
      const response = await getCurrentUser();
      const userData: User = response.data;

      // Store user data
      localStorage.setItem("user", JSON.stringify(userData));
      setUser(userData);

      toast.success("Login successful!");
    } catch (error: unknown) {
      console.error("Failed to authenticate with token:", error);
      localStorage.removeItem("token");
      const message = getErrorMessage(error);
      toast.error(message || "Authentication failed");
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, setAuthFromToken }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
