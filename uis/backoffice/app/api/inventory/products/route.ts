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
    const upstreamResponse = await fetch(buildInventoryApiUrl("/inventory/products"), {
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

export async function POST(request: Request): Promise<Response> {
  const headers = await getInventoryAuthHeaders({
    "Content-Type": "application/json",
  });

  if (!headers) {
    return Response.json({ detail: "Unauthorized" }, { status: 401 });
  }

  try {
    const body = await request.json();

    const upstreamResponse = await fetch(buildInventoryApiUrl("/inventory/products"), {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      return toInventoryErrorResponse(upstreamResponse, "Error del backend de inventory");
    }

    return Response.json(await upstreamResponse.json(), { status: 201 });
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend Python de inventory" },
      { status: 502 }
    );
  }
}
