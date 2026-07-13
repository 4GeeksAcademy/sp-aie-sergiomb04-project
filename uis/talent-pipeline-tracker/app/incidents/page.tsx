import React from "react";

import { IncidentUploadForm } from "@/app/features/incidents/components/IncidentUploadForm";

export default function IncidentsPage() {
  return (
    <main className="min-h-screen bg-zinc-100 px-4">
      <IncidentUploadForm />
    </main>
  );
}
