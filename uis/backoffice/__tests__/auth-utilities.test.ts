import { getNextStatuses } from "@/app/features/incidents/types/incident-domain";
import { hasAnalysisResult, downloadCsvBlob } from "@/app/features/incidents/services/api";
import {
  buildTrackflowApiUrl,
  createAuthorizedHeaders,
  applySessionCookie,
  clearSessionCookie,
} from "@/app/features/auth/server/session";
import { NextResponse } from "next/server";

// ─── Utility 1: getNextStatuses ───────────────────────────────────────────────

describe("getNextStatuses", () => {
  it("returns [in_progress, discarded] for open", () => {
    const result = getNextStatuses("open");
    expect(result).toEqual(["in_progress", "discarded"]);
  });

  it("returns [resolved, discarded] for in_progress", () => {
    const result = getNextStatuses("in_progress");
    expect(result).toEqual(["resolved", "discarded"]);
  });

  it("returns empty array for resolved", () => {
    const result = getNextStatuses("resolved");
    expect(result).toEqual([]);
  });

  it("returns empty array for discarded", () => {
    const result = getNextStatuses("discarded");
    expect(result).toEqual([]);
  });

  // Failure mode: invalid status
  it("returns empty array for unknown status", () => {
    const result = getNextStatuses("unknown" as any);
    expect(result).toEqual([]);
  });
});

// ─── Utility 2: hasAnalysisResult ─────────────────────────────────────────────

describe("hasAnalysisResult", () => {
  it("returns false when result is null", () => {
    expect(hasAnalysisResult(null)).toBe(false);
  });

  it("returns true when result is an object", () => {
    const result = {
      source_file: "test.csv",
      total_records: 10,
      valid_records: 8,
      invalid_records: 2,
      invalid_breakdown: {},
      by_category: {},
      category_percentages: {},
      by_status: {},
      status_percentages: {},
      by_country: {},
      country_percentages: {},
      satisfaction: { counts: {}, scored_incidents: 0, closed_incidents: 0, average: 0 },
    };
    expect(hasAnalysisResult(result)).toBe(true);
  });

  it("returns true for empty analysis result", () => {
    const result = {
      source_file: "empty.csv",
      total_records: 0,
      valid_records: 0,
      invalid_records: 0,
      invalid_breakdown: {},
      by_category: {},
      category_percentages: {},
      by_status: {},
      status_percentages: {},
      by_country: {},
      country_percentages: {},
      satisfaction: { counts: {}, scored_incidents: 0, closed_incidents: 0, average: 0 },
    };
    expect(hasAnalysisResult(result)).toBe(true);
  });

  it("returns false for null", () => {
    expect(hasAnalysisResult(null)).toBe(false);
  });

  // undefined is !== null so hasAnalysisResult returns true for undefined
  it("returns true for undefined (since undefined !== null)", () => {
    expect(hasAnalysisResult(undefined as any)).toBe(true);
  });
});

// ─── Utility 3: buildTrackflowApiUrl ──────────────────────────────────────────

describe("buildTrackflowApiUrl", () => {
  const OLD_ENV = process.env;

  beforeEach(() => {
    process.env = { ...OLD_ENV };
    delete process.env.TRACKFLOW_API_BASE_URL;
  });

  afterEach(() => {
    process.env = OLD_ENV;
  });

  it("uses default base URL when env var is not set", () => {
    const url = buildTrackflowApiUrl("/auth/me");
    expect(url).toBe("http://localhost:8000/auth/me");
  });

  it("uses custom base URL from env var", () => {
    process.env.TRACKFLOW_API_BASE_URL = "https://api.trackflow.test";
    const url = buildTrackflowApiUrl("/auth/me");
    expect(url).toBe("https://api.trackflow.test/auth/me");
  });

  it("adds leading slash to path if missing", () => {
    const url = buildTrackflowApiUrl("auth/me");
    expect(url).toBe("http://localhost:8000/auth/me");
  });

  it("removes trailing slash from base URL", () => {
    process.env.TRACKFLOW_API_BASE_URL = "https://api.trackflow.test/";
    const url = buildTrackflowApiUrl("/auth/me");
    expect(url).toBe("https://api.trackflow.test/auth/me");
  });

  it("builds URL with query params", () => {
    const url = buildTrackflowApiUrl("/suppliers?country=USA");
    expect(url).toBe("http://localhost:8000/suppliers?country=USA");
  });
});

// ─── Utility 4: createAuthorizedHeaders ──────────────────────────────────────

describe("createAuthorizedHeaders", () => {
  it("creates headers with Bearer token", () => {
    const headers = createAuthorizedHeaders("my-token");
    expect(headers.get("Authorization")).toBe("Bearer my-token");
  });

  it("preserves existing headers from init", () => {
    const init = new Headers({ "X-Custom": "value" });
    const headers = createAuthorizedHeaders("token-123", init);
    expect(headers.get("Authorization")).toBe("Bearer token-123");
    expect(headers.get("X-Custom")).toBe("value");
  });

  it("overrides Authorization header if present in init", () => {
    const init = new Headers({ Authorization: "Bearer old-token" });
    const headers = createAuthorizedHeaders("new-token", init);
    expect(headers.get("Authorization")).toBe("Bearer new-token");
  });

  it("returns a Headers instance", () => {
    const headers = createAuthorizedHeaders("test");
    expect(headers).toBeInstanceOf(Headers);
  });
});

// ─── Utility 5: applySessionCookie / clearSessionCookie ──────────────────────

describe("applySessionCookie", () => {
  it("sets the session cookie on the response", () => {
    const response = NextResponse.json({});
    const result = applySessionCookie(response, "test-token");
    const cookies = result.cookies.getAll();
    const authCookie = cookies.find((c) => c.name === "trackflow_backoffice_token");
    expect(authCookie).toBeDefined();
    expect(authCookie!.value).toBe("test-token");
  });
});

describe("clearSessionCookie", () => {
  it("clears the session cookie with maxAge 0", () => {
    const response = NextResponse.json({});
    const result = clearSessionCookie(response);
    const cookies = result.cookies.getAll();
    const authCookie = cookies.find((c) => c.name === "trackflow_backoffice_token");
    expect(authCookie).toBeDefined();
    expect(authCookie!.value).toBe("");
    expect(authCookie!.maxAge).toBe(0);
  });
});