"""Ventanas consultadas y días completos; nunca infiere cobertura de un foco aislado."""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo('America/La_Paz')


def unir_ventanas(windows):
    merged = []
    for start, end in sorted(windows):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def ventanas(ingestas, inicio, fin, now):
    archive, nrt = [], []
    for item in ingestas:
        if item.estado != 'ok':
            continue
        if item.origen == 'historico' and item.completa:
            start = datetime.combine(item.inicio, time.min, timezone.utc)
            end = datetime.combine(item.fin + timedelta(days=1), time.min, timezone.utc)
            target = archive
        elif item.origen == 'nrt':
            detail = item.detalle or {}
            if detail.get('fuente_datos') == 'nasa_keyless':
                published = detail.get('datos_hasta')
                if not published:
                    continue
                published = datetime.fromisoformat(published)
                if published.tzinfo is None or published > item.fecha + timedelta(minutes=5):
                    continue
                                                                                                
                start, end = item.fecha - timedelta(hours=24), min(item.fecha, published)
            elif detail.get('fuente_datos') == 'nasa_mapkey':
                start = datetime.combine(item.inicio, time.min, timezone.utc)
                end = min(item.fecha, datetime.combine(item.fin + timedelta(days=1), time.min, timezone.utc))
            else:
                continue
            target = nrt
        else:
            continue
        start, end = max(start, inicio), min(end, fin, now)
        if end > start:
            target.append((start, end))
    archive, nrt = unir_ventanas(archive), unir_ventanas(nrt)
    return archive, nrt, unir_ventanas(archive + nrt)


def dias_completos(windows):
    days = set()
    for start, end in windows:
        cursor = start.astimezone(TZ).date()
        while datetime.combine(cursor + timedelta(days=1), time.min, TZ) <= end:
            if datetime.combine(cursor, time.min, TZ) >= start:
                days.add(cursor)
            cursor += timedelta(days=1)
    return days


def horas_en(windows, inicio, fin):
    return sum(max(0, (min(end, fin) - max(start, inicio)).total_seconds()) for start, end in windows) / 3600


def horas_del_dia(windows):
    if dias_completos(windows):
        return set(range(24))
    hours = set()
    for start, end in windows:
        cursor = start.astimezone(TZ).replace(minute=0, second=0, microsecond=0)
        while cursor < end:
            hours.add(cursor.hour)
            cursor += timedelta(hours=1)
    return hours
