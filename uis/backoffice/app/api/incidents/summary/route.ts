import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

export const runtime = "nodejs";

export async function GET(): Promise<Response> {
  const authHeaders = await getAuthorizedSessionHeaders();
  if (!authHeaders) {
    return Response.json({ detail: "Unauthorized" }, { status: 401 });
  }

  try {
    const upstreamResponse = await fetch(
      buildTrackflowApiUrl("/api/incidents/summary"),
      {
        method: "GET",
        headers: authHeaders,
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      const payload = await upstreamResponse.json().catch(() => null);
      return Response.json(payload ?? { detail: `Error HTTP ${upstreamResponse.status}` }, {
        status: upstreamResponse.status,
      });
    }

    const data = await upstreamResponse.json();
    return Response.json(data, { status: 200 });
  } catch {
    return Response.json({ detail: "Error interno del servidor" }, { status: 500 });
  }
}