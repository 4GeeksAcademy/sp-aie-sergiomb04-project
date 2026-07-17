import {
  Supplier,
  SupplierCategory,
  SupplierCreateInput,
  SupplierCountry,
  SupplierRateUpdateInput,
  SupplierStatusUpdateInput,
} from "@/app/features/suppliers/types/suppliers";

type ApiErrorPayload = {
  error?: string;
  detail?: string | Array<{ loc?: Array<string | number>; msg?: string }>;
};

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as ApiErrorPayload;

    if (payload.error) {
      return payload.error;
    }

    if (typeof payload.detail === "string") {
      return payload.detail;
    }

    if (Array.isArray(payload.detail)) {
      return payload.detail
        .map((item) => {
          const path = item.loc?.join(".") ?? "body";
          return `${path}: ${item.msg ?? "Error de validacion"}`;
        })
        .join(" | ");
    }
  } catch {
    // No-op: use fallback message.
  }

  return `Error HTTP ${response.status}`;
}

function buildSuppliersUrl(filters?: {
  country?: SupplierCountry;
  category?: SupplierCategory;
}): string {
  const params = new URLSearchParams();

  if (filters?.country) {
    params.set("country", filters.country);
  }

  if (filters?.category) {
    params.set("category", filters.category);
  }

  const query = params.toString();
  return query ? `/api/suppliers?${query}` : "/api/suppliers";
}

export async function fetchSuppliers(filters?: {
  country?: SupplierCountry;
  category?: SupplierCategory;
}): Promise<Supplier[]> {
  const response = await fetch(buildSuppliersUrl(filters), {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as Supplier[];
}

export async function createSupplier(payload: SupplierCreateInput): Promise<Supplier> {
  const response = await fetch("/api/suppliers", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as Supplier;
}

export async function updateSupplierRate(
  supplierId: string,
  payload: SupplierRateUpdateInput
): Promise<Supplier> {
  const response = await fetch(`/api/suppliers/${supplierId}/rate`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as Supplier;
}

export async function updateSupplierStatus(
  supplierId: string,
  payload: SupplierStatusUpdateInput
): Promise<Supplier> {
  const response = await fetch(`/api/suppliers/${supplierId}/status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as Supplier;
}

export async function deleteSupplier(supplierId: string): Promise<void> {
  const response = await fetch(`/api/suppliers/${supplierId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }
}
