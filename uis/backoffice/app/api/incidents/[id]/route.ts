import { NextRequest } from "next/server";

import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

export const runtime = "nodejs";

async function toErrorResponse(upstreamResponse: Response): Promise<Response> {
  return upstreamResponse.json().then(
    (payload: Record<string, unknown>) =>
      new Response(JSON.stringify(payload), {
        status: upstreamResponse.status,
        headers: { "Content-Type": "application/json" },
      }),
    () =>
      new Response(
        JSON.stringify({ detail: `Error HTTP ${upstreamResponse.status}` }),
        {
          status: upstreamResponse.status,
          headers: { "Content-Type": "application/json" },
        },
      ),
  );
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const authHeaders = await getAuthorizedSessionHeaders();
  if (!authHeaders) {
    return Response.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;

  try {
    const upstreamResponse = await fetch(
      buildTrackflowApiUrl(`/api/incidents/${id}`),
      {
        method: "GET",
        headers: authHeaders,
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      return toErrorResponse(upstreamResponse);
    }

    const data = await upstreamResponse.json();
    return Response.json(data, { status: 200 });
  } catch {
    return Response.json({ detail: "Error interno del servidor" }, { status: 500 });
  }
}