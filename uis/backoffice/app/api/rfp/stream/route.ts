import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const lastEventIdParam = url.searchParams.get("last_event_id");
  const onceParam = url.searchParams.get("once");

  const queryParams = new URLSearchParams();
  if (lastEventIdParam) {
    queryParams.set("last_event_id", lastEventIdParam);
  }
  if (onceParam) {
    queryParams.set("once", onceParam);
  }

  const queryString = queryParams.toString();
  const upstreamUrl = buildTrackflowApiUrl(
    `/api/rfp/stream${queryString ? `?${queryString}` : ""}`
  );

  // Extract JWT from incoming Authorization header or session cookie
  const incomingAuth = request.headers.get("Authorization");
  let headers: Headers | null = null;

  if (incomingAuth && incomingAuth.trim().toLowerCase().startsWith("bearer ")) {
    headers = new Headers({ Authorization: incomingAuth.trim() });
  } else {
    try {
      headers = await getAuthorizedSessionHeaders();
    } catch {
      headers = null;
    }
  }

  if (!headers) {
    return Response.json(
      { detail: "Token JWT requerido para suscribirse al stream SSE de RFPs." },
      { status: 401 }
    );
  }

  headers.set("Accept", "text/event-stream");
  headers.set("Cache-Control", "no-cache");
  headers.set("X-SSE-Client", "backoffice-stream");

  const lastEventIdHeader = request.headers.get("Last-Event-ID");
  if (lastEventIdHeader) {
    headers.set("Last-Event-ID", lastEventIdHeader);
  }

  try {
    const upstreamResponse = await fetch(upstreamUrl, {
      method: "GET",
      headers,
      cache: "no-store",
      signal: request.signal,
    });

    if (!upstreamResponse.ok || !upstreamResponse.body) {
      const errText = await upstreamResponse.text().catch(() => "");
      return new Response(
        errText || JSON.stringify({ detail: "No se pudo abrir el stream SSE." }),
        {
          status: upstreamResponse.status || 502,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    return new Response(upstreamResponse.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    return Response.json(
      {
        detail: `Error conectando al stream SSE de RFPs: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 502 }
    );
  }
}
