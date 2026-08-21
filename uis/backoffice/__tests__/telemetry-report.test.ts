import { GET as getReportProxy } from "@/app/api/telemetry/report/route";

describe("Telemetry Report API Proxy & Features", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("handles upstream telemetry report proxying successfully", async () => {
    const mockReportData = {
      period: {
        from: "2026-08-12T00:00:00Z",
        to: "2026-08-19T00:00:00Z",
      },
      metrics: {
        events_per_day: [{ date: "2026-08-18", count: 12 }],
        error_rate_by_type: [{ event_type: "api_request_failed", count: 1, total_events: 12, error_rate: 0.0833 }],
        auth_failure_rate: [{ date: "2026-08-18", failed: 1, succeeded: 3, total_attempts: 4, failure_rate: 0.25 }],
        latency_by_route: [{ api_route: "/api/incidents", method: "GET", sample_count: 5, avg_latency_ms: 120, min_latency_ms: 80, max_latency_ms: 200, p95_latency_ms: 190 }],
      },
    };

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockReportData,
    } as unknown as Response);

    const request = new Request("http://localhost:3000/api/telemetry/report?start_date=2026-08-12T00:00:00Z&end_date=2026-08-19T00:00:00Z");
    const response = await getReportProxy(request);

    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.period.from).toBe("2026-08-12T00:00:00Z");
    expect(data.metrics.events_per_day).toHaveLength(1);
    expect(data.metrics.auth_failure_rate).toHaveLength(1);
    expect(data.metrics.error_rate_by_type).toHaveLength(1);
  });

  it("handles upstream error gracefully", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => JSON.stringify({ detail: "Database connection error" }),
    } as unknown as Response);

    const request = new Request("http://localhost:3000/api/telemetry/report");
    const response = await getReportProxy(request);

    expect(response.status).toBe(500);
  });
});
