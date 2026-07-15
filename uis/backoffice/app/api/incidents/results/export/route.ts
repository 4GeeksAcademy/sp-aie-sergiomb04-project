import { getLatestAnalysis } from "@/app/features/incidents/server/analysis-store";

export const runtime = "nodejs";
const INCIDENTS_API_BASE_URL = process.env.INCIDENTS_API_BASE_URL;

export async function GET(): Promise<Response> {
  if (INCIDENTS_API_BASE_URL) {
    try {
      const upstreamResponse = await fetch(
        `${INCIDENTS_API_BASE_URL.replace(/\/$/, "")}/api/incidents/results/export`,
        {
          method: "GET",
          cache: "no-store",
        }
      );

      if (!upstreamResponse.ok) {
        const payload = (await upstreamResponse.json().catch(() => null)) as
          | { detail?: string; error?: string }
          | null;
        const message =
          payload?.detail ?? payload?.error ?? "No se pudo exportar el analisis";

        return Response.json(
          {
            error: message,
          },
          { status: upstreamResponse.status }
        );
      }

      const csv = await upstreamResponse.text();
      const contentDisposition =
        upstreamResponse.headers.get("content-disposition") ??
        'attachment; filename="incidents-analysis-results.csv"';

      return new Response(csv, {
        status: 200,
        headers: {
          "Content-Type": "text/csv; charset=utf-8",
          "Content-Disposition": contentDisposition,
          "Cache-Control": "no-store",
        },
      });
    } catch {
      return Response.json(
        { error: "No se pudo conectar con el backend Python de incidencias" },
        { status: 502 }
      );
    }
  }

  const latest = getLatestAnalysis();

  if (!latest) {
    return Response.json(
      {
        error:
          "No hay resultados para exportar. Ejecuta primero POST /api/incidents/analyze",
      },
      { status: 404 }
    );
  }

  return new Response(latest.exportCsv, {
    status: 200,
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename=\"${latest.exportFileName}\"`,
      "Cache-Control": "no-store",
    },
  });
}
