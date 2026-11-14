import httpx
import pytest
from app.config import Settings
from app.services import firms_client, gamc_client
from app.services.ingest_service import normalizar
from app.workers import ingesta_nrt

BBOX = (-66.5, -17.6, -65.8, -17.1)
HEADER = 'latitude,longitude,acq_date,acq_time,confidence,bright_ti4,frp\n'
CSV = HEADER + '-17.35,-66.17,2026-11-11,0900,n,340,12\n-10,-60,2026-11-11,1000,h,350,20\n'


def test_keyless_filters_bbox_and_preserves_unknown_type():
    batch = firms_client.parse_keyless(CSV.splitlines(), BBOX)
    assert batch['filas_globales'] == 2 and len(batch['rows']) == 1
    assert batch['columna_type'] is False and batch['sin_type'] == 1
    item = normalizar(batch['rows'][0], 'VIIRS_NOAA20_NRT', 'nrt')
    assert item['brightness_k'] == 340
    assert item['confidence'] == 'n' and item['confidence_score'] == 70
    assert item['candidata'] is False and item['revision_manual'] is True
    assert item['posible_oclusion'] is False


def test_keyless_excludes_nonvegetation_when_type_present():
    body = HEADER.rstrip() + ',type\n-17.35,-66.17,2026-11-11,0900,n,340,12,2\n'
    result = firms_client.parse_keyless(body.splitlines(), BBOX)
    assert result['rows'] == [] and result['excluidas_type'] == 1


@pytest.mark.parametrize('level,score,candidate', [('l', 30, True), ('n', 70, False), ('h', 90, False), ('90', None, True)])
def test_viirs_alerts_use_text_not_numeric_storage(level, score, candidate):
    row = firms_client.parse_keyless(CSV.splitlines(), BBOX)['rows'][0]
    row['confidence'] = level
    item = normalizar(row, 'VIIRS_SNPP_NRT', 'nrt')
    assert item['confidence_score'] == score and item['candidata'] is candidate


def test_modis_unified_temperature_and_original_score():
    row = firms_client.parse_keyless(CSV.splitlines(), BBOX)['rows'][0]
    row.update(brightness='321', confidence='85')
    item = normalizar(row, 'MODIS_NRT', 'nrt')
    assert item['brightness_k'] == 321 and item['confidence_score'] == 85


def test_partial_keyless_outage_does_not_erase_other_products(monkeypatch):
    calls = []
    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(404 if 'noaa-21' in str(request.url) else 200, text=CSV)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(firms_client.httpx, 'stream', client.stream)
        result = firms_client.fetch_nrt_keyless(BBOX)
    assert len(calls) == 3 and all(url.endswith('_24h.csv') for url in calls)
    assert 'VIIRS_SNPP_NRT' not in result
    assert result['VIIRS_NOAA21_NRT']['estado'] == 'error'
    assert len(result['VIIRS_NOAA20_NRT']['rows']) == 1


@pytest.mark.parametrize('key,provider', [('', 'nasa_keyless'), ('test-key', 'nasa_mapkey')])
def test_worker_never_mixes_keyless_and_area_in_one_run(monkeypatch, key, provider):
    calls = []
    monkeypatch.setattr(ingesta_nrt, 'fetch_nrt_keyless', lambda *_: calls.append('keyless') or {})
    monkeypatch.setattr(ingesta_nrt, 'fetch_area', lambda *_: calls.append('mapkey') or [])
    assert ingesta_nrt.obtener_lotes(Settings(firms_map_key=key))[0] == provider
    assert set(calls) == ({'mapkey'} if key else {'keyless'})


def test_gamc_failure_returns_none_and_suppresses_repeat_requests(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(gamc_client, 'get_settings', lambda: Settings(gamc_wms_key='test-key', data_dir=tmp_path))
    calls = []
    def get(*args, **kwargs):
        calls.append(kwargs['timeout'])
        return httpx.Response(502, request=httpx.Request('GET', 'https://example.org'))
    monkeypatch.setattr(gamc_client.httpx, 'get', get)
    assert gamc_client.fetch_wms('distritos', {'REQUEST': 'GetMap'}) is None
    assert gamc_client.fetch_wms('cota2750', {'REQUEST': 'GetMap'}) is None
    assert calls == [5]
    assert caplog.text.count('GAMC 502, usando fallback NASA') == 1
