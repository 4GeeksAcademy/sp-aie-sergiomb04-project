import type {
  Incident,
  IncidentCreateInput,
  IncidentStatusUpdateInput,
  IncidentSummary,
} from "@/app/features/incidents/types/incident-domain";

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as {
      field?: string;
      message?: string;
      detail?: string | Record<string, unknown>;
    };
    if (payload.field && payload.message) {
      return payload.message;
    }
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (payload.detail && typeof payload.detail === "object") {
      const d = payload.detail as Record<string, unknown>;
      if (typeof d.message === "string") {
        return d.message;
      }
    }
    if (payload.message) {
      return payload.message;
    }
  } catch {
    // ignore parse errors
  }
  return `Error HTTP ${response.status}`;
}

export async function createIncident(
  input: IncidentCreateInput,
): Promise<Incident> {
  const response = await fetch("/api/incidents", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return response.json() as Promise<Incident>;
}

export async function listIncidents(
  filters?: {
    status?: string;
    origin?: string;
    branch?: string;
    category?: string;
  },
): Promise<Incident[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.origin) params.set("origin", filters.origin);
  if (filters?.branch) params.set("branch", filters.branch);
  if (filters?.category) params.set("category", filters.category);

  const queryString = params.toString();
  const url = `/api/incidents${queryString ? `?${queryString}` : ""}`;

  const response = await fetch(url, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return response.json() as Promise<Incident[]>;
}

export async function getIncident(id: string): Promise<Incident> {
  const response = await fetch(`/api/incidents/${id}`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return response.json() as Promise<Incident>;
}

export async function updateIncidentStatus(
  id: string,
  input: IncidentStatusUpdateInput,
): Promise<Incident> {
  const response = await fetch(`/api/incidents/${id}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return response.json() as Promise<Incident>;
}

export async function getIncidentSummary(): Promise<IncidentSummary> {
  const response = await fetch("/api/incidents/summary", {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return response.json() as Promise<IncidentSummary>;
}