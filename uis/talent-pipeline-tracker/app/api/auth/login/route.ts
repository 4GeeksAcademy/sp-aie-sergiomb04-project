import { LoginResponse } from "@/app/features/auth/types/auth";
import { proxyAuthRequest } from "@/app/api/auth/_lib/trackflow-auth";

export const runtime = "nodejs";

export async function POST(request: Request) {
  return proxyAuthRequest<LoginResponse>({
    method: "POST",
    path: "/auth/login",
    request,
    requireAuth: false,
  });
}
