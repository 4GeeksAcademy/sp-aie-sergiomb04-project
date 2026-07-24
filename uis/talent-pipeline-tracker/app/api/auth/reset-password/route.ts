import { MessageResponse } from "@/app/features/auth/types/auth";
import { proxyAuthRequest } from "@/app/api/auth/_lib/trackflow-auth";

export const runtime = "nodejs";

export async function POST(request: Request) {
  return proxyAuthRequest<MessageResponse>({
    method: "POST",
    path: "/auth/reset-password",
    request,
    requireAuth: false,
  });
}
