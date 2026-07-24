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

export const INCIDENT_STATUSES = ["open", "in_progress", "resolved", "discarded"] as const;
export const INCIDENT_ORIGINS = ["customer", "branch", "internal"] as const;
export const INCIDENT_BRANCHES = ["los_angeles", "zaragoza"] as const;

export type IncidentCategory = (typeof INCIDENT_CATEGORIES)[number];
export type IncidentStatus = (typeof INCIDENT_STATUSES)[number];
export type IncidentOrigin = (typeof INCIDENT_ORIGINS)[number];
export type IncidentBranch = (typeof INCIDENT_BRANCHES)[number];

export type Incident = {
  id: string;
  title: string;
  description: string;
  category: IncidentCategory;
  status: IncidentStatus;
  origin: IncidentOrigin;
  branch: IncidentBranch;
  created_at: string;
  updated_at: string;
};

export type IncidentCreateInput = {
  title: string;
  description: string;
  category: IncidentCategory;
  status?: IncidentStatus;
  origin: IncidentOrigin;
  branch: IncidentBranch;
};

export type IncidentStatusUpdateInput = {
  status: IncidentStatus;
};

export type IncidentSummary = {
  total: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_origin: Record<string, number>;
  by_branch: Record<string, number>;
};

export const STATUS_TRANSITIONS: Record<IncidentStatus, IncidentStatus[]> = {
  open: ["in_progress", "discarded"],
  in_progress: ["resolved", "discarded"],
  resolved: [],
  discarded: [],
};

export const CATEGORY_LABELS: Record<IncidentCategory, string> = {
  carrier_last_mile: "Última milla",
  carrier_international: "Transportista internacional",
  warehouse_operations: "Operaciones de almacén",
  reverse_logistics: "Logística inversa",
  customer_experience: "Experiencia del cliente",
  commercial: "Comercial",
  technology: "Tecnología",
  executive: "Dirección",
};

export const STATUS_LABELS: Record<IncidentStatus, string> = {
  open: "Abierta",
  in_progress: "En progreso",
  resolved: "Resuelta",
  discarded: "Descartada",
};

export const ORIGIN_LABELS: Record<IncidentOrigin, string> = {
  customer: "Cliente",
  branch: "Sede",
  internal: "Interno",
};

export const BRANCH_LABELS: Record<IncidentBranch, string> = {
  los_angeles: "Los Ángeles",
  zaragoza: "Zaragoza",
};

export function getNextStatuses(current: IncidentStatus): IncidentStatus[] {
  return STATUS_TRANSITIONS[current] ?? [];
}