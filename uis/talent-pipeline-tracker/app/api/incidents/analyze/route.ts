import { randomUUID } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";

import { runIncidentsAnalysis } from "@/app/features/incidents/server/analysis-runner";
import { setLatestAnalysis } from "@/app/features/incidents/server/analysis-store";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  const formData = await request.formData();
  const uploadedFile = formData.get("file");

  if (!(uploadedFile instanceof File)) {
    return Response.json(
      { error: "Debe enviarse un archivo en el campo 'file'" },
      { status: 400 }
    );
  }

  if (!uploadedFile.name.toLowerCase().endsWith(".csv")) {
    return Response.json(
      { error: "El archivo debe tener extension .csv" },
      { status: 400 }
    );
  }

  const buffer = Buffer.from(await uploadedFile.arrayBuffer());
  const tmpId = randomUUID();
  const inputPath = path.join(os.tmpdir(), `incidents-input-${tmpId}.csv`);
  const exportPath = path.join(os.tmpdir(), `incidents-export-${tmpId}.csv`);

  try {
    await fs.writeFile(inputPath, buffer);

    const { result, exportCsv } = await runIncidentsAnalysis(inputPath, exportPath);
    const generatedAt = new Date().toISOString();

    setLatestAnalysis({
      generatedAt,
      sourceFile: uploadedFile.name,
      exportFileName: `incidents-results-${Date.now()}.csv`,
      exportCsv,
      result,
    });

    return Response.json({
      data: result,
      meta: {
        source_file: uploadedFile.name,
        generated_at: generatedAt,
      },
    });
  } catch (unknownError: unknown) {
    return Response.json(
      {
        error:
          unknownError instanceof Error
            ? unknownError.message
            : "No se pudo analizar el archivo CSV",
      },
      { status: 500 }
    );
  } finally {
    await Promise.allSettled([fs.unlink(inputPath), fs.unlink(exportPath)]);
  }
}
