import { AuthProfile } from "@/app/features/auth/types/auth";
import { proxyAuthRequest } from "@/app/api/auth/_lib/trackflow-auth";

export const runtime = "nodejs";

export async function PUT(request: Request) {
  return proxyAuthRequest<AuthProfile>({
    method: "PUT",
    path: "/profiles/me",
    request,
    requireAuth: true,
  });
}
