import { useState } from 'react';
import Icon from './Icon';
import { ETIQUETAS, ESTADOS, NIVELES } from '../utils/constantes';
import { fecha, distritoLabel } from '../utils/formatters';
import { useFiltros } from '../context/FiltrosContext';
import { leerToken, guardarToken } from '../api/client';

export default function TarjetaAlerta({ alerta, cambiar, saving }) {
  const { seleccion, setSeleccion, data } = useFiltros();
  const [open, setOpen] = useState(false);
  const [token, setToken] = useState(leerToken);
  return <article className={`alert-card ${seleccion?.id === alerta.id ? 'selected' : ''}`} style={{ '--level': NIVELES[alerta.nivel] }}>
    <div className="alert-top"><span className="level"><i />{ETIQUETAS[alerta.nivel]}</span><time dateTime={alerta.fecha}>{fecha(alerta.fecha)}</time></div>
    <button className="alert-focus" onClick={() => setSeleccion(alerta)}><strong>{distritoLabel(alerta.distrito)}</strong><Icon name="external" size={16} /></button>
    <p>{alerta.descripcion}</p>
    <div className="alert-bottom"><span>{ESTADOS[alerta.estado]}</span><button className="text-button" onClick={() => setOpen(!open)} aria-expanded={open}><Icon name={open ? 'minus' : 'plus'} size={14} />Gestionar</button></div>
    {open && <div className="alert-actions"><label>Token de operador<input type="password" autoComplete="off" value={token} onChange={(e) => { setToken(e.target.value); guardarToken(e.target.value); }} /></label><label>Estado de la alerta<select disabled={saving} value={alerta.estado} onChange={(e) => cambiar(alerta.id, e.target.value)}>{Object.entries(ESTADOS).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label>
      {alerta.revision_manual && ['nueva', 'en_revision'].includes(alerta.estado) && <button className="confirm-button" disabled={saving} onClick={() => cambiar(alerta.id, 'en_revision', true)}><Icon name="check" size={15} />Confirmar detección revisada</button>}
      <small>{data?.demo ? 'Los cambios de ejemplo duran hasta recargar la página.' : 'Confirmar la revisión permite notificar una señal crítica si Telegram está habilitado.'}</small>
    </div>}
  </article>;
}
