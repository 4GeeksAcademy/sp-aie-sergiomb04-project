export const STATUS_OPTIONS = ["received", "in_progress", "selected", "discarded"] as const;

export const STAGE_OPTIONS = [
  "pending",
  "review",
  "personal_interview",
  "technical_interview",
  "offer_presented",
] as const;

export type FiltersState = {
  status: string;
  stage: string;
  search: string;
  page: number;
  limit: number;
};

export const DEFAULT_FILTERS: FiltersState = {
  status: "",
  stage: "",
  search: "",
  page: 1,
  limit: 20,
};

const FILTER_VALUE_LABELS: Record<string, string> = {
  received: "Recibida",
  in_progress: "En proceso",
  selected: "Seleccionada",
  discarded: "Descartada",
  pending: "Pendiente de revisión",
  review: "En revisión",
  personal_interview: "Entrevista personal",
  technical_interview: "Entrevista técnica",
  offer_presented: "Oferta presentada",
};

export function prettifyFilterValue(value: string): string {
  return FILTER_VALUE_LABELS[value] ?? value;
}
