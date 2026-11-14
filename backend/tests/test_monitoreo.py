from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import httpx
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import app
from app.services import gamc_client, live_firms

NOW = datetime(2026, 11, 11, 12, tzinfo=timezone.utc)
HEADER = 'latitude,longitude,acq_date,acq_time,satellite,confidence,frp,brightness\n'
CSV = HEADER + '-17.35,-66.17,2026-11-11,0900,T,76,8.83,317.24\n'
BBOX = (-66.5, -17.6, -65.8, -17.1)


def state(points=None, status='ok', modified=None):
    return {'ultimo_intento': NOW.isoformat(), 'fuentes': {'modis': {
        'estado': status, 'producto': 'MODIS_NRT', 'consultado_en': NOW.isoformat(),
        'modificado_en': (modified or NOW).isoformat(), 'datos_hasta': NOW.isoformat(),
        'detecciones': points or []}}}


def filters(district=None):
    return SimpleNamespace(inicio=NOW - timedelta(days=6), fin=NOW + timedelta(days=1), distrito=district)


def test_public_csv_preserves_measurement_time_and_candidate():
    points, latest = live_firms.parse_csv(CSV, 'MODIS_NRT', BBOX)
    assert len(points) == 1 and points[0]['fecha'] == '2026-11-11T09:00:00+00:00'
    assert points[0]['satelite'] == 'Terra' and points[0]['frp'] == 8.83
    assert points[0]['candidata'] is True and points[0]['en_tunari'] is None
    assert latest == points[0]['fecha']


def test_public_csv_excludes_distant_points_and_deduplicates():
    body = CSV + '-17.35,-66.17,2026-11-11,0900,T,76,8.83,317.24\n' + '-10,-60,2026-11-11,1000,T,99,30,330\n'
    points, latest = live_firms.parse_csv(body, 'MODIS_NRT', BBOX)
    assert len(points) == 1
    assert latest.endswith('10:00:00+00:00')


def test_empty_valid_csv_is_different_from_error_document():
    assert live_firms.parse_csv(HEADER, 'MODIS_NRT', BBOX) == ([], None)
    with pytest.raises(ValueError):
        live_firms.parse_csv('<html>Unavailable</html>', 'MODIS_NRT', BBOX)


@pytest.mark.parametrize('url', ['https://example.org/test_7d.csv', '//example.org/test_7d.csv',
                                'http://firms.modaps.eosdis.nasa.gov/data/active_fire/test_7d.csv', '/api/unknown_7d.csv'])
def test_catalog_cannot_redirect_to_arbitrary_sources(url):
    with pytest.raises(ValueError):
        live_firms.csv_url(url)


def test_real_empty_response_remains_empty_without_mock(monkeypatch):
    monkeypatch.setattr(live_firms, 'snapshot', lambda: state())
    result = live_firms.monitor(filters(), NOW)
    assert result['estado'] == 'ok' and result['demo'] is False
    assert result['detecciones'] == [] and result['alertas'] == []
    assert result['estadisticas']['detecciones_hoy'] == 0
    assert result['estadisticas']['alertas_activas'] is None


def test_failed_download_does_not_report_zero_or_fake_points(monkeypatch):
    monkeypatch.setattr(live_firms, 'snapshot', lambda: {'ultimo_intento': NOW.isoformat(), 'fuentes': {}, 'error_catalogo': 'Fallo'})
    result = live_firms.monitor(filters(), NOW)
    assert result['estado'] == 'no_disponible'
    assert result['estadisticas']['detecciones_hoy'] is None and result['detecciones'] == []


def test_old_dataset_marked_stale_even_after_successful_download(monkeypatch):
    monkeypatch.setattr(live_firms, 'snapshot', lambda: state(modified=NOW - timedelta(hours=25)))
    result = live_firms.monitor(filters(), NOW)
    assert result['estado'] == 'parcial' and result['estadisticas']['fuentes']['modis']['estado'] == 'atrasada'


def test_previous_observations_retained_with_error_provenance(monkeypatch):
    points, _ = live_firms.parse_csv(CSV, 'MODIS_NRT', BBOX)
    monkeypatch.setattr(live_firms, 'snapshot', lambda: state(points, 'error'))
    result = live_firms.monitor(filters(), NOW)
    assert result['estado'] == 'parcial'
    assert result['detecciones'][0]['fuente_estado'] == 'error'


def test_outage_with_empty_previous_cache_does_not_claim_zero_today(monkeypatch):
    monkeypatch.setattr(live_firms, 'snapshot', lambda: state(status='error'))
    result = live_firms.monitor(filters(), NOW)
    assert result['estadisticas']['detecciones_hoy'] is None


def test_district_filter_does_not_assign_unknown_points(monkeypatch):
    points, _ = live_firms.parse_csv(CSV, 'MODIS_NRT', BBOX)
    monkeypatch.setattr(live_firms, 'snapshot', lambda: state(points))
    result = live_firms.monitor(filters(13), NOW)
    assert result['detecciones'] == []
    assert any('sin distrito' in message for message in result['avisos'])


def test_gamc_district_uses_published_attribute(monkeypatch):
    monkeypatch.setattr(gamc_client, 'feature_info', lambda *a: [{'Distrito': 'D10', 'Comuna': 'ADELA ZAMUDIO'}])
    assert gamc_client.district_at(-66.1568, -17.3895) == 10
    monkeypatch.setattr(gamc_client, 'feature_info', lambda *a: [{'Distrito': 'D10'}, {'Distrito': 'D11'}])
    assert gamc_client.district_at(-66.1568, -17.3895) is None


def test_wms_xml_exception_is_never_accepted_as_png(monkeypatch, tmp_path):
    monkeypatch.setattr(gamc_client, 'get_settings', lambda: Settings(gamc_wms_key='test-key', data_dir=tmp_path))
    monkeypatch.setattr(gamc_client.httpx, 'get', lambda *a, **kw: httpx.Response(200, text='<ServiceException/>', request=httpx.Request('GET', 'https://example.org')))
    assert gamc_client.fetch_wms('distritos', {'REQUEST': 'GetMap'}) is None
    assert gamc_client.availability()['disponible'] is False
    assert 'test-key' not in str(gamc_client.metadata())


def test_metadata_never_discloses_key(monkeypatch):
    monkeypatch.setattr(gamc_client, 'get_settings', lambda: Settings(gamc_wms_key='test-key'))
    response = TestClient(app).get('/api/capas')
    assert response.status_code == 200 and 'test-key' not in response.text
    assert len(response.json()['servicios']) == 3


def test_wms_rejects_unknown_layers_and_invalid_bbox():
    client = TestClient(app)
    assert client.get('/api/gamc/wms?capa=unknown').status_code == 422
    assert client.get('/api/gamc/wms?capa=distritos&BBOX=nan,0,1,1&WIDTH=256&HEIGHT=256').status_code == 422


def test_no_database_mode_rejects_mutations(monkeypatch):
    import app.api.deps as deps
    monkeypatch.setattr(deps, 'get_settings', lambda: Settings(database_enabled=False))
    assert TestClient(app).patch('/api/alertas/1', json={'estado': 'atendida'}).status_code == 503
