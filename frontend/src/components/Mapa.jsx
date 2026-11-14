import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet.heat';
import { useFiltros } from '../context/FiltrosContext';
import { useEventos } from '../hooks/useEventos';
import { CAPAS, CENTRO, BBOX_CERCADO, NIVELES, SENSORES, ETIQUETAS } from '../utils/constantes';
import { fecha, distritoLabel, frp, areaKm2 } from '../utils/formatters';
import { consultarTerritorio } from '../api/client';
import Icon, { createIconElement } from './Icon';

const CARTO_KEY = import.meta.env.VITE_CARTO_API_KEY || '';
const DISTRICT_STYLE = { color: '#2a3140', weight: 1, fillColor: '#1a2028', fillOpacity: 0.15, dashArray: '4,4' };
const PNT_STYLE = { color: '#22c55e', weight: 2, fillColor: '#22c55e', fillOpacity: 0.10, dashArray: '8,4' };
const GAMC_LAYERS = { gamcDistritos: 'distritos', periurbanos: 'periurbanos', cota2750: 'cota2750' };

function popup(title, fields, icon) {
  const root = document.createElement('div');
  const heading = document.createElement('strong'); heading.textContent = title; if (icon) heading.prepend(createIconElement(icon)); root.append(heading);
  for (const [key, value] of fields) {
    const row = document.createElement('div'); row.className = 'popup-row';
    const label = document.createElement('span'); label.textContent = key;
    const text = document.createElement('b'); text.textContent = value == null ? 'Sin dato' : String(value);
    row.append(label, text); root.append(row);
  }
  return root;
}

export default function Mapa() {
  const element = useRef(null), map = useRef(null), markers = useRef(new Map());
  const capasRef = useRef({ distritosLayer: null, pntLayer: null });
  const cartografiaRef = useRef({});
  const activeDistrict = useRef('');
  const { capas, setCapas, filtros, seleccion, data, loading, mostrarDistritos, setMostrarDistritos, mostrarPNT, setMostrarPNT, geografia, errorGeografia, cargarGeografia } = useFiltros();
  activeDistrict.current = filtros.distrito;
  const { detecciones } = useEventos();
  const [tileError, setTileError] = useState(false);
  const [layerMenu, setLayerMenu] = useState(false);
  const [gamcErrors, setGamcErrors] = useState([]);
  useEffect(() => {
    const instance = L.map(element.current, { zoomControl: false, preferCanvas: false }).setView(CENTRO, 11);
    map.current = instance;
    instance.createPane('limites').style.zIndex = 350;
    instance.createPane('cartografia').style.zIndex = 345;
    cargarGeografia();
    const tiles = CARTO_KEY ? `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=${encodeURIComponent(CARTO_KEY)}` : 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
    L.tileLayer(tiles, {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' + (CARTO_KEY ? ' &copy; <a href="https://carto.com/attributions">CARTO</a>' : ''),
      className: CARTO_KEY ? 'carto-tiles' : 'osm-dark-tiles', maxZoom: 19,
    }).on('tileerror', () => setTileError(true)).addTo(instance);
    L.control.zoom({ position: 'bottomright', zoomInText: createIconElement('plus').outerHTML, zoomOutText: createIconElement('minus').outerHTML, zoomInTitle: 'Acercar mapa', zoomOutTitle: 'Alejar mapa' }).addTo(instance);
    L.control.scale({ imperial: false, position: 'bottomleft' }).addTo(instance);
    const resize = new ResizeObserver(() => instance.invalidateSize()); resize.observe(element.current);
    return () => { resize.disconnect(); instance.remove(); map.current = null; };
  }, [cargarGeografia]);
  const gamcConfigured = data?.capas?.configurado === true && data.capas.disponible !== false;
  useEffect(() => {
    const instance = map.current;
    if (!instance || !gamcConfigured || !geografia.territorio) return;
    const layers = [];
    for (const [flag, key] of Object.entries(GAMC_LAYERS)) {
      if (!capas[flag]) continue;
      if (geografia.territorio.cartografia?.capas?.some((c) => c.capa === key)) continue;
      const layer = L.tileLayer.wms('/api/gamc/wms', { capa: key, layers: '', format: 'image/png',
        transparent: true, version: '1.1.1', maxZoom: 19, opacity: key === 'distritos' ? 0.65 : 0.45,
        attribution: '<a href="https://recursosgamc.cochabamba.bo/api-doc">GAMC</a>',
      });
      layer.on('tileerror', () => setGamcErrors((current) => current.includes(key) ? current : [...current, key]));
      layer.addTo(instance); layers.push(layer);
    }
    let current = 0;
    const inspect = async (event) => {
      const id = ++current;
      const active = Object.entries(GAMC_LAYERS).filter(([flag]) => capas[flag]).map(([, key]) => key);
      if (!active.length) return;
      const panel = L.popup().setLatLng(event.latlng).setContent(popup('Consultando GAMC…', [])).openOn(instance);
      const rows = await Promise.all(active.map(async (key) => {
        try {
          const result = await consultarTerritorio(event.latlng.lat, event.latlng.lng, key);
          return [CAPAS[key], result.disponible === false ? 'Consulta no disponible' : result.atributos.length ? result.atributos.map((p) => Object.entries(p).map(([name, value]) => `${name}: ${value}`).join(' · ')).join('; ') : 'Sin coincidencia'];
        } catch { return [CAPAS[key], 'Consulta no disponible']; }
      }));
      if (id === current && instance.hasLayer(panel)) panel.setContent(popup('Información territorial · GAMC', rows));
    };
    instance.on('click', inspect);
    return () => { current++; instance.off('click', inspect); layers.forEach((layer) => instance.removeLayer(layer)); };
  }, [gamcConfigured, capas.gamcDistritos, capas.periurbanos, capas.cota2750, geografia.territorio]);
  useEffect(() => {
    const instance = map.current, territory = geografia.territorio;
    if (!instance || !territory) return;
    const cache = territory.cartografia;
    if (cache?.disponible) {
      const [west, south, east, north] = cache.consulta.BBOX;
      for (const entry of cache.capas) {
        cartografiaRef.current[entry.capa] = L.imageOverlay(entry.url, [[south, west], [north, east]], {
          pane: 'cartografia', opacity: entry.capa === 'distritos' ? .25 : .9,
          className: `gamc-cache gamc-${entry.capa}`, zIndex: entry.capa === 'distritos' ? 1 : 2,
          attribution: '<a href="https://recursosgamc.cochabamba.bo/api-doc">GAMC · cartografía guardada</a>',
        });
      }
    }
    for (const [category, key] of [['cercado', 'distritos'], ['periurbano', 'periurbanos']]) {
      const features = territory.features.filter(f => f.properties.clase === category);
      if (features.length) cartografiaRef.current[key] = L.geoJSON({type:'FeatureCollection', features}, {
        pane:'limites', bubblingMouseEvents:false, style:{color:key === 'distritos' ? '#baa3ff' : '#ff9f64', weight:2, fillOpacity:.12},
        onEachFeature:(f, layer) => layer.bindPopup(popup(f.properties.nombre, [['Fuente',f.properties.fuente || 'Geometría local verificada']])),
      });
    }
    return () => { Object.values(cartografiaRef.current).forEach(layer => instance.removeLayer(layer)); cartografiaRef.current = {}; };
  }, [geografia.territorio]);
  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    for (const [key, visible] of [['distritos',capas.gamcDistritos], ['periurbanos',capas.periurbanos]]) {
      const layer = cartografiaRef.current[key];
      if (layer) { if (visible) layer.addTo(instance); else instance.removeLayer(layer); }
    }
  }, [geografia.territorio, capas.gamcDistritos, capas.periurbanos]);
  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const selectedStyle = (feature) => String(feature.properties.id) === String(activeDistrict.current)
      ? { ...DISTRICT_STYLE, color: '#ff6b00', weight: 2, fillOpacity: 0.25 } : { ...DISTRICT_STYLE };
    if (geografia.distritos) capasRef.current.distritosLayer = L.geoJSON(geografia.distritos, {
      pane: 'limites', bubblingMouseEvents: false, style: selectedStyle,
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        layer.bindPopup(popup(p.nombre, [['Área del polígono', areaKm2(p.area_km2)], ['Alertas activas', p.alertas_activas], ['Eventos históricos', p.eventos_historicos], ['Límite', p.verificada ? 'Verificado' : 'Ilustrativo / no oficial']], 'map'));
        layer.on('mouseover', () => layer.setStyle({ ...selectedStyle(feature), weight: 2, fillOpacity: 0.3 }));
        layer.on('mouseout', () => layer.setStyle(selectedStyle(feature)));
      },
    });
    if (geografia.pnt) capasRef.current.pntLayer = L.geoJSON(geografia.pnt, {
      pane: 'limites', bubblingMouseEvents: false, style: PNT_STYLE,
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        layer.bindPopup(popup(p.nombre, [['Área del polígono', areaKm2(p.area_km2)], ['Distritos que cruza', p.distritos_que_cruza], ['Alertas activas', p.alertas_activas], ['Límite', p.verificada ? 'Verificado' : 'Ilustrativo / no oficial']], 'tree'));
      },
    });
    return () => {
      for (const layer of Object.values(capasRef.current)) if (layer) instance.removeLayer(layer);
      capasRef.current = { distritosLayer: null, pntLayer: null };
    };
  }, [geografia]);
  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    for (const [name, visible] of [['distritosLayer', mostrarDistritos], ['pntLayer', mostrarPNT]]) {
      const layer = capasRef.current[name];
      if (layer) { if (visible) layer.addTo(instance); else instance.removeLayer(layer); }
    }
    if (mostrarPNT) capasRef.current.pntLayer?.bringToBack();
  }, [mostrarDistritos, mostrarPNT, geografia]);
  useEffect(() => {
    if (!map.current || !capasRef.current.distritosLayer) return;
    let selected;
    capasRef.current.distritosLayer.eachLayer((layer) => {
      const active = String(layer.feature.properties.id) === String(filtros.distrito);
      layer.setStyle(active ? { ...DISTRICT_STYLE, color: '#ff6b00', weight: 2, fillOpacity: 0.25 } : DISTRICT_STYLE);
      if (active) selected = layer;
    });
    map.current.fitBounds(selected ? selected.getBounds() : BBOX_CERCADO, { padding: [25, 25], maxZoom: 13, animate: false });
  }, [filtros.distrito, geografia]);
  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const layers = [];
    const add = (layer) => { layer.addTo(instance); layers.push(layer); };
    if (capas.heatmap) add(L.heatLayer(detecciones.map((d) => [d.latitude, d.longitude, Math.min(1, (d.frp ?? 1) / 50)]),
      { radius: 30, blur: 24, maxZoom: 13, minOpacity: 0.2, gradient: { 0.3: '#808e59', 0.6: '#eab066', 1: '#fc7373' } }));
    if (capas.detecciones) for (const d of detecciones) {
      add(L.circleMarker([d.latitude, d.longitude], { color: SENSORES[d.sensor], fillColor: SENSORES[d.sensor],
        bubblingMouseEvents: false,
        weight: 1.5, radius: 4 + Math.min(11, Math.sqrt(d.frp ?? 0) * 1.1), fillOpacity: d.candidata ? 0.12 : 0.5,
        dashArray: d.candidata ? '2 3' : undefined,
      }).bindPopup(popup(`${d.sensor} · ${d.candidata ? 'Candidata' : 'Detección satelital'}`, [
        ['Adquisición (BO)', fecha(d.fecha)], ['Satélite', d.satelite], ['FRP', frp(d.frp)], ['Confianza', d.confidence],
        ['Resolución', `${d.resolucion} m`], ['Unidad', distritoLabel(d.distrito)],
        ['Dentro del Tunari', d.en_tunari ? 'Sí' : data?.demo ? 'No (ejemplo)' : data?.estadisticas.tunari_verificado ? 'No' : 'Sin límite verificado'],
      ])));
    }
    markers.current.clear();
    if (capas.alertas) for (const a of data?.alertas || []) {
      if (!['nueva', 'en_revision'].includes(a.estado)) continue;
      const marker = L.circleMarker([a.latitude, a.longitude], { color: NIVELES[a.nivel], fillColor: NIVELES[a.nivel],
        bubblingMouseEvents: false,
        weight: 2, radius: 17, fillOpacity: 0.12,
      }).bindPopup(popup(`Alerta ${ETIQUETAS[a.nivel]}`, [['Unidad', distritoLabel(a.distrito)], ['Motivo', a.descripcion], ['Estado', a.estado]]));
      markers.current.set(a.id, marker); add(marker);
    }
    return () => layers.forEach((layer) => instance.removeLayer(layer));
  }, [capas, detecciones, data]);
  useEffect(() => {
    if (!seleccion || !map.current) return;
    map.current.flyTo([seleccion.latitude, seleccion.longitude], 13, { duration: 0.8 });
    markers.current.get(seleccion.id)?.openPopup();
  }, [seleccion, capas.alertas]);
  const illustrative = Object.values(geografia).some((g) => g?.features.some((f) => f.properties.ilustrativa));
  return <section className="map-shell" id="territorio" aria-label="Mapa de observación de Cochabamba">
    <div className="leaflet-canvas" ref={element} />
    <div className="map-toolbar"><div className="map-chip"><span className="live-dot" />Vista territorial <span className="divider" aria-hidden="true">/</span><span>{loading ? 'Actualizando…' : !data ? 'Sin datos' : `${detecciones.length} señales`}</span></div>
      <div className="layer-wrapper"><button className={`map-button ${layerMenu ? 'active' : ''}`} onClick={() => setLayerMenu(!layerMenu)} aria-expanded={layerMenu}><Icon name="layers" size={16} />Capas <Icon name="chevron" size={14} /></button>
        {layerMenu && <div className="layer-menu"><h3>Capas del mapa</h3>{Object.entries(CAPAS).map(([key, name]) => <label key={key}><input type="checkbox" checked={key === 'distritos' ? mostrarDistritos : key === 'tunari' ? mostrarPNT : capas[key]} onChange={(e) => key === 'distritos' ? setMostrarDistritos(e.target.checked) : key === 'tunari' ? setMostrarPNT(e.target.checked) : setCapas((c) => ({ ...c, [key]: e.target.checked }))} /><span>{name}</span></label>)}</div>}
      </div>
    </div>
    <div className="map-caption"><span>COCHABAMBA · BOLIVIA</span><h2>Cercado<span>Territorio y periurbanos</span></h2></div>
    <button className="reset-map map-button" onClick={() => map.current?.fitBounds(BBOX_CERCADO, {padding:[25,25]})} aria-label="Centrar mapa en Cercado"><Icon name="target" size={19} /></button>
    <div className="map-legend" id="leyenda-mapa">
      <div className="legend-section"><strong>Sensores</strong><span><i style={{ background: SENSORES.MODIS }} />MODIS <small>1 km</small></span><span><i style={{ background: SENSORES.VIIRS }} />VIIRS <small>375 m</small></span></div>
      <div className="legend-section"><strong>Territorio</strong><span><i style={{background:'#baa3ff'}} />Cercado / distritos</span><span><i style={{background:'#ff9566'}} />Periurbanos · colores GAMC</span></div>
      {(mostrarDistritos || mostrarPNT) && <div className="legend-section"><strong>Esquemas</strong><span><i className="legend-boundary pnt-line" />PNT ilustrativo</span><span><i className="legend-boundary district-line" />Distritos ilustrativos</span></div>}
      <div className="legend-section"><strong>Alertas</strong>{Object.entries(NIVELES).map(([level, color]) => <span key={level}><i style={{ background: color }} />{ETIQUETAS[level]}</span>)}</div>
    </div>
    <div className="map-notices" aria-live="polite">
      {illustrative && (mostrarDistritos || mostrarPNT) && <span>Esquemas vectoriales ilustrativos · No oficiales</span>}
      {geografia.territorio?.cartografia?.disponible && <span>Cartografía GAMC guardada · {new Date(geografia.territorio.cartografia.capturada).toLocaleDateString('es-BO')} · sin descarga al mover el mapa</span>}
      {gamcErrors.length > 0 && <span>Capas GAMC con errores: {gamcErrors.join(', ')}</span>}
      {data?.capas?.disponible === false && <span>GAMC en línea no disponible · Focos: NASA FIRMS</span>}
      {data?.estado === 'ok' && !detecciones.length && <span>Sin detecciones en el período consultado. No confirma ausencia de fuego.</span>}
      {!CARTO_KEY && <span>Mapa base OpenStreetMap · CARTO pendiente de clave</span>}
      {errorGeografia && <span>Límites no disponibles</span>}{tileError && <span>Algunas teselas no están disponibles</span>}
      {data?.truncado && <span>Vista limitada: reduce el período para ver todos los registros</span>}
    </div>
  </section>;
}
