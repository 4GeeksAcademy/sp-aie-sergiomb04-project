import React from "react";

interface CandidateDetailProps {
  candidate: {
    id: string;
    full_name: string;
    email: string;
    phone: string;
    position: string;
    linkedin_url: string;
    cv_url: string;
    status: string;
    stage: string;
    experience_years: number;
    notes_count: number;
    applied_at: string;
    updated_at: string;
  };
}

export const CandidateDetail: React.FC<CandidateDetailProps> = ({ candidate }) => {
  return (
    <div>
      <h1>{candidate.full_name}</h1>
      <p><strong>Email:</strong> {candidate.email}</p>
      <p><strong>Teléfono:</strong> {candidate.phone}</p>
      <p><strong>Puesto:</strong> {candidate.position}</p>
      <p><strong>LinkedIn:</strong> <a href={candidate.linkedin_url} target="_blank" rel="noopener noreferrer">Perfil</a></p>
      <p><strong>CV:</strong> <a href={candidate.cv_url} target="_blank" rel="noopener noreferrer">Descargar</a></p>
      <p><strong>Estado:</strong> {candidate.status}</p>
      <p><strong>Etapa:</strong> {candidate.stage}</p>
      <p><strong>Años de experiencia:</strong> {candidate.experience_years}</p>
      <p><strong>Notas:</strong> {candidate.notes_count}</p>
      <p><strong>Aplicó el:</strong> {new Date(candidate.applied_at).toLocaleString()}</p>
      <p><strong>Actualizado el:</strong> {new Date(candidate.updated_at).toLocaleString()}</p>
    </div>
  );
};
