import { getAuthorizedSessionHeaders } from "@/app/features/auth/server/session";

type UpstreamError = {
  detail?: unknown;
  error?: string;
  message?: string;
};

const DEFAULT_INVENTORY_API_BASE_URL = "http://localhost:8000";

export function getInventoryApiBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_INVENTORY_API_URL ??
    process.env.TRACKFLOW_API_BASE_URL ??
    DEFAULT_INVENTORY_API_BASE_URL
  ).replace(/\/$/, "");
}

export function buildInventoryApiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${getInventoryApiBaseUrl()}${normalizedPath}`;
}

export async function getInventoryAuthHeaders(init?: HeadersInit): Promise<Headers | null> {
  return getAuthorizedSessionHeaders(init);
}

export async function toInventoryErrorResponse(
  upstreamResponse: Response,
  fallbackDetail: string
): Promise<Response> {
  const payload = (await upstreamResponse.json().catch(() => null)) as UpstreamError | null;

  return Response.json(
    {
      error: payload?.error,
      detail: payload?.detail ?? payload?.message ?? fallbackDetail,
    },
    { status: upstreamResponse.status }
  );
}
