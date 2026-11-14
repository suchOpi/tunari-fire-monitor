import { diaBolivia } from '../utils/formatters';

const now = Date.now();
const points = [
  [-17.326, -66.203, 13, 38.2, 0], [-17.332, -66.191, 13, 24.8, 1],
  [-17.342, -66.176, 13, 17.6, 2], [-17.349, -66.159, 2, 42.1, 3],
  [-17.357, -66.131, 1, 14.5, 6], [-17.371, -66.113, 3, 8.2, 8],
  [-17.392, -66.191, 4, 6.7, 20], [-17.405, -66.141, 10, 12.3, 25],
  [-17.428, -66.174, 9, 28.4, 32], [-17.449, -66.132, 14, 9.1, 48],
  [-17.465, -66.153, 15, 4.8, 55], [-17.338, -66.243, 13, 21.6, 68],
];
const detecciones = points.map(([latitude, longitude, distrito, frp, hours], index) => ({
  id: index + 1, latitude, longitude, distrito, frp, fecha: new Date(now - (hours + 0.2) * 3600000).toISOString(),
  sensor: index % 3 ? 'VIIRS' : 'MODIS', satelite: index % 3 ? 'N20' : 'Terra',
  confidence: index === 10 ? 'low' : index % 3 ? 'high' : '94',
  resolucion: index % 3 ? 375 : 1000, en_tunari: index < 3 || index === 11,
  candidata: index === 10, revision_manual: true, hex_id: `demo:${index}`,
}));
let alertas = [
  { id: 1, nivel: 'critica', senal: 'zona_critica', descripcion: 'Señal satelital simulada en la ladera del Tunari. Requiere verificación en terreno.', distrito: 13, latitude: -17.326, longitude: -66.203, fecha: detecciones[0].fecha },
  { id: 2, nivel: 'alta', senal: 'intensidad', descripcion: 'Ejemplo: FRP 2,4σ sobre la media histórica de la unidad-semana.', distrito: 2, latitude: -17.349, longitude: -66.159, fecha: detecciones[3].fecha },
  { id: 3, nivel: 'media', senal: 'persistencia', descripcion: 'Ejemplo de persistencia: detecciones en tres días consecutivos.', distrito: 9, latitude: -17.428, longitude: -66.174, fecha: detecciones[8].fecha },
].map((a) => ({ ...a, estado: 'nueva', revision_manual: true, notificacion: 'demo', unidad_id: `distrito:${a.distrito}`, evento_id: a.id }));

export function cambiarMock(id, state, confirm = false) {
  alertas = alertas.map((a) => a.id === id ? { ...a, estado: state, revision_manual: confirm ? false : a.revision_manual } : a);
}

export function getMock(filters) {
  const today = diaBolivia();
  const end = filters.hasta || today;
  const endDate = new Date(`${end}T12:00:00-04:00`);
  const start = filters.desde || diaBolivia(new Date(endDate.getTime() - (filters.dias - 1) * 86400000));
  const matches = (item) => (!filters.distrito || item.distrito === Number(filters.distrito)) && diaBolivia(item.fecha) >= start && diaBolivia(item.fecha) <= end;
  const detections = detecciones.filter(matches);
  const alerts = alertas.filter(matches);
  const serie = Array.from({ length: new Date().getFullYear() - 1999 }, (_, index) => ({
    anio: 2000 + index, eventos: Math.round((index < 12 ? 12 : 27) + index * 1.8 + Math.sin(index * 2) * 13),
    regimen: index < 12 ? 'MODIS' : 'MODIS+VIIRS', cobertura: 'simulada',
  }));
  return {
    detecciones: detections, eventos: detections.map((d) => ({ id: d.id, ...d, inicio: d.fecha, fin: d.fecha, frp_max: d.frp, sensores_presentes: [d.sensor] })),
    alertas: alerts,
    estadisticas: { detecciones_hoy: detecciones.filter((d) => diaBolivia(d.fecha) === today && (!filters.distrito || d.distrito === Number(filters.distrito))).length,
      alertas_activas: alerts.filter((a) => ['nueva', 'en_revision'].includes(a.estado)).length,
      eventos_historicos: null, serie: filters.distrito ? [] : serie, posible_oclusion: 0, climatologia_disponible: false,
      ultima_ingesta: null, fuentes: {}, geometrias_verificadas: 0 },
    truncado: false,
  };
}
