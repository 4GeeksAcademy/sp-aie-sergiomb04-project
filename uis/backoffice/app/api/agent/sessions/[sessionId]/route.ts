import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

export const runtime = "nodejs";

export async function GET(
  request: Request,
  context: { params: Promise<{ sessionId: string }> }
): Promise<Response> {
  const { sessionId } = await context.params;
  const url = new URL(request.url);
  const threadId = url.searchParams.get("thread_id") || sessionId;
  const upstreamUrl = buildTrackflowApiUrl(
    `/agent/sessions/${encodeURIComponent(sessionId)}?thread_id=${encodeURIComponent(threadId)}`
  );

  try {
    const authHeaders = await getAuthorizedSessionHeaders();
    if (!authHeaders) {
      return Response.json(
        { detail: "No hay sesión activa con JWT en el backoffice." },
        { status: 401 }
      );
    }

    const upstreamResponse = await fetch(upstreamUrl, {
      method: "GET",
      headers: authHeaders,
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      const errorText = await upstreamResponse.text();
      return new Response(errorText, {
        status: upstreamResponse.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    const data = await upstreamResponse.json();
    return Response.json(data, { status: 200 });
  } catch (error) {
    return Response.json(
      {
        detail: `No se pudo rehidratar la sesión ${sessionId}: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 500 }
    );
  }
}
