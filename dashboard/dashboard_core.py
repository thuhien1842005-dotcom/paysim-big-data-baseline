from __future__ import annotations

import os
import time
from types import SimpleNamespace
from datetime import UTC, datetime

import altair as alt
import pandas as pd
import streamlit as st
from pymongo import DESCENDING, MongoClient


PAGES = ["📡 Live Control Room", "🎯 Metrics theo 10 tracks", "🛡️ Fraud & Business", "🔎 Dòng dữ liệu mới"]

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "paysim")



@st.cache_resource
def get_database():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10_000, tz_aware=True)
    client.admin.command("ping")
    return client[MONGO_DATABASE]


def fmt_int(value) -> str:
    return f"{int(value or 0):,}"


def fmt_float(value, digits: int = 1) -> str:
    return f"{float(value or 0):,.{digits}f}"


def fmt_pct(value, digits: int = 2) -> str:
    return f"{float(value or 0):.{digits}%}"


def fmt_bytes(value) -> str:
    size = float(value or 0)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            return f"{size:,.1f} {unit}"
        size /= 1024
    return "0 B"


def detector_metrics(evaluation: dict, detector: str) -> dict:
    values = evaluation.get(detector, {}) if evaluation else {}
    tp, fp = int(values.get("tp", 0)), int(values.get("fp", 0))
    tn, fn = int(values.get("tn", 0)), int(values.get("fn", 0))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    total = tp + fp + tn + fn
    return {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "Precision": precision, "Recall": recall, "F1": f1,
        "Alert rate": (tp + fp) / total if total else 0.0,
    }


def pipeline_html() -> str:
    nodes = [
        ("PaySim", "6.36M rows"), ("Replayer", "live source"),
        ("Kafka", "3 partitions"), ("Spark", "micro-batches"),
        ("HDFS", "Bronze/Silver/Gold"), ("MLlib", "risk scoring"),
        ("MongoDB", "serving"), ("Streamlit", "live UI"),
    ]
    parts = ['<div class="pipeline-flow">']
    for index, (name, detail) in enumerate(nodes):
        parts.append(f'<div class="flow-node">{name}<small>{detail}</small></div>')
        if index < len(nodes) - 1:
            parts.append('<div class="flow-arrow"><span class="packet"></span></div>')
    parts.append("</div>")
    return "".join(parts)


def line_chart(frame: pd.DataFrame, columns: list[str], labels: dict, y_title: str, view=None):
    available = [column for column in columns if column in frame.columns]
    if not available:
        st.info("Đang chờ micro-batch telemetry đầu tiên.")
        return
    plot = frame[["created_at", *available]].rename(columns=labels)
    melted = plot.melt("created_at", var_name="Metric", value_name="Value")
    if view is not None:
        view.chart(melted, y_title)
        return
    chart = (
        alt.Chart(melted)
        .mark_line(point=True, strokeWidth=2.5)
        .encode(
            x=alt.X("created_at:T", title="Thời gian"),
            y=alt.Y("Value:Q", title=y_title),
            color=alt.Color("Metric:N", legend=alt.Legend(orient="top")),
            tooltip=[alt.Tooltip("created_at:T", title="Time"), "Metric:N", alt.Tooltip("Value:Q", format=",.2f")],
        )
        .properties(height=270)
        .interactive()
    )
    st.altair_chart(chart)


def track_block(number: int, title: str, scope: str, items: list[tuple], guardrail: str):
    with st.container(border=True):
        st.markdown(f"#### {number:02d}. {title}")
        st.caption(scope)
        columns = st.columns(min(3, len(items)))
        for index, (label, value, code, help_text) in enumerate(items):
            with columns[index % len(columns)]:
                st.metric(label, value, help=help_text)
                st.markdown(f'<div class="metric-code">{code}</div>', unsafe_allow_html=True)
        st.caption(f"Guardrail: {guardrail}")


def render_detector_comparison(evaluation: dict) -> None:
    model = detector_metrics(evaluation, "model")
    rule = detector_metrics(evaluation, "rule")
    comparison = pd.DataFrame([
        {"Detector": "Spark SQL rule", **rule},
        {"Detector": "Spark MLlib", **model},
    ])
    display = comparison.copy()
    for column in ["Precision", "Recall", "F1", "Alert rate"]:
        display[column] = display[column].map(fmt_pct)
    st.dataframe(display, hide_index=True)


def render_confusion_matrix(model: dict):
    matrix = pd.DataFrame([
        {"Actual": "Fraud", "Predicted": "Fraud", "Count": model["TP"]},
        {"Actual": "Fraud", "Predicted": "Legitimate", "Count": model["FN"]},
        {"Actual": "Legitimate", "Predicted": "Fraud", "Count": model["FP"]},
        {"Actual": "Legitimate", "Predicted": "Legitimate", "Count": model["TN"]},
    ])
    chart = (
        alt.Chart(matrix)
        .mark_rect(cornerRadius=5)
        .encode(
            x=alt.X("Predicted:N", title="Model dự đoán"),
            y=alt.Y("Actual:N", title="Ground truth"),
            color=alt.Color("Count:Q", scale=alt.Scale(scheme="blues")),
            tooltip=["Actual", "Predicted", alt.Tooltip("Count", format=",")],
        )
        .properties(height=260)
    )
    text = chart.mark_text(baseline="middle", fontSize=16).encode(
        text=alt.Text("Count:Q", format=","), color=alt.value("#111827")
    )
    st.altair_chart(chart + text)


def load_snapshot():
    load_started = time.perf_counter()
    database = get_database()
    run = database.runs.find_one(sort=[("started_at", DESCENDING)])
    if not run:
        return None

    run_id = run["run_id"]
    evaluation = database.evaluation_totals.find_one({"_id": run_id}) or {}
    latest_metric = database.pipeline_metrics.find_one(
        {"run_id": run_id}, sort=[("batch_id", DESCENDING)]
    ) or {}
    metrics = list(
        database.pipeline_metrics.find({"run_id": run_id}, {"_id": 0})
        .sort("batch_id", DESCENDING).limit(60)
    )
    metrics.reverse()
    aggregates = list(database.live_aggregates.find({"run_id": run_id}, {"_id": 0}))
    alerts_count = database.fraud_alerts.count_documents({"run_id": run_id})
    recent_transactions = list(
        database.recent_transactions.find({"run_id": run_id}, {"_id": 0})
        .sort("scored_at", DESCENDING).limit(60)
    )
    recent_alerts = list(
        database.fraud_alerts.find({"run_id": run_id}, {"_id": 0})
        .sort("scored_at", DESCENDING).limit(300)
    )
    system = database.system_metrics.find_one({"_id": "spark"}) or {}
    query_latency_ms = (time.perf_counter() - load_started) * 1000

    emitted = int(run.get("events_emitted", 0))
    processed = int(evaluation.get("processed", 0))
    lag = max(0, emitted - processed)
    model = detector_metrics(evaluation, "model")
    ranking = evaluation.get("latest_ranking", {})
    status = run.get("status", "unknown")
    is_live = status in {"starting", "running"}
    freshness = 0.0
    if evaluation.get("updated_at"):
        freshness = max(0.0, (datetime.now(UTC) - evaluation["updated_at"]).total_seconds())
    aggregate_count = sum(int(item.get("transactions", 0)) for item in aggregates)
    display_correct = aggregate_count == processed and alerts_count == model["TP"] + model["FP"]

    return SimpleNamespace(
        run=run,
        run_id=run_id,
        evaluation=evaluation,
        latest_metric=latest_metric,
        metrics=metrics,
        aggregates=aggregates,
        alerts_count=alerts_count,
        recent_transactions=recent_transactions,
        recent_alerts=recent_alerts,
        system=system,
        query_latency_ms=query_latency_ms,
        emitted=emitted,
        processed=processed,
        lag=lag,
        model=model,
        ranking=ranking,
        status=status,
        is_live=is_live,
        freshness=freshness,
        aggregate_count=aggregate_count,
        display_correct=display_correct,
    )


def render_page(snapshot, page):
    run = snapshot.run
    run_id = snapshot.run_id
    evaluation = snapshot.evaluation
    latest_metric = snapshot.latest_metric
    metrics = snapshot.metrics
    aggregates = snapshot.aggregates
    alerts_count = snapshot.alerts_count
    recent_transactions = snapshot.recent_transactions
    recent_alerts = snapshot.recent_alerts
    system = snapshot.system
    query_latency_ms = snapshot.query_latency_ms
    emitted = snapshot.emitted
    processed = snapshot.processed
    lag = snapshot.lag
    model = snapshot.model
    ranking = snapshot.ranking
    status = snapshot.status
    is_live = snapshot.is_live
    freshness = snapshot.freshness
    aggregate_count = snapshot.aggregate_count
    display_correct = snapshot.display_correct
    pages = PAGES
    history = pd.DataFrame(metrics)
    if page == pages[0]:
        if history.empty:
            st.info("Đang chờ micro-batch đầu tiên.")
        else:
            if True:
                chart_left, chart_right = st.columns(2)
                with chart_left:
                    st.subheader("Tốc độ ingest và xử lý")
                    line_chart(
                        history,
                        ["ingest_throughput", "processing_throughput"],
                        {"ingest_throughput": "Replayer → Kafka", "processing_throughput": "Spark processing"},
                        "Events/second",
                    )
                with chart_right:
                    st.subheader("Kafka consumer lag")
                    line_chart(history, ["consumer_lag"], {"consumer_lag": "Events đang chờ"}, "Events")

                chart_left, chart_right = st.columns(2)
                with chart_left:
                    st.subheader("Latency thay đổi theo micro-batch")
                    line_chart(
                        history,
                        ["ingest_latency_p95_ms", "latency_p95_ms"],
                        {"ingest_latency_p95_ms": "Ingest p95", "latency_p95_ms": "End-to-end p95"},
                        "Milliseconds",
                    )
                with chart_right:
                    st.subheader("Micro-batch duration")
                    line_chart(history, ["batch_duration_seconds"], {"batch_duration_seconds": "Batch duration"}, "Seconds")

            st.subheader("60 micro-batch gần nhất")
            columns = [column for column in [
                "batch_id", "created_at", "input_rows", "processed_rows",
                "consumer_lag", "processing_throughput", "latency_p95_ms",
                "invalid_rows", "duplicate_removed", "alerts",
            ] if column in history.columns]
            st.dataframe(
                history[columns].sort_values("batch_id", ascending=False),
                hide_index=True,
                column_config={
                    "batch_id": "Batch", "created_at": "Thời gian",
                    "input_rows": "Input", "processed_rows": "Processed",
                    "consumer_lag": "Kafka lag", "processing_throughput": "Processing ev/s",
                    "latency_p95_ms": "Latency p95 (ms)", "invalid_rows": "Bad records",
                    "duplicate_removed": "Duplicates removed", "alerts": "Alerts",
                },
            )

    elif page == pages[1]:
        st.info(
            "Metric live thay đổi theo từng micro-batch. Những metric ghi “Benchmark-only” "
            "cần chạy protocol before/after riêng và không được giả lập từ live telemetry."
        )
        total_storage = latest_metric.get("storage_size_bytes", 0)
        bad_rate = int(latest_metric.get("invalid_rows", 0)) / max(int(latest_metric.get("input_rows", 0)), 1)
        late_rate = int(latest_metric.get("late_event_rows", 0)) / max(int(latest_metric.get("processed_rows", 0)), 1)
        event_loss = int(run.get("delivery_errors", 0)) + int(evaluation.get("ground_truth_missing", 0))

        track_block(1, "Ingestion", "Replayer → Kafka → Spark consumer", [
            ("Ingest throughput", f"{fmt_float(latest_metric.get('ingest_throughput'))} ev/s", "ingest_throughput", "Tốc độ event được phát vào Kafka"),
            ("Consumer lag", fmt_int(lag), "consumer_lag", "Events đã phát nhưng Spark chưa xử lý"),
            ("Ingest latency p95", f"{fmt_float(latest_metric.get('ingest_latency_p95_ms'), 0)} ms", "ingest_latency_p95", "95% events vào Kafka trong thời gian này"),
        ], f"Delivery errors={fmt_int(run.get('delivery_errors'))}; duplicates injected={fmt_int(run.get('duplicates_injected'))}")

        track_block(2, "Storage", "HDFS Bronze / Silver / Gold", [
            ("Storage size", fmt_bytes(total_storage), "storage_size", "Tổng dung lượng ba lớp dữ liệu"),
            ("Compression ratio", f"{fmt_float(latest_metric.get('compression_ratio'), 2)}×", "compression_ratio", "Raw JSON bytes / Bronze Parquet bytes"),
            ("Write duration", f"{fmt_float(latest_metric.get('storage_write_seconds'), 2)} s", "write_duration", "Tổng thời gian ghi Bronze, Silver và Gold"),
            ("Read duration", "Benchmark-only", "read_duration", "Đo trong workload đọc chuẩn hóa"),
            ("Small files", fmt_int(latest_metric.get("small_file_count")), "small_file_count", "Số file dữ liệu tích lũy trên HDFS"),
        ], f"Processed records={fmt_int(processed)}; HDFS record guardrail được đối chiếu qua pipeline count")

        track_block(3, "Data Quality", "Validate, deduplicate, null và late event", [
            ("Bad record rate", fmt_pct(bad_rate), "bad_record_rate", "Tỷ lệ record không hợp lệ"),
            ("Duplicates removed", fmt_int(latest_metric.get("duplicate_removed")), "duplicate_removed", "Bản ghi trùng bị loại trong batch mới nhất"),
            ("Late event rate", fmt_pct(late_rate), "late_event_rate", "Event trễ hơn ingest trên một phút"),
            ("Event completeness", fmt_pct(latest_metric.get("event_completeness", 1.0)), "event_completeness", "Valid unique records / input records"),
            ("Transformation", "PASS" if latest_metric.get("transformation_correctness") else "CHECK", "transformation_correctness", "Aggregate output khớp valid row count"),
        ], f"Ground truth missing={fmt_int(evaluation.get('ground_truth_missing'))}")

        track_block(4, "Stream Processing", "Spark Structured Streaming", [
            ("Micro-batch", f"{fmt_float(latest_metric.get('batch_duration_seconds'), 2)} s", "microbatch_duration", "Thời gian xử lý batch gần nhất"),
            ("Processing throughput", f"{fmt_float(latest_metric.get('processing_throughput'))} ev/s", "processing_throughput", "Valid events xử lý mỗi giây"),
            ("Processing latency p95", f"{fmt_float(latest_metric.get('latency_p95_ms'), 0)} ms", "processing_latency_p95", "End-to-end latency p95"),
            ("Late events handled", fmt_int(latest_metric.get("late_event_rows")), "late_event_handling", "Late events được nhận diện trong batch"),
        ], f"Lag={fmt_int(lag)}; duplicates removed={fmt_int(latest_metric.get('duplicate_removed'))}")

        track_block(5, "SQL Analytics", "Spark SQL rule và aggregate nghiệp vụ", [
            ("Query duration", f"{fmt_float(latest_metric.get('sql_query_duration_ms'), 1)} ms", "query_duration", "Thời gian groupBy aggregate theo loại giao dịch"),
            ("Aggregate correctness", "PASS" if latest_metric.get("aggregate_correctness") else "CHECK", "aggregate_correctness", "Tổng aggregate khớp valid rows"),
            ("Scan size", "Benchmark-only", "scan_size", "Đo bằng workload truy vấn chuẩn"),
            ("Partition pruning", "run_id / type", "partition_pruning", "Silver partition theo run và loại giao dịch"),
        ], "Semantics aggregate giữ nguyên; expected output khớp processed count")

        track_block(6, "Fraud Detection", "Spark MLlib model và feature", [
            ("PR-AUC", fmt_pct(ranking.get("pr_auc")), "pr_auc (latest batch)", "Average precision của batch gần nhất"),
            ("Recall@K", fmt_pct(ranking.get("recall_at_k")), "recall_at_k", "Tỷ lệ fraud nằm trong top K batch gần nhất"),
            ("Precision@K", fmt_pct(ranking.get("precision_at_k")), "precision_at_k", "Tỷ lệ fraud trong top K"),
            ("F1", fmt_pct(model["F1"]), "f1", "F1 tích lũy của run"),
            ("Scoring latency", f"{fmt_float(latest_metric.get('scoring_latency_ms_per_1k'), 1)} ms/1K", "scoring_latency", "Thời gian scoring quy đổi trên 1.000 records"),
        ], f"Alert rate={fmt_pct(model['Alert rate'])}; feature set không dùng label")

        track_block(7, "Alert Optimization", "Risk score, threshold và Top-K", [
            ("Precision@K", fmt_pct(ranking.get("precision_at_k")), "precision_at_k", "Precision trong top K batch gần nhất"),
            ("Recall@K", fmt_pct(ranking.get("recall_at_k")), "recall_at_k", "Recall trong top K batch gần nhất"),
            ("Fraud in Top-K", f"{fmt_int(ranking.get('fraud_in_top_k'))}/{fmt_int(ranking.get('top_k'))}", "fraud_in_top_k", "Số fraud thực trong top K"),
            ("Alert volume", fmt_int(alerts_count), "alert_volume", "Tổng alert tích lũy"),
            ("Alert rate", fmt_pct(model["Alert rate"]), "alert_rate", "Tỷ lệ giao dịch thành alert"),
        ], "Threshold=0.50; recall tổng và evaluation set không bị thay đổi")

        track_block(8, "Serving", "MongoDB document, index và query", [
            ("Mongo write latency", f"{fmt_float(latest_metric.get('mongo_write_latency_ms'), 1)} ms", "mongo_write_latency", "Thời gian ghi alerts, recent events, aggregates và evaluation"),
            ("Query latency", f"{fmt_float(query_latency_ms, 1)} ms", "query_latency (snapshot)", "Thời gian dashboard tải snapshot MongoDB"),
            ("Write success", fmt_pct(latest_metric.get("mongo_write_success_rate", 0.0)), "write_success_rate", "Tỷ lệ write operation thành công"),
        ], f"Alert count={fmt_int(alerts_count)}; Gold-to-serving count được kiểm tra live")

        track_block(9, "Dashboard", "Streamlit query, cache và hiển thị", [
            ("Dashboard freshness", f"{fmt_float(freshness, 1)} s", "dashboard_freshness", "Độ trễ từ evaluation mới nhất tới UI"),
            ("Snapshot response", f"{fmt_float(query_latency_ms, 1)} ms", "dashboard_response_time", "Thời gian tải toàn bộ dữ liệu cho một refresh"),
            ("Display correctness", "PASS" if display_correct else "SYNCING", "display_correctness", "Aggregate, processed và alert count nhất quán"),
        ], "Refresh 2 giây; metric definitions lấy trực tiếp từ telemetry canonical")

        track_block(10, "Reliability", "Checkpoint, persistence và restart", [
            ("Recovery time", f"{fmt_float(system.get('recovery_time_seconds'), 1)} s", "recovery_time", "Thời gian Spark từ start tới query ready"),
            ("Event loss", fmt_int(event_loss), "event_loss_after_restart", "Delivery errors cộng ground truth missing"),
            ("Duplicates after restart", fmt_int(latest_metric.get("duplicate_removed")), "duplicate_after_restart", "Duplicates Spark loại trong batch"),
            ("Pipeline status", "RUNNING" if system.get("status") == "running" else "CHECK", "pipeline_run_success", "Spark query và checkpoint đang hoạt động"),
            ("Spark starts", fmt_int(system.get("restart_count")), "restart_count", "Số lần Spark pipeline được khởi động"),
        ], f"Checkpoint HDFS active; processed={fmt_int(processed)}; lag={fmt_int(lag)}")

    elif page == pages[2]:
        left, right = st.columns(2)
        with left:
            st.subheader("Rule baseline vs Spark MLlib")
            render_detector_comparison(evaluation)
        with right:
            st.subheader("Confusion matrix — Spark MLlib")
            render_confusion_matrix(model)

        if aggregates:
            aggregate_frame = pd.DataFrame(aggregates)
            st.subheader("Giao dịch và alerts theo nghiệp vụ")
            plot = aggregate_frame.melt(
                id_vars=["type"], value_vars=["model_alerts", "rule_alerts"],
                var_name="Detector", value_name="Alerts",
            )
            bars = (
                alt.Chart(plot).mark_bar().encode(
                    x=alt.X("type:N", title="Loại giao dịch", sort="-y"),
                    y=alt.Y("Alerts:Q", title="Số alerts"),
                    color=alt.Color("Detector:N", title="Detector"),
                    xOffset="Detector:N",
                    tooltip=["type", "Detector", alt.Tooltip("Alerts", format=",")],
                ).properties(height=310)
            )
            st.altair_chart(bars)

        if recent_alerts:
            alert_frame = pd.DataFrame(recent_alerts)
            st.subheader("Risk score và giá trị giao dịch — 300 alerts mới nhất")
            scatter = (
                alt.Chart(alert_frame).mark_circle(opacity=.65, size=65).encode(
                    x=alt.X("amount:Q", title="Số tiền", scale=alt.Scale(type="log")),
                    y=alt.Y("risk_score:Q", title="Risk score", scale=alt.Scale(domain=[0, 1])),
                    color=alt.Color("type:N", title="Loại giao dịch"),
                    tooltip=["event_id", "type", alt.Tooltip("amount", format=",.2f"), alt.Tooltip("risk_score", format=".4f")],
                ).properties(height=360).interactive()
            )
            st.altair_chart(scatter)

    elif page == pages[3]:
        st.subheader("Giao dịch vừa đi qua Spark")
        st.caption("Bảng tự đổi sau mỗi micro-batch; dòng mới nhất nằm trên cùng.")
        if recent_transactions:
            frame = pd.DataFrame(recent_transactions)
            columns = [column for column in [
                "scored_at", "event_id", "source_cycle", "source_row", "type",
                "amount", "risk_score", "prediction", "end_to_end_latency_ms",
            ] if column in frame.columns]
            st.dataframe(
                frame[columns], hide_index=True,
                column_config={
                    "scored_at": "Scored at", "event_id": "Event ID",
                    "source_cycle": "Cycle", "source_row": "Source row",
                    "type": "Transaction type", "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
                    "risk_score": st.column_config.ProgressColumn("Risk score", min_value=0.0, max_value=1.0, format="%.4f"),
                    "prediction": "Alert", "end_to_end_latency_ms": "E2E latency (ms)",
                },
            )
        else:
            st.info("Đang chờ batch giao dịch mới.")

        if aggregates:
            st.subheader("Tổng hợp live theo transaction type")
            aggregate_frame = pd.DataFrame(aggregates).sort_values("transactions", ascending=False)
            donut = (
                alt.Chart(aggregate_frame).mark_arc(innerRadius=70).encode(
                    theta=alt.Theta("transactions:Q"),
                    color=alt.Color("type:N", legend=alt.Legend(orient="right")),
                    tooltip=["type", alt.Tooltip("transactions", format=","), alt.Tooltip("total_amount", format=",.2f")],
                ).properties(height=350)
            )
            st.altair_chart(donut)



@st.fragment(run_every=2.0)
def live_dashboard(view=None, selected_page=None):
    snapshot = load_snapshot()
    if snapshot is None:
        st.info("The pipeline is getting ready. The replayer starts after Spark is ready.")
        return
    if view is not None:
        view.render(snapshot, selected_page)
        return
    run = snapshot.run
    run_id = snapshot.run_id
    evaluation = snapshot.evaluation
    latest_metric = snapshot.latest_metric
    metrics = snapshot.metrics
    aggregates = snapshot.aggregates
    alerts_count = snapshot.alerts_count
    recent_transactions = snapshot.recent_transactions
    recent_alerts = snapshot.recent_alerts
    system = snapshot.system
    query_latency_ms = snapshot.query_latency_ms
    emitted = snapshot.emitted
    processed = snapshot.processed
    lag = snapshot.lag
    model = snapshot.model
    ranking = snapshot.ranking
    status = snapshot.status
    is_live = snapshot.is_live
    freshness = snapshot.freshness
    aggregate_count = snapshot.aggregate_count
    display_correct = snapshot.display_correct
    dot_class = "live-dot" if is_live else "live-dot idle-dot"
    status_text = "LIVE — dữ liệu đang chảy" if is_live else f"{status.upper()}"
    st.markdown(
        f'<div class="live-line"><span class="{dot_class}"></span><b>{status_text}</b>'
        f'<span>· run {run_id} · refresh 2 giây · {datetime.now(UTC).strftime("%H:%M:%S UTC")}</span></div>',
        unsafe_allow_html=True,
    )

    if view is None:
        top = st.columns(3)
        top[0].metric("Nguồn đã phát", fmt_int(emitted), help="Tổng events Replayer đã đưa vào Kafka")
        top[1].metric("Spark đã xử lý", fmt_int(processed), delta=f"{fmt_int(lag)} đang chờ")
        top[2].metric("Fraud alerts", fmt_int(alerts_count), delta=fmt_pct(model["Alert rate"]))
        top = st.columns(3)
        top[0].metric("Ingest hiện tại", f"{fmt_float(run.get('instant_emission_rate'))} ev/s")
        top[1].metric("Processing throughput", f"{fmt_float(latest_metric.get('processing_throughput'))} ev/s")
        top[2].metric("End-to-end latency p95", f"{fmt_float(latest_metric.get('latency_p95_ms'), 0)} ms")
    else:
        view.metrics(run, emitted, processed, lag, alerts_count, model, latest_metric)

    source_progress = min(float(run.get("source_progress_pct", 0.0)), 1.0)
    st.caption(
        f"Dataset cycle {int(run.get('source_cycle', 1))} · dòng nguồn "
        f"{fmt_int(run.get('source_row'))}/{fmt_int(run.get('dataset_rows'))}"
    )
    st.progress(source_progress, text=f"Tiến độ vòng dữ liệu hiện tại: {source_progress:.2%}")
    st.markdown(pipeline_html(), unsafe_allow_html=True)

    pages = PAGES
    if view is None:
        page = st.radio(
            "Chế độ xem",
            pages,
            horizontal=True,
            label_visibility="collapsed",
            key="dashboard_page",
        )
    else:
        page = selected_page

    render_page(snapshot, page)





def render(view=None):
    if view is not None:
        st.set_page_config(**view.PAGE_CONFIG)
        selected_page = view.setup()
        live_dashboard(view, selected_page)
        return
    st.set_page_config(
        page_title="PaySim Big Data Baseline",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.6rem; padding-bottom: 3rem;}
        [data-testid="stMetric"] {
            background: linear-gradient(145deg, #ffffff, #f5f7fb);
            border: 1px solid #e3e8f0; border-radius: 12px; padding: 12px 14px;
        }
        [data-testid="stMetricLabel"] {font-weight: 650;}
        .live-line {display:flex; align-items:center; gap:9px; color:#4b5563; margin-bottom:8px;}
        .live-dot {width:10px; height:10px; border-radius:50%; background:#16a34a;
            box-shadow:0 0 0 rgba(22,163,74,.6); animation:pulse 1.4s infinite;}
        .idle-dot {background:#94a3b8; animation:none;}
        @keyframes pulse {0%{box-shadow:0 0 0 0 rgba(22,163,74,.6)}70%{box-shadow:0 0 0 10px rgba(22,163,74,0)}100%{box-shadow:0 0 0 0 rgba(22,163,74,0)}}
        .pipeline-flow {display:flex; align-items:center; width:100%; overflow-x:auto;
            padding:16px 2px 22px 2px; gap:3px;}
        .flow-node {min-width:78px; padding:11px 4px; border-radius:12px; font-size:.82rem;
            border:1px solid #dbe4ef; background:#fff; text-align:center; font-weight:700;
            box-shadow:0 3px 10px rgba(15,23,42,.05);}
        .flow-node small {display:block; color:#64748b; font-weight:500; font-size:.66rem; margin-top:3px;}
        .flow-arrow {position:relative; min-width:12px; height:3px; background:#cbd5e1; overflow:visible;}
        .flow-arrow:after {content:'›'; position:absolute; right:-2px; top:-15px; color:#64748b; font-size:26px;}
        .packet {position:absolute; width:8px; height:8px; border-radius:50%; background:#2563eb;
            top:-3px; left:0; animation:flow 1.7s linear infinite;}
        @keyframes flow {from{transform:translateX(0)}to{transform:translateX(38px)}}
        .metric-code {font-family:monospace; color:#64748b; font-size:.76rem; margin-top:-6px;}
        .track-title {margin-bottom:0!important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


    if view is None:
        st.title("PaySim — Live Big Data Control Room")
    else:
        view.header()
    st.write(
        "Theo dõi dữ liệu giao dịch đi xuyên suốt pipeline, metric vận hành và "
        "không gian cải tiến của 10 optimization tracks."
    )

    with st.sidebar:
        st.header("System UIs")
        st.link_button("HDFS NameNode", "http://127.0.0.1:9870")
        st.link_button("Spark Web UI", "http://127.0.0.1:4040")
        st.caption("Dùng 127.0.0.1 để tách cookie localhost giữa các công cụ.")
        st.divider()
        st.markdown("**Live mode mặc định**")
        st.caption("50 events/s · loop toàn bộ PaySim · refresh UI 2 giây")
        st.code("docker compose logs -f replayer spark", language="bash")

    # Navigation outside the fragment: sidebar widgets cannot be written by a main-area fragment.
    selected_page = view.navigation(PAGES) if view is not None else None
    live_dashboard(view, selected_page)
