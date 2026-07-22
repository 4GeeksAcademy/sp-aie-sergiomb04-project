"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuthSession } from "@/app/features/auth/components/AuthSessionProvider";
import { getSessionToken } from "@/app/features/auth/lib/session";

const PUBLIC_PATHS = new Set(["/login", "/register"]);

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isLoading } = useAuthSession();

  const isPublicRoute = PUBLIC_PATHS.has(pathname);

  useEffect(() => {
    const token = getSessionToken();

    if (isPublicRoute) {
      if (token) {
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
