export const CENTRO = [-17.3895, -66.1568];
export const BBOX_CBB = [[-17.6, -66.5], [-17.1, -65.8]];
export const BBOX_CERCADO = [[-17.53119, -66.280703], [-17.257306, -66.06952]];
export const DISTRITOS = Array.from({ length: 15 }, (_, i) => ({ id: i + 1, nombre: `Distrito ${i + 1}` }));
export const SENSORES = { MODIS: '#bd9cff', VIIRS: '#f7ac65' };
export const NIVELES = { critica: '#ff7376', alta: '#ffad65', media: '#e8d477', baja: '#a3ce8d' };
export const ETIQUETAS = { critica: 'Crítica', alta: 'Alta', media: 'Media', baja: 'Baja' };
export const ESTADOS = { nueva: 'Nueva', en_revision: 'En revisión', atendida: 'Atendida', falsa_alarma: 'Falsa alarma' };
export const CAPAS = { detecciones: 'Detecciones satelitales', alertas: 'Alertas', heatmap: 'Mapa de calor', gamcDistritos: 'Cercado y distritos · GAMC', periurbanos: 'Periurbanos · GAMC', distritos: 'Esquema distrital ilustrativo', tunari: 'Esquema PNT ilustrativo', cota2750: 'Cota 2750 · GAMC en línea' };
