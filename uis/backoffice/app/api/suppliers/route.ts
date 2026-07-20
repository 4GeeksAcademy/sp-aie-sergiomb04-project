export const runtime = "nodejs";

type UpstreamError = {
  detail?: unknown;
  error?: string;
};

import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

function buildUpstreamUrl(request: Request): string {
  const requestUrl = new URL(request.url);
  const upstreamUrl = new URL(buildTrackflowApiUrl("/suppliers"));

  const country = requestUrl.searchParams.get("country");
  const category = requestUrl.searchParams.get("category");

  if (country) {
    upstreamUrl.searchParams.set("country", country);
  }

  if (category) {
    upstreamUrl.searchParams.set("category", category);
  }

  return upstreamUrl.toString();
}

async function toErrorResponse(upstreamResponse: Response): Promise<Response> {
  const payload = (await upstreamResponse.json().catch(() => null)) as UpstreamError | null;

  return Response.json(
    {
      error: payload?.error,
      detail: payload?.detail ?? "Error del backend de proveedores",
    },
    { status: upstreamResponse.status }
  );
}

export async function GET(request: Request): Promise<Response> {
  const headers = await getAuthorizedSessionHeaders();

  if (!headers) {
    return Response.json({ detail: "Unauthorized" }, { status: 401 });
  }

  try {
    const upstreamResponse = await fetch(buildUpstreamUrl(request), {
      method: "GET",
      headers,
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      return toErrorResponse(upstreamResponse);
    }

    const suppliers = await upstreamResponse.json();
    return Response.json(suppliers, { status: 200 });
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend Python de suppliers" },
      { status: 502 }
    );
  }
}

export async function POST(request: Request): Promise<Response> {
  const headers = await getAuthorizedSessionHeaders({
    "Content-Type": "application/json",
  });

  if (!headers) {
    return Response.json({ detail: "Unauthorized" }, { status: 401 });
  }

  try {
    const body = await request.json();

    const upstreamResponse = await fetch(buildTrackflowApiUrl("/suppliers"), {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      return toErrorResponse(upstreamResponse);
    }

    const supplier = await upstreamResponse.json();
    return Response.json(supplier, { status: 201 });
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend Python de suppliers" },
      { status: 502 }
    );
  }
}
