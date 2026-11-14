import { useState } from 'react';
import Icon from './Icon';
import { useAlertas } from '../hooks/useAlertas';
import TarjetaAlerta from './TarjetaAlerta';
import { useFiltros } from '../context/FiltrosContext';

export default function PanelAlertas() {
  const { alertas, cambiar, saving, error, loading } = useAlertas();
  const { data } = useFiltros();
  const unavailable = !data || data.motor_alertas?.disponible === false;
  const [all, setAll] = useState(false);
  const visible = alertas.filter((a) => all || ['nueva', 'en_revision'].includes(a.estado));
  const order = { critica: 0, alta: 1, media: 2, baja: 3 };
  visible.sort((a, b) => order[a.nivel] - order[b.nivel]);
  return <section className="alerts" aria-labelledby="alerts-title">
    <div className="section-head"><h2 id="alerts-title"><Icon name="alert" />Alertas {unavailable ? 'sin evaluar' : all ? '' : 'activas'} <span className="count">{unavailable ? '—' : visible.length}</span></h2>{!unavailable && <button className="text-button" onClick={() => setAll(!all)}><Icon name="eye" size={14} />{all ? 'Solo activas' : 'Ver todas'}</button>}</div>
    {error && <p role="alert" className="error">{error}</p>}
    {!visible.length && <p className="empty">{loading ? 'Consultando observaciones…' : !data ? 'Sin datos disponibles para evaluar alertas.' : data.motor_alertas?.disponible === false ? data.motor_alertas.motivo : 'Sin alertas para estos filtros. Esto no confirma ausencia de fuego.'}</p>}
    <div className="alert-list">{visible.map((alert) => <TarjetaAlerta key={alert.id} alerta={alert} cambiar={cambiar} saving={saving} />)}</div>
  </section>;
}
