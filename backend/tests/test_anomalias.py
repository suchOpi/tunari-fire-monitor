from datetime import date, timedelta
from types import SimpleNamespace
import pytest
from app.services.anomalias import Climatologia, climatologia, dias_consecutivos, evaluar, factor_feedback, percentil, regimen
from app.services.ingest_service import normalizar
from app.services.alertas_service import anios_cubiertos
from app.services.firms_client import fetch_area
from app.config import Settings


def row(**overrides):
    return {'latitude': '-17.35', 'longitude': '-66.17', 'acq_date': '2025-08-06', 'acq_time': '0530',
            'frp': '24', 'confidence': '94', 'brightness': '330', 'satellite': 'Terra', **overrides}


def test_percentile_interpolated_not_maximum():
    assert percentil([0, 0, 0, 0, 100]) == pytest.approx(80)


def test_regime_transition_has_no_overlap():
    assert regimen(2011) == 'MODIS'
    assert regimen(2012) == 'MODIS+VIIRS'


def test_zero_years_count_in_occurrence_probability():
    baseline = climatologia([{'eventos': 0, 'frps': []}] * 19 + [{'eventos': 1, 'frps': [20]}])
    assert baseline.probabilidad == 0.05
    assert baseline.frp_media == 20
    assert baseline.anios == 20


def test_out_of_season_is_strictly_less_than_five_percent():
    baseline = Climatologia(20, 2, 20, 4, 24, 0.05)
    assert 'fuera_temporada' not in [s['senal'] for s in evaluar(1, 20, [], False, baseline)]


def test_missing_baseline_does_not_invent_statistical_alerts():
    assert evaluar(12, 999, [], False, None) == []
    assert evaluar(12, 999, [], False, Climatologia(2, 1, 1, 1, 1, 0)) == []


def test_no_current_events_means_no_fire_alert():
    assert evaluar(0, None, [], True, Climatologia(10, 0, 1, 0, 1, 0)) == []


def test_critical_does_not_require_history_or_change_with_feedback():
    assert evaluar(1, None, [], True, None, factor=1.5)[0]['nivel'] == 'critica'


def test_three_days_persistence_includes_duplicates_and_year_boundary():
    days = [date(2024, 12, 30), date(2024, 12, 31), date(2024, 12, 31), date(2025, 1, 1)]
    assert dias_consecutivos(days) == 3
    assert evaluar(1, None, days, False, None)[0]['nivel'] == 'media'


def test_non_consecutive_days_are_not_persistence():
    assert dias_consecutivos([date(2025, 1, 1), date(2025, 1, 3), date(2025, 1, 5)]) == 1


def test_five_days_escalate_to_high():
    days = [date(2025, 1, 1) + timedelta(days=i) for i in range(5)]
    assert evaluar(1, None, days, False, None)[0]['nivel'] == 'alta'


def test_intensity_explanation_contains_sigma():
    signals = evaluar(1, 34, [], False, Climatologia(6, 4, 10, 10, 30, 0.2))
    assert len(signals) == 1
    assert '2.40σ' in signals[0]['descripcion']


def test_zero_variance_does_not_divide_by_zero():
    signals = evaluar(1, 11, [], False, Climatologia(6, 4, 10, 0, 10, 0.2))
    assert 'dispersión histórica nula' in signals[0]['descripcion']


def test_feedback_requires_three_closed_and_is_capped():
    assert factor_feedback(2, 2) == 1
    assert factor_feedback(8, 10) == 1.4
    assert factor_feedback(10, 10) == 1.5


@pytest.mark.parametrize('confidence,candidate', [('80', True), ('80.1', False), ('0', True), ('100', False)])
def test_modis_confidence_is_strict(confidence, candidate):
    assert normalizar(row(confidence=confidence), 'MODIS_NRT', 'nrt')['candidata'] is candidate


@pytest.mark.parametrize('confidence,candidate', [('l', True), ('low', True), ('n', False), ('nominal', False), ('h', False), ('high', False), ('', True)])
def test_viirs_confidence(confidence, candidate):
    item = normalizar(row(confidence=confidence, bright_ti4='345'), 'VIIRS_SNPP_NRT', 'nrt')
    assert item['candidata'] is candidate
    assert item['bright_ti4'] == 345 and item['resolucion'] == 375


@pytest.mark.parametrize('kind,discarded', [('0', False), ('1', True), ('2', True), ('3', True)])
def test_nonvegetation_excluded(kind, discarded):
    assert normalizar(row(type=kind), 'MODIS_SP', 'historico')['descartada'] is discarded


def test_unknown_type_keeps_manual_review():
    assert normalizar(row(), 'MODIS_NRT', 'nrt')['revision_manual'] is True
    assert normalizar(row(type='0'), 'MODIS_SP', 'historico')['revision_manual'] is False


def test_standard_and_nrt_share_identity():
    assert normalizar(row(), 'MODIS_NRT', 'nrt')['clave'] == normalizar(row(type='0'), 'MODIS_SP', 'historico')['clave']


def test_utc_time_zero_padding():
    item = normalizar(row(acq_time='5'), 'MODIS_NRT', 'nrt')
    assert item['fecha'].hour == 0 and item['fecha'].minute == 5 and item['fecha'].utcoffset().total_seconds() == 0


@pytest.mark.parametrize('overrides', [{'latitude': 'nan'}, {'frp': '-1'}, {'acq_time': '2460'}, {'confidence': '101'}, {'type': '7'}])
def test_malformed_values_rejected(overrides):
    with pytest.raises(ValueError):
        normalizar(row(**overrides), 'MODIS_NRT', 'nrt')


def test_partial_archive_never_counts_as_coverage():
    item = SimpleNamespace(completa=False, estado='ok', fuente='MODIS_SP', inicio=date(2001, 1, 1), fin=date(2001, 12, 31))
    assert anios_cubiertos([item], 10, 2011) == []
    item.completa = True
    assert anios_cubiertos([item], 10, 2011) == [2001]
    assert anios_cubiertos([item], 10, 2025) == []


def test_incomplete_sensor_fleet_does_not_count_as_coverage():
    item = SimpleNamespace(completa=True, estado='ok', fuente='MODIS_SP', inicio=date(2020, 1, 1), fin=date(2020, 12, 31))
    assert anios_cubiertos([item], 10, 2025) == []


def test_api_day_limit_and_worker_frequency():
    with pytest.raises(ValueError): fetch_area('MODIS_NRT', 6)
    with pytest.raises(ValueError): fetch_area('invented', 1)
    with pytest.raises(ValueError): Settings(nrt_interval_hours=2)


def test_api_contract_lists_all_requested_routes():
    from app.main import app
    paths = app.openapi()['paths']
    assert all(f'/api/{route}' in paths for route in ['salud', 'detecciones', 'eventos', 'alertas', 'estadisticas'])


def test_annual_zeros_require_complete_archive():
    from app.api.routes.estadisticas import cobertura_anual
    item = SimpleNamespace(completa=True, estado='ok', fuente='MODIS_SP', inicio=date(2001, 1, 1), fin=date(2001, 12, 31))
    assert cobertura_anual(2001, [item], 2026)
    item.completa = False
    assert not cobertura_anual(2001, [item], 2026)
    assert not cobertura_anual(2026, [item], 2026)


def test_firms_plaintext_error_is_not_an_empty_success(monkeypatch):
    import httpx
    import app.services.firms_client as client
    monkeypatch.setattr(client, 'get_settings', lambda: Settings(firms_map_key='unit-test-not-a-secret'))
    monkeypatch.setattr(client.httpx, 'get', lambda *a, **k: httpx.Response(200, text='Invalid MAP_KEY.', request=httpx.Request('GET', 'https://example.org')))
    with pytest.raises(RuntimeError, match='CSV válido'):
        client.fetch_area('MODIS_NRT')


def test_firms_genuine_empty_response(monkeypatch):
    import httpx
    import app.services.firms_client as client
    monkeypatch.setattr(client, 'get_settings', lambda: Settings(firms_map_key='unit-test-not-a-secret'))
    monkeypatch.setattr(client.httpx, 'get', lambda *a, **k: httpx.Response(200, text='No data', request=httpx.Request('GET', 'https://example.org')))
    assert client.fetch_area('MODIS_NRT') == []
