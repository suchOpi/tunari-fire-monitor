import { useFiltros } from '../context/FiltrosContext';
export function useEventos() {
  const { data, loading } = useFiltros();
  return { eventos: data?.eventos || [], detecciones: data?.detecciones || [], loading };
}
