import { proxyAuthRequest } from "@/app/api/auth/_lib/trackflow-auth";

export const runtime = "nodejs";

export async function POST(request: Request) {
  return proxyAuthRequest({
    method: "POST",
    path: "/users",
    request,
    requireAuth: false,
  });
}
