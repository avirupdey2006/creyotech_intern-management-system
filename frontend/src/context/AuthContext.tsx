"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { clientLogger } from "@/lib/logger";
import { AuthStatusResponse, User, UserRole } from "@/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function getDashboardRouteForRole(role: UserRole): string {
  switch (role) {
    case "ADMIN":
      return "/admin/dashboard";
    case "HR_REVIEWER":
      return "/hr/dashboard";
    default:
      return "/candidate/dashboard";
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const router = useRouter();

  const refreshUser = useCallback(async (): Promise<User | null> => {
    try {
      const { data } = await apiClient.get<User>("/auth/me");
      setUser(data);
      return data;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const login = async (email: string, password: string): Promise<User> => {
    const { data } = await apiClient.post<AuthStatusResponse>("/auth/login", {
      email,
      password,
    });
    setUser(data.user);
    clientLogger.info({ role: data.user.role }, "User authenticated via HttpOnly cookie");
    return data.user;
  };

  const register = async (email: string, password: string): Promise<User> => {
    const { data } = await apiClient.post<AuthStatusResponse>("/auth/register", {
      email,
      password,
    });
    setUser(data.user);
    clientLogger.info({ role: data.user.role }, "Candidate account registered");
    return data.user;
  };

  const logout = async (): Promise<void> => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
      // Ignore logout errors if token already expired
    } finally {
      setUser(null);
      router.push("/login");
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}