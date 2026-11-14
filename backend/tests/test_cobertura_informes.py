from datetime import datetime, timedelta, timezone, date
from types import SimpleNamespace
from app.services.cobertura_informes import ventanas, dias_completos, horas_en, TZ


def test_overlapping_batches_cover_only_full_local_days_without_double_counting():
    now = datetime(2026, 11, 14, 10, tzinfo=timezone.utc)
    records = [SimpleNamespace(estado='ok', origen='nrt', fecha=stamp,
                               detalle={'fuente_datos': 'nasa_keyless', 'datos_hasta': (stamp-timedelta(hours=1)).isoformat()})
               for stamp in (now-timedelta(hours=6), now-timedelta(hours=3), now)]
    _, _, coverage = ventanas(records, datetime(2026, 1, 1, tzinfo=TZ), now, now)
    assert dias_completos(coverage) == {date(2026, 11, 13)}
    assert horas_en(coverage, coverage[0][0], now) == 29


def test_empty_stale_or_failed_global_files_do_not_establish_coverage():
    now = datetime(2026, 11, 13, 20, tzinfo=timezone.utc)
    records = [SimpleNamespace(estado=state, origen='nrt', fecha=now,
                               detalle={'fuente_datos': 'nasa_keyless', 'datos_hasta': stamp})
               for state, stamp in [('ok', None), ('ok', (now-timedelta(days=3)).isoformat()),
                                    ('error', now.isoformat()), ('ok', (now+timedelta(days=1)).isoformat())]]
    assert ventanas(records, now-timedelta(days=4), now, now) == ([], [], [])


def test_utc_archive_does_not_claim_bolivia_tail_or_future_days():
    record = SimpleNamespace(estado='ok', origen='historico', completa=True,
                             inicio=date(2026, 1, 1), fin=date(2026, 12, 31))
    now = datetime(2026, 1, 3, 2, tzinfo=TZ)
    archive, _, coverage = ventanas([record], datetime(2026, 1, 1, tzinfo=TZ), datetime(2027, 1, 1, tzinfo=TZ), now)
    assert dias_completos(archive) == {date(2026, 1, 1), date(2026, 1, 2)}
    assert coverage[-1][1] == now
