import { useEffect, useRef, useState } from 'react';
import { useFiltros } from '../context/FiltrosContext';
import { cargarInforme, urlInforme } from '../api/client';
import Icon from './Icon';

const MONTHS = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
const SENSORS = {MODIS:'MODIS', VIIRS_NOAA20:'VIIRS NOAA-20', VIIRS_NOAA21:'VIIRS NOAA-21', VIIRS_SNPP:'VIIRS Suomi-NPP · retirado'};
const number = (v, digits=0) => v == null ? 'Sin dato' : v.toLocaleString('es-BO',{maximumFractionDigits:digits});
const fecha = value => value ? new Intl.DateTimeFormat('es-BO',{dateStyle:'medium',timeStyle:'short',timeZone:'America/La_Paz'}).format(new Date(value)) : 'Sin dato';

function Bars({ rows, title, unit, color='#00d5db' }) {
  const max = Math.max(1, ...rows.map(r => r.value || 0)), step = 560 / Math.max(1, rows.length);
  return <figure className="report-chart"><figcaption><span className="chart-title"><Icon name="chart" size={18} />{title}</span><small>{unit}</small></figcaption>
    <svg viewBox="0 0 610 185" role="img" aria-label={title}>
      {[0,.5,1].map(f => <g key={f}><line x1="36" x2="600" y1={145-f*120} y2={145-f*120} stroke="#35515a" strokeDasharray="3 4"/><text x="31" y={149-f*120} textAnchor="end">{number(max*f,1)}</text></g>)}
      {rows.map((r,i) => <g key={r.label}><rect x={40+i*step} y={145-(r.value || 0)/max*120} width={Math.max(3,step-9)} height={r.value == null ? 0 : Math.max(r.value ? 2 : 0,r.value/max*120)} rx="2" fill={color} opacity={r.partial ? .65 : 1}><title>{r.label}: {r.value == null ? 'sin dato' : number(r.value,2)}{r.partial ? ' · cobertura parcial' : ''}</title></rect><text x={40+i*step+(step-9)/2} y="165" textAnchor="middle">{r.label}{r.partial && r.value != null ? '*' : ''}</text>{r.value == null && <text x={40+i*step+(step-9)/2} y="135" textAnchor="middle">—</text>}{r.value === 0 && <text x={40+i*step+(step-9)/2} y="135" textAnchor="middle">0</text>}</g>)}
    </svg>
  </figure>;
}

function Calendar({ rows }) {
  const years = [...new Set(rows.map(r=>r.mes.slice(0,4)))], max=Math.max(1,...rows.map(r=>r.eventos || 0));
  return <figure className="report-calendar"><figcaption><span className="chart-title"><Icon name="calendar" size={18} />Cuándo se registraron eventos</span><small>— sin dato o mes futuro · borde punteado: cobertura parcial</small></figcaption>
    <div className="calendar-grid" style={{gridTemplateColumns:'42px repeat(12,minmax(0,1fr))'}}><span/>{MONTHS.map(m=><span key={m}>{m}</span>)}
      {years.map(y=><div className="calendar-year" key={y}><strong>{y}</strong>{rows.filter(r=>r.mes.startsWith(y)).map(r=><span key={r.mes} className={`calendar-cell ${r.cobertura === 'parcial' ? 'is-partial' : ''}`} title={`${r.mes}: ${r.eventos == null ? (r.cobertura === 'futuro' ? 'mes futuro' : 'sin dato') : `${r.eventos} eventos · ${r.dias_cubiertos} días completos · cobertura ${r.cobertura}`}`} style={{color:r.eventos/max >= .6 ? '#183f39' : 'var(--calendar-ink, #183f39)', background:r.eventos == null ? 'var(--calendar-missing, #edf0ed)' : `rgba(0,211,218,${.08+(r.eventos/max)*.65})`}}>{r.eventos ?? '—'}</span>)}</div>)}
    </div>
  </figure>;
}

export default function PanelEstadisticas() {
  const { filtros, data } = useFiltros();
  const lastYear = Number(new Intl.DateTimeFormat('en',{year:'numeric',timeZone:'America/La_Paz'}).format(new Date()));
  const [range,setRange] = useState({desde:lastYear-1,hasta:lastYear,ambito:'entorno',sensor:'MODIS'});
  const [report,setReport] = useState(null), [error,setError] = useState(''), [loading,setLoading] = useState(true);
  const [revision,setRevision] = useState(0);
  const cache = useRef(new Map());
  const params = {...range,distrito:filtros.distrito};
  const source = data?.estadisticas?.fuentes?.[`${range.sensor}_NRT`];
  const sourceRevision = range.hasta === lastYear ? `${source?.consultado_en || ''}|${source?.estado || ''}` : '';
  useEffect(() => {
    let active = true;
    setReport(null); setError('');
    if (range.desde > range.hasta) { setError('El año inicial debe ser anterior o igual al final.'); setLoading(false); return; }
    setLoading(true);
    const key = JSON.stringify({...range,distrito:filtros.distrito,sourceRevision});
    let item = cache.current.get(key);
    if (!item || Date.now()-item.time>300000) {
      if (cache.current.size >= 16) cache.current.clear();
      item = {time:Date.now(),promise:cargarInforme({...range,distrito:filtros.distrito})}; cache.current.set(key,item);
    }
    item.promise.then(value=>{if(active)setReport(value);}).catch(()=>{cache.current.delete(key);if(active)setError('No se pudieron consultar los registros del período.');}).finally(()=>{if(active)setLoading(false);});
    return ()=>{active=false;};
  }, [range.desde,range.hasta,range.ambito,range.sensor,filtros.distrito,revision,sourceRevision]);
  const years = Array.from({length:lastYear-1999},(_,i)=>lastYear-i);
  const ia = report?.ia;
  return <section className="history-reports" id="historico" aria-labelledby="history-title">
    <div className="reports-heading"><div><span className="eyebrow"><Icon name="history" size={18} />HISTÓRICO Y SEGUIMIENTO · NASA FIRMS</span><h2 id="history-title">Frecuencia, fechas y contexto</h2><p>Registros históricos y observaciones recientes, separados por sensor.</p></div><span className="source-badge">Sin datos simulados</span></div>
    <div className="report-controls">
      <label>Desde<select aria-label="Año histórico inicial" value={range.desde} onChange={e=>setRange(r=>({...r,desde:Number(e.target.value)}))}>{years.map(y=><option key={y}>{y}</option>)}</select></label>
      <label>Hasta<select aria-label="Año histórico final" value={range.hasta} onChange={e=>setRange(r=>({...r,hasta:Number(e.target.value)}))}>{years.map(y=><option key={y} value={y}>{y}{y === lastYear ? ' · en curso' : ''}</option>)}</select></label>
      <label>Área del informe<select aria-label="Área del informe" value={range.ambito} onChange={e=>setRange(r=>({...r,ambito:e.target.value}))}><option value="entorno">Cochabamba y entorno Tunari</option><option value="cercado">Cercado · extensión GAMC</option></select></label>
      <label>Sensor<select aria-label="Sensor del informe" value={range.sensor} onChange={e=>setRange(r=>({...r,sensor:e.target.value}))}>{Object.entries(SENSORS).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      <button onClick={()=>{cache.current.clear();setRevision(n=>n+1);}} disabled={loading}><Icon name="search" size={16} />Consultar</button>
    </div>
    {loading && <p className="report-status" role="status">Consultando registros y análisis local…</p>}
    {error && <p className="report-status" role="alert">{error}</p>}
    {report && <>
      <p className="report-scope">{report.ambito_descripcion} · {range.desde}–{range.hasta} · {SENSORS[report.sensor]}{filtros.distrito && ` · Distrito ${filtros.distrito}`}</p>
      {report.incluye_actual && <div className="report-current" role="status"><Icon name="clock" size={18} /><div><strong>{lastYear} en curso · cobertura parcial</strong><span>Fuente reciente: {report.actualizacion.estado === 'ok' ? 'vigente' : report.actualizacion.estado === 'atrasada' ? 'atrasada' : 'sin dato disponible'} · Última consulta de la fuente: {fecha(report.actualizacion.ultima_ingesta)}</span><span>Datos hasta: {fecha(report.corte_datos)}. {report.actualizacion.automatica ? `Actualización tras cada ingesta de ${report.actualizacion.intervalo_horas} h.` : 'Actualización manual.'} Los meses sin registros ni cobertura permanecen sin dato; no se descargó el año completo.</span></div></div>}
      <div className="report-metrics">
        <div><strong>{number(report.eventos)}</strong><span>Eventos satelitales agrupados</span></div>
        <div><strong>{number(report.detecciones)}</strong><span>{report.sensor === 'MODIS' ? 'Detecciones MODIS de confianza >80' : 'Detecciones VIIRS nominales o altas'}</span></div>
        <div><strong>{number(report.frecuencia_por_30_dias,2)}</strong><span>Eventos por 30 días cubiertos</span></div>
        <div><strong>{number(report.dias_con_eventos)}</strong><span>Días con eventos registrados</span></div>
      </div>
      <p className="report-summary">{report.eventos ? <>Primera observación: {fecha(report.primera_observacion)}. Última: {fecha(report.ultima_observacion)}. Meses con mayor frecuencia: {report.meses_mayor_frecuencia.map(m=>MONTHS[m-1]).join(', ') || 'sin dato'}.</> : report.eventos === 0 ? 'Sin eventos elegibles en las ventanas consultadas.' : 'Sin cobertura disponible para esta selección.'} {number(report.dias_cubiertos)} días completos cubiertos ({number(report.dias_archivo)} de archivo estándar). Las tasas excluyen días incompletos; un cero no acredita ausencia de fuego. Se conservan {number(report.registros_totales)} registros: {number(report.registros_baja_confianza)} de menor confianza y {number(report.registros_descartados)} descartados del análisis.</p>
      <div className="report-charts"><Bars rows={report.anual.map(r=>({label:r.anio,value:r.eventos,partial:r.cobertura !== 'completa'}))} title="Eventos por año" unit="Un sensor por serie · * cobertura parcial; no equivale al total anual" color="#baa3ff"/>
        <Bars rows={report.mensual.map(r=>({label:MONTHS[r.mes-1],value:r.eventos_por_30_dias,partial:r.cobertura !== 'completa'}))} title="Frecuencia estacional" unit="Eventos por 30 días completos cubiertos · — cobertura insuficiente"/>
        <Bars rows={report.horaria.map(r=>({label:r.hora,value:r.detecciones}))} title="Hora de adquisición" unit="Registros disponibles en hora de Bolivia · no indica el inicio del fuego" color="#f7ac65"/>
        <Calendar rows={report.calendario}/></div>
      <article className="ai-analysis" id="analisis" aria-labelledby="ai-title"><div className="section-head"><h3 id="ai-title" className="heading-with-icon"><Icon name="brain" size={25} />IA local · patrones de actividad</h3><span className="source-badge">{ia.estado==='entrenado' ? 'Modelo entrenado' : 'Muestra insuficiente'}</span></div>
        <p>{ia.metodo}. {ia.objetivo}.</p>
        {ia.estado!=='entrenado' ? <div className="ai-empty"><p>{ia.motivo} No se emite una predicción para este período.</p>{range.sensor === 'MODIS' && report.anios_disponibles?.length >= 3 && <><button onClick={()=>setRange(r=>({...r,desde:report.anios_disponibles[0],hasta:Math.max(r.hasta,report.anios_disponibles.at(-1))}))}><Icon name="brain" size={16} />Añadir histórico {report.anios_disponibles[0]}–{report.anios_disponibles.at(-1)} al análisis</button><small>Consulta local; conserva el seguimiento del año en curso.</small></>}</div> : <>
          <p>Entrenamiento: {ia.validacion.entrenamiento.join(' a ')}. Validación independiente: {ia.validacion.validacion.join(' a ')} ({ia.validacion.eventos_validacion} eventos; muestra de validación reducida).</p>
          <div className="ai-validation"><span>MAE modelo / promedio: <b>{ia.validacion.mae_modelo} / {ia.validacion.mae_base}</b></span><span>Devianza modelo / promedio: <b>{ia.validacion.devianza_modelo} / {ia.validacion.devianza_base}</b></span></div>
          <p>{ia.validacion.supera_base ? 'Menor devianza que el promedio histórico; revisa también el error MAE.' : 'El modelo no mejora la devianza del promedio histórico.'} Las estimaciones son exploratorias, no alertas operativas.</p>
          {ia.seguimiento_actual && <p>Seguimiento {ia.seguimiento_actual.anio}: {ia.seguimiento_actual.dias_comparables ? `${number(ia.seguimiento_actual.eventos_observados)} eventos observados y ${number(ia.seguimiento_actual.eventos_esperados,2)} esperados en ${number(ia.seguimiento_actual.dias_comparables)} días completos comparables.` : 'Aún no hay días completos consultados para comparar observaciones con el modelo.'} {ia.seguimiento_actual.nota}</p>}
          <div className="report-table-scroll"><table><caption>Estimación estacional de actividad MODIS · próximos 28 días</caption><thead><tr><th>Desde</th><th>Hasta</th><th>Eventos esperados</th></tr></thead><tbody>{ia.pronostico.map(p=><tr key={p.desde}><td>{p.desde}</td><td>{p.hasta}</td><td>{number(p.eventos_modis_esperados,2)}</td></tr>)}</tbody></table></div>
        </>}
        <p className="ai-caution">Sin meteorología actual ni evaluación de combustible. No estima la probabilidad de un incendio confirmado. Los focos recientes requieren revisión humana.</p>
      </article>
      <details className="report-detail"><summary><Icon name="file" size={17} />Últimos eventos y trazabilidad</summary><div className="report-table-scroll"><table><thead><tr><th>Adquisición (BO)</th><th>Observaciones</th><th>FRP máx. MW</th><th>Revisión</th></tr></thead><tbody>{report.ultimos_eventos.map(e=><tr key={e.id}><td>{fecha(e.fecha)}</td><td>{e.detecciones}</td><td>{number(e.frp_max,1)}</td><td>{e.revision_manual ? 'Pendiente' : 'Tipo de fuente disponible'}</td></tr>)}</tbody></table></div>
        <ul>{report.advertencias.map(a=><li key={a}>{a}</li>)}</ul><ul>{report.fuentes.map((s,i)=><li key={i}><a href={s.url} target="_blank" rel="noreferrer">NASA {s.producto} · {s.desde} a {s.hasta}</a></li>)}</ul>
      </details>
      <div className="report-actions"><a href={urlInforme(params,'csv')}><Icon name="download" size={16} />Descargar CSV mensual</a><a href={urlInforme(params,'informe')}><Icon name="file" size={16} />Descargar informe JSON</a><button onClick={()=>window.print()}><Icon name="printer" size={16} />Imprimir / guardar PDF</button></div>
    </>}
  </section>;
}
