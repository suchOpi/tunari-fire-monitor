import os
import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import Session
from app.database import Base
from app.models import Deteccion, Evento
from app.services.ingest_service import ingerir

pytestmark = pytest.mark.postgis


@pytest.fixture
def db():
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        pytest.skip('Configura TEST_DATABASE_URL con una base PostGIS de pruebas')
    engine = create_engine(url, connect_args={'connect_timeout': 5})
    schema = f'test_tunari_{uuid.uuid4().hex}'
    with engine.connect() as connection:
        connection.execute(text('SELECT PostGIS_Version()'))
        connection.execute(text(f'CREATE SCHEMA {schema}'))
        connection.execute(text(f'SET search_path TO {schema}, public'))
        connection = connection.execution_options(schema_translate_map={None: schema})
        Base.metadata.create_all(connection)
        connection.commit()
        session = Session(connection)
        try:
            yield session
        finally:
            session.rollback()
            session.close()
            connection.execute(text('SET search_path TO public'))
            connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))
            connection.commit()
    engine.dispose()


def row(**extra):
    return {'latitude':'-17.35','longitude':'-66.17','acq_date':'2025-08-06','acq_time':'1300',
            'satellite':'Terra','confidence':'94','frp':'30', **extra}


def test_repeated_ingest_and_standard_replacement(db):
    ingerir(db, [row()], 'MODIS_NRT')
    ingerir(db, [row()], 'MODIS_NRT')
    assert db.scalar(select(func.count()).select_from(Deteccion)) == 1
    assert db.scalar(select(func.count()).select_from(Evento)) == 1
    ingerir(db, [row(type='2')], 'MODIS_SP', 'historico')
    assert db.scalar(select(Deteccion)).descartada is True
    assert db.scalar(select(func.count()).select_from(Evento)) == 0
    ingerir(db, [row()], 'MODIS_NRT')
    assert db.scalar(select(Deteccion)).origen == 'historico'


def test_mixed_sensors_group_but_distant_days_do_not(db):
    ingerir(db, [row()], 'MODIS_NRT')
    ingerir(db, [row(satellite='N', confidence='n', latitude='-17.351', longitude='-66.171')], 'VIIRS_SNPP_NRT')
    event = db.scalar(select(Evento))
    assert event.sensores_presentes == ['MODIS', 'VIIRS']
    assert event.num_detecciones == 2 and event.sensor_principal == 'VIIRS'
    ingerir(db, [row(acq_date='2025-08-09')], 'MODIS_NRT')
    assert db.scalar(select(func.count()).select_from(Evento)) == 2


def test_critical_alert_is_idempotent_and_requires_review(db, monkeypatch):
    from geoalchemy2.elements import WKTElement
    from app.models import UnidadEspacial, Alerta
    from app.services.alertas_service import evaluar_actualizacion
    from app.services import monitoring_state
    from app.config import Settings
    from app.models import Ingesta
    monkeypatch.setattr(monitoring_state, 'get_settings', lambda: Settings(alerts_evaluation_enabled=True, firms_sources='MODIS_NRT'))
    polygon = WKTElement('POLYGON((-66.2 -17.4,-66.1 -17.4,-66.1 -17.3,-66.2 -17.3,-66.2 -17.4))', srid=4326)
    for district in range(1, 16):
        db.add(UnidadEspacial(id=f'test:district:{district}', distrito=district, clase='distrito', nombre='Solo prueba', verificada=True, geom=polygon))
    db.add(UnidadEspacial(id='test:park', clase='tunari', nombre='Parque de prueba', verificada=True,
                         geom=WKTElement('POLYGON((-66.2 -17.4,-66.1 -17.4,-66.1 -17.3,-66.2 -17.3,-66.2 -17.4))', srid=4326)))
    db.flush()
    ingerir(db, [row()], 'MODIS_NRT')
    now = datetime(2025, 8, 6, 16, tzinfo=timezone.utc)
    db.add(Ingesta(clave='test:fresh', fuente='MODIS_NRT', origen='nrt', inicio=now.date(), fin=now.date(), estado='ok', fecha=now, detalle={'fuente_datos':'nasa_mapkey'}))
    db.flush()
    evaluar_actualizacion(db, now)
    evaluar_actualizacion(db, now)
    alerts = db.scalars(select(Alerta)).all()
    assert len(alerts) == 1
    assert alerts[0].nivel == 'critica' and alerts[0].revision_manual is True


def test_persistent_monitor_and_acceptance_routes_use_saved_rows(db, monkeypatch):
    from datetime import date
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.deps import get_db, Filtros
    from app.config import Settings
    from app.models import Ingesta
    from app.services import persistent_monitor

    now = datetime(2025, 8, 6, 16, tzinfo=timezone.utc)
    ingerir(db, [row(confidence='n', satellite='N')], 'VIIRS_SNPP_NRT')
    db.add(Ingesta(clave='test:ingesta', fuente='VIIRS_SNPP_NRT', origen='nrt',
                   inicio=now.date(), fin=now.date(), estado='ok', fecha=now))
    db.flush()
    monkeypatch.setattr(persistent_monitor, 'get_settings', lambda: Settings(
        firms_sources='VIIRS_SNPP_NRT', firms_map_key='test-key', database_enabled=True, nrt_scheduler_enabled=False))
    filters = Filtros(dias=2, distrito=None, desde=date(2025, 8, 5), hasta=date(2025, 8, 6))
    result = persistent_monitor.monitor(db, filters, now)
    assert result['demo'] is False and result['modo'] == 'postgis'
    assert len(result['detecciones']) == 1 and len(result['eventos']) == 1
    assert result['estado'] == 'ok' and result['proxima_actualizacion'] is None
    assert result['estadisticas']['geometrias_verificadas'] == 0
    assert result['motor_alertas']['disponible'] is False

    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        response = client.get('/detecciones/recientes?desde=2025-08-05&hasta=2025-08-06')
        assert response.status_code == 200
        assert response.json()[0]['sensor'] == 'VIIRS_SNPP'
        assert client.get('/alertas').json() == []
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_empty_database_is_not_presented_as_zero_fire_activity(db, monkeypatch):
    from datetime import date
    from app.api.deps import Filtros
    from app.config import Settings
    from app.services import persistent_monitor
    monkeypatch.setattr(persistent_monitor, 'get_settings', lambda: Settings(firms_map_key=''))
    filters = Filtros(dias=2, distrito=None, desde=date(2025, 8, 5), hasta=date(2025, 8, 6))
    result = persistent_monitor.monitor(db, filters)
    assert result['estado'] == 'no_disponible' and result['detecciones'] == []
    assert result['estadisticas']['detecciones_hoy'] is None
    assert result['estadisticas']['alertas_activas'] is None
    assert all(s['estado'] == 'sin_ingesta' for s in result['estadisticas']['fuentes'].values())


def test_fresh_empty_batch_zero_stale_null_and_geometry_guard(db, monkeypatch):
    from datetime import timedelta
    from app.models import Ingesta, Alerta, EvaluacionUnidad
    from app.api.deps import Filtros
    from app.config import Settings
    from app.services import persistent_monitor, monitoring_state
    from app.services.alertas_service import evaluar_actualizacion
    settings = Settings(firms_sources='MODIS_NRT', firms_map_key='test-key', nrt_scheduler_enabled=True, alerts_evaluation_enabled=True)
    monkeypatch.setattr(persistent_monitor, 'get_settings', lambda: settings)
    monkeypatch.setattr(monitoring_state, 'get_settings', lambda: settings)
    now = datetime.now(timezone.utc)
    db.add(Ingesta(clave='test:empty', fuente='MODIS_NRT', origen='nrt', inicio=now.date(), fin=now.date(), estado='ok', fecha=now, detalle={'fuente_datos':'nasa_mapkey'}))
    monitoring_state.registrar(db, 'worker:last_scheduled', now)
    monitoring_state.registrar(db, 'worker:last_attempt', now)
    db.flush()
    filters = Filtros(dias=1, distrito=None, desde=None, hasta=None)
    result = persistent_monitor.monitor(db, filters, now)
    assert result['monitoreo']['estado'] == 'continuo'
    assert result['estadisticas']['detecciones_hoy'] == 0
    assert result['estadisticas']['alertas_activas'] is None
    assert result['proxima_actualizacion'] == (now + timedelta(hours=3)).isoformat()
    blocked = evaluar_actualizacion(db, now)
    assert blocked['estado'] == 'deshabilitada' and 'verificados' in blocked['motivo']
    assert db.scalar(select(func.count()).select_from(Alerta)) == 0
    assert db.scalar(select(func.count()).select_from(EvaluacionUnidad)) == 0
    later = persistent_monitor.monitor(db, filters, now + timedelta(hours=4))
    assert later['monitoreo']['estado'] == 'atrasado'
    assert later['estadisticas']['detecciones_hoy'] is None


def test_evaluator_freshness_and_feature_flag(db, monkeypatch):
    from datetime import timedelta
    from geoalchemy2.elements import WKTElement
    from app.config import Settings
    from app.models import UnidadEspacial, Ingesta
    from app.services.monitoring_state import operational_state, registrar
    now = datetime.now(timezone.utc)
    polygon = WKTElement('POLYGON((-66.2 -17.4,-66.1 -17.4,-66.1 -17.3,-66.2 -17.3,-66.2 -17.4))', srid=4326)
    for number in range(1,16):
        db.add(UnidadEspacial(id=f'test:{number}', clase='distrito', distrito=number, nombre='Prueba', verificada=True, geom=polygon))
    db.add(UnidadEspacial(id='test:park', clase='tunari', nombre='Prueba', verificada=True, geom=polygon))
    db.add(Ingesta(clave='test:latest', fuente='MODIS_NRT', origen='nrt', inicio=now.date(), fin=now.date(), fecha=now, estado='ok', detalle={'fuente_datos':'nasa_mapkey'}))
    settings = Settings(firms_sources='MODIS_NRT', alerts_evaluation_enabled=True)
    registrar(db, 'evaluador:last_success', now-timedelta(hours=4))
    db.flush()
    assert not operational_state(db, settings, now)['motor_alertas']['disponible']
    registrar(db, 'evaluador:last_success', now)
    db.flush()
    assert operational_state(db, settings, now)['motor_alertas']['disponible']
    settings.alerts_evaluation_enabled = False
    assert not operational_state(db, settings, now)['motor_alertas']['disponible']


def test_keyless_provenance_and_deduplication_across_nasa_modes(db):
    sample = row(confidence='n', satellite='N20', bright_ti4='340')
    ingerir(db, [sample], 'VIIRS_NOAA20_NRT', provider='nasa_keyless')
    detection = db.scalar(select(Deteccion))
    assert detection.fuente == 'nasa_keyless' and detection.producto == 'VIIRS_NOAA20_NRT'
    assert detection.brightness_k == 340 and detection.confidence_score == 70
    assert detection.confidence == 'n' and detection.candidata is False
    assert detection.posible_oclusion is False
    ingerir(db, [sample], 'VIIRS_NOAA20_NRT', provider='nasa_mapkey')
    assert db.scalar(select(func.count()).select_from(Deteccion)) == 1


def test_geography_collections_details_and_live_counts_with_cached_geometry(db, monkeypatch):
    from contextlib import nullcontext
    from geoalchemy2.elements import WKTElement
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.deps import get_db
    from app.api.routes import geografia
    from app.models import UnidadEspacial, Alerta
    for district in range(1, 16):
        west = -66.45 + district * .02
        db.add(UnidadEspacial(id=f'distrito:{district}', distrito=district, clase='distrito', nombre=f'Distrito {district}',
               propiedades={'demo': True}, verificada=False,
               geom=WKTElement(f'POLYGON(({west} -17.4,{west+.01} -17.4,{west+.01} -17.39,{west} -17.39,{west} -17.4))', srid=4326)))
    db.add(UnidadEspacial(id='tunari:test', clase='tunari', nombre='PNT de prueba', propiedades={'demo': True},
           geom=WKTElement('POLYGON((-66.5 -17.5,-66.3 -17.5,-66.3 -17.3,-66.5 -17.3,-66.5 -17.5))', srid=4326)))
    ingerir(db, [row(type='0', frp='10')], 'MODIS_SP', origin='historico')
    ingerir(db, [row(type='0', frp='30', satellite='N', confidence='n')], 'VIIRS_SNPP_SP', origin='historico')
    for detection in db.scalars(select(Deteccion)):
        detection.distrito = 5
        db.get(Evento, detection.evento_id).distrito = 5
    db.flush()
    geografia.geometrias_cache.cache_clear()
    monkeypatch.setattr(geografia, 'SessionLocal', lambda: nullcontext(db))
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        collection = client.get('/geografia/distritos').json()
        assert collection['type'] == 'FeatureCollection' and len(collection['features']) == 15
        assert all(f['properties']['area_km2'] > 0 and f['geometry']['type'] == 'Polygon' for f in collection['features'])
        fifth = next(f for f in collection['features'] if f['id'] == 5)
        assert fifth['properties']['eventos_historicos'] == 1
        assert fifth['properties']['alertas_activas'] is None
        assert fifth['properties']['ilustrativa'] is True and fifth['properties']['poblacion_aproximada'] is None
        db.add(Alerta(clave='geo:test', unidad_id='distrito:5', distrito=5, nivel='alta', senal='prueba',
                      descripcion='Solo prueba', latitude=-17.35, longitude=-66.17))
        db.flush()
        detail = client.get('/geografia/distrito/5').json()
        assert detail['properties']['alertas_activas'] is None
        assert detail['estadisticas']['eventos_por_anio'] == [{'anio': 2025, 'eventos': 1}]
        assert detail['estadisticas']['frp_promedio'] == 20
        assert detail['estadisticas']['sensores'] == ['MODIS', 'VIIRS']
        assert len(detail['estadisticas']['alertas_activas']) == 1
        park = client.get('/api/geografia/pnt').json()
        assert len(park['features']) == 1 and park['features'][0]['properties']['distritos_que_cruza'] > 0
        empty = client.get('/geografia/distrito/4').json()['estadisticas']
        assert empty['sensores'] == [] and empty['alertas_activas'] == [] and empty['eventos_por_anio'] == []
        assert geografia.geometrias_cache.cache_info().misses == 1
    finally:
        app.dependency_overrides.pop(get_db, None)
        geografia.geometrias_cache.cache_clear()


def test_missing_geography_does_not_return_sample_boundaries(db, monkeypatch):
    from contextlib import nullcontext
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.deps import get_db
    from app.api.routes import geografia
    geografia.geometrias_cache.cache_clear()
    monkeypatch.setattr(geografia, 'SessionLocal', lambda: nullcontext(db))
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        assert client.get('/geografia/distritos').json()['features'] == []
        assert client.get('/geografia/distrito/5').status_code == 404
        assert client.get('/geografia/distrito/16').status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)
        geografia.geometrias_cache.cache_clear()


def test_current_report_includes_nrt_separates_sensors_and_keeps_gaps(db):
    from datetime import date, timedelta
    from app.models import Ingesta
    from app.services.informes import informe
    now = datetime(2026, 11, 13, 20, tzinfo=timezone.utc)
    ingerir(db, [row(acq_date='2026-11-13', type='0')], 'MODIS_NRT')
    ingerir(db, [row(acq_date='2026-11-13', satellite='N21', confidence='n')], 'VIIRS_NOAA21_NRT')
    for source in ('MODIS_NRT', 'VIIRS_NOAA21_NRT'):
        db.add(Ingesta(clave='report-current:' + source, fuente=source, origen='nrt',
                       inicio=date(2026, 11, 12), fin=date(2026, 11, 13), fecha=now, estado='ok',
                       detalle={'fuente_datos': 'nasa_keyless', 'datos_hasta': (now-timedelta(hours=1)).isoformat()}))
    db.flush()
    result = informe(db, 2026, 2026, ambito='entorno', cached=False, now=now)
    assert result['eventos'] == 1 and result['detecciones'] == 1
    assert result['anual'][0]['cobertura'] == 'parcial'
    assert result['calendario'][0]['eventos'] is None
    assert result['calendario'][10]['eventos'] == 1 and result['calendario'][11]['cobertura'] == 'futuro'
    assert result['dias_cubiertos'] == 0 and result['frecuencia_por_30_dias'] is None
    assert result['ia']['dias'] == 0 and result['ia']['estado'] == 'datos_insuficientes'
    viirs = informe(db, 2026, 2026, ambito='entorno', sensor='VIIRS_NOAA21', cached=False, now=now)
    assert viirs['detecciones'] == 1 and viirs['sensor'] == 'VIIRS_NOAA21'
                                                                                          
    ingerir(db, [row(acq_date='2026-11-13', type='0')], 'MODIS_SP', 'historico')
    standard = informe(db, 2026, 2026, ambito='entorno', cached=False, now=now)
    assert standard['detecciones'] == 1 and standard['ia']['dias'] == 0
    assert standard['ultimos_eventos'][0]['provisional'] is False


def test_current_ai_comparison_uses_full_days_without_training_on_nrt(db, monkeypatch):
    from datetime import date, timedelta
    from app.models import Ingesta
    from app.services import informes
    now = datetime(2026, 11, 14, 10, tzinfo=timezone.utc)
    ingerir(db, [row(type='0')], 'MODIS_SP', 'historico')
    ingerir(db, [row(acq_date='2026-11-13', type='0')], 'MODIS_NRT')
    db.add(Ingesta(clave='ai-archive', fuente='MODIS_SP', origen='historico',
                   inicio=date(2025, 1, 1), fin=date(2025, 12, 31), completa=True))
    for index, stamp in enumerate((now-timedelta(hours=6), now)):
        db.add(Ingesta(clave=f'ai-nrt:{index}', fuente='MODIS_NRT', origen='nrt', fecha=stamp,
                       inicio=date(2026, 11, 13), fin=date(2026, 11, 14), estado='ok',
                       detalle={'fuente_datos':'nasa_keyless','datos_hasta':(stamp-timedelta(hours=1)).isoformat()}))
    db.flush()
    def model(samples, today):
        assert {day.year for day, _ in samples} == {2025}
        assert today == date(2026, 11, 14)
        return {'estado':'entrenado','coeficientes':[0, 0, 0, 0, 0]}
    monkeypatch.setattr(informes, 'analizar', model)
    result = informes.informe(db, 2025, 2026, ambito='entorno', cached=False, now=now)
    comparison = result['ia']['seguimiento_actual']
    assert comparison['dias_comparables'] == 1
    assert comparison['eventos_observados'] == 1 and comparison['eventos_esperados'] == 1


def test_current_report_cache_advances_and_zero_requires_coverage(db):
    from datetime import date, timedelta
    from app.models import Ingesta
    from app.services.informes import informe, clear_cache
    now = datetime(2026, 11, 13, 20, tzinfo=timezone.utc)
    clear_cache()
    try:
        missing = informe(db, 2026, 2026, ambito='entorno', now=now)
        assert missing['eventos'] is None and all(h['detecciones'] is None for h in missing['horaria'])
        db.add(Ingesta(clave='report-zero', fuente='MODIS_NRT', origen='nrt', inicio=date(2026, 11, 12),
                       fin=date(2026, 11, 13), fecha=now, estado='ok',
                       detalle={'fuente_datos': 'nasa_keyless', 'datos_hasta': (now-timedelta(hours=1)).isoformat()}))
        db.flush()
        known = informe(db, 2026, 2026, ambito='entorno', now=now)
        assert known['eventos'] == 0 and known['calendario'][10]['eventos'] == 0
        assert known['calendario'][0]['eventos'] is None and known['mensual'][10]['eventos_por_30_dias'] is None
        district = informe(db, 2026, 2026, distrito=5, ambito='entorno', cached=False, now=now)
        assert district['eventos'] is None and all(h['detecciones'] is None for h in district['horaria'])
    finally:
        clear_cache()


def test_report_route_allows_current_year_and_exports_coverage(db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.deps import get_db
    from app.services.informes import clear_cache, TZ
    current = datetime.now(TZ).year
    clear_cache()
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        response = client.get(f'/api/informes/historico?desde={current}&hasta={current}&sensor=VIIRS_NOAA21')
        assert response.status_code == 200 and response.json()['incluye_actual'] is True
        assert response.json()['eventos'] is None
        csv_response = client.get(f'/api/informes/historico?desde={current}&hasta={current}&sensor=VIIRS_NOAA21&formato=csv')
        assert 'eventos_VIIRS_NOAA21' in csv_response.text and 'dias_cubiertos' in csv_response.text
        assert client.get(f'/api/informes/historico?desde={current}&hasta={current+1}').status_code == 422
        assert client.get(f'/api/informes/historico?desde={current}&hasta={current}&sensor=otro').status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)
        clear_cache()


def test_historical_report_deduplicates_events_and_keeps_sensor_coverage_separate(db):
    from datetime import date
    from app.models import Ingesta
    from app.services.informes import informe
    ingerir(db, [row(type='0'), row(type='0', satellite='Aqua',acq_time='1310')], 'MODIS_SP', 'historico')
    ingerir(db, [row(type='0',satellite='N',confidence='h')], 'VIIRS_SNPP_SP', 'historico')
    ingerir(db, [row(type='0',confidence='20',acq_date='2025-08-10')], 'MODIS_SP', 'historico')
    ingerir(db, [row(type='2',acq_date='2025-08-15')], 'MODIS_SP', 'historico')
    db.add(Ingesta(clave='report:2025',fuente='MODIS_SP',origen='historico',inicio=date(2025,1,1),fin=date(2025,12,31),completa=True))
    db.flush()
    result = informe(db,2025,2025,ambito='entorno',cached=False)
    assert result['eventos'] == 1 and result['detecciones'] == 2
    assert result['registros_totales'] == 4 and result['registros_baja_confianza'] == 1 and result['registros_descartados'] == 1
    assert result['dias_archivo'] == 364
    assert result['horaria'][9]['detecciones'] == 2
    assert result['mensual'][7]['eventos'] == 1
    assert result['calendario'][0]['eventos'] == 0
    assert result['ia']['estado'] == 'datos_insuficientes'
    district = informe(db,2025,2025,distrito=5,cached=False)
    assert district['dias_archivo'] == 0 and district['frecuencia_por_30_dias'] is None
    assert 'Distrito sin límite verificado' in district['advertencias'][-1]


def test_partial_historical_report_does_not_invent_zeros_and_exports_csv(db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.deps import get_db
    from app.services.informes import informe, clear_cache
    ingerir(db,[row(type='0')],'MODIS_SP','historico')
    report = informe(db,2025,2025,ambito='entorno',cached=False)
    assert report['anual'][0]['eventos'] == 1
    assert report['dias_archivo'] == 0
    assert report['mensual'][7]['eventos'] == 1 and report['mensual'][7]['eventos_por_30_dias'] is None
    assert report['calendario'][7]['eventos'] == 1 and report['calendario'][0]['eventos'] is None
    clear_cache()
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        response = client.get('/api/informes/historico?desde=2025&hasta=2025&ambito=entorno&formato=csv')
        assert response.status_code == 200
        assert 'text/csv' in response.headers['content-type']
        assert '2025-08,1,' in response.text and '2025-01,,' in response.text
        assert client.get('/api/informes/historico?desde=2025&hasta=2024').status_code == 422
        assert client.get('/api/geografia/cartografia/desconocida.png').status_code == 422
    finally:
        app.dependency_overrides.pop(get_db,None)
        clear_cache()
