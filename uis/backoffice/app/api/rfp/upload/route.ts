import {
  buildTrackflowApiUrl,
  getAuthorizedSessionHeaders,
} from "@/app/features/auth/server/session";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  const upstreamUrl = buildTrackflowApiUrl("/api/rfp/upload");

  try {
    const formData = await request.formData();
    const uploadedFile = formData.get("file");

    if (!(uploadedFile instanceof File)) {
      return Response.json(
        { detail: "Debe adjuntarse un archivo PDF en el campo 'file'." },
        { status: 400 }
      );
    }

    if (!uploadedFile.name.toLowerCase().endsWith(".pdf")) {
      return Response.json(
        { detail: "Formato incorrecto: el archivo debe tener extensión .pdf" },
        { status: 415 }
      );
    }

    let authHeaders: Headers | null = null;
    try {
      authHeaders = await getAuthorizedSessionHeaders();
    } catch {
      authHeaders = null;
    }

    const externalFormData = new FormData();
    externalFormData.append("file", uploadedFile, uploadedFile.name);

    const upstreamResponse = await fetch(upstreamUrl, {
      method: "POST",
      headers: authHeaders ?? undefined,
      body: externalFormData,
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      const errText = await upstreamResponse.text();
      return new Response(errText, {
        status: upstreamResponse.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    const data = await upstreamResponse.json();
    return Response.json(data, { status: upstreamResponse.status });
  } catch (error) {
    return Response.json(
      {
        detail: `Error al subir la RFP al backend: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 502 }
    );
  }
}
