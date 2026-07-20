import { redirect } from "next/navigation";

import { AuthUser } from "@/app/features/auth/types/auth";
import {
  buildTrackflowApiUrl,
  createAuthorizedHeaders,
  getSessionToken,
} from "@/app/features/auth/server/session";

export async function getCurrentUserFromSession(): Promise<AuthUser | null> {
  const token = await getSessionToken();

  if (!token) {
    return null;
  }

  try {
    const response = await fetch(buildTrackflowApiUrl("/auth/me"), {
      method: "GET",
      headers: createAuthorizedHeaders(token),
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as AuthUser;
  } catch {
    return null;
  }
}

export async function requireAuthenticatedUser(): Promise<AuthUser> {
  const user = await getCurrentUserFromSession();

  if (!user) {
    redirect("/login");
  }

  return user;
}