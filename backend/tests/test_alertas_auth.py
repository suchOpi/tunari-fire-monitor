import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import app

BODY = {'estado': 'atendida'}


def client_with(monkeypatch, token):
    import app.api.deps as deps
    monkeypatch.setattr(deps, 'get_settings', lambda: Settings(database_enabled=False, api_token=token))
    return TestClient(app)


def test_mutations_are_disabled_when_no_token_is_configured(monkeypatch):
    response = client_with(monkeypatch, '').patch('/api/alertas/1', json=BODY)
    assert response.status_code == 503 and 'API_TOKEN' in response.json()['detail']


@pytest.mark.parametrize('headers', [{}, {'X-API-Token': 'incorrecto'}, {'Authorization': 'Bearer incorrecto'}, {'Authorization': 'Basic s3cret'}])
def test_mutations_reject_missing_or_wrong_token(monkeypatch, headers):
    client = client_with(monkeypatch, 's3cret')
    assert client.patch('/api/alertas/1', json=BODY, headers=headers).status_code == 401
    assert client.post('/api/alertas/1/confirmar', headers=headers).status_code == 401


@pytest.mark.parametrize('headers', [{'X-API-Token': 's3cret'}, {'Authorization': 'Bearer s3cret'}])
def test_mutations_accept_the_configured_token(monkeypatch, headers):
    client = client_with(monkeypatch, 's3cret')
    # El token es válido: la petición llega a la base de datos, deshabilitada en esta prueba.
    assert client.patch('/api/alertas/1', json=BODY, headers=headers).status_code == 503
    assert client.post('/api/alertas/1/confirmar', headers=headers).status_code == 503


def test_reading_alerts_does_not_require_a_token(monkeypatch):
    client = client_with(monkeypatch, 's3cret')
    assert client.get('/api/alertas').status_code != 401
