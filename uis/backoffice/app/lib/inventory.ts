import type {
  InventoryOrdersResponse,
  InventoryProduct,
  InventoryStockEntryCreateInput,
  InventoryStockEntryResponse,
  InventoryStockExitCreateInput,
  InventoryStockExitResponse,
} from "@/app/features/inventory/types/inventory";

type ApiErrorPayload = {
  error?: string;
  message?: string;
  detail?:
    | string
    | {
        field?: string;
        message?: string;
      }
    | Array<{ field?: string; message?: string; loc?: Array<string | number>; msg?: string }>;
};

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as ApiErrorPayload;

    if (typeof payload.error === "string" && payload.error.trim() !== "") {
      return payload.error;
    }

    if (typeof payload.detail === "string") {
      return payload.detail;
    }

    if (payload.detail && typeof payload.detail === "object" && !Array.isArray(payload.detail)) {
      const detail = payload.detail;
      if (typeof detail.message === "string") {
        return detail.message;
      }
      if (typeof detail.field === "string" && typeof detail.message === "string") {
        return `${detail.field}: ${detail.message}`;
      }
    }

    if (Array.isArray(payload.detail)) {
      return payload.detail
        .map((item) => {
          if (item.field && item.message) {
            return `${item.field}: ${item.message}`;
          }
          if (item.loc && item.msg) {
            return `${item.loc.join(".")}: ${item.msg}`;
          }
          if (item.message) {
            return item.message;
          }
          return "Error de validacion";
        })
        .join(" | ");
    }

    if (typeof payload.message === "string") {
      return payload.message;
    }
  } catch {
    // Fallback below
  }

  return `Error HTTP ${response.status}`;
}

import { normalizeWarehouse, track } from "@/app/services/telemetry";

async function requestInventory<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method || "GET") as "GET" | "POST" | "PATCH" | "DELETE";
  const startTime = typeof performance !== "undefined" ? performance.now() : Date.now();

  try {
    const response = await fetch(path, {
      ...init,
      cache: "no-store",
    });

    const elapsed = typeof performance !== "undefined" ? performance.now() - startTime : Date.now() - startTime;
    const latencyMs = Math.max(1, Math.round(elapsed));

    // Track latency sample
    track("api_request_latency_sampled", {
      api_route: path,
      method,
      status_code: response.status,
      latency_ms: latencyMs,
      upstream_service: "inventory_service",
      request_source: "web_backoffice",
    });

    if (!response.ok) {
      const errorMessage = await parseErrorMessage(response);

      // Track failed request
      track("api_request_failed", {
        api_route: path,
        method,
        status_code: response.status,
        error_family: response.status >= 500 ? "server_error" : "client_error",
        error_message_sanitized: errorMessage.slice(0, 200),
        retryable: response.status >= 500 || response.status === 429,
        request_source: "web_backoffice",
      });

      throw new Error(errorMessage);
    }

    return (await response.json()) as T;
  } catch (err) {
    if (err instanceof Error && !err.message.startsWith("Error HTTP")) {
      track("api_request_failed", {
        api_route: path,
        method,
        status_code: 500,
        error_family: "network_error",
        error_message_sanitized: err.message.slice(0, 200),
        retryable: true,
        request_source: "web_backoffice",
      });
    }
    throw err;
  }
}

export async function listInventoryProducts(): Promise<InventoryProduct[]> {
  const products = await requestInventory<InventoryProduct[]>("/api/inventory/products");

  // Check and report stock thresholds
  const DEFAULT_MINIMUM_THRESHOLD = 10;
  for (const product of products) {
    if (product.current_stock < DEFAULT_MINIMUM_THRESHOLD) {
      track("stock_threshold_triggered", {
        warehouse: normalizeWarehouse(product.warehouse),
        client_id: product.client_name,
        product_id: product.sku,
        product_category: product.category,
        quantity: product.current_stock,
        minimum_threshold: DEFAULT_MINIMUM_THRESHOLD,
        deficit_units: Math.max(0, DEFAULT_MINIMUM_THRESHOLD - product.current_stock),
      });
    }
  }

  return products;
}

export async function getInventoryProduct(id: number): Promise<InventoryProduct> {
  return requestInventory<InventoryProduct>(`/api/inventory/products/${id}`);
}

export async function createStockEntry(
  input: InventoryStockEntryCreateInput
): Promise<InventoryStockEntryResponse> {
  return requestInventory<InventoryStockEntryResponse>("/api/inventory/orders/inbound", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
}

export async function createStockExit(
  input: InventoryStockExitCreateInput
): Promise<InventoryStockExitResponse> {
  return requestInventory<InventoryStockExitResponse>("/api/inventory/orders/outbound", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
}

export async function listInventoryOrders(): Promise<InventoryOrdersResponse> {
  return requestInventory<InventoryOrdersResponse>("/api/inventory/orders");
}
