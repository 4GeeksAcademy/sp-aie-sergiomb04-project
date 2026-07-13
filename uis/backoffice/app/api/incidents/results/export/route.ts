import { getLatestAnalysis } from "@/app/features/incidents/server/analysis-store";

export const runtime = "nodejs";

export async function GET(): Promise<Response> {
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
