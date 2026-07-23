import { AuthUser } from "@/app/features/auth/types/auth";
import { proxyAuthRequest } from "@/app/api/auth/_lib/trackflow-auth";

export const runtime = "nodejs";

export async function GET(request: Request) {
  return proxyAuthRequest<AuthUser>({
    method: "GET",
    path: "/auth/me",
    request,
    requireAuth: true,
  });
}
