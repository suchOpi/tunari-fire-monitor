import { useFiltros } from '../context/FiltrosContext';
import { numero } from '../utils/formatters';
import Icon from './Icon';

export default function Overview() {
  const { data } = useFiltros();
  const stats = data?.estadisticas;
  return <section className="overview" aria-label="Resumen del observatorio">
    <div className="intro">
      <span className="intro-kicker"><Icon name="tree" size={17} />Nuestro Tunari</span>
      <h1>Un territorio.<br /><span>Muchas señales.</span></h1>
      <p>Parque Nacional Tunari y los 15 distritos de Cochabamba.</p>
    </div>
    <div className="kpis">
      <div><span className="kpi-icon warm" aria-hidden="true"><Icon name="radar" size={24} /></span><strong>{stats?.detecciones_hoy == null ? '—' : numero(stats.detecciones_hoy)}</strong><span>Detecciones hoy</span><small className="kpi-status">{stats?.detecciones_hoy == null ? 'Sin dato disponible' : stats?.disponibilidad?.detecciones_hoy === 'parcial' ? 'Conteo parcial' : 'Observaciones disponibles'}</small></div>
      <div><span className="kpi-icon red" aria-hidden="true"><Icon name="alert" size={24} /></span><strong>{stats?.alertas_activas == null ? '—' : numero(stats.alertas_activas)}</strong><span>Alertas activas</span><small className="kpi-status" title={data?.motor_alertas?.motivo}>{stats?.alertas_activas == null ? 'Evaluación no disponible' : 'Evaluación vigente'}</small></div>
      <div><span className="kpi-icon green" aria-hidden="true"><Icon name="history" size={24} /></span><strong>{stats?.eventos_historicos == null ? '—' : numero(stats.eventos_historicos)}</strong><span>Eventos históricos</span></div>
    </div>
  </section>;
}
