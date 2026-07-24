import { IncidentList } from "@/app/features/incidents/components/IncidentList";
import { IncidentRegistrationForm } from "@/app/features/incidents/components/IncidentRegistrationForm";
import { IncidentSummaryPanel } from "@/app/features/incidents/components/IncidentSummaryPanel";
import { IncidentUploadPanel } from "@/app/features/incidents/components/IncidentUploadPanel";

export default function IncidentsPage() {
  return (
    <main className="flex flex-1 flex-col gap-8 px-6 py-10 lg:px-10">
      <IncidentUploadPanel />
      <IncidentRegistrationForm />
      <IncidentList />
      <IncidentSummaryPanel />
    </main>
  );
}