// services/api.ts
// Servicio para interactuar con la API REST usando la URL de entorno

const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL) {
  throw new Error('NEXT_PUBLIC_API_URL no está definida en .env.local');
}

export async function getCandidateById(id: string) {
  const endpoint = `${API_URL}/records/${id}`;

  console.log('Fetching candidate detail from:', endpoint);

  const res = await fetch(endpoint, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorBody = await res.text();

    console.error('HTTP Error:', {
      status: res.status,
      statusText: res.statusText,
      body: errorBody,
    });

    throw new Error(
      `Error al obtener detalle de candidato: ${res.status} ${res.statusText}`
    );
  }

  return res.json();
}

export type CandidateFilters = {
  status?: string;
  stage?: string;
  search?: string;
  page?: number;
  limit?: number;
};

export async function fetchCandidates(filters: CandidateFilters = {}) {
  const params = new URLSearchParams();

  if (filters.status) params.set('status', filters.status);
  if (filters.stage) params.set('stage', filters.stage);
  if (filters.search) params.set('search', filters.search);
  if (filters.page && Number.isInteger(filters.page) && filters.page >= 1) {
    params.set('page', String(filters.page));
  }
  if (filters.limit && Number.isInteger(filters.limit) && filters.limit >= 1 && filters.limit <= 100) {
    params.set('limit', String(filters.limit));
  }

  const query = params.toString();
  const endpoint = query ? `${API_URL}/records?${query}` : `${API_URL}/records`;

  const res = await fetch(endpoint, {
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
