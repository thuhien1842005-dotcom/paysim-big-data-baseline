"""UI equivalence on a deterministic Mongo fixture (not a pipeline E2E test)."""
from collections import Counter
from copy import deepcopy
import csv
from io import StringIO
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import mongomock
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'dashboard'))
import dashboard_core


RUN_METRICS = {
    'Source emitted', 'Spark processed', 'Fraud alerts', 'Current ingest',
    'Processing throughput', 'End-to-end latency p95',
}
BASELINE_LABELS = {
    'Nguồn đã phát': 'Source emitted',
    'Spark đã xử lý': 'Spark processed',
    'Ingest hiện tại': 'Current ingest',
}
TIMING_METRICS = {'Query latency', 'Snapshot response', 'Dashboard freshness'}
VIETNAMESE_TEXT = re.compile(
    '[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ'
    'ùúủũụưừứửữựỳýỷỹỵđ]', re.IGNORECASE,
)


def fixture_database():
    db = mongomock.MongoClient(tz_aware=True).paysim
    now = datetime(2026, 10, 23, tzinfo=timezone.utc)
    db.runs.insert_one(dict(run_id='ui-test', started_at=now, status='completed', events_emitted=100,
                            instant_emission_rate=50, source_progress_pct=.5, source_row=100, dataset_rows=200))
    db.evaluation_totals.insert_one(dict(_id='ui-test', processed=100, updated_at=now,
        model=dict(tp=1, fp=1, tn=97, fn=1), rule=dict(tp=1, fp=0, tn=98, fn=1),
        latest_ranking=dict(pr_auc=.71, recall_at_k=.5, precision_at_k=.25,
                            fraud_in_top_k=2, top_k=8)))
    for i in range(3):
        db.pipeline_metrics.insert_one(dict(run_id='ui-test', batch_id=i, created_at=now,
            processing_throughput=25+i, ingest_throughput=50, consumer_lag=0,
            ingest_latency_p95_ms=10, latency_p95_ms=500+i, batch_duration_seconds=2+i,
            processed_rows=100, input_rows=104, invalid_rows=2, duplicate_removed=2,
            late_event_rows=3, event_completeness=.96,
            storage_size_bytes=4096, compression_ratio=2.5, storage_write_seconds=.3,
            small_file_count=12, sql_query_duration_ms=5.4, scoring_latency_ms_per_1k=6.7,
            mongo_write_latency_ms=1.2, mongo_write_success_rate=1.0,
            aggregate_correctness=True, transformation_correctness=True))
    db.live_aggregates.insert_one(dict(run_id='ui-test', type='TRANSFER', transactions=100,
                                     model_alerts=2, rule_alerts=1, total_amount=15000))
    for i in range(2):
        row=dict(run_id='ui-test', event_id=f'e{i}', scored_at=now, type='TRANSFER', amount=100+i,
                 risk_score=.8, prediction=1, source_cycle=1, source_row=i, end_to_end_latency_ms=500)
        db.fraud_alerts.insert_one(row.copy()); db.recent_transactions.insert_one(row.copy())
    db.system_metrics.insert_one(dict(_id='spark', status='running',
                                      recovery_time_seconds=3.5, restart_count=1))
    return db


def app_source(view):
    return ('from dashboard_core import render\n' +
            ('render()' if view == 'baseline' else f'import view_{view} as view\nrender(view)'))


def metrics(at):
    # Timing of the UI query and wall-clock freshness are not business results.
    # Normalize only translated presentation text: values and multiplicities stay exact.
    return sorted((BASELINE_LABELS.get(m.label, m.label), m.value,
                   m.delta.replace(' đang chờ', ' pending'))
                  for m in at.metric if m.label not in TIMING_METRICS)


def assert_english_interface(app):
    """Inspect rendered text, widget options/help, charts and embedded hero HTML.

    The fixture uses ASCII data. Internal session-state page values are deliberately
    Vietnamese for compatibility; only the labels actually sent to the UI count.
    Arrow data bytes are excluded, so original transaction contents are never relabeled.
    """
    def text_values(value):
        if isinstance(value, str):
            yield value
            if value.lstrip().startswith(('{', '[')):
                try:
                    yield from text_values(json.loads(value))
                except (ValueError, TypeError):
                    pass
        elif isinstance(value, dict):
            for item in value.values():
                yield from text_values(item)
        elif isinstance(value, list):
            for item in value:
                yield from text_values(item)

    def proto_strings(proto):
        for field, value in proto.ListFields():
            values = value if field.is_repeated else [value]
            for item in values:
                if field.type == field.TYPE_STRING:
                    yield from text_values(item)
                elif field.type == field.TYPE_MESSAGE:
                    yield from proto_strings(item)

    failures = []
    for element in app:
        proto = getattr(element, 'proto', None)
        if proto is None:
            continue
        for text in proto_strings(proto):
            match = VIETNAMESE_TEXT.search(text)
            if match:
                failures.append((element.type, text[max(match.start() - 50, 0):match.start() + 130]))
    assert not failures, failures


def navigate(app, page):
    app.radio(key='dashboard_page').set_value(page).run()
    assert not app.exception
    return app


def detector_table(app):
    """Find the canonical table independently of surrounding presentation tables."""
    for element in app.dataframe:
        frame = element.value
        if {'Detector', 'TP', 'FP', 'TN', 'FN', 'Precision', 'Recall', 'F1', 'Alert rate'} <= set(frame.columns):
            return frame.reset_index(drop=True)
    pytest.fail('The model/rule evaluation table is missing.')


@pytest.mark.parametrize('view', ['workspace'])
def test_all_four_pages_preserve_six_run_metrics(view):
    db = fixture_database()
    with patch.object(dashboard_core, 'get_database', return_value=db):
        before = AppTest.from_string(app_source('baseline'), default_timeout=15).run()
        after = AppTest.from_string(app_source(view), default_timeout=15).run()
        assert not before.exception and not after.exception
        pages = before.radio[0].options
        for page in pages:
            navigate(before, page)
            navigate(after, page)
            expected = [m for m in metrics(before) if m[0] in RUN_METRICS]
            actual = [m for m in metrics(after) if m[0] in RUN_METRICS]
            assert expected == actual
            # Core pages can be rearranged or enriched; six canonical run values stay identical.
            assert {m[0] for m in actual} == RUN_METRICS


@pytest.mark.parametrize('view', ['workspace'])
def test_tracks_preserve_every_canonical_value_and_benchmark_only(view):
    db = fixture_database()
    with patch.object(dashboard_core, 'get_database', return_value=db):
        before = navigate(AppTest.from_string(app_source('baseline'), default_timeout=15).run(), dashboard_core.PAGES[1])
        after = navigate(AppTest.from_string(app_source(view), default_timeout=15).run(), dashboard_core.PAGES[1])
        # Some tracks repeat labels; a multiset verifies their multiplicities too.
        assert Counter(metrics(before)) == Counter(metrics(after))
        benchmark = [(m.label, m.value) for m in after.metric if m.value == 'Benchmark-only']
        assert sorted(benchmark) == [('Read duration', 'Benchmark-only'), ('Scan size', 'Benchmark-only')]


@pytest.mark.parametrize('view', ['workspace'])
def test_model_and_rule_results_preserve_full_evaluation(view):
    db = fixture_database()
    with patch.object(dashboard_core, 'get_database', return_value=db):
        before = navigate(AppTest.from_string(app_source('baseline'), default_timeout=15).run(), dashboard_core.PAGES[2])
        after = navigate(AppTest.from_string(app_source(view), default_timeout=15).run(), dashboard_core.PAGES[2])
        pd.testing.assert_frame_equal(detector_table(before), detector_table(after))


def test_actual_entrypoint_renders_the_selected_view():
    """Protect app.py itself; synthetic entrypoints cannot catch a commented render()."""
    with patch.object(dashboard_core, 'get_database', return_value=fixture_database()):
        app = AppTest.from_file(str(ROOT / 'dashboard' / 'app.py'), default_timeout=15).run()
        assert not app.exception
        assert RUN_METRICS <= {metric.label for metric in app.metric}
        from ui_theme import PAGE_LABELS
        assert app.radio(key='dashboard_page').options == [PAGE_LABELS[page] for page in dashboard_core.PAGES]



@pytest.mark.parametrize('view', ['baseline', 'workspace'])
def test_empty_database_displays_waiting_message(view):
    db = mongomock.MongoClient().paysim
    with patch.object(dashboard_core, 'get_database', return_value=db):
        app = AppTest.from_string(app_source(view), default_timeout=15).run()
        assert not app.exception
        assert app.info[0].value == 'The pipeline is getting ready. The replayer starts after Spark is ready.'
        if view == 'workspace':
            assert_english_interface(app)


@pytest.mark.parametrize('view', ['workspace'])
def test_run_without_telemetry_or_transactions_handles_every_page(view):
    db = mongomock.MongoClient(tz_aware=True).paysim
    db.runs.insert_one(dict(run_id='starting', status='starting',
                            started_at=datetime(2026, 10, 23, tzinfo=timezone.utc)))
    with patch.object(dashboard_core, 'get_database', return_value=db):
        app = AppTest.from_string(app_source(view), default_timeout=15).run()
        assert not app.exception
        for page in dashboard_core.PAGES:
            navigate(app, page)
            assert RUN_METRICS <= {metric.label for metric in app.metric}
            assert_english_interface(app)


def test_all_pages_and_transaction_filter_states_use_english_display_text():
    """Cover normal content, all navigation labels and dynamic filter messages."""
    with patch.object(dashboard_core, 'get_database', return_value=fixture_database()):
        app = AppTest.from_string(app_source('workspace'), default_timeout=15).run()
        for page in dashboard_core.PAGES:
            navigate(app, page)
            assert_english_interface(app)
        prediction_key = transaction_key(app, '_prediction')
        assert app.selectbox(key=prediction_key).options == ['All', 'Alert', 'No alert']
        app.selectbox(key=prediction_key).set_value('No alert').run()
        assert not app.exception
        assert_english_interface(app)
        app.button(key=transaction_key(app, '_reset')).click().run()
        app.text_input(key=transaction_key(app, '_search')).set_value('not-in-snapshot').run()
        assert not app.exception
        assert_english_interface(app)
        app.button(key=transaction_key(app, '_reset')).click().run()
        app.number_input(key=transaction_key(app, '_amount_min')).set_value(200.0)
        app.number_input(key=transaction_key(app, '_amount_max')).set_value(100.0).run()
        assert not app.exception
        assert any('Minimum amount must be less than or equal to maximum amount.' == message.value
                   for message in app.warning)
        assert_english_interface(app)


def test_snapshot_preserves_run_isolation_limits_and_order():
    db = fixture_database()
    now = datetime(2026, 10, 23, tzinfo=timezone.utc)
    db.pipeline_metrics.delete_many({})
    db.recent_transactions.delete_many({})
    db.fraud_alerts.delete_many({})
    db.runs.insert_one(dict(run_id='old-run', status='completed', started_at=now - timedelta(days=1)))
    for index in range(65):
        stamp = now + timedelta(seconds=index)
        db.pipeline_metrics.insert_one(dict(run_id='ui-test', batch_id=index, created_at=stamp))
        db.recent_transactions.insert_one(dict(run_id='ui-test', event_id=f't{index}', scored_at=stamp))
    for index in range(305):
        db.fraud_alerts.insert_one(dict(run_id='ui-test', event_id=f'a{index}',
                                        scored_at=now + timedelta(seconds=index)))
    # Newer telemetry for an older run must not leak into the current run.
    future = now + timedelta(days=10)
    db.pipeline_metrics.insert_one(dict(run_id='old-run', batch_id=9999, created_at=future))
    db.recent_transactions.insert_one(dict(run_id='old-run', event_id='wrong-run', scored_at=future))
    db.fraud_alerts.insert_one(dict(run_id='old-run', event_id='wrong-alert', scored_at=future))
    with patch.object(dashboard_core, 'get_database', return_value=db):
        snapshot = dashboard_core.load_snapshot()
    assert snapshot.run_id == 'ui-test'
    assert [row['batch_id'] for row in snapshot.metrics] == list(range(5, 65))
    assert snapshot.latest_metric['batch_id'] == 64
    assert [row['event_id'] for row in snapshot.recent_transactions] == [f't{i}' for i in range(64, 4, -1)]
    assert [row['event_id'] for row in snapshot.recent_alerts] == [f'a{i}' for i in range(304, 4, -1)]
    assert snapshot.alerts_count == 305
    assert snapshot.processed == 100
    assert snapshot.emitted == 100
    assert snapshot.lag == 0
    assert all('_id' not in row for row in snapshot.metrics + snapshot.recent_transactions + snapshot.recent_alerts)


def test_detector_formulas_and_zero_denominators():
    values = dashboard_core.detector_metrics({'model': dict(tp=17, fp=3, tn=75, fn=5)}, 'model')
    assert (values['TP'], values['FP'], values['TN'], values['FN']) == (17, 3, 75, 5)
    assert values['Precision'] == pytest.approx(.85)
    assert values['Recall'] == pytest.approx(17 / 22)
    assert values['F1'] == pytest.approx(34 / 42)
    assert values['Alert rate'] == pytest.approx(.2)
    assert set(dashboard_core.detector_metrics({}, 'model').values()) == {0}


@pytest.fixture
def filter_rows():
    now = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
    return [
        dict(event_id='Alpha[1]', type='TRANSFER', amount=100, risk_score=.8, prediction=1, scored_at=now),
        dict(event_id='beta.2', type='CASH_OUT', amount=200, risk_score=.2, prediction=0,
             scored_at=now + timedelta(minutes=10)),
        dict(event_id='gamma', type='TRANSFER', amount=300, risk_score=.9, prediction=1,
             scored_at=now + timedelta(minutes=20)),
        dict(event_id='missing'),
    ]


@pytest.mark.parametrize(('criteria', 'expected'), [
    ({'types': ['TRANSFER']}, ['Alpha[1]', 'gamma']),
    ({'types': []}, []),
    ({'amount_range': (100, 200)}, ['Alpha[1]', 'beta.2']),
    ({'amount_range': (None, 100)}, ['Alpha[1]']),
    ({'amount_range': (300, None)}, ['gamma']),
    ({'score_range': (.8, .9)}, ['Alpha[1]', 'gamma']),
    ({'prediction': 'Alert'}, ['Alpha[1]', 'gamma']),
    ({'prediction': 'No alert'}, ['beta.2']),
    ({'search': '['}, ['Alpha[1]']),
    ({'search': '.'}, ['beta.2']),
    ({'search': 'ALPHA'}, ['Alpha[1]']),
    ({'types': ['TRANSFER'], 'amount_range': (150, None), 'score_range': (.85, 1),
      'prediction': 'Alert'}, ['gamma']),
    ({'amount_range': (500, 100)}, []),
    ({'search': 'not-present'}, []),
])
def test_filters_are_inclusive_composable_and_literal(filter_rows, criteria, expected):
    from ui_transactions import filter_records
    original = deepcopy(filter_rows)
    filtered = filter_records(filter_rows, **criteria)
    assert [row['event_id'] for row in filtered] == expected
    assert filter_rows == original


def test_filters_default_and_empty_inputs_do_not_mutate_rows(filter_rows):
    from ui_transactions import filter_records
    original = deepcopy(filter_rows)
    filtered = filter_records(filter_rows)
    assert filtered == original
    assert filter_rows == original
    assert filtered is not filter_rows
    assert filter_records([]) == []


def test_time_filters_normalize_utc_and_keep_boundaries(filter_rows):
    from ui_transactions import filter_records
    now = filter_rows[0]['scored_at']
    criteria = dict(start=now + timedelta(minutes=10), end=now + timedelta(minutes=20))
    assert [r['event_id'] for r in filter_records(filter_rows, **criteria)] == ['beta.2', 'gamma']
    # Mongo dates are aware; imports may also expose equivalent ISO/naive timestamps.
    filter_rows[1]['scored_at'] = '2026-10-23T19:10:00+07:00'
    filter_rows[2]['scored_at'] = datetime(2026, 10, 23, 12, 20)
    assert [r['event_id'] for r in filter_records(filter_rows, **criteria)] == ['beta.2', 'gamma']
    filter_rows.append(dict(event_id='bad-date', scored_at='not-a-date'))
    assert [r['event_id'] for r in filter_records(filter_rows, **criteria)] == ['beta.2', 'gamma']


def test_csv_contains_only_filtered_rows_in_display_order_and_escapes_text():
    from ui_transactions import filter_records, records_csv
    source = [
        dict(event_id='ordinary', type='PAYMENT', amount=20, risk_score=.1, prediction=0),
        dict(event_id=' =SUM(1,2)', type='TRANSFER', amount=-12.5, risk_score=.8, prediction=1),
        dict(event_id='@danger', type='TRANSFER', amount=100, risk_score=.9, prediction=1),
    ]
    original = deepcopy(source)
    filtered = filter_records(source, prediction='Alert')
    payload = records_csv(filtered)
    assert payload.startswith(b'\xef\xbb\xbf')
    rows = list(csv.DictReader(StringIO(payload.decode('utf-8-sig'))))
    assert [row['event_id'] for row in rows] == ["' =SUM(1,2)", "'@danger"]
    assert rows[0]['amount'] == '-12.5'
    assert source == original


def transaction_table(app):
    for element in app.dataframe:
        frame = element.value
        if {'event_id', 'amount', 'risk_score'} <= set(frame.columns):
            return frame
    pytest.fail('The transaction table is missing.')


def transaction_key(app, suffix):
    elements = [*app.text_input, *app.selectbox, *app.button, *app.multiselect, *app.number_input, *app.slider]
    keys = [element.key for element in elements if element.key and element.key.endswith(suffix)]
    assert len(keys) == 1, f'Expected one transaction widget ending in {suffix}, got {keys}'
    return keys[0]


def test_ui_filter_changes_only_loaded_rows_and_reset_restores_them():
    db = fixture_database()
    with patch.object(dashboard_core, 'get_database', return_value=db):
        app = navigate(AppTest.from_string(app_source('workspace'), default_timeout=15).run(), dashboard_core.PAGES[3])
        assert not app.exception
        original_metrics = [m for m in metrics(app) if m[0] in RUN_METRICS]
        assert set(transaction_table(app)['event_id']) == {'e0', 'e1'}
        search_key = transaction_key(app, '_search')
        app.text_input(key=search_key).set_value('e0').run()
        assert not app.exception
        assert list(transaction_table(app)['event_id']) == ['e0']
        assert [m for m in metrics(app) if m[0] in RUN_METRICS] == original_metrics
        app.text_input(key=search_key).set_value('not-in-snapshot').run()
        assert not app.exception
        assert any('No matching records' in message.value for message in [*app.info, *app.warning])
        app.button(key=transaction_key(app, '_reset')).click().run()
        assert not app.exception
        search_key = transaction_key(app, '_search')
        assert app.text_input(key=search_key).value == ''
        assert set(transaction_table(app)['event_id']) == {'e0', 'e1'}
        assert [m for m in metrics(app) if m[0] in RUN_METRICS] == original_metrics


def test_selected_transaction_survives_new_row_and_clears_when_removed():
    db = fixture_database()
    with patch.object(dashboard_core, 'get_database', return_value=db):
        app = navigate(AppTest.from_string(app_source('workspace'), default_timeout=15).run(), dashboard_core.PAGES[3])
        assert not app.exception
        selected_key = transaction_key(app, '_selected_id')
        app.selectbox(key=selected_key).set_value('e0').run()
        assert not app.exception
        db.recent_transactions.insert_one(dict(run_id='ui-test', event_id='new-event',
            scored_at=datetime(2026, 10, 24, tzinfo=timezone.utc), type='CASH_OUT',
            amount=400, risk_score=.1, prediction=0))
        app.run()
        assert not app.exception
        assert app.selectbox(key=selected_key).value == 'e0'
        db.recent_transactions.delete_one({'event_id': 'e0'})
        app.run()
        assert not app.exception
        assert app.selectbox(key=selected_key).value is None
