import { NextResponse } from "next/server";

import {
  buildTrackflowApiUrl,
  clearSessionCookie,
  createAuthorizedHeaders,
  getSessionToken,
} from "@/app/features/auth/server/session";

type UpstreamError = {
  detail?: string;
  error?: string;
};

export const runtime = "nodejs";

export async function GET(): Promise<NextResponse> {
  const token = await getSessionToken();

  if (!token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  try {
    const upstreamResponse = await fetch(buildTrackflowApiUrl("/auth/me"), {
      method: "GET",
      headers: createAuthorizedHeaders(token),
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      const payload = (await upstreamResponse.json().catch(() => null)) as UpstreamError | null;
      const response = NextResponse.json(
        {
          error: payload?.error,
          detail: payload?.detail ?? "No se pudo cargar la sesion",
        },
        { status: upstreamResponse.status }
      );

      if (upstreamResponse.status === 401) {
        return clearSessionCookie(response);
      }

      return response;
    }

    return NextResponse.json(await upstreamResponse.json(), { status: 200 });
  } catch {
    return NextResponse.json(
      { error: "No se pudo conectar con el backend de autenticacion" },
      { status: 502 }
    );
  }
}