import {
  AuthUser,
  ChangePasswordPayload,
  ForgotPasswordPayload,
  LoginPayload,
  LoginResponse,
  MessageResponse,
  ProfileUpdatePayload,
  ResetPasswordPayload,
  RegisterRequestPayload,
} from "@/app/features/auth/types/auth";
import { clearSessionToken, getSessionToken, notifyUnauthorizedSession } from "@/app/features/auth/lib/session";

const API_URL = process.env.NEXT_PUBLIC_API_URL;
const AUTH_API_BASE_PATH = "/api/auth";

if (!API_URL) {
  throw new Error("NEXT_PUBLIC_API_URL no está definida en .env.local");
}

type ApiErrorPayload = {
  detail?: string;
  message?: string;
  error?: string;
};

function buildErrorMessage(status: number, fallback: string, payload: ApiErrorPayload | null): string {
  const detail = payload?.detail ?? payload?.message ?? payload?.error;
  return detail || `Error ${status}: ${fallback}`;
}

export async function authRequest<T>(
  path: string,
  init?: RequestInit,
  options?: { requireAuth?: boolean }
): Promise<T> {
  const token = getSessionToken();
  const requireAuth = options?.requireAuth ?? true;

  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  } else if (requireAuth) {
    notifyUnauthorizedSession();
    throw new Error("Tu sesión no es válida. Inicia sesión nuevamente.");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
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

    if (response.status === 401) {
      clearSessionToken();
      notifyUnauthorizedSession();
    }

    throw new Error(buildErrorMessage(response.status, response.statusText, payload));
  }

  const text = await response.text();
  return text ? (JSON.parse(text) as T) : ({} as T);
}

async function authGatewayRequest<T>(
  path: string,
  init?: RequestInit,
  options?: { requireAuth?: boolean }
): Promise<T> {
  const token = getSessionToken();
  const requireAuth = options?.requireAuth ?? true;

  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  } else if (requireAuth) {
    notifyUnauthorizedSession();
    throw new Error("Tu sesión no es válida. Inicia sesión nuevamente.");
  }

  const response = await fetch(`${AUTH_API_BASE_PATH}${path}`, {
    ...init,
    headers,
    cache: "no-store",
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

    if (response.status === 401) {
      clearSessionToken();
      notifyUnauthorizedSession();
    }

    throw new Error(buildErrorMessage(response.status, response.statusText, payload));
  }

  const text = await response.text();
  return text ? (JSON.parse(text) as T) : ({} as T);
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  return authGatewayRequest<LoginResponse>("/login", {
    method: "POST",
    body: JSON.stringify(payload),
  }, { requireAuth: false });
}

export async function register(payload: RegisterRequestPayload): Promise<void> {
  await authGatewayRequest("/register", {
    method: "POST",
    body: JSON.stringify(payload),
  }, { requireAuth: false });
}

export async function fetchMe(): Promise<AuthUser> {
  return authGatewayRequest<AuthUser>("/me");
}

export async function updateMyProfile(payload: ProfileUpdatePayload): Promise<AuthUser["profile"]> {
  return authGatewayRequest<AuthUser["profile"]>("/profile", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function forgotPassword(payload: ForgotPasswordPayload): Promise<MessageResponse> {
  return authGatewayRequest<MessageResponse>(
    "/forgot-password",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    { requireAuth: false }
  );
}

export async function resetPassword(payload: ResetPasswordPayload): Promise<MessageResponse> {
  return authGatewayRequest<MessageResponse>(
    "/reset-password",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    { requireAuth: false }
  );
}

export async function changePassword(payload: ChangePasswordPayload): Promise<MessageResponse> {
  return authGatewayRequest<MessageResponse>("/change-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
