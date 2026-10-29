import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  try {
    const body = await request.json();
    let authHeaders: Headers | null = null;
    try {
      authHeaders = await getAuthorizedSessionHeaders({
        "Content-Type": "application/json",
      });
    } catch {
      authHeaders = null;
    }

    const headers =
      authHeaders ?? new Headers({ "Content-Type": "application/json" });

    const upstreamResponse = await fetch(
      buildTrackflowApiUrl("/telemetry/events"),
      {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        cache: "no-store",
      },
    );

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
        detail: `Error al enviar eventos de telemetria: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 500 },
    );
  }
}
