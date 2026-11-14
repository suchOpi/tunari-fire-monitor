from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import httpx
import pytest
from app.config import Settings
from app.services.monitoring_state import source_status, apply_availability
from app.services import firms_client

NOW = datetime(2026, 11, 13, 16, tzinfo=timezone.utc)


@pytest.mark.parametrize('count,complete,expected', [(None, True, None), (0, False, None), (0, True, 0), (3, False, 3)])
def test_null_zero_and_partial_counts_are_distinct(count, complete, expected):
    result = apply_availability({'detecciones_hoy': count, 'alertas_activas': 0},
                                {'completa': complete, 'motor_alertas': {'disponible': False}})
    assert result['detecciones_hoy'] == expected
    assert result['alertas_activas'] is None


def test_unverified_district_never_claims_zero_and_evaluated_zero_is_valid():
    operation = {'completa': True, 'motor_alertas': {'disponible': True}}
    result = apply_availability({'detecciones_hoy': 0, 'alertas_activas': 0}, operation, district_verified=False)
    assert result['detecciones_hoy'] is None and result['alertas_activas'] == 0


@pytest.mark.parametrize('checked,published,expected', [(0, 1, 'ok'), (3.1, 1, 'ok'), (4, 1, 'atrasada'), (0, 25, 'atrasada')])
def test_successful_download_does_not_hide_stale_publication(checked, published, expected):
    record = SimpleNamespace(fecha=NOW-timedelta(hours=checked), estado='ok', detalle={
        'fuente_datos': 'nasa_keyless', 'datos_hasta': (NOW-timedelta(hours=published)).isoformat()})
    assert source_status(record, NOW, Settings())['estado'] == expected


def test_empty_global_file_without_publication_time_is_not_fresh():
    record = SimpleNamespace(fecha=NOW, estado='ok', detalle={'fuente_datos': 'nasa_keyless'})
    assert source_status(record, NOW, Settings())['estado'] == 'atrasada'


def test_http_backoff_is_bounded_and_does_not_retry_authorization(monkeypatch):
    sleeps, calls = [], []
    monkeypatch.setattr(firms_client.time, 'sleep', sleeps.append)
    monkeypatch.setattr(firms_client, 'get_settings', lambda: Settings(nrt_http_retries=2))
    def unstable():
        calls.append(1)
        if len(calls) < 3:
            raise httpx.ConnectError('offline')
        return 'ok'
    assert firms_client.request_with_backoff(unstable) == ('ok', 3)
    assert sleeps == [2, 4]
    sleeps.clear()
    def unauthorized():
        httpx.Response(403, request=httpx.Request('GET', 'https://example.org')).raise_for_status()
    with pytest.raises(httpx.HTTPStatusError):
        firms_client.request_with_backoff(unauthorized)
    assert sleeps == []
