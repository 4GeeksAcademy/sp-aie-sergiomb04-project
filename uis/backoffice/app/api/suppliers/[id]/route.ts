export const runtime = "nodejs";

const INCIDENTS_API_BASE_URL = "http://localhost:8000";

type UpstreamError = {
  detail?: unknown;
  error?: string;
};

async function toErrorResponse(upstreamResponse: Response): Promise<Response> {
  const payload = (await upstreamResponse.json().catch(() => null)) as UpstreamError | null;

  return Response.json(
    {
      error: payload?.error,
      detail: payload?.detail ?? "Error del backend de proveedores",
    },
    { status: upstreamResponse.status }
  );
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> }
): Promise<Response> {
  const { id } = await context.params;

  try {
    const upstreamResponse = await fetch(`${INCIDENTS_API_BASE_URL}/suppliers/${id}`, {
      method: "GET",
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      return toErrorResponse(upstreamResponse);
    }

    return Response.json(await upstreamResponse.json(), { status: 200 });
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend Python de suppliers" },
      { status: 502 }
    );
  }
}

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ id: string }> }
): Promise<Response> {
  const { id } = await context.params;

  try {
    const upstreamResponse = await fetch(`${INCIDENTS_API_BASE_URL}/suppliers/${id}`, {
      method: "DELETE",
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      return toErrorResponse(upstreamResponse);
    }

    return Response.json(await upstreamResponse.json(), { status: 200 });
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend Python de suppliers" },
      { status: 502 }
    );
  }
}
