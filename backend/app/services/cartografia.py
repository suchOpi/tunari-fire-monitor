import json
from ..config import get_settings


def metadata_cache():
    root = get_settings().data_dir / 'geo/gamc'
    try:
        manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
        layers = [{**item, 'url': f"/api/geografia/cartografia/{item['capa']}.png?v={item.get('sha256','')[:12]}"}
                  for item in manifest['capas'] if item['capa'] in {'distritos', 'periurbanos'} and (root / f"{item['capa']}.png").is_file()]
        return {**manifest, 'capas': layers, 'disponible': bool(layers)}
    except (OSError, ValueError, KeyError):
        return {'proveedor': 'GAMC', 'disponible': False, 'capas': []}
