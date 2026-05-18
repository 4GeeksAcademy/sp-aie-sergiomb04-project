import { CandidateDetail } from "@/app/components/candidates/CandidateDetail";
import { getCandidateById, getCandidateNotes } from "@/services/api";
import { notFound } from "next/navigation";

interface CandidateDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function CandidateDetailPage({ params }: CandidateDetailPageProps) {
  const { id } = await params;

  if (!id) {
    notFound();
  }

  const [candidate, notesResponse] = await Promise.all([getCandidateById(id), getCandidateNotes(id)]);
  return <CandidateDetail candidate={candidate} initialNotes={notesResponse.data ?? []} />;
}
