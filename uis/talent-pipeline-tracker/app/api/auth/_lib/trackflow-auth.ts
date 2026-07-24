import { NextResponse } from "next/server";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

type UpstreamError = {
  detail?: string;
  error?: string;
  message?: string;
};

export type ProxyOptions = {
  method: "GET" | "POST" | "PUT";
  path: string;
  request?: Request;
  requireAuth?: boolean;
};

export function getTrackflowApiBaseUrl(): string {
  return (process.env.TRACKFLOW_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

export function buildTrackflowApiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${getTrackflowApiBaseUrl()}${normalizedPath}`;
}

function parseAuthorizationToken(request: Request): string | null {
  const authorization = request.headers.get("authorization");
  if (!authorization || !authorization.startsWith("Bearer ")) {
    return null;
  }

  const token = authorization.slice("Bearer ".length).trim();
  return token.length > 0 ? token : null;
}

function toHeaders(request: Request | undefined, requireAuth: boolean): Headers {
  const headers = new Headers();
  headers.set("Content-Type", "application/json");

  if (!request) {
    return headers;
  }

  const token = parseAuthorizationToken(request);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  } else if (requireAuth) {
    throw new Error("UNAUTHORIZED");
  }

  return headers;
}

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

function mapProxyError(message: string): NextResponse<UpstreamError> {
  if (message === "UNAUTHORIZED") {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  return NextResponse.json(
    { error: "No se pudo conectar con el backend de autenticacion" },
    { status: 502 }
  );
}

export async function proxyAuthRequest<T>({
  method,
  path,
  request,
  requireAuth = false,
}: ProxyOptions): Promise<NextResponse<T | UpstreamError>> {
  try {
    const headers = toHeaders(request, requireAuth);

    const upstreamResponse = await fetch(buildTrackflowApiUrl(path), {
      method,
      headers,
      body: request && method !== "GET" ? await request.text() : undefined,
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      const payload = await parseErrorPayload(upstreamResponse);
      return NextResponse.json(
        {
          error: payload?.error,
          detail: payload?.detail ?? payload?.message ?? "No se pudo completar la solicitud",
        },
        { status: upstreamResponse.status }
      );
    }

    const bodyText = await upstreamResponse.text();
    if (!bodyText) {
      return NextResponse.json({} as T, { status: upstreamResponse.status });
    }

    return NextResponse.json(JSON.parse(bodyText) as T, { status: upstreamResponse.status });
  } catch (error) {
    const message = error instanceof Error ? error.message : "UNKNOWN";
    return mapProxyError(message);
  }
}

export const runtime = "nodejs";
