/**
 * Shared types for Incidents domain.
 * Categories, statuses, origins, and branches based on CONTEXT.md.
 * Do not invent new values — use exactly these.
 */

// ─── Categories (based on TrackFlow departments/areas) ────────────────────────
export const INCIDENT_CATEGORIES = [
  "carrier_last_mile",
  "carrier_international",
  "warehouse_operations",
  "reverse_logistics",
  "customer_experience",
  "commercial",
  "technology",
  "executive",
] as const;

export type IncidentCategory = (typeof INCIDENT_CATEGORIES)[number];

// ─── Statuses ─────────────────────────────────────────────────────────────────
export const INCIDENT_STATUSES = ["open", "in_progress", "resolved", "discarded"] as const;
export type IncidentStatus = (typeof INCIDENT_STATUSES)[number];

// ─── Origins ──────────────────────────────────────────────────────────────────
export const INCIDENT_ORIGINS = ["customer", "branch", "internal"] as const;
export type IncidentOrigin = (typeof INCIDENT_ORIGINS)[number];

// ─── Branches / Locations (sedes) ─────────────────────────────────────────────
export const INCIDENT_BRANCHES = ["los_angeles", "zaragoza"] as const;
export type IncidentBranch = (typeof INCIDENT_BRANCHES)[number];

// ─── Valid state transitions ──────────────────────────────────────────────────
export const STATUS_TRANSITIONS: Record<IncidentStatus, IncidentStatus[]> = {
  open: ["in_progress", "discarded"],
  in_progress: ["resolved", "discarded"],
  resolved: [],
  discarded: [],
};

// ─── Validation helpers ───────────────────────────────────────────────────────
export interface ValidationError {
  field: string;
  message: string;
}

export function isValidStatus(value: string): value is IncidentStatus {
  return INCIDENT_STATUSES.includes(value as IncidentStatus);
}

export function isValidOrigin(value: string): value is IncidentOrigin {
  return INCIDENT_ORIGINS.includes(value as IncidentOrigin);
}

export function isValidCategory(value: string): value is IncidentCategory {
  return INCIDENT_CATEGORIES.includes(value as IncidentCategory);
}

export function isValidBranch(value: string): value is IncidentBranch {
  return INCIDENT_BRANCHES.includes(value as IncidentBranch);
}

export function canTransitionStatus(
  current: IncidentStatus,
  next: IncidentStatus,
): boolean {
  const allowed = STATUS_TRANSITIONS[current];
  if (!allowed) return false;
  return allowed.includes(next);
}

export function validateIncidentFields(data: Record<string, unknown>): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!data.title || typeof data.title !== "string" || data.title.trim().length === 0) {
    errors.push({ field: "title", message: "El título es obligatorio" });
  }

  if (
    !data.description ||
    typeof data.description !== "string" ||
    data.description.trim().length === 0
  ) {
    errors.push({ field: "description", message: "La descripción es obligatoria" });
  }

  if (!data.category || !isValidCategory(String(data.category))) {
    errors.push({ field: "category", message: "Categoría inválida" });
  }

  if (!data.status || !isValidStatus(String(data.status))) {
    errors.push({ field: "status", message: "Estado inválido" });
  }

  if (!data.origin || !isValidOrigin(String(data.origin))) {
    errors.push({ field: "origin", message: "Origen inválido" });
  }

  if (!data.branch || !isValidBranch(String(data.branch))) {
    errors.push({ field: "branch", message: "Sede inválida" });
  }

  return errors;
}