import {
  CandidateDetail,
  CandidateFilters,
  CandidateListResponse,
  CandidateNote,
  CandidateNotesResponse,
  CandidatePayload,
} from "@/app/features/candidates/types/candidate";
import { authRequest } from "@/app/features/auth/services/auth-api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return authRequest<T>(path, init);
}

export async function fetchCandidates(
  filters: CandidateFilters = {}
): Promise<CandidateListResponse> {
  const params = new URLSearchParams();

  if (filters.status) {
    params.set("status", filters.status);
  }

  if (filters.stage) {
    params.set("stage", filters.stage);
  }

  if (filters.search) {
    params.set("search", filters.search);
  }

  if (
    filters.page &&
    Number.isInteger(filters.page) &&
    filters.page >= 1
  ) {
    params.set("page", String(filters.page));
  }

  if (
    filters.limit &&
    Number.isInteger(filters.limit) &&
    filters.limit >= 1 &&
    filters.limit <= 100
  ) {
    params.set("limit", String(filters.limit));
  }

  const query = params.toString();

  return request<CandidateListResponse>(
    query ? `/records?${query}` : "/records"
  );
}

export async function getCandidateById(
  id: string
): Promise<CandidateDetail> {
  return request<CandidateDetail>(`/records/${id}`);
}

export async function createCandidate(
  payload: CandidatePayload
): Promise<CandidateDetail> {
  return request<CandidateDetail>("/records", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateCandidate(
  id: string,
  payload: CandidatePayload
): Promise<CandidateDetail> {
  return request<CandidateDetail>(`/records/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function patchCandidateStatusAndStage(
  id: string,
  payload: Pick<CandidatePayload, "status" | "stage">
): Promise<CandidateDetail> {
  return request<CandidateDetail>(`/records/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getCandidateNotes(
  id: string
): Promise<CandidateNotesResponse> {
  return request<CandidateNotesResponse>(`/records/${id}/notes`);
}

export async function addCandidateNote(
  id: string,
  content: string
): Promise<CandidateNote> {
  return request<CandidateNote>(`/records/${id}/notes`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function deleteCandidateNote(
  id: string,
  noteId: string
): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(
    `/records/${id}/notes/${noteId}`,
    {
      method: "DELETE",
    }
  );
}