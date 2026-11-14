const BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
  try {
    const response = await fetch(`${BASE}${path}`, { ...options, signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...options.headers } });
    if (!response.ok) throw new Error(`API ${response.status}`);
    return await response.json();
  } finally { clearTimeout(timeout); }
}

export async function cargarDatos(filters) {
  const query = new URLSearchParams(Object.entries(filters).filter(([, v]) => v !== '' && v != null)).toString();
  const data = await request(`/monitoreo?${query}`);
  if (data.demo !== false || !Array.isArray(data.detecciones) || !data.estadisticas?.fuentes) throw new Error('Contrato NRT inválido');
  return data;
}

export async function actualizarAlerta(id, state, demo, confirm = false) {
  if (demo) throw new Error('El modo simulado está deshabilitado');
  return request(`/alertas/${id}${confirm ? '/confirmar' : ''}`, {
    method: confirm ? 'POST' : 'PATCH', ...(confirm ? {} : { body: JSON.stringify({ estado: state }) }),
  });
}

export async function consultarTerritorio(lat, lon, capa) {
  return request(`/gamc/consulta?${new URLSearchParams({ lat, lon, capa })}`);
}

export async function cargarLimites(tipo) {
  const data = await request(`/geografia/${tipo}`);
  if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)) throw new Error('GeoJSON inválido');
  return data;
}

export function cargarDetalleDistrito(id) {
  return request(`/geografia/distrito/${encodeURIComponent(id)}`);
}

export function urlInforme(params, formato = 'json') {
  const query = new URLSearchParams(Object.entries({ ...params, formato }).filter(([,v]) => v !== '' && v != null));
  return `${BASE}/informes/historico?${query}`;
}

export function cargarInforme(params) {
  const query = new URLSearchParams(Object.entries(params).filter(([,v]) => v !== '' && v != null));
  return request(`/informes/historico?${query}`);
}
