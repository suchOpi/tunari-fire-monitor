"""Actualiza manualmente dos imágenes GAMC; sin teselas ni tareas periódicas."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings
from app.services.gamc_client import fetch_wms, LAYERS


def main():
    root = get_settings().data_dir / 'geo/gamc'
    root.mkdir(parents=True, exist_ok=True)
    manifest_file = root / 'manifest.json'
    manifest = json.loads(manifest_file.read_text(encoding='utf-8')) if manifest_file.exists() else {
        'proveedor':'GAMC','documentacion':'https://recursosgamc.cochabamba.bo/api-doc',
        'consulta':{'BBOX':[-66.3,-17.55,-66.05,-17.25],'WIDTH':512,'HEIGHT':512,'SRS':'EPSG:4326','REQUEST':'GetMap'}}
    params = {**manifest['consulta'],'BBOX':','.join(map(str,manifest['consulta']['BBOX'])),
              'SERVICE':'WMS','VERSION':'1.1.1','FORMAT':'image/png','TRANSPARENT':'true','LAYERS':''}
    images = {}
    for layer in ('distritos','periurbanos'):
        response = fetch_wms(layer, params)
        if response is None:
            print('GAMC no disponible: se conserva la cartografía guardada, sin reintentos.')
            return 1
        if len(response.content) > 4 * 1024 * 1024:
            print('Imagen mayor de 4 MB: se conserva la copia anterior.')
            return 1
        images[layer] = response.content
    manifest['capas'] = []
    for layer, content in images.items():
        target = root / f'{layer}.png'
        temp = target.with_suffix('.tmp')
        temp.write_bytes(content)
        temp.replace(target)
        manifest['capas'].append({'capa':layer,'archivo':target.name,'service_id':LAYERS[layer]['id'],
                                 'sha256':hashlib.sha256(content).hexdigest()})
    manifest['capturada'] = datetime.now(timezone.utc).isoformat()
    temp = manifest_file.with_suffix('.tmp')
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(manifest_file)
    print('Dos imágenes actualizadas. Recarga la página; no es necesario reiniciar PostGIS.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
