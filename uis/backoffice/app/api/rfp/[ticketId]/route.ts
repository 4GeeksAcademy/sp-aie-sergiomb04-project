import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{ ticketId: string }>;
};

export async function GET(
  _request: Request,
  context: RouteContext
): Promise<Response> {
  const { ticketId } = await context.params;
  const upstreamUrl = buildTrackflowApiUrl(`/api/rfp/${encodeURIComponent(ticketId)}`);

  try {
    let authHeaders: Headers | null = null;
    try {
      authHeaders = await getAuthorizedSessionHeaders();
    } catch {
      authHeaders = null;
    }

    const upstreamResponse = await fetch(upstreamUrl, {
      method: "GET",
      headers: authHeaders ?? undefined,
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
        detail: `Error al consultar el ticket RFP: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 502 }
    );
  }
}
