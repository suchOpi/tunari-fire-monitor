import { useFiltros } from './context/FiltrosContext';
import Sidebar from './components/Sidebar';
import Mapa from './components/Mapa';
import PanelEstadisticas from './components/PanelEstadisticas';
import Overview from './components/Overview';
import SourceStatus from './components/SourceStatus';
import Icon from './components/Icon';
import ThemeToggle from './components/ThemeToggle';

export default function App() {
  const { data, loading, error, refrescar } = useFiltros();
  const monitoringLabels = {continuo: 'Monitoreo continuo', atrasado: 'Datos atrasados', sin_dato: 'Sin datos', manual: 'Actualización manual'};
  const status = error ? 'Sin conexión' : !data ? 'Conectando' : data.monitoreo ? monitoringLabels[data.monitoreo.estado] || 'Sin datos' : data.estado === 'ok' ? 'FIRMS NRT' : data.estado === 'parcial' ? 'Cobertura parcial' : data.modo === 'postgis' ? 'Sin ingesta NRT' : 'Fuente no disponible';
  return <div className="app">
    <header className="app-header"><a className="brand" href="/" aria-label="Tunari Fire Monitor, inicio"><img src="/icono.png" alt="" width="68" height="68" /><span>TUNARI<small>FIRE MONITOR</small></span></a>
      <nav className="section-nav" aria-label="Secciones del observatorio"><a href="#territorio"><Icon name="map" />Territorio</a><a href="#historico"><Icon name="chart" />Históricos</a><a href="#analisis"><Icon name="brain" />Análisis IA</a></nav>
      <div className="header-location"><span>CERCADO · COCHABAMBA, BOLIVIA</span><small>Centro de observación de incendios</small><small className="database-state">{error ? 'PostGIS · conexión no disponible' : data?.modo === 'postgis' ? 'PostGIS · conectado' : 'PostGIS · consultando'}</small></div>
      <div className="header-status"><span className="source-label">NASA FIRMS + GAMC <b>OBSERVACIONES REALES</b></span><span className={`status-pill ${error || data?.estado !== 'ok' ? 'demo' : ''}`}><i />{status}</span><ThemeToggle /></div>
    </header>
    {error && <div className="source-banner source-error" role="alert"><span>{error}{data ? ' Se conserva la última consulta, sin garantizar su vigencia.' : ''}</span></div>}
    <main className="dashboard"><Overview />
      <div className="workspace-heading"><div><span className="section-symbol"><Icon name="map" size={24} /></span><h2>Exploración territorial</h2></div>
        <div className="workspace-actions"><span className="workspace-context">CERCADO / TUNARI</span><button className="refresh-button" onClick={refrescar} disabled={loading} aria-busy={loading} title={data?.modo === 'postgis' ? 'Consultar los registros guardados' : 'Consultar el estado; las descargas se actualizan cada 3 horas'}><span className="refresh-button-icon"><Icon name="refresh" size={17} /></span><span>{loading ? 'Consultando…' : 'Actualizar'}</span></button></div>
      </div>
      <div className="workspace"><Sidebar /><div className="territory"><Mapa /><SourceStatus /></div></div>
      <PanelEstadisticas />
    </main>
    <footer className="app-footer"><span>TUNARI / OBSERVATORIO LOCAL</span><span><Icon name="clock" size={14} />NRT: sujeto al horario de sobrevuelo y publicación</span><a href="https://firms.modaps.eosdis.nasa.gov/active_fire/" target="_blank" rel="noreferrer">Focos: NASA FIRMS <Icon name="external" size={14} /></a><a href="https://recursosgamc.cochabamba.bo/api-doc" target="_blank" rel="noreferrer">Cartografía: GAMC <Icon name="external" size={14} /></a></footer>
  </div>;
}
