from contextlib import nullcontext
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from app.config import Settings
from app.main import app
from app.api.routes import monitoreo


def test_database_mode_never_uses_public_downloader(monkeypatch):
    monkeypatch.setattr(monitoreo, 'get_settings', lambda: Settings(database_enabled=True))
    db = object()
    monkeypatch.setattr(monitoreo, 'SessionLocal', lambda: nullcontext(db))
    calls = []

    def persisted(session, filters):
        calls.append(session)
        return {'demo': False, 'modo': 'postgis', 'detecciones': []}

    def public(*args):
        raise AssertionError('El modo PostGIS no debe descargar archivos regionales')

    monkeypatch.setattr(monitoreo, 'persistent_monitor', persisted)
    monkeypatch.setattr(monitoreo.live_firms, 'monitor', public)
    response = TestClient(app).get('/api/monitoreo')
    assert response.status_code == 200 and response.json()['modo'] == 'postgis'
    assert calls == [db]


def test_database_failure_is_503_without_fallback(monkeypatch):
    monkeypatch.setattr(monitoreo, 'get_settings', lambda: Settings(database_enabled=True))

    def unavailable():
        raise OperationalError('connect', {}, Exception('unavailable'))

    monkeypatch.setattr(monitoreo, 'SessionLocal', unavailable)
    response = TestClient(app).get('/api/monitoreo')
    assert response.status_code == 503
    assert response.json() == {'detail': 'PostGIS no está disponible'}


def test_worker_defaults_to_one_cycle(monkeypatch):
    from app.workers import ingesta_nrt as worker
    calls = []
    monkeypatch.setattr('sys.argv', ['ingesta_nrt'])
    monkeypatch.setattr(worker, 'get_settings', lambda: Settings(firms_map_key='test-key'))
    monkeypatch.setattr(worker, 'init_db', lambda: None)
    monkeypatch.setattr(worker, 'ciclo', lambda: calls.append('cycle'))
    monkeypatch.setattr(worker.time, 'sleep', lambda *_: pytest.fail('El worker no debe repetir la ingesta'))
    worker.main()
    assert calls == ['cycle']


def test_worker_without_key_runs_once_with_keyless_fallback(monkeypatch):
    from app.workers import ingesta_nrt as worker
    monkeypatch.setattr('sys.argv', ['ingesta_nrt'])
    monkeypatch.setattr(worker, 'get_settings', lambda: Settings(firms_map_key=''))
    calls = []
    monkeypatch.setattr(worker, 'init_db', lambda: None)
    monkeypatch.setattr(worker, 'ciclo', lambda: calls.append('keyless'))
    worker.main()
    assert calls == ['keyless']
