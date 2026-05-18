export type CandidateStatus = "received" | "in_progress" | "selected" | "discarded";

export type CandidateStage =
  | "pending"
  | "review"
  | "personal_interview"
  | "technical_interview"
  | "offer_presented";

export type Candidate = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  status: CandidateStatus;
  stage: CandidateStage;
};

export type CandidateDetail = Candidate & {
  linkedin_url: string;
  cv_url: string;
  experience_years: number;
  notes_count: number;
  applied_at: string;
  updated_at: string;
};

export type CandidateListResponse = {
  data?: Candidate[];
  meta?: {
    total?: number;
    page?: number;
    limit?: number;
  };
};

export type CandidatePayload = {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string;
  cv_url: string;
  status: CandidateStatus;
  stage: CandidateStage;
  experience_years: number;
};

export type CandidateFilters = {
  status?: string;
  stage?: string;
  search?: string;
  page?: number;
  limit?: number;
};

export type CandidateNote = {
  id: string;
  record_id: string;
  content: string;
  created_at: string;
};

export type CandidateNotesResponse = {
  data?: CandidateNote[];
  meta?: {
    total?: number;
  };
};
