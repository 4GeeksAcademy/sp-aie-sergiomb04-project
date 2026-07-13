import {
  AnalyzeIncidentsApiResponse,
  IncidentAnalysisResult,
} from "@/app/features/incidents/types/incidents";

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { error?: string };
    if (payload.error) {
      return payload.error;
    }
  } catch {
    // Fallback below if response body is not JSON.
  }
  return `Error HTTP ${response.status}`;
}

export async function analyzeIncidentsFile(
  file: File
): Promise<AnalyzeIncidentsApiResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/incidents/analyze", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as AnalyzeIncidentsApiResponse;
}

export async function getLatestExportCsv(): Promise<Blob> {
  const response = await fetch("/api/incidents/results/export", {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return response.blob();
}

export function downloadCsvBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function hasAnalysisResult(
  result: IncidentAnalysisResult | null
): result is IncidentAnalysisResult {
  return result !== null;
}
