import { NextResponse } from "next/server";
import { getSessionToken } from "@/app/features/auth/server/session";

export const runtime = "nodejs";

export async function GET(): Promise<NextResponse> {
  const token = await getSessionToken();

  if (!token) {
    return NextResponse.json(
      { detail: "No hay sesión activa con JWT en el backoffice." },
      { status: 401 }
    );
  }

  return NextResponse.json(
    { access_token: token, token_type: "bearer" },
    { status: 200 }
  );
}
