import { useFiltros } from '../context/FiltrosContext';
import Icon from './Icon';
import { fecha } from '../utils/formatters';

export default function SourceStatus() {
  const { data } = useFiltros();
  const stats = data?.estadisticas;
  return <section className="source-details" aria-label="Estado de fuentes reales">
    <div className="source-heading"><div><span className="eyebrow">TRAZABILIDAD</span><h2 className="heading-with-icon"><Icon name="database" />Estado de fuentes</h2></div>
      {data?.fuente_datos && <span className="source-badge">Fuente: {data.fuente_datos === 'gamc' ? 'GAMC' : 'NASA FIRMS'}</span>}
    </div>
    {data?.monitoreo && <div className="monitoring-status">
      <div><span><Icon name="clock" size={14} />Último lote programado</span><strong>{fecha(data.monitoreo.ultima_ejecucion_programada)}</strong></div>
      <div><span><Icon name="check" size={14} />Última ingesta completa</span><strong>{fecha(data.monitoreo.ultima_ingesta_completa)}</strong></div>
      <div><span><Icon name="alert" size={14} />Evaluador</span><strong>{data.motor_alertas?.disponible ? 'Habilitado' : 'Deshabilitado'}</strong><small>Última comprobación: {fecha(data.motor_alertas?.ultima_ejecucion)}</small><small>Última ejecución exitosa: {fecha(data.motor_alertas?.ultima_exitosa)}</small></div>
    </div>}
    <div className="source-grid">{Object.entries(stats?.fuentes || {}).map(([key, source]) => <div key={key}><span>{source.producto}</span><b className={source.estado === 'ok' ? 'green' : 'warm'}>{source.estado === 'ok' ? 'Disponible' : source.estado === 'atrasada' ? 'Atrasada' : source.estado === 'sin_ingesta' ? 'Pendiente' : 'Error'}</b></div>)}</div>
    <p className="source-latest">{stats?.ultima_deteccion_area ? `Última detección en el área: ${new Date(stats.ultima_deteccion_area).toLocaleString('es-BO', { timeZone: 'America/La_Paz' })}.` : 'No hay una última detección disponible para esta área.'}</p>
    <div className="source-notes">{data?.avisos?.map((notice) => <p key={notice} className="warm">{notice}</p>)}</div>
  </section>;
}
