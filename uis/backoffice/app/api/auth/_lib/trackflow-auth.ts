import { NextResponse } from "next/server";

import {
  buildTrackflowApiUrl,
  clearSessionCookie,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

type UpstreamError = {
  detail?: string;
  error?: string;
  message?: string;
};

type ProxyOptions = {
  method: "GET" | "POST" | "PUT";
  path: string;
  request?: Request;
  requireAuth?: boolean;
};

async function parseErrorPayload(response: Response): Promise<UpstreamError | null> {
  const raw = await response.text();

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as UpstreamError;
  } catch {
    return { detail: raw };
  }
}

function toProxyHeaders(headers: Headers | null): Headers {
  const nextHeaders = headers ? new Headers(headers) : new Headers();
  nextHeaders.set("Content-Type", "application/json");
  return nextHeaders;
}

export async function proxyAuthRequest<T>({
  method,
  path,
  request,
  requireAuth = false,
}: ProxyOptions): Promise<NextResponse<T | UpstreamError>> {
  const authorizedHeaders = requireAuth ? await getAuthorizedSessionHeaders() : null;

  if (requireAuth && !authorizedHeaders) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  try {
    const upstreamResponse = await fetch(buildTrackflowApiUrl(path), {
      method,
      headers: toProxyHeaders(authorizedHeaders),
      body: request && method !== "GET" ? await request.text() : undefined,
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      const payload = await parseErrorPayload(upstreamResponse);
      const response = NextResponse.json(
        {
          error: payload?.error,
          detail: payload?.detail ?? payload?.message ?? "No se pudo completar la solicitud",
        },
        { status: upstreamResponse.status }
      );

      if (upstreamResponse.status === 401) {
        return clearSessionCookie(response);
      }

      return response;
    }

    const bodyText = await upstreamResponse.text();
    if (!bodyText) {
      return NextResponse.json({} as T, { status: upstreamResponse.status });
    }

    return NextResponse.json(JSON.parse(bodyText) as T, { status: upstreamResponse.status });
  } catch {
    return NextResponse.json(
      { error: "No se pudo conectar con el backend de autenticacion" },
      { status: 502 }
    );
  }
}

export const runtime = "nodejs";