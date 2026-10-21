import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{ ticketId: string }>;
};

export async function POST(
  request: Request,
  context: RouteContext
): Promise<Response> {
  const { ticketId } = await context.params;
  const upstreamUrl = buildTrackflowApiUrl(`/api/rfp/${encodeURIComponent(ticketId)}/generate`);

  try {
    let authHeaders: Headers | null = null;
    try {
      authHeaders = await getAuthorizedSessionHeaders();
    } catch {
      authHeaders = null;
    }

    const headers = new Headers(authHeaders ?? {});
    headers.set("Content-Type", "application/json");

    let body: string | null = null;
    try {
      body = await request.text();
    } catch {
      body = null;
    }

    const upstreamResponse = await fetch(upstreamUrl, {
      method: "POST",
      headers,
      body: body || undefined,
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
    return Response.json(data, { status: upstreamResponse.status });
  } catch (error) {
    return Response.json(
      {
        detail: `Error al iniciar generación de propuesta: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 502 }
    );
  }
}
