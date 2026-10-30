"""Shared, local presentation assets. Never queries or changes pipeline data."""
from functools import lru_cache
import base64
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from dashboard_core import PAGES, fmt_float, fmt_int, fmt_pct

PAGE_LABELS = dict(zip(PAGES, ['📡 Live Control Room', '🎯 Metrics theo 10 tracks', '🛡️ Fraud & Business', '🔎 New data streams']))

PALETTE = ['#AD476B', '#8270A7', "#C1428A", '#548A80', '#C86953', '#657E9D']

# Small Lucide/Feather icons, vendored locally (see assets/LICENSE-icons.txt).
_ICONS = {
    'activity': '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    'wallet': '<path d="M20 8V5a2 2 0 0 0-2-2H5a3 3 0 0 0 0 6h15v11H5a3 3 0 0 1-3-3V6"/><path d="M20 12h-5v4h5"/>',
    'shield': '<path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/>',
    'shield-alert': '<path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="M12 8v4m0 4h.01"/>',
    'sliders': '<path d="M4 21v-7m0-4V3m8 18v-9m0-4V3m8 18v-5m0-4V3M1 14h6m2-6h6m2 8h6"/>',
    'receipt': '<path d="M4 3v18l4-2 4 2 4-2 4 2V3l-4 2-4-2-4 2-4-2Z"/><path d="M8 9h8M8 13h6"/>',
    'download': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
    'search': '<circle cx="10.5" cy="10.5" r="7.5"/><path d="m16 16 5 5"/>',
    'clock': '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    'check': '<path d="m5 12 4 4L19 6"/>',
    'sparkles': '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3ZM20 2v4m-2-2h4"/>',
    'arrow-up-right': '<path d="M7 17 17 7M7 7h10v10"/>',
    'arrow-right': '<path d="M5 12h14m-6-6 6 6-6 6"/>',
    'database': '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 4 18 4 18 0V5M3 12c0 4 18 4 18 0"/>',
    'layers': '<path d="m12 3 10 5-10 5L2 8l10-5ZM2 12l10 5 10-5M2 16l10 5 10-5"/>',
    'target': '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    'chart': '<path d="M3 3v18h18M7 14l4-4 4 3 6-8"/>',
    'file-text': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6ZM14 2v6h6M8 13h8M8 17h6"/>',
}


def icon(name: str, size: int = 18) -> str:
    aliases = {'filter': 'sliders', 'shield-check': 'shield', 'receipt-text': 'receipt',
               'wallet-cards': 'wallet', 'bar-chart-3': 'chart'}
    drawing = _ICONS.get(aliases.get(name, name), _ICONS['activity'])
    return (f'<svg width="{int(size)}" height="{int(size)}" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="1.65" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{drawing}</svg>')


@lru_cache(maxsize=1)
def _css() -> str:
    return (Path(__file__).parent / 'assets' / 'dashboard.css').read_text(encoding='utf-8')


@lru_cache(maxsize=1)
def _hero_document() -> str:
    assets = Path(__file__).parent / 'assets'
    image = base64.b64encode((assets / 'fluid-glass.png').read_bytes()).decode('ascii')
    return (assets / 'hero.html').read_text(encoding='utf-8').replace('__FLUID_IMAGE__', 'data:image/png;base64,' + image)


def setup_shell() -> str:
    """The decorative scene stays mounted outside the 2-second data fragment."""
    st.markdown(f'<style>{_css()}</style>', unsafe_allow_html=True)
    label = 'LIVE DATA WORKSPACE'
    st.markdown(
        '<div class="workspace-top"><div class="workspace-brand"><span class="brand-mark">'
        + icon('layers', 21) + '</span><strong>PaySim</strong><span class="brand-divider">/</span>'
        '<span>data workspace</span></div><span class="workspace-edition">' + label + '</span></div>',
        unsafe_allow_html=True,
    )
    with st.container(key='workspace-hero-frame'):
        components.html(_hero_document(), height=468, scrolling=False, tab_index=-1)
    selected = st.radio('View', PAGES, index=0, format_func=PAGE_LABELS.get,
                        horizontal=True, key='dashboard_page', label_visibility='collapsed')
    with st.sidebar:
        st.markdown('### PaySim workspace')
        st.caption('System tools')
        st.link_button('HDFS NameNode ↗', 'http://127.0.0.1:9870')
        st.link_button('Spark Web UI ↗', 'http://127.0.0.1:4040')
        st.caption('Filters affect the visible records. Results for the full run stay unchanged.')
        st.caption('Icons: Lucide / Feather · ISC / MIT')
    return selected


def section(title: str, eyebrow: str = '', description: str = '') -> None:
    st.markdown('<div class="section-heading">'
                + (f'<span class="eyebrow">{escape(eyebrow)}</span>' if eyebrow else '')
                + f'<h3>{escape(title)}</h3>'
                + (f'<p>{escape(description)}</p>' if description else '') + '</div>',
                unsafe_allow_html=True)


def run_header(s) -> None:
    status = str(s.status).upper()
    st.markdown(
        f'<div class="run-strip"><span class="run-state {"is-live" if s.is_live else "is-idle"}">'
        f'<i></i>{escape(status)}</span><span class="run-id">{escape(str(s.run_id))}</span>'
        f'<span class="run-cycle">Cycle {escape(str(s.run.get("source_cycle", 1)))}</span></div>',
        unsafe_allow_html=True,
    )


def run_metrics(s) -> None:
    """The same six labels, values and deltas as the original Control Room."""
    items = [
        ('Source emitted', fmt_int(s.emitted), None, 'wallet'),
        ('Spark processed', fmt_int(s.processed), f'{fmt_int(s.lag)} pending', 'layers'),
        ('Fraud alerts', fmt_int(s.alerts_count), fmt_pct(s.model['Alert rate']), 'shield-alert'),
        ('Current ingest', f"{fmt_float(s.run.get('instant_emission_rate'))} ev/s", None, 'activity'),
        ('Processing throughput', f"{fmt_float(s.latest_metric.get('processing_throughput'))} ev/s", None, 'chart'),
        ('End-to-end latency p95', f"{fmt_float(s.latest_metric.get('latency_p95_ms'), 0)} ms", None, 'clock'),
    ]
    for offset in (0, 3):
        columns = st.columns(3)
        for index, (column, (label, value, delta, symbol)) in enumerate(zip(columns, items[offset:offset + 3]), start=offset):
            with column:
                with st.container(border=True, key=f'panel-kpi-{index}'):
                    st.markdown('<span class="metric-illustration">' + icon(symbol) + '</span>', unsafe_allow_html=True)
                    st.metric(label, value, delta=delta, delta_color='off')


def style_chart(chart):
    return chart.configure(
        background='transparent', view={'stroke': None},
        axis={'labelColor': '#785D65', 'titleColor': '#60454E', 'gridColor': '#F0E3DE',
              'domain': False, 'ticks': False, 'labelFont': 'Segoe UI', 'titleFont': 'Segoe UI',
              'labelFontSize': 11, 'titleFontSize': 12, 'titlePadding': 12},
        legend={'labelColor': '#60454E', 'titleColor': '#60454E', 'labelFont': 'Segoe UI',
                'titleFont': 'Segoe UI', 'symbolType': 'circle'},
        range={'category': PALETTE},
        title={'color': '#503741', 'font': 'Segoe UI', 'anchor': 'start'},
    )


def activity_feed(s, *, limit: int = 4) -> None:
    section('Recent activity', 'LATEST TRANSACTIONS')
    if not s.recent_transactions:
        st.info('Waiting for new transactions from the pipeline.')
        return
    # Only already-loaded records. IDs, amounts and predictions are escaped.
    for row in s.recent_transactions[:limit]:
        flagged = bool(row.get('prediction'))
        st.markdown(
            '<div class="activity-item"><span class="activity-icon">' + icon('receipt') + '</span>'
            '<div><strong>' + escape(str(row.get('type', '—'))) + '</strong>'
            '<span class="activity-id">' + escape(str(row.get('event_id', '—'))) + '</span></div>'
            '<div class="activity-value"><strong>' + fmt_float(row.get('amount'), 2) + '</strong>'
            '<span class="' + ('alert-text' if flagged else '') + '">'
            + ('Alert' if flagged else 'No alert') + '</span></div></div>',
            unsafe_allow_html=True,
        )


def footer(s) -> None:
    st.markdown('<div class="workspace-footer"><span>' + icon('database', 14)
                + ' Same data · same results</span><span>PaySim / live analytics</span></div>',
                unsafe_allow_html=True)
