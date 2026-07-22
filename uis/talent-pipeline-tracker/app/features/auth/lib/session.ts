const TOKEN_KEY = "token";
const AUTH_CHANGED_EVENT = "trackflow-auth-changed";
const AUTH_UNAUTHORIZED_EVENT = "trackflow-auth-unauthorized";

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getTokenStorageKey(): string {
  return TOKEN_KEY;
}

export function getAuthChangedEventName(): string {
  return AUTH_CHANGED_EVENT;
}

export function getUnauthorizedEventName(): string {
  return AUTH_UNAUTHORIZED_EVENT;
}

export function getSessionToken(): string | null {
  if (!isBrowser()) {
    return null;
  }

  return localStorage.getItem(TOKEN_KEY);
}

export function setSessionToken(token: string): void {
  if (!isBrowser()) {
    return;
  }

  localStorage.setItem(TOKEN_KEY, token);
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export function clearSessionToken(): void {
  if (!isBrowser()) {
    return;
  }

  localStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export function notifyUnauthorizedSession(): void {
  if (!isBrowser()) {
    return;
  }

  window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
}
