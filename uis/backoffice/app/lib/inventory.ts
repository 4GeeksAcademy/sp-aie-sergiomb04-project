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

async function requestInventory<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as T;
}

export async function listInventoryProducts(): Promise<InventoryProduct[]> {
  return requestInventory<InventoryProduct[]>("/api/inventory/products");
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
