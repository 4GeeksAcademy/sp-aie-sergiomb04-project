import { IncidentAnalysisResult } from "@/app/features/incidents/types/incidents";

export type StoredIncidentsAnalysis = {
  generatedAt: string;
  sourceFile: string;
  exportFileName: string;
  exportCsv: string;
  result: IncidentAnalysisResult;
};

let latestAnalysis: StoredIncidentsAnalysis | null = null;

export function setLatestAnalysis(analysis: StoredIncidentsAnalysis): void {
  latestAnalysis = analysis;
}

export function getLatestAnalysis(): StoredIncidentsAnalysis | null {
  return latestAnalysis;
}
