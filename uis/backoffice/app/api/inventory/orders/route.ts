export const runtime = "nodejs";

import {
  buildInventoryApiUrl,
  getInventoryAuthHeaders,
  toInventoryErrorResponse,
} from "@/app/api/inventory/_lib/inventory-proxy";

export async function GET(): Promise<Response> {
  const headers = await getInventoryAuthHeaders();

  if (!headers) {
    return Response.json({ detail: "Unauthorized" }, { status: 401 });
  }

  try {
    const upstreamResponse = await fetch(buildInventoryApiUrl("/inventory/orders"), {
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
