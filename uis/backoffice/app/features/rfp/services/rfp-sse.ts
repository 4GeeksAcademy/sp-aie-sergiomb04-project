export const RFP_TICKET_CREATED_EVENT = "rfp_ticket_created";

export interface RFPTicketMetadataFields {
  client_name?: string | null;
  client_country?: string | null;
  currency?: string | null;
  services_requested?: string[];
  monthly_volume?: number | null;
  deadline?: string | null;
  budget_range?: string | null;
  departments_needed?: string[];
  readability_metrics?: Record<string, number>;
}

export interface RFPTicketSSEPayload extends RFPTicketMetadataFields {
  event_id?: string;
  event?: string;
  ticket_id: string;
  id?: string;
  rfp_id: string;
  status: string;
  raw_pdf_path: string;
  pdf_path?: string;
  original_filename?: string | null;
  metadata?: RFPTicketMetadataFields;
  created_at: string;
  updated_at: string;
}

export interface RFPTicketUIItem extends RFPTicketSSEPayload {
  isLiveNotification?: boolean;
  receivedViaSseAt?: string;
}

export interface ParsedSseFrame {
  id: string | null;
  event: string;
  data: string;
  isComment: boolean;
}

/**
 * Parse raw SSE stream text into complete frames and trailing incomplete buffer.
 */
export function parseSseStreamBuffer(buffer: string): {
  frames: ParsedSseFrame[];
  remainder: string;
} {
  const normalized = buffer.replace(/\r\n/g, "\n");
  const parts = normalized.split("\n\n");
  const remainder = parts.pop() ?? "";
  const frames: ParsedSseFrame[] = [];

  for (const rawBlock of parts) {
    const trimmedBlock = rawBlock.trim();
    if (!trimmedBlock) {
      continue;
    }

    const lines = rawBlock.split("\n");
    const nonEmptyLines = lines.filter((line) => line.trim().length > 0);
    if (nonEmptyLines.every((line) => line.trim().startsWith(":"))) {
      frames.push({
        id: null,
        event: "comment",
        data: nonEmptyLines.map((l) => l.replace(/^:\s?/, "")).join("\n"),
        isComment: true,
      });
      continue;
    }

    let frameId: string | null = null;
    let eventName = "message";
    const dataLines: string[] = [];

    for (const line of lines) {
      if (!line || line.startsWith(":")) {
        continue;
      }
      if (line.startsWith("id:")) {
        frameId = line.slice(3).trim();
      } else if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }

    frames.push({
      id: frameId,
      event: eventName,
      data: dataLines.join("\n"),
      isComment: false,
    });
  }

  return { frames, remainder };
}

/**
 * Compute progressive (exponential) backoff delay in milliseconds for SSE reconnection.
 */
export function calculateProgressiveBackoff(
  attempt: number,
  baseDelayMs = 1000,
  maxDelayMs = 30000
): number {
  const safeAttempt = Math.max(0, Math.floor(attempt));
  const delay = baseDelayMs * Math.pow(2, safeAttempt);
  return Math.min(maxDelayMs, delay);
}

/**
 * Normalize an incoming RFP ticket payload so top-level and nested metadata fields are always consistent.
 */
export function normalizeRfpTicketPayload(
  raw: Partial<RFPTicketSSEPayload> & { ticket_id: string },
  options?: { isLiveNotification?: boolean; eventId?: string | null }
): RFPTicketUIItem {
  const meta = raw.metadata ?? {};
  const ticketId = String(raw.ticket_id || raw.id || "");
  const rfpId =
    raw.rfp_id ||
    `RFP-${ticketId.replace(/-/g, "").slice(0, 6).toUpperCase()}`;
  const rawPdfPath =
    raw.raw_pdf_path || raw.pdf_path || `data/raw/${ticketId}.pdf`;
  const createdAt = raw.created_at || new Date().toISOString();
  const updatedAt = raw.updated_at || createdAt;
  const clientCountry = raw.client_country ?? meta.client_country ?? null;
  const currency =
    raw.currency ??
    meta.currency ??
    (clientCountry === "Spain"
      ? "EUR"
      : clientCountry === "USA"
        ? "USD"
        : null);

  return {
    event_id: options?.eventId || raw.event_id || `evt-${ticketId}`,
    event: raw.event || RFP_TICKET_CREATED_EVENT,
    ticket_id: ticketId,
    id: ticketId,
    rfp_id: rfpId,
    status: raw.status || "analizando",
    raw_pdf_path: rawPdfPath,
    pdf_path: rawPdfPath,
    original_filename: raw.original_filename ?? null,
    client_name: raw.client_name ?? meta.client_name ?? null,
    client_country: clientCountry,
    currency,
    services_requested:
      raw.services_requested ?? meta.services_requested ?? [],
    monthly_volume: raw.monthly_volume ?? meta.monthly_volume ?? null,
    deadline: raw.deadline ?? meta.deadline ?? null,
    budget_range: raw.budget_range ?? meta.budget_range ?? null,
    departments_needed:
      raw.departments_needed ?? meta.departments_needed ?? [],
    readability_metrics:
      raw.readability_metrics ?? meta.readability_metrics ?? {},
    metadata: {
      client_name: raw.client_name ?? meta.client_name ?? null,
      client_country: clientCountry,
      currency,
      services_requested:
        raw.services_requested ?? meta.services_requested ?? [],
      monthly_volume: raw.monthly_volume ?? meta.monthly_volume ?? null,
      deadline: raw.deadline ?? meta.deadline ?? null,
      budget_range: raw.budget_range ?? meta.budget_range ?? null,
      departments_needed:
        raw.departments_needed ?? meta.departments_needed ?? [],
    },
    created_at: createdAt,
    updated_at: updatedAt,
    isLiveNotification: Boolean(options?.isLiveNotification),
    receivedViaSseAt: options?.isLiveNotification
      ? new Date().toISOString()
      : undefined,
  };
}

/**
 * Deduplicate and merge RFP ticket lists by `ticket_id` (and `rfp_id`), preserving live SSE notification badges.
 */
export function deduplicateRfpTickets(
  existing: RFPTicketUIItem[],
  incoming: RFPTicketUIItem[]
): RFPTicketUIItem[] {
  const byTicketId = new Map<string, RFPTicketUIItem>();

  for (const item of existing) {
    if (!item?.ticket_id) continue;
    byTicketId.set(item.ticket_id, item);
  }

  for (const item of incoming) {
    if (!item?.ticket_id) continue;
    const prev = byTicketId.get(item.ticket_id);
    if (!prev) {
      byTicketId.set(item.ticket_id, item);
      continue;
    }

    byTicketId.set(item.ticket_id, {
      ...prev,
      ...item,
      client_name: item.client_name ?? prev.client_name,
      client_country: item.client_country ?? prev.client_country,
      currency: item.currency ?? prev.currency,
      services_requested:
        item.services_requested && item.services_requested.length > 0
          ? item.services_requested
          : prev.services_requested,
      departments_needed:
        item.departments_needed && item.departments_needed.length > 0
          ? item.departments_needed
          : prev.departments_needed,
      monthly_volume: item.monthly_volume ?? prev.monthly_volume,
      deadline: item.deadline ?? prev.deadline,
      budget_range: item.budget_range ?? prev.budget_range,
      isLiveNotification: Boolean(
        prev.isLiveNotification || item.isLiveNotification
      ),
      receivedViaSseAt: prev.receivedViaSseAt ?? item.receivedViaSseAt,
    });
  }

  return Array.from(byTicketId.values()).sort((a, b) => {
    const timeA = Date.parse(a.created_at || "") || 0;
    const timeB = Date.parse(b.created_at || "") || 0;
    return timeB - timeA;
  });
}

export interface ConnectRfpSseOptions {
  url: string;
  jwtToken: string;
  lastEventId?: string | null;
  signal: AbortSignal;
  onOpen?: () => void;
  onKeepAlive?: () => void;
  onTicketCreated: (ticket: RFPTicketUIItem, eventId: string | null) => void;
}

/**
 * Consume an SSE stream using `fetch` + `ReadableStream` so the Backoffice JWT can be sent in headers.
 */
export async function connectRfpSseWithFetch({
  url,
  jwtToken,
  lastEventId,
  signal,
  onOpen,
  onKeepAlive,
  onTicketCreated,
}: ConnectRfpSseOptions): Promise<void> {
  const headers: Record<string, string> = {
    Accept: "text/event-stream",
    "Cache-Control": "no-cache",
    Authorization: `Bearer ${jwtToken}`,
  };

  if (lastEventId) {
    headers["Last-Event-ID"] = lastEventId;
  }

  const response = await fetch(url, {
    method: "GET",
    headers,
    signal,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(
      `SSE connection failed with HTTP ${response.status}`
    );
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("text/event-stream")) {
    throw new Error(
      `Invalid SSE Content-Type: expected text/event-stream, received '${contentType}'`
    );
  }

  if (!response.body) {
    throw new Error("ReadableStream body is not available on SSE response");
  }

  onOpen?.();

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (!signal.aborted) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const { frames, remainder } = parseSseStreamBuffer(buffer);
      buffer = remainder;

      for (const frame of frames) {
        if (frame.isComment) {
          onKeepAlive?.();
          continue;
        }

        if (frame.event === RFP_TICKET_CREATED_EVENT && frame.data) {
          try {
            const parsed = JSON.parse(frame.data) as RFPTicketSSEPayload;
            if (parsed && parsed.ticket_id) {
              const normalized = normalizeRfpTicketPayload(parsed, {
                isLiveNotification: true,
                eventId: frame.id,
              });
              onTicketCreated(normalized, normalized.event_id ?? frame.id);
            }
          } catch {
            // Ignore malformed JSON frames without crashing the stream reader
          }
        }
      }
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // Reader already released
    }
  }
}
