import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { cargarDatos, cargarLimites } from '../api/client';

const Context = createContext(null);
export function FiltrosProvider({ children }) {
  const [filtros, setFiltros] = useState({ dias: 7, distrito: '', desde: '', hasta: '' });
  const [capas, setCapas] = useState({ detecciones: true, alertas: true, heatmap: false, gamcDistritos: true, periurbanos: true, cota2750: false });
  const [mostrarDistritos, setMostrarDistritos] = useState(false);
  const [mostrarPNT, setMostrarPNT] = useState(false);
  const [geografia, setGeografia] = useState({ distritos: null, pnt: null, territorio: null });
  const [errorGeografia, setErrorGeografia] = useState('');
  const geoRequest = useRef(null);
  const cargarGeografia = useCallback(() => {
    if (!geoRequest.current) geoRequest.current = Promise.allSettled([cargarLimites('distritos'), cargarLimites('pnt'), cargarLimites('territorio')]).then(([distritos, pnt, territorio]) => {
      setGeografia({ distritos: distritos.status === 'fulfilled' ? distritos.value : null, pnt: pnt.status === 'fulfilled' ? pnt.value : null, territorio: territorio.status === 'fulfilled' ? territorio.value : null });
      setErrorGeografia(distritos.status === 'rejected' || pnt.status === 'rejected' ? 'Límites no disponibles' : '');
    });
    return geoRequest.current;
  }, []);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [seleccion, setSeleccion] = useState(null);
  const revision = useRef(0);
  const refrescar = useCallback(async () => {
    const current = ++revision.current;
    setLoading(true);
    try {
      const result = await cargarDatos(filtros);
      if (current === revision.current) { setData(result); setError(''); }
    } catch {
      if (current === revision.current) setError('El servicio de monitoreo no está disponible. No se muestran datos simulados.');
    } finally {
      if (current === revision.current) setLoading(false);
    }
  }, [filtros]);
  useEffect(() => {
    setSeleccion(null);
    setData(null);
    refrescar();
    const refrescarVisible = () => { if (!document.hidden) refrescar(); };
    const timer = setInterval(refrescarVisible, 60000);
    document.addEventListener('visibilitychange', refrescarVisible);
    return () => { revision.current++; clearInterval(timer); document.removeEventListener('visibilitychange', refrescarVisible); };
  }, [refrescar]);
  const value = useMemo(() => ({ filtros, setFiltros, capas, setCapas, mostrarDistritos, setMostrarDistritos, mostrarPNT, setMostrarPNT, geografia, errorGeografia, cargarGeografia, data, loading, error, refrescar, seleccion, setSeleccion }),
    [filtros, capas, mostrarDistritos, mostrarPNT, geografia, errorGeografia, cargarGeografia, data, loading, error, refrescar, seleccion]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useFiltros() { return useContext(Context); }
