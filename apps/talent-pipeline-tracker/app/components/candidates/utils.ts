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

export function prettifyFilterValue(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
