import { randomUUID } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";

import { runIncidentsAnalysis } from "@/app/features/incidents/server/analysis-runner";
import { setLatestAnalysis } from "@/app/features/incidents/server/analysis-store";

export const runtime = "nodejs";

function badRequest(message: string): Response {
  return Response.json({ error: message }, { status: 400 });
}

export async function POST(request: Request): Promise<Response> {
  const formData = await request.formData();
  const uploadedFile = formData.get("file");

  if (!(uploadedFile instanceof File)) {
    return badRequest("Debe enviarse un archivo CSV en el campo file");
  }

  if (!uploadedFile.name.toLowerCase().endsWith(".csv")) {
    return Response.json(
      { error: "Formato incorrecto: el archivo debe tener extension .csv" },
      { status: 415 }
    );
  }

  if (uploadedFile.size === 0) {
    return badRequest("El fichero esta vacio");
  }

  const buffer = Buffer.from(await uploadedFile.arrayBuffer());
  const textPreview = buffer.toString("utf-8", 0, Math.min(buffer.length, 2048));
  if (!textPreview.includes(",")) {
    return Response.json(
      { error: "Formato incorrecto: no parece un CSV delimitado por comas" },
      { status: 415 }
    );
  }

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
    const message =
      unknownError instanceof Error
        ? unknownError.message
        : "No se pudo analizar el archivo CSV";

    return Response.json({ error: message }, { status: 422 });
  } finally {
    await Promise.allSettled([fs.unlink(inputPath), fs.unlink(exportPath)]);
  }
}
