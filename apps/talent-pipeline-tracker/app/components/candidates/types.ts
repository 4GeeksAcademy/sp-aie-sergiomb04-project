export type Candidate = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  status: string;
  stage: string;
};

export type CandidateListResponse = {
  data?: Candidate[];
};
