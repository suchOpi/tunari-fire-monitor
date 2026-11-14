from datetime import date, timedelta
from app.services.ia_incendios import analizar, entrenar, estimar


def series(start, end):
    result = []
    while start <= end:
        result.append((start, int(start.month in (7,8,9) and start.day % 2 == 0)))
        start += timedelta(days=1)
    return result


def test_ia_requires_temporal_coverage_and_events():
    result = analizar(series(date(2025,1,1),date(2025,12,30)), date(2026,1,1))
    assert result['estado'] == 'datos_insuficientes' and result['pronostico'] == []
    empty = [(d,0) for d,_ in series(date(2021,1,1),date(2025,12,30))]
    assert analizar(empty,date(2026,1,1))['estado'] == 'datos_insuficientes'


def test_seasonal_model_learns_and_validates_last_year_only():
    samples = series(date(2022,1,1),date(2025,12,30))
    result = analizar(samples, date(2026,7,1))
    assert result['estado'] == 'entrenado'
    assert result['validacion']['entrenamiento'] == ['2022-01-01','2024-12-31']
    assert result['validacion']['validacion'] == ['2025-01-01','2025-12-30']
    assert result['validacion']['devianza_modelo'] < result['validacion']['devianza_base']
    assert len(result['pronostico']) == 4
    weights = entrenar(samples)
    assert estimar(weights,date(2026,8,15)) > estimar(weights,date(2026,2,15))
    assert all(p['eventos_modis_esperados'] >= 0 for p in result['pronostico'])
    assert 'probabilidad_incendio' not in result
