import { CandidateDetailScreen } from "@/app/features/candidates/components/CandidateDetailScreen";
import { notFound } from "next/navigation";

interface CandidateDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function CandidateDetailPage({ params }: CandidateDetailPageProps) {
  const { id } = await params;

  if (!id) {
    notFound();
  }

  return <CandidateDetailScreen id={id} />;
}
