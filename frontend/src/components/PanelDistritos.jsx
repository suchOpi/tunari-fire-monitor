import { useEffect, useRef, useState } from 'react';
import { useFiltros } from '../context/FiltrosContext';
import { cargarDetalleDistrito } from '../api/client';
import { DISTRITOS } from '../utils/constantes';
import Icon from './Icon';

export default function PanelDistritos() {
  const { filtros, setFiltros, geografia, errorGeografia, mostrarDistritos, setMostrarDistritos, mostrarPNT, setMostrarPNT, capas, setCapas } = useFiltros();
  const [detalle, setDetalle] = useState(null), [error, setError] = useState('');
  const cache = useRef(new Map());
  const districts = geografia.distritos?.features.map((f) => f.properties) || DISTRITOS;
  const select = (id) => { setFiltros((f) => ({ ...f, distrito: id === '' ? '' : String(id) })); setMostrarDistritos(id !== ''); };
  useEffect(() => {
    let active = true;
    setDetalle(null); setError('');
    const id = filtros.distrito;
    if (id) {
      if (!cache.current.has(id)) cache.current.set(id, cargarDetalleDistrito(id));
      cache.current.get(id).then((value) => { if (active) setDetalle(value); })
        .catch(() => { cache.current.delete(id); if (active) setError('Detalle no disponible'); });
    }
    return () => { active = false; };
  }, [filtros.distrito]);
  const stats = detalle?.estadisticas;
  return <section className="districts-section" aria-labelledby="districts-title">
    <div className="section-head"><h2 id="districts-title"><Icon name="grid" />Distritos</h2><span className="count">{districts.length}</span></div>
    <div className="boundary-toggles">
      <label><input type="checkbox" checked={capas.gamcDistritos} onChange={(e) => setCapas(c => ({...c, gamcDistritos:e.target.checked}))} />Mostrar Cercado y distritos · GAMC</label>
      <label><input type="checkbox" checked={capas.periurbanos} onChange={(e) => setCapas(c => ({...c, periurbanos:e.target.checked}))} />Mostrar periurbanos · GAMC</label>
    </div>
    {geografia.territorio?.cartografia.disponible && <p className="district-note">Cartografía GAMC guardada · {new Date(geografia.territorio.cartografia.capturada).toLocaleDateString('es-BO')}</p>}
    <details className="boundary-illustrations"><summary><Icon name="layers" size={15} />Esquemas de referencia</summary><div className="boundary-toggles">
      <label><input type="checkbox" checked={mostrarDistritos} onChange={(e) => setMostrarDistritos(e.target.checked)} />Mostrar límites de distritos ilustrativos</label>
      <label><input type="checkbox" checked={mostrarPNT} onChange={(e) => setMostrarPNT(e.target.checked)} />Mostrar Parque Nacional Tunari ilustrativo</label>
    </div></details>
    {errorGeografia && <p className="district-note" role="status">Límites no disponibles</p>}
    {districts.some((d) => d.ilustrativa) && <p className="district-note">Las tarjetas usan esquemas ilustrativos. La cartografía visible de Cercado y periurbanos procede de GAMC.</p>}
    <button className="district-all" aria-pressed={!filtros.distrito} onClick={() => select('')}><Icon name="map" size={16} />Todos los distritos</button>
    <ul className="district-list" aria-label="Seleccionar distrito">{districts.map((d) => <li key={d.id}>
      <button className="district-card" aria-pressed={String(filtros.distrito) === String(d.id)} aria-label={`Seleccionar distrito ${d.id}`} onClick={() => select(d.id)} title={d.nombre}>
        <span className="district-card-title">{d.nombre.replace(' · posición ilustrativa', '')}{d.en_pnt && <span aria-label="Interseca el PNT" title="Interseca el PNT"><Icon name="tree" size={15} /></span>}</span>
        <span className={`district-alert-count ${d.alertas_activas > 0 ? 'has-alerts' : ''}`} aria-label={`${d.alertas_activas ?? 'Sin dato de'} alertas activas`}>{d.alertas_activas ?? '—'}</span>
        <small>{d.eventos_historicos ?? '—'} eventos históricos</small>
      </button>
    </li>)}</ul>
    {filtros.distrito && <article className="district-detail" aria-live="polite">
      <h3>Detalle del distrito {filtros.distrito}</h3>
      {!detalle ? <p>{error || 'Consultando detalle…'}</p> : <>
        <dl><div><dt>Área del polígono</dt><dd>{detalle.properties.area_km2.toFixed(1)} km²</dd></div>
          <div><dt>Población aproximada</dt><dd>{detalle.properties.poblacion_aproximada ?? 'Sin dato'}</dd></div>
          <div><dt>Alertas activas</dt><dd>{detalle.properties.alertas_activas ?? 'Sin dato'}</dd></div>
          <div><dt>FRP promedio</dt><dd>{stats.mediciones_frp ? `${stats.frp_promedio.toFixed(2)} MW` : 'Sin dato'}</dd></div>
          <div><dt>Sensores</dt><dd>{stats.sensores.join(', ') || 'Sin registros'}</dd></div></dl>
        {stats.eventos_por_anio.length ? <ul className="district-years">{stats.eventos_por_anio.map((y) => <li key={y.anio}>{y.anio}: {y.eventos} eventos</li>)}</ul> : <p>Sin eventos históricos registrados.</p>}
        {!detalle.properties.verificada && <p>El área corresponde al esquema local. Los registros sin distrito verificado no se asignan a este límite.</p>}
      </>}
    </article>}
  </section>;
}
