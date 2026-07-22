"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuthSession } from "@/app/features/auth/components/AuthSessionProvider";
import { getSessionToken } from "@/app/features/auth/lib/session";

const PUBLIC_PATHS = new Set(["/login", "/register", "/forgot-password", "/reset-password"]);
const AUTO_REDIRECT_WHEN_AUTHENTICATED = new Set(["/login", "/register"]);

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isLoading } = useAuthSession();

  const isPublicRoute = PUBLIC_PATHS.has(pathname);

  useEffect(() => {
    const token = getSessionToken();

    if (isPublicRoute) {
      if (token && AUTO_REDIRECT_WHEN_AUTHENTICATED.has(pathname)) {
        router.replace("/");
      }
      return;
    }

    if (!token) {
      router.replace("/login");
    }
  }, [isPublicRoute, pathname, router]);

  if (!isPublicRoute && isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 text-zinc-700">
        Validando sesión...
      </div>
    );
  }

  return <>{children}</>;
}
