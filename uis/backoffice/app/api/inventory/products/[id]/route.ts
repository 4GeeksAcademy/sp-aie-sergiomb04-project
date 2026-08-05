export const runtime = "nodejs";

import {
  buildInventoryApiUrl,
  getInventoryAuthHeaders,
  toInventoryErrorResponse,
} from "@/app/api/inventory/_lib/inventory-proxy";

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> }
): Promise<Response> {
  const { id } = await context.params;
  const headers = await getInventoryAuthHeaders();

  if (!headers) {
    return Response.json({ detail: "Unauthorized" }, { status: 401 });
  }

  try {
    const upstreamResponse = await fetch(buildInventoryApiUrl(`/inventory/products/${id}`), {
      method: "GET",
      headers,
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      return toInventoryErrorResponse(upstreamResponse, "Error del backend de inventory");
    }

    return Response.json(await upstreamResponse.json(), { status: 200 });
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend Python de inventory" },
      { status: 502 }
    );
  }
}
