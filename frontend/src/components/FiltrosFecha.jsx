import { useFiltros } from '../context/FiltrosContext';
import Icon from './Icon';

export default function FiltrosFecha() {
  const { filtros, setFiltros } = useFiltros();
  const set = (key, value) => setFiltros((f) => ({ ...f, [key]: value }));
  return <section className="filters" aria-labelledby="filters-title">
    <div className="section-head"><h2 id="filters-title"><Icon name="filter" />Área de observación</h2><span className="eyebrow">FILTROS</span></div>
    <div className="filter-period">
      <label>Período<select value={filtros.dias} onChange={(e) => setFiltros((f) => ({ ...f, dias: Number(e.target.value), desde: '', hasta: '' }))}>
        <option value="1">Hoy</option><option value="3">Últimos 3 días</option><option value="7">Últimos 7 días</option><option value="30">Últimos 30 días</option>
      </select></label>
    </div>
    <details className="date-range"><summary><Icon name="calendar" size={15} />Elegir fechas</summary><div className="filter-grid">
      <label>Desde<input type="date" value={filtros.desde} max={filtros.hasta || undefined} onChange={(e) => set('desde', e.target.value)} /></label>
      <label>Hasta<input type="date" value={filtros.hasta} min={filtros.desde || undefined} onChange={(e) => set('hasta', e.target.value)} /></label>
    </div><small>Fechas inclusivas, hora de Bolivia. Un día comienza a medianoche.</small></details>
  </section>;
}
