import telemetryService, {
  track,
  normalizeWarehouse,
  sha256,
  getDeviceType,
} from "@/app/services/telemetry";

describe("TelemetryService", () => {
  beforeEach(() => {
    telemetryService.destroy();
    jest.clearAllMocks();
  });

  afterEach(() => {
    telemetryService.destroy();
  });

  it("normalizes warehouse names accurately", () => {
    expect(normalizeWarehouse("LA")).toBe("los_angeles");
    expect(normalizeWarehouse("la")).toBe("los_angeles");
    expect(normalizeWarehouse("los_angeles")).toBe("los_angeles");
    expect(normalizeWarehouse("ZGZ")).toBe("zaragoza");
    expect(normalizeWarehouse("zgz")).toBe("zaragoza");
    expect(normalizeWarehouse("zaragoza")).toBe("zaragoza");
    expect(normalizeWarehouse(null)).toBe("los_angeles");
    expect(normalizeWarehouse(undefined)).toBe("los_angeles");
  });

  it("hashes identifiers with SHA-256 fallback", async () => {
    const hash = await sha256("test@trackflow.com");
    expect(typeof hash).toBe("string");
    expect(hash.length).toBeGreaterThan(0);
    // Same input produces same hash
    const hash2 = await sha256("test@trackflow.com");
    expect(hash).toBe(hash2);
  });

  it("queues and tracks events without throwing", () => {
    expect(() => {
      track("inbound_order_created", {
        warehouse: "los_angeles",
        client_id: "Fashion Co",
        product_id: "CLT-001",
        product_category: "fashion",
        quantity: 50,
        order_id: "ord-1",
        reference: "PO-100",
        user_uuid: "user-1",
      });
    }).not.toThrow();
  });

  it("handles getDeviceType correctly", () => {
    const device = getDeviceType();
    expect(["desktop", "mobile", "tablet", "unknown"]).toContain(device);
  });
});
