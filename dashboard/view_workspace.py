"""One independently designed workspace, consuming the unmodified snapshot."""
import streamlit as st
from dashboard_core import PAGES
from ui_pages import render_page
from ui_theme import footer, run_header, run_metrics, setup_shell

PAGE_CONFIG = dict(page_title='PaySim | Data Workspace', layout='wide', initial_sidebar_state='collapsed')


def setup():
    return setup_shell()


def render(snapshot, page):
    # Scheduled fragment refreshes must use the current navigation, rather than
    # an earlier selected_page argument captured by a previous full-page run.
    page = st.session_state.get('dashboard_page', page)
    run_header(snapshot)
    # The explorer gets first use of the screen; its filters never affect KPIs.
    if page != PAGES[3]:
        run_metrics(snapshot)
    render_page(snapshot, page, key_prefix='workspace')
    if page == PAGES[3]:
        run_metrics(snapshot)
    footer(snapshot)
