import { NextRequest } from "next/server";

import { PATCH as patchIncidentStatus } from "@/app/api/incidents/[id]/status/route";
import { POST as createIncidentProxy } from "@/app/api/incidents/route";
import { POST as postTelemetryEventsProxy } from "@/app/api/telemetry/events/route";

const mockCookieGet = jest.fn();

jest.mock("next/headers", () => ({
  cookies: jest.fn(async () => ({
    get: mockCookieGet,
  })),
}));

describe("Incident & Telemetry API Proxy Routes", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("forwards Content-Type: application/json and Authorization in PATCH /api/incidents/[id]/status", async () => {
    mockCookieGet.mockReturnValue({ value: "valid-jwt-token" });

    const mockUpdatedIncident = {
      id: "inc-123",
      title: "Retraso en aduana",
      description: "Contenedor retenido",
      category: "customs",
      status: "in_progress",
      origin: "branch",
      branch: "zgz",
      created_at: "2026-10-29T10:00:00Z",
      updated_at: "2026-10-29T11:00:00Z",
    };

    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockUpdatedIncident,
    } as unknown as Response);
    global.fetch = fetchMock;

    const request = new NextRequest(
      "http://localhost:3000/api/incidents/inc-123/status",
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "in_progress" }),
      },
    );

    const response = await patchIncidentStatus(request, {
      params: Promise.resolve({ id: "inc-123" }),
    });

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [calledUrl, calledInit] = fetchMock.mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(calledUrl).toContain("/api/incidents/inc-123/status");
    expect(calledInit.method).toBe("PATCH");

    const headers = new Headers(calledInit.headers);
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("Authorization")).toBe("Bearer valid-jwt-token");
    expect(calledInit.body).toBe(JSON.stringify({ status: "in_progress" }));
  });

  it("forwards Content-Type: application/json and Authorization in POST /api/incidents", async () => {
    mockCookieGet.mockReturnValue({ value: "valid-jwt-token" });

    const payload = {
      title: "Paquete dañado",
      description: "Caja aplastada en tránsito",
      category: "damage",
      origin: "customer",
      branch: "la",
    };

    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        id: "inc-456",
        ...payload,
        status: "open",
        created_at: "2026-10-29T10:00:00Z",
        updated_at: "2026-10-29T10:00:00Z",
      }),
    } as unknown as Response);
    global.fetch = fetchMock;

    const request = new Request("http://localhost:3000/api/incidents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const response = await createIncidentProxy(request);
    expect(response.status).toBe(201);

    const [, calledInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(calledInit.headers);
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("Authorization")).toBe("Bearer valid-jwt-token");
  });

  it("proxies POST /api/telemetry/events with Content-Type: application/json", async () => {
    mockCookieGet.mockReturnValue(undefined);

    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({ received: 1, rejected: 0, errors: [] }),
    } as unknown as Response);
    global.fetch = fetchMock;

    const request = new Request("http://localhost:3000/api/telemetry/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events: [] }),
    });

    const response = await postTelemetryEventsProxy(request);
    expect(response.status).toBe(202);

    const [calledUrl, calledInit] = fetchMock.mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(calledUrl).toContain("/telemetry/events");
    const headers = new Headers(calledInit.headers);
    expect(headers.get("Content-Type")).toBe("application/json");
  });
});
