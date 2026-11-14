import json
from types import SimpleNamespace
import httpx
from app.services import cartografia
from scripts import actualizar_cartografia


def test_provider_failure_keeps_both_saved_maps(tmp_path, monkeypatch):
    root = tmp_path / 'geo/gamc'
    root.mkdir(parents=True)
    (root / 'distritos.png').write_bytes(b'previous-districts')
    (root / 'periurbanos.png').write_bytes(b'previous-periurban')
    monkeypatch.setattr(actualizar_cartografia,'get_settings',lambda:SimpleNamespace(data_dir=tmp_path))
    calls = []
    def response(layer, params):
        calls.append(layer)
        return httpx.Response(200,content=b'new-districts') if layer == 'distritos' else None
    monkeypatch.setattr(actualizar_cartografia,'fetch_wms',response)
    assert actualizar_cartografia.main() == 1
    assert calls == ['distritos','periurbanos']
    assert (root / 'distritos.png').read_bytes() == b'previous-districts'
    assert (root / 'periurbanos.png').read_bytes() == b'previous-periurban'


def test_successful_cache_has_bounds_provenance_and_versioned_urls(tmp_path, monkeypatch):
    settings = SimpleNamespace(data_dir=tmp_path)
    monkeypatch.setattr(actualizar_cartografia,'get_settings',lambda:settings)
    monkeypatch.setattr(cartografia,'get_settings',lambda:settings)
    monkeypatch.setattr(actualizar_cartografia,'fetch_wms',lambda layer, params:httpx.Response(200,content=b'PNG-'+layer.encode()))
    assert actualizar_cartografia.main() == 0
    result = cartografia.metadata_cache()
    assert result['disponible'] and len(result['capas']) == 2
    assert result['consulta']['BBOX'] == [-66.3,-17.55,-66.05,-17.25]
    assert all('?v=' in item['url'] and len(item['sha256']) == 64 for item in result['capas'])
    assert 'key' not in json.dumps(result)
