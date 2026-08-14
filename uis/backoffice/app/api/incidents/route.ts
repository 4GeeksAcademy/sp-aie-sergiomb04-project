import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

export const runtime = "nodejs";

function toErrorResponse(upstreamResponse: Response): Promise<Response> {
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

export async function POST(request: Request): Promise<Response> {
  const authHeaders = await getAuthorizedSessionHeaders();

  if (!authHeaders) {
    return Response.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();

  try {
    const upstreamResponse = await fetch(
      buildTrackflowApiUrl("/api/incidents"),
      {
        method: "POST",
        headers: {
          Authorization: authHeaders.get("Authorization")!,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      return toErrorResponse(upstreamResponse);
    }

    const data = await upstreamResponse.json();
    return Response.json(data, { status: 201 });
  } catch {
    return Response.json({ detail: "Error interno del servidor" }, { status: 500 });
  }
}

export async function GET(request: Request): Promise<Response> {
  const authHeaders = await getAuthorizedSessionHeaders();
  if (!authHeaders) {
    return Response.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const url = new URL(request.url);
  const params = new URLSearchParams(url.search);
  const queryString = params.toString();

  try {
    const upstreamUrl = buildTrackflowApiUrl(
      `/api/incidents${queryString ? `?${queryString}` : ""}`,
    );
    const upstreamResponse = await fetch(upstreamUrl, {
      method: "GET",
      headers: authHeaders,
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      return toErrorResponse(upstreamResponse);
    }

    const data = await upstreamResponse.json();
    return Response.json(data, { status: 200 });
  } catch {
    return Response.json({ detail: "Error interno del servidor" }, { status: 500 });
  }
}