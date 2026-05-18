import { CandidateDetail } from "@/app/components/candidates/CandidateDetail";
import { getCandidateById } from "@/services/api";
import { notFound } from "next/navigation";

interface CandidateDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function CandidateDetailPage({ params }: CandidateDetailPageProps) {
  const { id } = await params;

  if (!id) {
    notFound();
  }

  const candidate = await getCandidateById(id);
  return <CandidateDetail candidate={candidate} />;
}
