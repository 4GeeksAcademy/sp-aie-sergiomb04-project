"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { fetchMe } from "@/app/features/auth/services/auth-api";
import {
  clearSessionToken,
  getAuthChangedEventName,
  getSessionToken,
  getUnauthorizedEventName,
} from "@/app/features/auth/lib/session";
import { AuthUser } from "@/app/features/auth/types/auth";

type AuthSessionContextValue = {
  user: AuthUser | null;
  isLoading: boolean;
  setUser: (user: AuthUser | null) => void;
  logout: () => void;
};

const AuthSessionContext = createContext<AuthSessionContextValue | undefined>(undefined);

export function AuthSessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    clearSessionToken();
    setUser(null);
    router.push("/login");
    router.refresh();
  }, [router]);

  const refreshUser = useCallback(async () => {
    const token = getSessionToken();

    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const currentUser = await fetchMe();
      setUser(currentUser);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  useEffect(() => {
    const authChangedHandler = () => {
      void refreshUser();
    };

    const unauthorizedHandler = () => {
      if (pathname !== "/login") {
        logout();
      }
    };

    window.addEventListener(getAuthChangedEventName(), authChangedHandler);
    window.addEventListener(getUnauthorizedEventName(), unauthorizedHandler);

    return () => {
      window.removeEventListener(getAuthChangedEventName(), authChangedHandler);
      window.removeEventListener(getUnauthorizedEventName(), unauthorizedHandler);
    };
  }, [logout, pathname, refreshUser]);

  const value = useMemo<AuthSessionContextValue>(
    () => ({
      user,
      isLoading,
      setUser,
      logout,
    }),
    [user, isLoading, logout]
  );

  return <AuthSessionContext.Provider value={value}>{children}</AuthSessionContext.Provider>;
}

export function useAuthSession(): AuthSessionContextValue {
  const context = useContext(AuthSessionContext);
  if (!context) {
    throw new Error("useAuthSession debe usarse dentro de AuthSessionProvider");
  }

  return context;
}
