"""Pastel renderers for the existing snapshot. No queries or model changes."""
from html import escape
import altair as alt
import pandas as pd
import streamlit as st

from dashboard_core import PAGES, detector_metrics, fmt_bytes, fmt_float, fmt_int, fmt_pct
from ui_theme import PALETTE, activity_feed, section, style_chart
from ui_transactions import render_alerts, render_transactions


def telemetry_chart(metrics, fields, labels, unit, *, height=250):
    frame = pd.DataFrame(metrics)
    available = [field for field in fields if field in frame]
    if frame.empty or not available or 'created_at' not in frame:
        st.info('Waiting for the first micro-batch telemetry.')
        return
    data = frame[['created_at', *available]].rename(columns=labels).melt('created_at', var_name='Metric', value_name='Value')
    chart = alt.Chart(data).mark_line(point=alt.OverlayMarkDef(size=35), strokeWidth=2.5).encode(
        x=alt.X('created_at:T', title='Time', axis=alt.Axis(format='%H:%M:%S', labelAngle=0)),
        y=alt.Y('Value:Q', title=unit, scale=alt.Scale(zero=False)),
        color=alt.Color('Metric:N', scale=alt.Scale(range=PALETTE), legend=alt.Legend(orient='top', title=None)),
        tooltip=[alt.Tooltip('created_at:T', title='Time'), 'Metric:N', alt.Tooltip('Value:Q', format=',.2f', title=unit)],
    ).properties(height=height).interactive()
    st.altair_chart(style_chart(chart), theme=None, use_container_width=True)


def pipeline_status(s):
    with st.container(border=True, key='run-progress'):
        section('Pipeline activity', 'PIPELINE STATUS')
        st.caption('Reconcile processed records, aggregates and alerts')
        st.success('PASS · Data is consistent') if s.display_correct else st.info('SYNCING · Reconciling data')
        st.caption(f"Cycle {s.run.get('source_cycle', 1)} · row {fmt_int(s.run.get('source_row'))}/{fmt_int(s.run.get('dataset_rows'))}")
        st.progress(min(float(s.run.get('source_progress_pct', 0)), 1.0), text='Current data cycle progress')
        st.caption(f'{fmt_int(s.lag)} events waiting for Spark processing')
    with st.container(border=True, key='panel-activity'):
        activity_feed(s)


def render_operations(s, *, key_prefix='operations', compact=False):
    section('Live data flow', 'LIVE CONTROL ROOM', 'Throughput, lag and latency from the same snapshot.')
    label, choice = st.columns([3, 1])
    with label:
        st.caption('Latest telemetry · up to 60 loaded micro-batches')
    with choice:
        window = st.selectbox('Chart window', [60, 30, 15], format_func=lambda value: f'{value} micro-batches', key=f'{key_prefix}_window')
    metrics = s.metrics[-window:]
    charts, status = st.columns([2.3 if compact else 2.5, 1], gap='large')
    with charts:
        with st.container(border=True, key='panel-throughput'):
            section('Ingest and processing throughput', 'STREAM PERFORMANCE')
            telemetry_chart(metrics, ['ingest_throughput', 'processing_throughput'],
                {'ingest_throughput': 'Replayer → Kafka', 'processing_throughput': 'Spark processing'}, 'Events/second', height=270)
        left, right = st.columns(2)
        with left:
            with st.container(border=True, key='panel-lag'):
                section('Kafka consumer lag')
                telemetry_chart(metrics, ['consumer_lag'], {'consumer_lag': 'Pending events'}, 'Events', height=185)
        with right:
            with st.container(border=True, key='panel-latency'):
                section('Latency p95')
                telemetry_chart(metrics, ['ingest_latency_p95_ms', 'latency_p95_ms'],
                    {'ingest_latency_p95_ms': 'Ingest p95', 'latency_p95_ms': 'End-to-end p95'}, 'Milliseconds', height=185)
    with status:
        pipeline_status(s)
    with st.expander('Micro-batch duration & history', expanded=False):
        telemetry_chart(metrics, ['batch_duration_seconds'], {'batch_duration_seconds': 'Batch duration'}, 'Seconds', height=180)
        history = pd.DataFrame(metrics)
        if not history.empty:
            columns = [name for name in ['batch_id', 'created_at', 'input_rows', 'processed_rows', 'consumer_lag',
                'processing_throughput', 'latency_p95_ms', 'invalid_rows', 'duplicate_removed', 'alerts'] if name in history]
            if 'batch_id' in history:
                history = history.sort_values('batch_id', ascending=False)
            st.dataframe(history[columns], hide_index=True, use_container_width=True)


def detector_comparison(s):
    comparison = pd.DataFrame([dict(Detector=name, **detector_metrics(s.evaluation, key))
        for key, name in [('rule', 'Spark SQL rule'), ('model', 'Spark MLlib')]])
    display = comparison.copy()
    for column in ['Precision', 'Recall', 'F1', 'Alert rate']:
        display[column] = display[column].map(fmt_pct)
    return comparison, display


def render_comparison(s):
    comparison, display = detector_comparison(s)
    section('Rule baseline vs Spark MLlib', 'DETECTION QUALITY', 'The same cumulative evaluation for the current run.')
    data = comparison.melt(id_vars=['Detector'], value_vars=['Precision', 'Recall', 'F1'], var_name='Metric', value_name='Value')
    chart = alt.Chart(data).mark_bar(size=12, cornerRadiusEnd=5).encode(
        y=alt.Y('Metric:N', title=None, sort=['Precision', 'Recall', 'F1']),
        x=alt.X('Value:Q', title=None, scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format='%')),
        yOffset='Detector:N', color=alt.Color('Detector:N',
            scale=alt.Scale(domain=['Spark SQL rule', 'Spark MLlib'], range=['#B39ABE', '#AD476B']),
            legend=alt.Legend(orient='top', title=None)),
        tooltip=['Detector:N', 'Metric:N', alt.Tooltip('Value:Q', format='.2%')],
    ).properties(height=240)
    st.altair_chart(style_chart(chart), theme=None, use_container_width=True)
    with st.expander('Detailed metrics and classification results'):
        st.dataframe(display, hide_index=True, use_container_width=True)


def render_matrix(s):
    section('Confusion matrix — Spark MLlib', 'CLASSIFICATION')
    matrix = pd.DataFrame([
        {'Actual': 'Fraud', 'Predicted': 'Fraud', 'Count': s.model['TP']},
        {'Actual': 'Fraud', 'Predicted': 'Legitimate', 'Count': s.model['FN']},
        {'Actual': 'Legitimate', 'Predicted': 'Fraud', 'Count': s.model['FP']},
        {'Actual': 'Legitimate', 'Predicted': 'Legitimate', 'Count': s.model['TN']},
    ])
    base = alt.Chart(matrix).encode(x=alt.X('Predicted:N', title='Model prediction'),
        y=alt.Y('Actual:N', title='Ground truth'), tooltip=['Actual:N', 'Predicted:N', alt.Tooltip('Count:Q', format=',')])
    blocks = base.mark_rect(cornerRadius=8).encode(color=alt.Color('Count:Q', scale=alt.Scale(range=['#FFF4E3', '#E9ABC1']), legend=None))
    text = base.mark_text(fontSize=19, color='#573747').encode(text=alt.Text('Count:Q', format=','))
    st.altair_chart(style_chart((blocks + text).properties(height=245)), theme=None, use_container_width=True)
    st.caption('Fraud / Legitimate represents the ground truth; alerts represent predictions.')


def render_distribution(s):
    section('Transaction mix', 'BUSINESS MIX', 'Aggregates for the entire run · unaffected by transaction filters.')
    if not s.aggregates:
        st.info('Waiting for transaction aggregates by type.')
        return
    chart = alt.Chart(pd.DataFrame(s.aggregates)).mark_bar(color='#B96788', cornerRadiusEnd=6, size=21).encode(
        y=alt.Y('type:N', title=None, sort='-x'), x=alt.X('transactions:Q', title='Transactions'),
        tooltip=['type:N', alt.Tooltip('transactions:Q', format=','), alt.Tooltip('total_amount:Q', format=',.2f'), 'model_alerts:Q', 'rule_alerts:Q'],
    ).properties(height=230)
    st.altair_chart(style_chart(chart), theme=None, use_container_width=True)


def render_business(s, *, key_prefix='business'):
    left, right = st.columns([1.5, 1], gap='large')
    with left:
        with st.container(border=True, key='panel-comparison'):
            render_comparison(s)
    with right:
        with st.container(border=True, key='risk-matrix'):
            render_matrix(s)
    with st.container(border=True, key='panel-distribution'):
        render_distribution(s)
    with st.expander('Transactions and alerts by type', expanded=False):
        if s.aggregates:
            plot = pd.DataFrame(s.aggregates).melt(id_vars=['type'], value_vars=['model_alerts', 'rule_alerts'], var_name='Detector', value_name='Alerts')
            chart = alt.Chart(plot).mark_bar(cornerRadiusEnd=3).encode(
                x=alt.X('type:N', title='Transaction type'), y=alt.Y('Alerts:Q', title='Alerts'), xOffset='Detector:N',
                color=alt.Color('Detector:N', scale=alt.Scale(range=PALETTE[:2])), tooltip=['type:N', 'Detector:N', 'Alerts:Q'],
            ).properties(height=240)
            st.altair_chart(style_chart(chart), theme=None, use_container_width=True)
        if s.recent_alerts:
            st.caption('Risk score and amount · up to 300 loaded alerts')
            scatter = alt.Chart(pd.DataFrame(s.recent_alerts)).mark_circle(size=55, opacity=.65).encode(
                x=alt.X('amount:Q', title='Amount', scale=alt.Scale(type='log')),
                y=alt.Y('risk_score:Q', title='Risk score', scale=alt.Scale(domain=[0, 1])),
                color=alt.Color('type:N', scale=alt.Scale(range=PALETTE), title='Transaction type'),
                tooltip=['event_id:N', 'type:N', alt.Tooltip('amount:Q', format=',.2f'), alt.Tooltip('risk_score:Q', format='.4f')],
            ).properties(height=260).interactive()
            st.altair_chart(style_chart(scatter), theme=None, use_container_width=True)
    with st.expander('Explore the latest alerts', expanded=False):
        render_alerts(s, key_prefix=f'{key_prefix}_alerts')


def track_block(number, title, scope, items, guardrail):
    with st.expander(f'{number:02d}. {title}', expanded=number in (1, 6)):
        st.caption(scope)
        columns = st.columns(min(3, len(items)))
        for index, (label, value, code, help_text) in enumerate(items):
            with columns[index % len(columns)]:
                st.metric(label, value, help=help_text)
                st.markdown(f'<div class="metric-code">{escape(code)}</div>', unsafe_allow_html=True)
        st.caption(f'Guardrail: {guardrail}')


def render_tracks(snapshot):
    section('Metrics across 10 tracks', 'OPTIMIZATION TRACKS', 'Expand each group to review metrics, definitions and reconciliation checks.')
    run = snapshot.run
    evaluation = snapshot.evaluation
    latest_metric = snapshot.latest_metric
    processed = snapshot.processed
    lag = snapshot.lag
    model = snapshot.model
    ranking = snapshot.ranking
    alerts_count = snapshot.alerts_count
    query_latency_ms = snapshot.query_latency_ms
    freshness = snapshot.freshness
    display_correct = snapshot.display_correct
    system = snapshot.system
    # Canonical definitions copied without changing any metric expression.
    st.info(
        "Live metrics change with each micro-batch. Metrics marked “Benchmark-only” "
        "require a separate before/after benchmark protocol and must not be simulated from live telemetry."
    )
    total_storage = latest_metric.get("storage_size_bytes", 0)
    bad_rate = int(latest_metric.get("invalid_rows", 0)) / max(int(latest_metric.get("input_rows", 0)), 1)
    late_rate = int(latest_metric.get("late_event_rows", 0)) / max(int(latest_metric.get("processed_rows", 0)), 1)
    event_loss = int(run.get("delivery_errors", 0)) + int(evaluation.get("ground_truth_missing", 0))

    track_block(1, "Ingestion", "Replayer → Kafka → Spark consumer", [
        ("Ingest throughput", f"{fmt_float(latest_metric.get('ingest_throughput'))} ev/s", "ingest_throughput", "Rate of events emitted to Kafka"),
        ("Consumer lag", fmt_int(lag), "consumer_lag", "Emitted events not yet processed by Spark"),
        ("Ingest latency p95", f"{fmt_float(latest_metric.get('ingest_latency_p95_ms'), 0)} ms", "ingest_latency_p95", "95% of events reach Kafka within this time"),
    ], f"Delivery errors={fmt_int(run.get('delivery_errors'))}; duplicates injected={fmt_int(run.get('duplicates_injected'))}")

    track_block(2, "Storage", "HDFS Bronze / Silver / Gold", [
        ("Storage size", fmt_bytes(total_storage), "storage_size", "Total size of all three data layers"),
        ("Compression ratio", f"{fmt_float(latest_metric.get('compression_ratio'), 2)}×", "compression_ratio", "Raw JSON bytes / Bronze Parquet bytes"),
        ("Write duration", f"{fmt_float(latest_metric.get('storage_write_seconds'), 2)} s", "write_duration", "Total write time for Bronze, Silver and Gold"),
        ("Read duration", "Benchmark-only", "read_duration", "Measured with a standardized read workload"),
        ("Small files", fmt_int(latest_metric.get("small_file_count")), "small_file_count", "Accumulated data files on HDFS"),
    ], f"Processed records={fmt_int(processed)}; HDFS record guardrail is reconciled against the pipeline count")

    track_block(3, "Data Quality", "Validation, deduplication, nulls and late events", [
        ("Bad record rate", fmt_pct(bad_rate), "bad_record_rate", "Proportion of invalid records"),
        ("Duplicates removed", fmt_int(latest_metric.get("duplicate_removed")), "duplicate_removed", "Duplicate records removed in the latest batch"),
        ("Late event rate", fmt_pct(late_rate), "late_event_rate", "Events arriving more than one minute after ingestion"),
        ("Event completeness", fmt_pct(latest_metric.get("event_completeness", 1.0)), "event_completeness", "Valid unique records / input records"),
        ("Transformation", "PASS" if latest_metric.get("transformation_correctness") else "CHECK", "transformation_correctness", "Aggregate output matches the valid row count"),
    ], f"Ground truth missing={fmt_int(evaluation.get('ground_truth_missing'))}")

    track_block(4, "Stream Processing", "Spark Structured Streaming", [
        ("Micro-batch", f"{fmt_float(latest_metric.get('batch_duration_seconds'), 2)} s", "microbatch_duration", "Processing time of the latest batch"),
        ("Processing throughput", f"{fmt_float(latest_metric.get('processing_throughput'))} ev/s", "processing_throughput", "Valid events processed per second"),
        ("Processing latency p95", f"{fmt_float(latest_metric.get('latency_p95_ms'), 0)} ms", "processing_latency_p95", "End-to-end latency p95"),
        ("Late events handled", fmt_int(latest_metric.get("late_event_rows")), "late_event_handling", "Late events identified in the batch"),
    ], f"Lag={fmt_int(lag)}; duplicates removed={fmt_int(latest_metric.get('duplicate_removed'))}")

    track_block(5, "SQL Analytics", "Spark SQL rules and business aggregates", [
        ("Query duration", f"{fmt_float(latest_metric.get('sql_query_duration_ms'), 1)} ms", "query_duration", "GroupBy aggregation time by transaction type"),
        ("Aggregate correctness", "PASS" if latest_metric.get("aggregate_correctness") else "CHECK", "aggregate_correctness", "Aggregate totals match valid rows"),
        ("Scan size", "Benchmark-only", "scan_size", "Measured with a standardized query workload"),
        ("Partition pruning", "run_id / type", "partition_pruning", "Silver is partitioned by run and transaction type"),
    ], "Aggregate semantics are preserved; expected output matches the processed count")

    track_block(6, "Fraud Detection", "Spark MLlib model and features", [
        ("PR-AUC", fmt_pct(ranking.get("pr_auc")), "pr_auc (latest batch)", "Average precision of the latest batch"),
        ("Recall@K", fmt_pct(ranking.get("recall_at_k")), "recall_at_k", "Proportion of fraud captured in the latest batch's top K"),
        ("Precision@K", fmt_pct(ranking.get("precision_at_k")), "precision_at_k", "Proportion of fraud among the top K"),
        ("F1", fmt_pct(model["F1"]), "f1", "Cumulative F1 for the run"),
        ("Scoring latency", f"{fmt_float(latest_metric.get('scoring_latency_ms_per_1k'), 1)} ms/1K", "scoring_latency", "Scoring time normalized to 1,000 records"),
    ], f"Alert rate={fmt_pct(model['Alert rate'])}; the feature set excludes labels")

    track_block(7, "Alert Optimization", "Risk score, threshold and Top-K", [
        ("Precision@K", fmt_pct(ranking.get("precision_at_k")), "precision_at_k", "Precision in the latest batch's top K"),
        ("Recall@K", fmt_pct(ranking.get("recall_at_k")), "recall_at_k", "Recall in the latest batch's top K"),
        ("Fraud in Top-K", f"{fmt_int(ranking.get('fraud_in_top_k'))}/{fmt_int(ranking.get('top_k'))}", "fraud_in_top_k", "Actual fraud count among the top K"),
        ("Alert volume", fmt_int(alerts_count), "alert_volume", "Cumulative alert count"),
        ("Alert rate", fmt_pct(model["Alert rate"]), "alert_rate", "Proportion of transactions flagged as alerts"),
    ], "Threshold=0.50; overall recall and the evaluation set remain unchanged")

    track_block(8, "Serving", "MongoDB documents, indexes and queries", [
        ("Mongo write latency", f"{fmt_float(latest_metric.get('mongo_write_latency_ms'), 1)} ms", "mongo_write_latency", "Write time for alerts, recent events, aggregates and evaluation"),
        ("Query latency", f"{fmt_float(query_latency_ms, 1)} ms", "query_latency (snapshot)", "Time for the dashboard to load a MongoDB snapshot"),
        ("Write success", fmt_pct(latest_metric.get("mongo_write_success_rate", 0.0)), "write_success_rate", "Proportion of successful write operations"),
    ], f"Alert count={fmt_int(alerts_count)}; Gold-to-serving count is checked live")

    track_block(9, "Dashboard", "Streamlit queries, cache and display", [
        ("Dashboard freshness", f"{fmt_float(freshness, 1)} s", "dashboard_freshness", "Delay from the latest evaluation to the UI"),
        ("Snapshot response", f"{fmt_float(query_latency_ms, 1)} ms", "dashboard_response_time", "Time to load all data for one refresh"),
        ("Display correctness", "PASS" if display_correct else "SYNCING", "display_correctness", "Aggregates, processed records and alert counts are consistent"),
    ], "Refreshes every 2 seconds; metric definitions come directly from canonical telemetry")

    track_block(10, "Reliability", "Checkpoint, persistence and restart", [
        ("Recovery time", f"{fmt_float(system.get('recovery_time_seconds'), 1)} s", "recovery_time", "Time from Spark startup until the query is ready"),
        ("Event loss", fmt_int(event_loss), "event_loss_after_restart", "Delivery errors plus missing ground truth"),
        ("Duplicates after restart", fmt_int(latest_metric.get("duplicate_removed")), "duplicate_after_restart", "Duplicates removed by Spark in the batch"),
        ("Pipeline status", "RUNNING" if system.get("status") == "running" else "CHECK", "pipeline_run_success", "The Spark query and checkpoint are active"),
        ("Spark starts", fmt_int(system.get("restart_count")), "restart_count", "Number of Spark pipeline starts"),
    ], f"Checkpoint HDFS active; processed={fmt_int(processed)}; lag={fmt_int(lag)}")


def render_page(s, page, *, key_prefix):
    if page == PAGES[0]:
        render_operations(s, key_prefix=f'{key_prefix}_ops')
    elif page == PAGES[1]:
        render_tracks(s)
    elif page == PAGES[2]:
        render_business(s, key_prefix=f'{key_prefix}_risk')
    elif page == PAGES[3]:
        render_transactions(s, key_prefix=f'{key_prefix}_transactions')
        with st.expander('Transaction aggregates for the entire run', expanded=False):
            render_distribution(s)
