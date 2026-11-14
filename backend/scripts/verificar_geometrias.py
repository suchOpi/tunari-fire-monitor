import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text
from app.config import ROOT, get_settings
from app.database import SessionLocal


def main():
    west, south, east, north = map(float, get_settings().bbox.split(','))
    with SessionLocal.begin() as db:
        db.execute(text('SELECT pg_advisory_xact_lock(734201)'))
        invalid = db.execute(text("SELECT id, ST_IsValidReason(geom) AS motivo FROM unidades_espaciales WHERE clase IN ('distrito','tunari') AND NOT ST_IsValid(geom)")).mappings().all()
        for row in invalid:
            db.execute(text('UPDATE unidades_espaciales SET geom=ST_MakeValid(geom) WHERE id=:id'), {'id': row['id']})
        units = [dict(r) for r in db.execute(text("SELECT id, clase, ST_IsValid(geom) AS valida, ST_IsEmpty(geom) AS vacia, ST_SRID(geom) AS srid, verificada, propiedades->>'demo' AS demo FROM unidades_espaciales WHERE clase IN ('distrito','tunari') ORDER BY clase,id")).mappings()]
        checks = [dict(r) for r in db.execute(text("""
            SELECT d.id, d.latitude, d.longitude, count(u.id) AS coincidencias,
                   array_agg(u.id ORDER BY u.id) FILTER (WHERE u.id IS NOT NULL) AS distritos
            FROM detecciones_raw d LEFT JOIN unidades_espaciales u
              ON u.clase='distrito' AND ST_Contains(u.geom,d.geom)
            WHERE d.origen='nrt'
            GROUP BY d.id,d.latitude,d.longitude ORDER BY d.id
        """)).mappings()]
        parks = [dict(r) for r in db.execute(text("""
            SELECT p.id, ST_CoveredBy(p.geom,ST_MakeEnvelope(:w,:s,:e,:n,4326)) AS dentro_bbox,
                   count(d.id) AS distritos_solapados,
                   array_agg(d.id ORDER BY d.id) FILTER (WHERE d.id IS NOT NULL) AS distritos
            FROM unidades_espaciales p LEFT JOIN unidades_espaciales d
              ON d.clase='distrito' AND ST_Intersects(p.geom,d.geom)
                 AND ST_Area(ST_Intersection(p.geom,d.geom))>0
            WHERE p.clase='tunari' GROUP BY p.id,p.geom
        """), {'w': west, 's': south, 'e': east, 'n': north}).mappings()]
    incidents = [r for r in checks if r['coincidencias'] != 1]
    date = datetime.now(ZoneInfo('America/La_Paz')).isoformat(timespec='seconds')
    counts = {kind: sum(u['clase'] == kind for u in units) for kind in ('distrito', 'tunari')}
    lines = ['# Verificación local de geometrías', '', f'Fecha: {date}. Ejecución única; sin fuentes externas.', '',
             'El esquema usa `unidades_espaciales`, con `clase=distrito` y `clase=tunari`; no existen tablas separadas `distritos` y `pnt`.',
             f"Conteo equivalente: {counts['distrito']} distritos + {counts['tunari']} PNT = {len(units)} geometrías.",
             f"ST_IsValid: {sum(u['valida'] for u in units)}/{len(units)} válidas. Correcciones ST_MakeValid: {len(invalid)}.", '',
             '**Validez topológica no acredita límites oficiales.** Se conserva `verificada=false` en las geometrías ilustrativas y no se usan para afirmar el distrito real de un foco.', '',
             '| ID | Clase | Válida | SRID | Demo | Verificada |', '|---|---|---|---|---|---|']
    lines.extend(f"| {u['id']} | {u['clase']} | {u['valida']} | {u['srid']} | {u['demo']} | {u['verificada']} |" for u in units)
    if invalid:
        lines += ['', 'Correcciones automáticas:', *[f"- {r['id']}: {r['motivo']} → ST_MakeValid." for r in invalid]]
    lines += ['', '## Cruce con detecciones NRT', '', f'Detecciones examinadas: {len(checks)}. Coincidencia exacta con un distrito: {len(checks)-len(incidents)}. Incidencias: {len(incidents)}.']
    if not checks:
        lines.append('No hay detecciones NRT cargadas: el cruce no puede verificarse empíricamente. Esto no certifica que los límites coincidan con datos reales.')
    if incidents:
        lines += ['', '| Detección | Latitud | Longitud | Coincidencias | Distrito IDs |', '|---|---|---|---|---|']
        lines.extend(f"| {r['id']} | {r['latitude']} | {r['longitude']} | {r['coincidencias']} | {', '.join(r['distritos'] or []) or 'ninguno'} |" for r in incidents)
    lines += ['', '## PNT', '']
    for p in parks:
        lines.append(f"- {p['id']}: dentro del bbox={p['dentro_bbox']}; solapamiento con {p['distritos_solapados']} distritos ({', '.join(p['distritos'] or [])}). Umbral solicitado ≤3: {'cumple' if p['distritos_solapados'] <= 3 else 'INCIDENCIA'}.")
    lines += ['', 'Los cruces usan ST_Contains; un punto sobre un borde puede tener cero coincidencias. El solapamiento del PNT cuenta intersecciones con área positiva. No se corrigieron límites manualmente ni se certificó su procedencia.']
    (ROOT / 'docs/geometrias.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    summary = {'fecha': date, 'conteos': counts, 'validas': sum(u['valida'] for u in units),
               'corregidas': len(invalid), 'detecciones': len(checks), 'incidencias': incidents, 'pnt': parks}
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
