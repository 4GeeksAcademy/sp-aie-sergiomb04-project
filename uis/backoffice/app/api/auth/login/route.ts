import { NextResponse } from "next/server";

import { AuthUser, LoginPayload, LoginResponse } from "@/app/features/auth/types/auth";
import {
  applySessionCookie,
  buildTrackflowApiUrl,
  createAuthorizedHeaders,
} from "@/app/features/auth/server/session";

type UpstreamError = {
  detail?: string;
  error?: string;
};

export const runtime = "nodejs";

async function toErrorResponse(upstreamResponse: Response): Promise<NextResponse> {
  const payload = (await upstreamResponse.json().catch(() => null)) as UpstreamError | null;

  return NextResponse.json(
    {
      error: payload?.error,
      detail: payload?.detail ?? "No se pudo iniciar sesion",
    },
    { status: upstreamResponse.status }
  );
}

export async function POST(request: Request): Promise<NextResponse> {
  try {
    const body = (await request.json()) as LoginPayload;

    const loginResponse = await fetch(buildTrackflowApiUrl("/auth/login"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    if (!loginResponse.ok) {
      return toErrorResponse(loginResponse);
    }

    const { access_token } = (await loginResponse.json()) as LoginResponse;
    const meResponse = await fetch(buildTrackflowApiUrl("/auth/me"), {
      method: "GET",
      headers: createAuthorizedHeaders(access_token),
      cache: "no-store",
    });

    if (!meResponse.ok) {
      return toErrorResponse(meResponse);
    }

    const currentUser = (await meResponse.json()) as AuthUser;
    const response = NextResponse.json(currentUser, { status: 200 });
    return applySessionCookie(response, access_token);
  } catch {
    return NextResponse.json(
      { error: "No se pudo conectar con el backend de autenticacion" },
      { status: 502 }
    );
  }
}