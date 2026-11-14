from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, pstdev


@dataclass(frozen=True)
class Climatologia:
    anios: int
    p95_eventos: float
    frp_media: float | None
    frp_desv: float | None
    frp_maximo: float | None
    probabilidad: float


def regimen(year: int) -> str:
    return 'MODIS' if year < 2012 else 'MODIS+VIIRS'


def percentil(values, probability=0.95):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * probability
    low = int(position)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (position - low)


def climatologia(samples: list[dict]) -> Climatologia | None:
                                                                                      
    if not samples:
        return None
    frps = [value for sample in samples for value in sample['frps'] if value is not None]
    counts = [sample['eventos'] for sample in samples]
    return Climatologia(len(samples), percentil(counts), mean(frps) if frps else None,
                        pstdev(frps) if frps else None, max(frps) if frps else None,
                        sum(count > 0 for count in counts) / len(counts))


def dias_consecutivos(days: list[date]):
    longest = streak = 0
    previous = None
    for day in sorted(set(days)):
        streak = streak + 1 if previous and day - previous == timedelta(days=1) else 1
        longest = max(longest, streak)
        previous = day
    return longest


def factor_feedback(false_alarms: int, closed: int):
    return 1.0 if closed < 3 else 1 + min(0.5, false_alarms / closed * 0.5)


def evaluar(eventos: int, frp_max: float | None, days: list[date], critical: bool,
            baseline: Climatologia | None, factor=1.0, min_years=5):
    signals = []
    if not eventos:
        return signals
    if critical:
        signals.append(dict(senal='zona_critica', nivel='critica', descripcion='Detección en el PNT o a ≤2 km de un asentamiento verificado.'))
    consecutive = dias_consecutivos(days)
    if consecutive >= 3:
        signals.append(dict(senal='persistencia', nivel='alta' if consecutive >= 5 else 'media',
                            descripcion=f'Detecciones en {consecutive} días consecutivos (hora de Bolivia).'))
    if baseline is None or baseline.anios < min_years:
        return signals
    if eventos > baseline.p95_eventos * factor:
        signals.append(dict(senal='frecuencia', nivel='alta', descripcion=
            f'{eventos} eventos > P95 histórico {baseline.p95_eventos:.2f} × ajuste {factor:.2f}; {baseline.anios} años comparables.'))
    if frp_max is not None and baseline.frp_media is not None:
        threshold = baseline.frp_media + 2 * baseline.frp_desv * factor
        if frp_max > threshold:
            distance = f'{(frp_max - baseline.frp_media) / baseline.frp_desv:.2f}σ sobre la media' if baseline.frp_desv else 'supera la media con dispersión histórica nula'
            signals.append(dict(senal='intensidad', nivel='alta', descripcion=
                f'FRP {frp_max:.1f} MW: {distance}; umbral {threshold:.1f} MW, ajuste {factor:.2f}.'))
    if baseline.probabilidad < 0.05 / factor:
        signals.append(dict(senal='fuera_temporada', nivel='media', descripcion=
            f'Ocurrencia histórica {baseline.probabilidad:.1%} en esta unidad-semana ({baseline.anios} años); umbral {0.05 / factor:.1%}.'))
    return signals
