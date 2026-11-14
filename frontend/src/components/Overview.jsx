import { useFiltros } from '../context/FiltrosContext';
import { numero } from '../utils/formatters';
import Icon from './Icon';

export default function Overview() {
  const { data } = useFiltros();
  const stats = data?.estadisticas;
  return <section className="overview" aria-label="Resumen del observatorio">
    <div className="intro">
      <span className="intro-kicker"><Icon name="tree" size={17} />Nuestro Tunari</span>
      <h1>Un <span className="pill-visual pill-map" aria-hidden="true"><Icon name="map" size={26} /></span>territorio.<br /><span>Muchas <span className="pill-visual pill-radar" aria-hidden="true"><Icon name="radar" size={26} /></span>señales.</span></h1>
      <p>Parque Nacional Tunari y los 15 distritos de Cochabamba, observados con datos satelitales reales.</p>
      <div className="hero-actions"><a className="cta cta-primary" href="#territorio"><Icon name="map" size={18} />Explorar el mapa</a><a className="cta cta-secondary" href="#historico"><Icon name="chart" size={18} />Ver históricos</a></div>
    </div>
    <div className="hero-art" aria-hidden="true"><div className="orbit orbit-a" /><div className="orbit orbit-b" /><div className="orb"><img src={`${import.meta.env.BASE_URL}icono.png`} alt="" width="512" height="512" /></div></div>
    <div className="kpis">
      <div><span className="kpi-icon warm" aria-hidden="true"><Icon name="radar" size={24} /></span><strong>{stats?.detecciones_hoy == null ? '—' : numero(stats.detecciones_hoy)}</strong><span>Detecciones hoy</span><small className="kpi-status">{stats?.detecciones_hoy == null ? 'Sin dato disponible' : stats?.disponibilidad?.detecciones_hoy === 'parcial' ? 'Conteo parcial' : 'Observaciones disponibles'}</small><small className="kpi-detail">Focos de calor detectados por satélite en el día, según NASA FIRMS (MODIS y VIIRS). Un conteo en cero no confirma ausencia de fuego.</small></div>
      <div><span className="kpi-icon red" aria-hidden="true"><Icon name="alert" size={24} /></span><strong>{stats?.alertas_activas == null ? '—' : numero(stats.alertas_activas)}</strong><span>Alertas activas</span><small className="kpi-status" title={data?.motor_alertas?.motivo}>{stats?.alertas_activas == null ? 'Evaluación no disponible' : 'Evaluación vigente'}</small><small className="kpi-detail">Las alertas se evalúan sobre unidades verificadas del territorio. Mientras los límites oficiales no estén verificados, la evaluación permanece deshabilitada.</small></div>
      <div><span className="kpi-icon green" aria-hidden="true"><Icon name="history" size={24} /></span><strong>{stats?.eventos_historicos == null ? '—' : numero(stats.eventos_historicos)}</strong><span>Eventos históricos</span><small className="kpi-detail">Eventos satelitales agrupados (1,5 km y 24 h) desde el archivo histórico. No equivalen a incendios confirmados.</small></div>
    </div>
  </section>;
}
