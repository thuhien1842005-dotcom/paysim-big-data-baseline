"""Read-only exploration of the current snapshot; no database or scoring calls.

Filters only affect loaded rows. Canonical run metrics are rendered by the views
and never recomputed from this small, filtered window.
"""
from __future__ import annotations

from datetime import datetime, time, timezone
from hashlib import sha256
from html import escape
import math
from typing import Iterable

import pandas as pd
import streamlit as st

from dashboard_core import fmt_float
from ui_theme import icon, section


PREDICTIONS = ("All", "Alert", "No alert")
TRANSACTION_TYPES = ("CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER")
DISPLAY_COLUMNS = (
    "scored_at", "event_id", "type", "amount", "risk_score", "prediction",
    "source_cycle", "source_row", "end_to_end_latency_ms",
)


def _number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _prediction_flag(value):
    if isinstance(value, str):
        value = value.strip().casefold()
        if value in {"1", "1.0", "true", "alert", "có cảnh báo"}:
            return True
        if value in {"0", "0.0", "false", "no alert", "không cảnh báo"}:
            return False
        return None
    if value is None:
        return None
    if value == 1:
        return True
    if value == 0:
        return False
    return None


def _timestamp(value):
    try:
        parsed = pd.to_datetime(value, utc=True, errors="coerce")
        return None if pd.isna(parsed) else parsed
    except (TypeError, ValueError):
        return None


def _within(value, bounds):
    if bounds is None:
        return True
    low, high = bounds
    if low is None and high is None:
        return True
    number = _number(value)
    return number is not None and (low is None or number >= low) and (high is None or number <= high)


def filter_records(
    records: Iterable[dict], *, types=None, amount_range=None, score_range=None,
    prediction="All", search="", start=None, end=None,
) -> list[dict]:
    """Copy matching rows in input order, with inclusive bounds.

    ``types=None`` means all types; an empty collection matches none. Search is
    literal and case-insensitive against event_id. Time bounds and scored_at are
    parsed as UTC; rows with missing/invalid values only fail active filters.
    ``prediction`` accepts the three UI labels, 0/1 or booleans.
    """
    selected_types = None if types is None else {str(value) for value in types}
    needle = str(search or "").strip().casefold()
    required_prediction = None
    if prediction not in (None, "All", "all", "Tất cả"):
        required_prediction = _prediction_flag(prediction)
        if required_prediction is None:
            raise ValueError("prediction must be All, Alert, No alert, 0 or 1")
    start_at, end_at = _timestamp(start), _timestamp(end)
    if start is not None and start_at is None:
        raise ValueError("Invalid UTC start time")
    if end is not None and end_at is None:
        raise ValueError("Invalid UTC end time")
    result = []
    for source in records:
        if selected_types is not None and str(source.get("type", "")) not in selected_types:
            continue
        if needle and needle not in str(source.get("event_id", "")).casefold():
            continue
        if not _within(source.get("amount"), amount_range) or not _within(source.get("risk_score"), score_range):
            continue
        if required_prediction is not None and _prediction_flag(source.get("prediction")) != required_prediction:
            continue
        if start_at is not None or end_at is not None:
            scored_at = _timestamp(source.get("scored_at"))
            if scored_at is None or (start_at is not None and scored_at < start_at) or (end_at is not None and scored_at > end_at):
                continue
        result.append(dict(source))
    return result


def records_csv(records: Iterable[dict], columns=None) -> bytes:
    """UTF-8 CSV of the displayed rows, with text formula injection escaped."""
    frame = pd.DataFrame([dict(row) for row in records])
    columns = [name for name in (columns or DISPLAY_COLUMNS) if name in frame.columns]
    frame = frame.reindex(columns=columns).copy()

    def safe_cell(value):
        if isinstance(value, str) and value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
            return "'" + value
        return value

    for column in frame.columns:
        frame[column] = frame[column].map(safe_cell)
    return frame.to_csv(index=False).encode("utf-8-sig")


def _reset_filters(prefix):
    # New widget identities reset both server state and browser-local pending
    # input. Reusing deleted keys can restore old values on timed reruns.
    st.session_state[f'{prefix}_filter_generation'] = st.session_state.get(f'{prefix}_filter_generation', 0) + 1
    st.session_state[f'{prefix}_selected_id'] = None
    st.session_state.pop(f'{prefix}_last_table_selection', None)
    # A new table identity discards old positional row selections after reset.
    st.session_state[f"{prefix}_table_generation"] = st.session_state.get(f"{prefix}_table_generation", 0) + 1


def _time_bounds(prefix, records, enabled):
    dates = [stamp for row in records if (stamp := _timestamp(row.get("scored_at"))) is not None]
    earliest = min(dates).to_pydatetime() if dates else datetime.now(timezone.utc)
    latest = max(dates).to_pydatetime() if dates else earliest
    # Do not change widget defaults as the live window crosses a date boundary.
    default_start, default_end = st.session_state.setdefault(
        f"{prefix}_date_defaults", (earliest.date(), latest.date())
    )
    first, last = st.columns(2)
    with first:
        start_date = st.date_input("Start date (UTC)", value=default_start, key=f"{prefix}_start_date", disabled=not enabled)
        start_time = st.time_input("Start time (UTC)", value=time.min, key=f"{prefix}_start_time", disabled=not enabled, step=60)
    with last:
        end_date = st.date_input("End date (UTC)", value=default_end, key=f"{prefix}_end_date", disabled=not enabled)
        end_time = st.time_input("End time (UTC)", value=time(23, 59), key=f"{prefix}_end_time", disabled=not enabled, step=60)
    if not enabled:
        return None, None
    start = datetime.combine(start_date, start_time, tzinfo=timezone.utc)
    # Time picker precision is one minute: include that entire ending minute.
    end = datetime.combine(end_date, end_time, tzinfo=timezone.utc).replace(second=59, microsecond=999999)
    return start, end


def _filters(records, prefix, noun):
    base_prefix = prefix
    prefix = f'{base_prefix}_filters_{st.session_state.get(f"{base_prefix}_filter_generation", 0)}'
    types = sorted(set(TRANSACTION_TYPES).union(str(row.get("type")) for row in records if row.get("type")))
    with st.container(border=True, key=f'panel-{prefix}-filters'):
        st.markdown(f"{icon('filter')} **Filter {noun}**", unsafe_allow_html=True)
        first, second, third = st.columns([1.3, 1, 1])
        with first:
            selected_types = st.multiselect("Transaction type", types,
                default=st.session_state.get(f"{prefix}_types", types), key=f"{prefix}_types")
        with second:
            prediction = st.selectbox("Alert status", PREDICTIONS, key=f"{prefix}_prediction")
        with third:
            search = st.text_input("Search Event ID", placeholder="Enter part of a transaction ID…", key=f"{prefix}_search")
        first, second, third = st.columns([1, 1, 1.3])
        with first:
            minimum = st.number_input("Minimum amount", min_value=0.0, value=None, placeholder="No limit", key=f"{prefix}_amount_min")
        with second:
            maximum = st.number_input("Maximum amount", min_value=0.0, value=None, placeholder="No limit", key=f"{prefix}_amount_max")
        with third:
            score = st.slider("Risk score range", 0.0, 1.0, (0.0, 1.0), step=0.01, key=f"{prefix}_score", help="Filters existing scores only. The model threshold and predictions stay unchanged.")
        with st.expander("Time & display order"):
            enabled = st.toggle("Filter by UTC time", key=f"{prefix}_time_enabled")
            start, end = _time_bounds(prefix, records, enabled)
            order = st.radio("Transaction order", ("Newest first", "Oldest first"), horizontal=True, key=f"{prefix}_sort")
        st.button("Reset filters", key=f"{prefix}_reset", on_click=_reset_filters, args=(base_prefix,), icon=":material/filter_alt_off:")
    if minimum is not None and maximum is not None and minimum > maximum:
        st.warning("Minimum amount must be less than or equal to maximum amount.")
        return [], False
    if start is not None and start > end:
        st.warning("Start time must be before or equal to end time.")
        return [], False
    filtered = filter_records(records, types=selected_types, amount_range=(minimum, maximum), score_range=None if tuple(score) == (0.0, 1.0) else score, prediction=prediction, search=search, start=start, end=end)
    # The serving query already returns newest first. Reverse only this copy.
    if order == "Oldest first":
        filtered.reverse()
    return filtered, True


def _event_id(row):
    event_id = row.get("event_id")
    return str(event_id) if event_id is not None and str(event_id) else None


def _new_records(records, prefix, run_id):
    current_ids = {event_id for row in records if (event_id := _event_id(row)) is not None}
    previous = st.session_state.get(f"{prefix}_last_ids")
    previous_run = st.session_state.get(f"{prefix}_run_id")
    same_run = previous_run == run_id
    if previous_run is not None and not same_run:
        st.session_state[f"{prefix}_selected_id"] = None
        st.session_state.pop(f"{prefix}_last_table_selection", None)
        st.session_state[f"{prefix}_table_generation"] = st.session_state.get(f"{prefix}_table_generation", 0) + 1
        st.info("Switched to a new run. Select a transaction to view its details.")
    new_ids = current_ids.difference(previous or ()) if previous is not None and same_run else set()
    st.session_state[f"{prefix}_last_ids"] = current_ids
    st.session_state[f"{prefix}_run_id"] = run_id
    if new_ids:
        labels = " · ".join(escape(event_id) for event_id in sorted(new_ids)[:4])
        st.markdown(
            '<style>.tx-new-records{padding:10px 14px;border-radius:12px;background:#ffe9c7;color:#62452f;margin:6px 0 12px;animation:tx-arrival .45s ease-out;}@keyframes tx-arrival{from{transform:translateY(5px);opacity:.4}to{transform:translateY(0);opacity:1}}@media(prefers-reduced-motion:reduce){.tx-new-records{animation:none}}</style>'
            f'<div class="tx-new-records">{icon("sparkles")} <strong>{len(new_ids)} new records</strong> · {labels}</div>',
            unsafe_allow_html=True,
        )


def _inspector(row):
    with st.container(border=True, key='panel-inspector'):
        st.markdown(f"{icon('receipt')} **Transaction details**", unsafe_allow_html=True)
        st.code(str(row.get("event_id", "—")), language=None)
        left, right = st.columns(2)
        with left:
            st.caption("TRANSACTION TYPE")
            st.write(str(row.get("type", "—")))
        with right:
            st.caption("AMOUNT")
            st.write(fmt_float(row.get("amount"), 2) if _number(row.get("amount")) is not None else "No data yet")
        score = _number(row.get("risk_score"))
        if score is not None:
            st.progress(min(max(score, 0.0), 1.0), text=f"Recorded risk score: {score:.4f}")
        else:
            st.caption("No risk score is available for this record yet.")
        flag = _prediction_flag(row.get("prediction"))
        if flag is True:
            st.warning("Model prediction: Alert")
        elif flag is False:
            st.success("Model prediction: No alert")
        else:
            st.info("No prediction is available yet.")
        st.caption("An alert is a model prediction and does not confirm actual fraud.")
        scored_at = _timestamp(row.get("scored_at"))
        st.write(f"Scored at: {scored_at.isoformat() if scored_at is not None else '—'}")
        latency = _number(row.get("end_to_end_latency_ms"))
        st.caption(f"End-to-end latency: {fmt_float(latency, 0)} ms" if latency is not None else "End-to-end latency: no data yet")
        with st.expander("Transaction data fields"):
            st.json({name: value for name, value in row.items() if name != "_id"}, expanded=False)


def _render_records(s, *, prefix, alerts=False):
    records = [dict(row) for row in (s.recent_alerts if alerts else s.recent_transactions)]
    noun = "alerts" if alerts else "transactions"
    limit = 300 if alerts else 60
    section("Latest alerts" if alerts else "Latest transactions processed by Spark", eyebrow="ALERT EXPLORER" if alerts else "TRANSACTION EXPLORER", description=f"Explore up to {limit} of the latest {noun} in the current run.")
    _new_records(records, prefix, s.run_id)
    filtered, valid = _filters(records, prefix, noun)
    st.caption(f"Showing {len(filtered)}/{len(records)} loaded {noun} · up to {limit} records · searches this snapshot only.")
    st.caption("Filters apply to this explorer only. Run-wide KPIs and model quality remain unchanged.")
    if not records:
        # Keep the controls discoverable while waiting for the first batch.
        st.info("Waiting for new alerts." if alerts else "Waiting for a new transaction batch.")
        st.session_state[f"{prefix}_selected_id"] = None
        return
    source_ids = {event_id for row in records if (event_id := _event_id(row)) is not None}
    by_id = {_event_id(row): row for row in reversed(filtered) if _event_id(row) is not None}
    current = st.session_state.get(f"{prefix}_selected_id")
    if current is not None and current not in by_id:
        st.session_state[f"{prefix}_selected_id"] = None
        st.info("The selected transaction is no longer in the latest snapshot." if current not in source_ids else "The selected transaction is no longer in the filtered results.")
    if not filtered:
        if valid:
            st.info("No matching records. Try broader criteria or reset the filters.")
        return
    frame = pd.DataFrame(filtered)
    columns = [name for name in DISPLAY_COLUMNS if name in frame.columns]
    display = frame[columns].copy()
    # Fingerprint row order so a refreshed window never reuses positional
    # selection state for a different transaction. The inspector uses event_id.
    fingerprint = sha256(repr((s.run_id, [(_event_id(row), str(row.get("scored_at"))) for row in filtered])).encode()).hexdigest()[:14]
    generation = st.session_state.get(f"{prefix}_table_generation", 0)
    table_key = f"{prefix}_table_{fingerprint}_{generation}"
    event = st.dataframe(
        display, key=table_key, hide_index=True, height=min(480, max(160, 40 + len(filtered) * 35)),
        on_select="rerun", selection_mode="single-row",
        column_config={
            "scored_at": st.column_config.DatetimeColumn("Scored at (UTC)", format="YYYY-MM-DD HH:mm:ss", timezone="UTC"),
            "event_id": st.column_config.TextColumn("Event ID"),
            "type": st.column_config.TextColumn("Transaction type"),
            "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
            "risk_score": st.column_config.ProgressColumn("Risk score", min_value=0.0, max_value=1.0, format="%.4f"),
            "prediction": st.column_config.NumberColumn("Prediction (1 = alert)", format="%d"),
            "source_cycle": "Cycle", "source_row": "Source row",
            "end_to_end_latency_ms": st.column_config.NumberColumn("E2E latency (ms)", format="%.0f"),
        },
    )
    selection = tuple(getattr(getattr(event, "selection", None), "rows", ()))
    selection_token = (table_key, selection)
    if selection_token != st.session_state.get(f"{prefix}_last_table_selection"):
        st.session_state[f"{prefix}_last_table_selection"] = selection_token
        if selection and 0 <= selection[0] < len(filtered):
            selected = _event_id(filtered[selection[0]])
            if selected is not None:
                st.session_state[f"{prefix}_selected_id"] = selected
    left, right = st.columns([2, 1])
    with left:
        # Streamlit 1.50 rebuilds selectboxes when their options change. Restore
        # the default by ID, rather than letting a refreshed window clear it or
        # select whatever transaction moved into the former row position.
        ids = list(by_id)
        current_id = st.session_state.get(f"{prefix}_selected_id")
        selected = st.selectbox("Select transaction by Event ID", ids,
            index=ids.index(current_id) if current_id in by_id else None,
            placeholder="Select a table row or search for an ID here…", key=f"{prefix}_selected_id")
    with right:
        st.download_button("Download visible CSV", data=records_csv(filtered, columns), file_name=f"paysim-{noun}-{s.run_id}.csv", mime="text/csv", key=f"{prefix}_csv", icon=":material/download:", on_click="ignore")
    if selected is not None:
        with st.expander("Selected transaction", expanded=True):
            _inspector(by_id[selected])


def render_transactions(s, *, key_prefix="transactions"):
    """Render filters, table, CSV and a stable-by-event-ID inspector (max 60)."""
    _render_records(s, prefix=key_prefix)


def render_alerts(s, *, key_prefix="alerts"):
    """Render the same read-only explorer for the 300-alert snapshot window."""
    _render_records(s, prefix=key_prefix, alerts=True)
