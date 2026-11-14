import { useState } from 'react';
import { useFiltros } from '../context/FiltrosContext';
import { actualizarAlerta } from '../api/client';

export function useAlertas() {
  const { data, refrescar, loading } = useFiltros();
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  async function cambiar(id, state, confirm = false) {
    setError(''); setSaving(true);
    try { await actualizarAlerta(id, state, data.demo, confirm); await refrescar(); }
    catch { setError('No se pudo guardar el cambio. La alerta conserva su estado anterior.'); }
    finally { setSaving(false); }
  }
  return { alertas: data?.alertas || [], cambiar, error, saving, loading };
}
