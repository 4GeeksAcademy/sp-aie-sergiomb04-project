import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

export const runtime = "nodejs";

async function resolveAuthHeaders(request: Request): Promise<Headers | null> {
  const incomingAuth = request.headers.get("Authorization");
  if (incomingAuth && incomingAuth.trim().toLowerCase().startsWith("bearer ")) {
    return new Headers({ Authorization: incomingAuth.trim() });
  }
  try {
    return await getAuthorizedSessionHeaders();
  } catch {
    return null;
  }
}

export async function GET(request: Request): Promise<Response> {
  const upstreamUrl = buildTrackflowApiUrl("/api/rfp");

  try {
    const authHeaders = await resolveAuthHeaders(request);

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
        detail: `Error al listar tickets RFP: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 502 }
    );
  }
}

export async function POST(request: Request): Promise<Response> {
  const upstreamUrl = buildTrackflowApiUrl("/api/rfp/tickets");

  try {
    const authHeaders = await resolveAuthHeaders(request);
    const headers = authHeaders ? new Headers(authHeaders) : new Headers();
    headers.set("Content-Type", "application/json");

    const bodyText = await request.text();
    const upstreamResponse = await fetch(upstreamUrl, {
      method: "POST",
      headers,
      body: bodyText,
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
        detail: `Error al registrar ticket RFP: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 502 }
    );
  }
}
