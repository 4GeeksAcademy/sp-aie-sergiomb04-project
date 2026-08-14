/**
 * TelemetryService — Centralized telemetry capture for TrackFlow Backoffice.
 *
 * Responsibilities:
 * - Queue events in a local in-memory buffer.
 * - Flush in batches (every 10 s or 20 events, whichever comes first).
 * - Reliable flush via navigator.sendBeacon on visibilitychange.
 * - Exponential-backoff retries (max 3 attempts) before discarding a batch.
 * - Auto-generate envelope fields (eventId, sessionId, userId, timestamp,
 *   schemaVersion, requestId) so callers only provide eventType + properties.
 *
 * Public API: `track(eventType, properties)` — the only function components should call.
 */

// ─── Configuration ────────────────────────────────────────────────────────────

const TELEMETRY_ENDPOINT =
  process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT ?? "http://localhost:8000/telemetry/events";

const BATCH_SIZE = 20;
const FLUSH_INTERVAL_MS = 10_000;
const MAX_RETRIES = 3;
const SCHEMA_VERSION = "1.0.0";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function generateUUID(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for environments without crypto.randomUUID
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function getDeviceType(): "desktop" | "mobile" | "tablet" | "unknown" {
  if (typeof navigator === "undefined") return "unknown";
  const ua = navigator.userAgent.toLowerCase();
  if (/tablet|ipad/i.test(ua)) return "tablet";
  if (/mobile|iphone|android.*mobile/i.test(ua)) return "mobile";
  if (/windows|macintosh|linux/i.test(ua)) return "desktop";
  return "unknown";
}

/**
 * Compute a SHA-256 hash of a string (for identity_hash).
 * Uses SubtleCrypto when available, returns a hex-encoded hash.
 */
async function sha256(input: string): Promise<string> {
  if (typeof crypto !== "undefined" && crypto.subtle) {
    const data = new TextEncoder().encode(input);
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    return Array.from(new Uint8Array(hashBuffer))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }
  // Fallback: return a simple hash indicator (non-production)
  return `hash_${input.length}_${Date.now()}`;
}

function normalizeWarehouse(warehouse?: string | null): "los_angeles" | "zaragoza" {
  if (!warehouse) return "los_angeles";
  const normalized = warehouse.toLowerCase().trim();
  if (normalized === "zgz" || normalized === "zaragoza") {
    return "zaragoza";
  }
  return "los_angeles";
}

// ─── Event envelope type ──────────────────────────────────────────────────────

type TelemetryEvent = {
  eventId: string;
  timestamp: string;
  sessionId: string;
  userId: string | null;
  event_type: string;
  schemaVersion: string;
  requestId: string;
  properties: Record<string, unknown>;
};

// ─── Singleton service ────────────────────────────────────────────────────────

class TelemetryService {
  private queue: TelemetryEvent[] = [];
  private flushTimer: ReturnType<typeof setInterval> | null = null;
  private sessionId: string;
  private userId: string | null = null;
  private initialized = false;

  constructor() {
    this.sessionId = generateUUID();
  }

  /**
   * Initialize the service: start the flush interval and register
   * the visibilitychange listener. Call once on app mount.
   */
  init(): void {
    if (this.initialized) return;
    this.initialized = true;

    // Periodic flush
    this.flushTimer = setInterval(() => {
      void this.flush();
    }, FLUSH_INTERVAL_MS);

    // Reliable flush on page hide
    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") {
          this.flushWithBeacon();
        }
      });
    }
  }

  /**
   * Set the authenticated user ID for envelope enrichment.
   */
  setUserId(userId: string | null): void {
    this.userId = userId;
  }

  /**
   * Get current session ID (for external use, e.g., session_age_seconds calculation).
   */
  getSessionId(): string {
    return this.sessionId;
  }

  /**
   * Track a telemetry event. Components should only call this function.
   * Envelope fields are generated automatically.
   */
  track(eventType: string, properties: Record<string, unknown>): void {
    const event: TelemetryEvent = {
      eventId: generateUUID(),
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
      userId: this.userId,
      event_type: eventType,
      schemaVersion: SCHEMA_VERSION,
      requestId: generateUUID(),
      properties,
    };

    this.queue.push(event);

    // Flush immediately if batch size reached
    if (this.queue.length >= BATCH_SIZE) {
      void this.flush();
    }
  }

  /**
   * Flush queued events via fetch with exponential-backoff retries.
   */
  private async flush(): Promise<void> {
    if (this.queue.length === 0) return;

    const batch = this.queue.splice(0);
    const payload = JSON.stringify({ events: batch });

    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      try {
        const response = await fetch(TELEMETRY_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload,
        });

        if (response.ok) {
          return; // Success — batch delivered
        }

        // Non-retryable server error
        if (response.status >= 400 && response.status < 500) {
          console.warn(
            `[Telemetry] Server rejected batch (HTTP ${response.status}). Discarding ${batch.length} events.`
          );
          return;
        }
      } catch {
        // Network error — will retry
      }

      // Exponential backoff: 1s, 2s, 4s
      const delayMs = Math.pow(2, attempt) * 1000;
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }

    // All retries exhausted — discard
    console.warn(
      `[Telemetry] Failed after ${MAX_RETRIES} retries. Discarding ${batch.length} events.`
    );
  }

  /**
   * Flush using navigator.sendBeacon for reliable delivery on page unload.
   */
  private flushWithBeacon(): void {
    if (this.queue.length === 0) return;

    const batch = this.queue.splice(0);
    const payload = JSON.stringify({ events: batch });

    if (typeof navigator !== "undefined" && navigator.sendBeacon) {
      const sent = navigator.sendBeacon(
        TELEMETRY_ENDPOINT,
        new Blob([payload], { type: "application/json" })
      );

      if (!sent) {
        console.warn(
          `[Telemetry] sendBeacon failed. Discarding ${batch.length} events.`
        );
      }
    }
  }

  /**
   * Teardown — clear the flush timer. Mostly for testing.
   */
  destroy(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
    this.initialized = false;
  }
}

// ─── Singleton instance ───────────────────────────────────────────────────────

const telemetryService = new TelemetryService();

/**
 * Track a telemetry event. This is the only public function components should use.
 *
 * @param eventType — The event_type from the approved telemetry catalog.
 * @param properties — Event-specific properties matching the allowlist for this event_type.
 */
export function track(
  eventType: string,
  properties: Record<string, unknown>
): void {
  telemetryService.track(eventType, properties);
}

export function initTelemetry(): void {
  telemetryService.init();
}

export function setTelemetryUserId(userId: string | null): void {
  telemetryService.setUserId(userId);
}

export function getTelemetrySessionId(): string {
  return telemetryService.getSessionId();
}

export { sha256, getDeviceType, normalizeWarehouse };

export default telemetryService;
