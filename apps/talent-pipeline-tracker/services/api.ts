// services/api.ts
// Servicio para interactuar con la API REST usando la URL de entorno

const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL) {
  throw new Error('NEXT_PUBLIC_API_URL no está definida en .env.local');
}

export async function fetchCandidates() {
  const res = await fetch(`${API_URL}/records`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    cache: 'no-store', // Next.js recomienda para datos dinámicos
  });

  if (!res.ok) {
    throw new Error('Error al obtener candidatos');
  }

  return res.json();
}
