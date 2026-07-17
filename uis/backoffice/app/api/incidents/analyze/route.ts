import { setLatestAnalysis } from "@/app/features/incidents/server/analysis-store";
import { IncidentAnalysisResult } from "@/app/features/incidents/types/incidents";

export const runtime = "nodejs";
const INCIDENTS_API_BASE_URL = "http://localhost:8000";

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

  try {
    const externalFormData = new FormData();
    externalFormData.append("file", uploadedFile, uploadedFile.name);

    const upstreamResponse = await fetch(
      `${INCIDENTS_API_BASE_URL}/api/incidents/analyze`,
      {
        method: "POST",
        body: externalFormData,
        cache: "no-store",
      }
    );

    if (!upstreamResponse.ok) {
      const payload = (await upstreamResponse.json().catch(() => null)) as
        | { detail?: string; error?: string }
        | null;
      const message =
        payload?.detail ??
        payload?.error ??
        "No se pudo analizar el archivo CSV en el backend Python";

      return Response.json(
        { error: message },
        { status: upstreamResponse.status }
      );
    }

    const payload = (await upstreamResponse.json()) as {
      data: IncidentAnalysisResult;
      meta?: {
        source_file?: string;
        generated_at?: string;
      };
    };

    const exportResponse = await fetch(
      `${INCIDENTS_API_BASE_URL}/api/incidents/results/export`,
      {
        method: "GET",
        cache: "no-store",
      }
    );

    const exportCsv = exportResponse.ok ? await exportResponse.text() : "";

    setLatestAnalysis({
      generatedAt: payload.meta?.generated_at ?? new Date().toISOString(),
      sourceFile: payload.meta?.source_file ?? uploadedFile.name,
      exportFileName: `incidents-results-${Date.now()}.csv`,
      exportCsv,
      result: payload.data,
    });

    return Response.json(payload);
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend Python de incidencias" },
      { status: 502 }
    );
  }
}
