import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  const upstreamUrl = buildTrackflowApiUrl("/knowledge/query");

  try {
    const body = await request.json();
    let authHeaders: Headers | null = null;
    try {
      authHeaders = await getAuthorizedSessionHeaders();
    } catch {
      authHeaders = null;
    }
    const headers = authHeaders ?? new Headers();
    headers.set("Content-Type", "application/json");

    const upstreamResponse = await fetch(upstreamUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
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
        detail: `Error al consultar la base de conocimiento: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 500 }
    );
  }
}
