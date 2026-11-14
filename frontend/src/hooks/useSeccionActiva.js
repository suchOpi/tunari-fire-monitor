import { useEffect, useState } from 'react';

/** Devuelve el id de la sección visible para marcar el enlace activo de la navegación. */
export function useSeccionActiva(ids) {
  const [activa, setActiva] = useState(ids[0]);
  useEffect(() => {
    const elementos = ids.map((id) => document.getElementById(id)).filter(Boolean);
    if (!elementos.length || typeof IntersectionObserver === 'undefined') return undefined;
    const visibles = new Map();
    const observer = new IntersectionObserver((entradas) => {
      for (const e of entradas) visibles.set(e.target.id, e.isIntersecting ? e.intersectionRatio : 0);
      const [mejor] = [...visibles.entries()].sort((a, b) => b[1] - a[1]);
      if (mejor && mejor[1] > 0) setActiva(mejor[0]);
    }, { rootMargin: '-25% 0px -45% 0px', threshold: [0, .1, .3, .6, 1] });
    elementos.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [ids]);
  return activa;
}
