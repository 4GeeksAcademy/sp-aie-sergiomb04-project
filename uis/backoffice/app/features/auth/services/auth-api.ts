import {
  AuthUser,
  ForgotPasswordPayload,
  LoginPayload,
  MessageResponse,
  RegisterRequestPayload,
  ResetPasswordPayload,
} from "@/app/features/auth/types/auth";

const AUTH_API_BASE_PATH = "/api/auth";

type ApiErrorPayload = {
  detail?: string;
  message?: string;
  error?: string;
};

function buildErrorMessage(status: number, fallback: string, payload: ApiErrorPayload | null): string {
  const detail = payload?.detail ?? payload?.message ?? payload?.error;
  return detail || `Error ${status}: ${fallback}`;
}

async function authGatewayRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");

  const response = await fetch(`${AUTH_API_BASE_PATH}${path}`, {
    ...init,
    headers,
    cache: "no-store",
    credentials: "same-origin",
  });

  if (!response.ok) {
    const textBody = await response.text();
    let payload: ApiErrorPayload | null = null;

    if (textBody) {
      try {
        payload = JSON.parse(textBody) as ApiErrorPayload;
      } catch {
        payload = { detail: textBody };
      }
    }

    throw new Error(buildErrorMessage(response.status, response.statusText, payload));
  }

  const text = await response.text();
  return text ? (JSON.parse(text) as T) : ({} as T);
}

export async function login(payload: LoginPayload): Promise<AuthUser> {
  return authGatewayRequest<AuthUser>("/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function register(payload: RegisterRequestPayload): Promise<void> {
  await authGatewayRequest("/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function forgotPassword(payload: ForgotPasswordPayload): Promise<MessageResponse> {
  return authGatewayRequest<MessageResponse>("/forgot-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function resetPassword(payload: ResetPasswordPayload): Promise<MessageResponse> {
  return authGatewayRequest<MessageResponse>("/reset-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}