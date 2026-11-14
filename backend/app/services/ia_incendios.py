"""Regresión Poisson estacional entrenada localmente, sin servicios externos."""
import math
from datetime import timedelta
from statistics import mean

VERSION = 'poisson-estacional-v1'


def variables(day):
    angle = 2 * math.pi * (day.timetuple().tm_yday - 1) / 365.2425
    return [1, math.sin(angle), math.cos(angle), math.sin(2 * angle), math.cos(2 * angle)]


def estimar(weights, day):
    return math.exp(max(-12, min(8, sum(w * x for w, x in zip(weights, variables(day))))))


def entrenar(samples):
    weights = [math.log(max(.001, mean(n for _, n in samples))), 0, 0, 0, 0]
    rows = [(variables(day), count) for day, count in samples]
    for _ in range(300):
        gradient = [0.0] * 5
        for values, observed in rows:
            predicted = math.exp(max(-12, min(8, sum(w * x for w, x in zip(weights, values)))))
            for j in range(5):
                gradient[j] += (predicted - observed) * values[j]
        change = [.12 * (g / len(rows) + (.01 * weights[j] if j else 0)) for j, g in enumerate(gradient)]
        weights = [w - max(-.3, min(.3, delta)) for w, delta in zip(weights, change)]
        if max(map(abs, change)) < 1e-7:
            break
    return weights


def deviance(actual, predicted):
    return mean(2 * (y * math.log(y / max(p, 1e-12)) - y + p if y else p) for y, p in zip(actual, predicted))


def analizar(samples, today):
    years = sorted({day.year for day, _ in samples})
    base = {'version': VERSION, 'metodo': 'Regresión Poisson con dos armónicos anuales y regularización L2',
            'ejecucion': 'Local, CPU, bajo demanda; sin claves ni llamadas a modelos externos',
            'objetivo': 'Eventos satelitales MODIS por día; no probabilidad de incendio confirmado',
            'variables': ['seno anual', 'coseno anual', 'seno semestral', 'coseno semestral'],
            'dias': len(samples), 'anios': years, 'pronostico': [],
            'limitaciones': ['No incorpora viento, lluvia, humedad ni combustible.',
                             'Las detecciones dependen de sobrevuelos y nubes; un cero no acredita ausencia de fuego.',
                             'Los registros MODIS no son directamente comparables con VIIRS.',
                             'Estimación exploratoria; requiere verificación de campo.']}
    if len(years) < 3 or len(samples) < 730 or sum(n for _, n in samples) < 20:
        return {**base, 'estado': 'datos_insuficientes', 'motivo': 'Se requieren al menos 3 años, 730 días con archivo MODIS completo y 20 eventos.'}
    train = [(d, n) for d, n in samples if d.year < years[-1]]
    validation = [(d, n) for d, n in samples if d.year == years[-1]]
    if len(validation) < 300 or len(train) < 600:
        return {**base, 'estado': 'datos_insuficientes', 'motivo': 'Falta cobertura temporal suficiente para separar entrenamiento y validación.'}
    weights = entrenar(train)
    values = [n for _, n in validation]
    predictions = [estimar(weights, d) for d, _ in validation]
    average = mean(n for _, n in train)
    score, reference = deviance(values, predictions), deviance(values, [average] * len(values))
    evaluation = {'entrenamiento': [str(train[0][0]), str(train[-1][0])],
                  'validacion': [str(validation[0][0]), str(validation[-1][0])],
                  'dias_validacion': len(validation), 'eventos_validacion': sum(values),
                  'mae_modelo': round(mean(abs(a - b) for a, b in zip(values, predictions)), 4),
                  'mae_base': round(mean(abs(a - average) for a in values), 4),
                  'devianza_modelo': round(score, 4), 'devianza_base': round(reference, 4),
                  'supera_base': score < reference, 'base': 'Promedio diario del período de entrenamiento'}
    fitted = entrenar(samples)
    forecasts = []
    for week in range(4):
        start = today + timedelta(days=week * 7)
        forecasts.append({'desde': str(start), 'hasta': str(start + timedelta(days=6)),
                          'eventos_modis_esperados': round(sum(estimar(fitted, start + timedelta(days=i)) for i in range(7)), 2)})
    return {**base, 'estado': 'entrenado', 'validacion': evaluation, 'pronostico': forecasts,
            'coeficientes': [round(w, 6) for w in fitted],
            'motivo': 'Modelo estacional entrenado y contrastado con el último año disponible.'}
