import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export const AUTH_COOKIE_NAME = "trackflow_backoffice_token";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export function getTrackflowApiBaseUrl(): string {
  return (process.env.TRACKFLOW_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

export function buildTrackflowApiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${getTrackflowApiBaseUrl()}${normalizedPath}`;
}

export async function getSessionToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(AUTH_COOKIE_NAME)?.value ?? null;
}

export async function getAuthorizedSessionHeaders(init?: HeadersInit): Promise<Headers | null> {
  const token = await getSessionToken();

  if (!token) {
    return null;
  }

  return createAuthorizedHeaders(token, init);
}

export function applySessionCookie(response: NextResponse, token: string): NextResponse {
  response.cookies.set({
    name: AUTH_COOKIE_NAME,
    value: token,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  });

  return response;
}

export function clearSessionCookie(response: NextResponse): NextResponse {
  response.cookies.set({
    name: AUTH_COOKIE_NAME,
    value: "",
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });

  return response;
}

export function createAuthorizedHeaders(token: string, init?: HeadersInit): Headers {
  const headers = new Headers(init);
  headers.set("Authorization", `Bearer ${token}`);
  return headers;
}