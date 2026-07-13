export type IncidentInvalidRule =
  | "invalid_tracking"
  | "invalid_carrier"
  | "invalid_category"
  | "invalid_email"
  | "closed_missing_score"
  | "score_out_of_range"
  | "invalid_country"
  | "invalid_description";

export type IncidentCategory =
  | "LOST_PARCEL"
  | "DELAYED_DELIVERY"
  | "WRONG_ADDRESS"
  | "RETURN_REQUEST"
  | "DAMAGE";

export type IncidentStatus = "OPEN" | "CLOSED" | "DISCARDED";

export type IncidentCountry = "US" | "ES";

export type IncidentCustomerType = "B2B" | "B2C";

export type IncidentAnalysisResult = {
  source_file: string;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  invalid_breakdown: Partial<Record<IncidentInvalidRule, number>>;
  by_category: Record<string, number>;
  category_percentages: Record<string, number>;
  by_status: Record<string, number>;
  status_percentages: Record<string, number>;
  by_country: Record<string, number>;
  country_percentages: Record<string, number>;
  satisfaction: {
    counts: Record<string, number>;
    scored_incidents: number;
    closed_incidents: number;
    average: number;
  };
};

export type AnalyzeIncidentsApiResponse = {
  data: IncidentAnalysisResult;
  meta: {
    source_file: string;
    generated_at: string;
  };
};
