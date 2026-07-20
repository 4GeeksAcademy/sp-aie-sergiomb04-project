export const runtime = "nodejs";

import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

type UpstreamError = {
  detail?: unknown;
  error?: string;
};

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

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> }
): Promise<Response> {
  const { id } = await context.params;
  const headers = await getAuthorizedSessionHeaders();

  if (!headers) {
    return Response.json({ detail: "Unauthorized" }, { status: 401 });
  }

  try {
    const upstreamResponse = await fetch(buildTrackflowApiUrl(`/suppliers/${id}`), {
      method: "GET",
      headers,
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      return toErrorResponse(upstreamResponse);
    }

    return Response.json(await upstreamResponse.json(), { status: 200 });
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend Python de suppliers" },
      { status: 502 }
    );
  }
}

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ id: string }> }
): Promise<Response> {
  const { id } = await context.params;
  const headers = await getAuthorizedSessionHeaders();

  if (!headers) {
    return Response.json({ detail: "Unauthorized" }, { status: 401 });
  }

  try {
    const upstreamResponse = await fetch(buildTrackflowApiUrl(`/suppliers/${id}`), {
      method: "DELETE",
      headers,
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      return toErrorResponse(upstreamResponse);
    }

    return Response.json(await upstreamResponse.json(), { status: 200 });
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend Python de suppliers" },
      { status: 502 }
    );
  }
}
