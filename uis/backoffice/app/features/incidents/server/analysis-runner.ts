import { execFile } from "node:child_process";
import { promises as fs } from "node:fs";
import path from "node:path";
import { promisify } from "node:util";

import { IncidentAnalysisResult } from "@/app/features/incidents/types/incidents";

const execFileAsync = promisify(execFile);

export async function runIncidentsAnalysis(
  inputCsvPath: string,
  exportCsvPath: string
): Promise<{ result: IncidentAnalysisResult; exportCsv: string }> {
  const scriptPath = path.resolve(
    process.cwd(),
    "../../scripts/incidents-analysis/analyze.py"
  );

  const { stdout, stderr } = await execFileAsync("python3", [
    scriptPath,
    inputCsvPath,
    "--json",
    "--no-prompt",
    "--export-path",
    exportCsvPath,
  ]);

  if (stderr?.trim()) {
    throw new Error(stderr.trim());
  }

  let parsed: IncidentAnalysisResult;
  try {
    parsed = JSON.parse(stdout) as IncidentAnalysisResult;
  } catch {
    throw new Error("No se pudo parsear la salida JSON del analizador Python");
  }

  const exportCsv = await fs.readFile(exportCsvPath, "utf-8");
  return { result: parsed, exportCsv };
}
