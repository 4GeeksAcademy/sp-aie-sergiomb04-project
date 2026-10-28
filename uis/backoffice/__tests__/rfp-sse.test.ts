import {
  RFP_TICKET_CREATED_EVENT,
  calculateProgressiveBackoff,
  connectRfpSseWithFetch,
  deduplicateRfpTickets,
  normalizeRfpTicketPayload,
  parseSseStreamBuffer,
} from "@/app/features/rfp/services/rfp-sse";

describe("parseSseStreamBuffer", () => {
  it("parses keep-alive comments and rfp_ticket_created frames across chunks", () => {
    const raw =
      ": keep-alive\n\n" +
      "id: evt-101\n" +
      "event: rfp_ticket_created\n" +
      'data: {"ticket_id":"101","rfp_id":"RFP-101AAA","status":"analizando","raw_pdf_path":"data/raw/101.pdf"}\n\n' +
      "id: evt-incomplete\nevent: rfp_ticket_created";

    const { frames, remainder } = parseSseStreamBuffer(raw);
    expect(frames).toHaveLength(2);
    expect(frames[0].isComment).toBe(true);
    expect(frames[1].isComment).toBe(false);
    expect(frames[1].id).toBe("evt-101");
    expect(frames[1].event).toBe(RFP_TICKET_CREATED_EVENT);
    expect(JSON.parse(frames[1].data).ticket_id).toBe("101");
    expect(remainder).toBe("id: evt-incomplete\nevent: rfp_ticket_created");
  });
});

describe("calculateProgressiveBackoff", () => {
  it("computes progressive exponential backoff capped at maxDelayMs", () => {
    expect(calculateProgressiveBackoff(0, 1000, 30000)).toBe(1000);
    expect(calculateProgressiveBackoff(1, 1000, 30000)).toBe(2000);
    expect(calculateProgressiveBackoff(2, 1000, 30000)).toBe(4000);
    expect(calculateProgressiveBackoff(3, 1000, 30000)).toBe(8000);
    expect(calculateProgressiveBackoff(6, 1000, 30000)).toBe(30000);
  });
});

describe("deduplicateRfpTickets", () => {
  it("deduplicates tickets by ticket_id and preserves live SSE status and newest metadata", () => {
    const t1 = normalizeRfpTicketPayload(
      {
        ticket_id: "t-1",
        rfp_id: "RFP-000001",
        status: "analizando",
        raw_pdf_path: "data/raw/t-1.pdf",
        client_name: "ModaViva",
        client_country: "Spain",
        created_at: "2026-10-23T10:00:00Z",
        updated_at: "2026-10-23T10:00:00Z",
      },
      { isLiveNotification: true }
    );

    const t1DuplicateFromRefetch = normalizeRfpTicketPayload(
      {
        ticket_id: "t-1",
        rfp_id: "RFP-000001",
        status: "analisis_completo",
        raw_pdf_path: "data/raw/t-1.pdf",
        client_name: "ModaViva",
        client_country: "Spain",
        departments_needed: ["warehouse", "reverse"],
        created_at: "2026-10-23T10:00:00Z",
        updated_at: "2026-10-23T10:05:00Z",
      },
      { isLiveNotification: false }
    );

    const t2 = normalizeRfpTicketPayload({
      ticket_id: "t-2",
      rfp_id: "RFP-000002",
      status: "analizando",
      raw_pdf_path: "data/raw/t-2.pdf",
      client_name: "Luna Cosmetics",
      client_country: "USA",
      created_at: "2026-10-23T11:00:00Z",
      updated_at: "2026-10-23T11:00:00Z",
    });

    const merged = deduplicateRfpTickets([t1], [t1DuplicateFromRefetch, t2]);
    expect(merged).toHaveLength(2);
    expect(merged[0].ticket_id).toBe("t-2");
    expect(merged[1].ticket_id).toBe("t-1");
    expect(merged[1].isLiveNotification).toBe(true);
    expect(merged[1].status).toBe("analisis_completo");
    expect(merged[1].departments_needed).toEqual(["warehouse", "reverse"]);
  });
});

describe("connectRfpSseWithFetch", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("sends Authorization Bearer JWT and Last-Event-ID headers and streams ReadableStream frames", async () => {
    const encoder = new TextEncoder();
    const chunks = [
      encoder.encode(": keep-alive\n\n"),
      encoder.encode(
        'id: evt-t-99\nevent: rfp_ticket_created\ndata: {"ticket_id":"t-99","rfp_id":"RFP-999999","status":"analizando","raw_pdf_path":"data/raw/t-99.pdf","client_name":"ModaViva","client_country":"Spain","currency":"EUR","departments_needed":["warehouse","reverse"],"created_at":"2026-10-23T12:00:00Z","updated_at":"2026-10-23T12:00:00Z"}\n\n'
      ),
    ];

    let index = 0;
    const mockStream = new ReadableStream<Uint8Array>({
      pull(controller) {
        if (index < chunks.length) {
          controller.enqueue(chunks[index++]);
        } else {
          controller.close();
        }
      },
    });

    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({
        "Content-Type": "text/event-stream; charset=utf-8",
      }),
      body: mockStream,
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    const received: Array<{ ticketId: string; eventId: string | null }> = [];
    let opened = false;
    let keepAlives = 0;
    const abortController = new AbortController();

    await connectRfpSseWithFetch({
      url: "/api/rfp/stream",
      jwtToken: "jwt-secret-token-123",
      lastEventId: "evt-prev-1",
      signal: abortController.signal,
      onOpen: () => {
        opened = true;
      },
      onKeepAlive: () => {
        keepAlives += 1;
      },
      onTicketCreated: (ticket, eventId) => {
        received.push({ ticketId: ticket.ticket_id, eventId });
      },
    });

    expect(opened).toBe(true);
    expect(keepAlives).toBe(1);
    expect(received).toEqual([{ ticketId: "t-99", eventId: "evt-t-99" }]);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, requestInit] = fetchMock.mock.calls[0];
    expect(requestInit.headers).toMatchObject({
      Accept: "text/event-stream",
      Authorization: "Bearer jwt-secret-token-123",
      "Last-Event-ID": "evt-prev-1",
    });
  });
});
