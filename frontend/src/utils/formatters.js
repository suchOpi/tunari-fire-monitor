export const numero = (value) => new Intl.NumberFormat('es-BO').format(value ?? 0);
export const fecha = (value) => value ? new Intl.DateTimeFormat('es-BO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'America/La_Paz', hour12: false }).format(new Date(value)) : 'Sin actualización';
export const diaBolivia = (value = new Date()) => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/La_Paz', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value));
export const distritoLabel = (value) => value ? `Distrito ${value}` : 'Sin distrito verificado';
export const frp = (value) => value == null ? 'No disponible' : `${value.toFixed(1)} MW`;
