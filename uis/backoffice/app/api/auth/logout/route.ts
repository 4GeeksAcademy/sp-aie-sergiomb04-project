import { NextResponse } from "next/server";

import { clearSessionCookie } from "@/app/features/auth/server/session";

export const runtime = "nodejs";

export async function POST(): Promise<NextResponse> {
  const response = NextResponse.json({ ok: true }, { status: 200 });
  return clearSessionCookie(response);
}