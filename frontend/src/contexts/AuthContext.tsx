import React, { createContext, useContext, useState, useEffect } from "react";
import type { User } from "../lib/types";
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
  verifyAuthCookie: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing auth on mount by calling /auth/me
  // SECURITY: We no longer store tokens in localStorage - auth is via httpOnly cookie only
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Try to get current user using httpOnly cookie
        const response = await getCurrentUser();
        setUser(response.data);
      } catch {
        // Not authenticated or cookie expired - this is normal
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      // Backend sets httpOnly cookie on successful login
      const response = await apiLogin(email, password);
      // Response includes user data (but token is in httpOnly cookie, not accessible to JS)
      setUser(response.data.user);
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
      // Backend logout - clears httpOnly cookie and blacklists token
      await logoutApi();

      // Clear local state
      setUser(null);
      queryClient.clear();

      toast.success("Logged out successfully");
    } catch (error) {
      // If backend fails, still clear local state but warn user
      setUser(null);
      queryClient.clear();

      toast.warning("Logged out locally, but server logout failed. Your session may still be active.");
      console.error("Backend logout failed:", error);
    }
  };

  /**
   * Verify authentication via httpOnly cookie
   * Used after OAuth callback where token is set via cookie (not URL)
   */
  const verifyAuthCookie = async () => {
    setIsLoading(true);
    try {
      // Call /auth/me - this will use the httpOnly cookie automatically
      const response = await getCurrentUser();
      setUser(response.data);
      toast.success("Login successful!");
    } catch (error: unknown) {
      console.error("Failed to verify auth cookie:", error);
      const message = getErrorMessage(error);
      toast.error(message || "Authentication failed");
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, verifyAuthCookie }}>
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
