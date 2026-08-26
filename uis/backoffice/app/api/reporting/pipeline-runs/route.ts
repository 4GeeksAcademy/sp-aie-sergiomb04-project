import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

export const runtime = "nodejs";

export async function GET(): Promise<Response> {
  const upstreamUrl = buildTrackflowApiUrl("/reporting/pipeline-runs/latest");

  try {
    let authHeaders: Headers | null = null;
    try {
      authHeaders = await getAuthorizedSessionHeaders();
    } catch {
      authHeaders = null;
    }
    const headers = authHeaders ?? new Headers();
    const upstreamResponse = await fetch(upstreamUrl, {
      method: "GET",
      headers,
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
        detail: `Error al consultar estado del pipeline: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 500 }
    );
  }
}

export async function POST(request: Request): Promise<Response> {
  const upstreamUrl = buildTrackflowApiUrl("/reporting/pipeline-runs");

  try {
    let body = {};
    try {
      body = await request.json();
    } catch {
      body = {};
    }

    let authHeaders: Headers | null = null;
    try {
      authHeaders = await getAuthorizedSessionHeaders({ "Content-Type": "application/json" });
    } catch {
      authHeaders = null;
    }
    const headers = authHeaders ?? new Headers({ "Content-Type": "application/json" });

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
    return Response.json(data, { status: upstreamResponse.status });
  } catch (error) {
    return Response.json(
      {
        detail: `Error al ejecutar pipeline: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 500 }
    );
  }
}
