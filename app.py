import streamlit as st
import pdfplumber
import re
import base64
import random
from collections import Counter
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, KeepInFrame
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.lib.units import inch

# PyMuPDF is used only to render generated PDFs as preview images inside Streamlit.
# If it is missing locally, install it automatically once so the preview works
# without requiring the user to run an extra command manually.
try:
    import fitz
except Exception:
    fitz = None
    try:
        import sys, subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMuPDF", "-q"])
        import fitz
    except Exception:
        fitz = None


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# UI THEME STATE — UI/UX ONLY
# Keeps every existing analysis/generation feature untouched.
# The selected theme is applied before the main CSS is rendered,
# so the entire Streamlit page follows the same palette.
# =========================================================
if "ui_theme_mode_v4" not in st.session_state:
    st.session_state.ui_theme_mode_v4 = "dark"

with st.sidebar:
    theme_is_dark = st.toggle(
        "🌙 Dark theme",
        value=st.session_state.ui_theme_mode_v4 == "dark",
        key="ui_theme_toggle_v4",
        help="Switch the complete application between the premium dark and clean light theme."
    )
    st.session_state.ui_theme_mode_v4 = "dark" if theme_is_dark else "light"

UI_THEME = st.session_state.ui_theme_mode_v4

st.markdown("""
<style>
/* =========================================================
   AI RESUME ANALYZER — FULL-PAGE STREAMLIT THEME BRIDGE
   These variables are defined INSIDE .stApp so Streamlit's
   Light/Dark theme variables resolve from the active app scope.
   ========================================================= */
.stApp {
  --app-bg: var(--background-color, #ffffff);
  --app-surface: var(--secondary-background-color, #f7f8fc);
  --app-text: var(--text-color, #172033);
  --app-primary: var(--primary-color, #6d5ef5);
  --app-border: color-mix(in srgb, var(--app-text) 20%, transparent);
  --app-muted: color-mix(in srgb, var(--app-text) 68%, transparent);
  --app-soft: color-mix(in srgb, var(--app-primary) 12%, var(--app-surface));
  background: var(--app-bg) !important;
  color: var(--app-text) !important;
}

/* FULL APPLICATION SURFACE */
html, body, #root, .stApp,
[data-testid="stApp"], [data-testid="stAppViewContainer"],
[data-testid="stMainViewContainer"], [data-testid="stMain"],
[data-testid="stAppViewBlockContainer"], [data-testid="stBottomBlockContainer"],
[data-testid="stMainBlockContainer"], [data-testid="stMainBlockContainer"] > div,
.main, .main > div, .main > div > div, .block-container,
section.main, section.main > div, [data-testid="stVerticalBlock"] {
  background-color: var(--app-bg) !important;
  color: var(--app-text) !important;
}
[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stBottom"] {
  background: var(--app-bg) !important;
  color: var(--app-text) !important;
}
.block-container { max-width:1420px; padding:1.5rem 2.2rem 4rem; }

/* SIDEBAR */
[data-testid="stSidebar"], [data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"], [data-testid="stSidebar"] > div {
  background:var(--app-surface) !important; color:var(--app-text) !important;
}
[data-testid="stSidebar"] * { color:var(--app-text) !important; }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background:var(--app-bg) !important; color:var(--app-text) !important;
  -webkit-text-fill-color:var(--app-text) !important;
}

/* TYPOGRAPHY */
.main p,.main li,.main label,.main small,.main strong,.main em,
.main h1,.main h2,.main h3,.main h4,.main h5,.main h6,
.main [data-testid="stMarkdownContainer"],
.main [data-testid="stMarkdownContainer"] p,
.main [data-testid="stMarkdownContainer"] li,
.main [data-testid="stCaptionContainer"],
[data-testid="stMetricLabel"],[data-testid="stMetricValue"],[data-testid="stMetricDelta"] {
  color:var(--app-text) !important; opacity:1 !important;
}
.main h1,.main h2,.main h3,.main h4,.main h5,.main h6 { background:transparent !important; text-shadow:none !important; }
.main a { color:var(--app-primary) !important; }
hr { border-color:var(--app-border) !important; }

/* HERO */
.premium-hero { padding:28px 32px; margin-bottom:22px; border-radius:22px;
  border:1px solid color-mix(in srgb,var(--app-primary) 45%,transparent) !important;
  background:linear-gradient(135deg,color-mix(in srgb,var(--app-primary) 18%,var(--app-surface)),var(--app-surface) 64%,var(--app-bg)) !important;
  color:var(--app-text) !important; box-shadow:0 10px 30px color-mix(in srgb,var(--app-text) 12%,transparent); }
.premium-hero * { color:var(--app-text) !important; }
.premium-hero .hero-kicker { color:var(--app-primary) !important; }
.hero-kicker { font-size:.78rem;text-transform:uppercase;letter-spacing:1.5px;font-weight:800;margin-bottom:7px; }
.hero-title { font-size:2.25rem;font-weight:850;letter-spacing:-1px;margin:0; }
.hero-copy { margin:7px 0 0;font-size:1rem;line-height:1.55;max-width:1050px; }
.main-title { font-size:2.7rem;font-weight:850;letter-spacing:-1.4px; }
.sub-title,.small-note { color:var(--app-muted) !important; }

/* CARDS */
.info-card,.resume-card,.section-head,.section-title-card,[data-testid="stMetric"],div[data-testid="stExpander"] {
  background:var(--app-surface) !important;color:var(--app-text) !important;
  border:1px solid var(--app-border) !important;
  box-shadow:0 8px 24px color-mix(in srgb,var(--app-text) 9%,transparent); }
.info-card *, .resume-card *, .section-head *, .section-title-card *,
[data-testid="stMetric"] *, div[data-testid="stExpander"] * { color:var(--app-text) !important; }
.info-card{border-radius:16px;padding:17px 19px}.resume-card{border-radius:16px;padding:19px;margin:8px 0 14px}
.section-head,.section-title-card{display:flex;align-items:center;gap:12px;margin:25px 0 12px;padding:14px 16px;border-radius:16px}
.section-head .num,.section-title-card .section-icon{width:34px;height:34px;min-width:34px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:var(--app-soft)!important;color:var(--app-primary)!important}
.section-head h2,.section-title-card .section-title{margin:0;font-size:1.45rem;font-weight:800;color:var(--app-text)!important}
.section-title-card .section-kicker,.step-chip{color:var(--app-primary)!important}
.section-title-card .section-kicker{font-size:.70rem;letter-spacing:1.2px;font-weight:800;text-transform:uppercase}
.step-chip{display:inline-block;padding:5px 10px;border-radius:999px;background:var(--app-soft)!important;font-size:.76rem;font-weight:750;margin-bottom:7px}
[data-testid="stMetric"]{padding:16px 17px;border-radius:16px;min-height:112px}
[data-testid="stMetricLabel"],[data-testid="stMetricLabel"] *{color:var(--app-muted)!important}
[data-testid="stMetricValue"],[data-testid="stMetricValue"] *{color:var(--app-text)!important}

/* LABELS — fixes Paste Job Description blending */
[data-testid="stTextArea"] label,
[data-testid="stTextArea"] label * {
  color:var(--app-text) !important;
  -webkit-text-fill-color:var(--app-text) !important;
  opacity:1 !important;
  font-weight:750 !important;
}
[data-testid="stTextArea"] [data-testid="InputInstructions"],
[data-testid="stTextArea"] [data-testid="InputInstructions"] * {
  color:var(--app-muted) !important; -webkit-text-fill-color:var(--app-muted) !important;
}

/* TEXTAREAS / INPUTS — tinted in both themes, never pure white */
[data-testid="stTextArea"] > div,
[data-testid="stTextArea"] > div > div,
[data-testid="stTextArea"] textarea {
  background:var(--app-soft) !important;color:var(--app-text)!important;
  -webkit-text-fill-color:var(--app-text)!important;
  border:1.5px solid color-mix(in srgb,var(--app-primary) 52%,transparent)!important;
  border-radius:12px!important; opacity:1!important;
}
[data-testid="stTextArea"] textarea::placeholder {
  color:var(--app-muted)!important;-webkit-text-fill-color:var(--app-muted)!important;opacity:1!important;
}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,[data-testid="stTimeInput"] input,
div[data-baseweb="select"] > div,div[data-baseweb="select"] input {
  background:var(--app-surface)!important;color:var(--app-text)!important;
  -webkit-text-fill-color:var(--app-text)!important;border-color:var(--app-border)!important;
}

/* UPLOADER — every nested surface, filename, size and icon has contrast */
[data-testid="stFileUploader"], [data-testid="stFileUploader"] > div,
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploaderDropzone"] > div {
  background:var(--app-surface)!important;color:var(--app-text)!important;
  border-color:var(--app-border)!important;opacity:1!important;
}
[data-testid="stFileUploader"] section {
  border:1.5px dashed color-mix(in srgb,var(--app-primary) 55%,var(--app-border))!important;
  border-radius:14px!important;
  background:color-mix(in srgb,var(--app-primary) 7%,var(--app-surface))!important;
}
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] label * {
  color:var(--app-text)!important;-webkit-text-fill-color:var(--app-text)!important;opacity:1!important;font-weight:750!important;
}
[data-testid="stFileUploader"] span,[data-testid="stFileUploader"] small,
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzoneInstructions"] * {
  color:var(--app-text)!important;-webkit-text-fill-color:var(--app-text)!important;opacity:1!important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"],
[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] > div {
  background:var(--app-surface)!important;color:var(--app-text)!important;
  border:1px solid var(--app-border)!important;border-radius:12px!important;opacity:1!important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] * {
  color:var(--app-text)!important;-webkit-text-fill-color:var(--app-text)!important;opacity:1!important;
}
[data-testid="stFileUploader"] button,
[data-testid="stFileUploader"] button:hover,
[data-testid="stFileUploader"] button:focus,
[data-testid="stFileUploader"] button:active {
  background:var(--app-primary)!important;color:#fff!important;-webkit-text-fill-color:#fff!important;
  border:1px solid var(--app-primary)!important;opacity:1!important;
}
[data-testid="stFileUploader"] button *,
[data-testid="stFileUploader"] button svg,
[data-testid="stFileUploader"] button svg * {
  color:#fff!important;fill:#fff!important;stroke:#fff!important;-webkit-text-fill-color:#fff!important;opacity:1!important;
}
[data-testid="stFileUploader"] section svg,
[data-testid="stFileUploaderDropzone"] svg {
  color:var(--app-primary)!important;stroke:var(--app-primary)!important;fill:none!important;opacity:1!important;
}

/* BUTTONS */
.stButton > button,.stDownloadButton > button {
  min-height:44px;border-radius:11px!important;font-weight:750!important;
  background:var(--app-primary)!important;color:#fff!important;-webkit-text-fill-color:#fff!important;
  border:1px solid var(--app-primary)!important;opacity:1!important;
}
.stButton > button *,.stDownloadButton > button * { color:#fff!important;fill:#fff!important;stroke:#fff!important;-webkit-text-fill-color:#fff!important;opacity:1!important; }

/* STATUS / EXPANDERS / DATA */
.status-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.status-item{display:flex;align-items:center;gap:9px;padding:12px 13px;border-radius:12px;border:1px solid var(--app-border);background:var(--app-surface);color:var(--app-text)}
.status-item.ok{background:color-mix(in srgb,#12b76a 14%,var(--app-surface))!important;border-color:color-mix(in srgb,#12b76a 42%,transparent)!important}
.status-item.ok,.status-item.ok *{color:#12b76a!important}
.status-item.missing{background:color-mix(in srgb,#f04438 14%,var(--app-surface))!important;border-color:color-mix(in srgb,#f04438 42%,transparent)!important}
.status-item.missing,.status-item.missing *{color:#f04438!important}
/* EXPANDERS — including "👀 Preview Generated Resume" */
div[data-testid="stExpander"],
div[data-testid="stExpander"] details,
div[data-testid="stExpander"] details > summary,
div[data-testid="stExpander"] details > summary > div,
div[data-testid="stExpander"] details > div {
  border-radius:14px!important;
  overflow:hidden;
  background:var(--app-surface)!important;
  color:var(--app-text)!important;
  border-color:var(--app-border)!important;
}
div[data-testid="stExpander"] details > summary,
div[data-testid="stExpander"] details > summary p,
div[data-testid="stExpander"] details > summary span,
div[data-testid="stExpander"] details > summary svg,
div[data-testid="stExpander"] details > summary svg * {
  color:var(--app-text)!important;
  fill:var(--app-text)!important;
  stroke:var(--app-text)!important;
  -webkit-text-fill-color:var(--app-text)!important;
  opacity:1!important;
}
div[data-testid="stExpander"] details > summary:hover {
  background:var(--app-soft)!important;
}
/* Streamlit HTML component wrapper around the PDF preview */
[data-testid="stIFrame"],
[data-testid="stIFrame"] > iframe {
  background:var(--app-surface)!important;
  border-color:var(--app-border)!important;
  color:var(--app-text)!important;
}
[data-testid="stAlert"] p,[data-testid="stAlert"] span,[data-testid="stAlert"] div,[data-testid="stAlert"] strong{color:var(--app-text)!important;-webkit-text-fill-color:var(--app-text)!important}
.main [data-baseweb="tab-list"]{background:var(--app-surface)!important}
.main [data-baseweb="tab"],.main [data-baseweb="tab"] *{color:var(--app-text)!important}
.main [aria-selected="true"][data-baseweb="tab"],.main [aria-selected="true"][data-baseweb="tab"] *{color:var(--app-primary)!important}
.main code,.main pre{background:color-mix(in srgb,var(--app-text) 9%,var(--app-surface))!important;color:var(--app-text)!important}

/* DATA TABLES — pure HTML/CSS to avoid Streamlit grid/canvas artifacts */
.analysis-table-wrap{width:100%;overflow-x:auto;border:1px solid var(--app-border);border-radius:16px;background:var(--app-surface);box-sizing:border-box;margin-top:10px}
.analysis-table{width:100%;border-collapse:collapse;min-width:420px;color:var(--app-text)!important;font-size:.92rem}
.analysis-table th{padding:12px 14px;text-align:left;background:var(--app-soft)!important;color:var(--app-text)!important;font-weight:800;border-bottom:1px solid var(--app-border)}
.analysis-table td{padding:11px 14px;text-align:left;color:var(--app-text)!important;border-bottom:1px solid var(--app-border);background:var(--app-surface)!important}
.analysis-table tr:last-child td{border-bottom:none}
.analysis-table td:last-child,.analysis-table th:last-child{text-align:right;font-variant-numeric:tabular-nums}
.analysis-table .score-pill{display:inline-flex;align-items:center;justify-content:center;min-width:42px;padding:4px 9px;border-radius:999px;background:var(--app-soft)!important;color:var(--app-primary)!important;font-weight:800}
@media(max-width:760px){.analysis-table{min-width:320px;font-size:.86rem}.analysis-table th,.analysis-table td{padding:9px 10px}}

/* ATS chart — pure HTML/CSS, no canvas artifact */
.ats-chart{width:100%;padding:16px 18px;border:1px solid var(--app-border);border-radius:16px;background:var(--app-surface)!important;box-sizing:border-box}
.nlp-chip-wrap{display:flex;flex-wrap:wrap;gap:7px;margin:8px 0 12px}
.nlp-chip{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;font-size:.82rem;font-weight:750;border:1px solid var(--app-border);background:var(--app-surface);color:var(--app-text)!important}
.nlp-chip-good{background:color-mix(in srgb,#12b76a 12%,var(--app-surface))!important;border-color:color-mix(in srgb,#12b76a 38%,transparent)!important;color:#12b76a!important}
.nlp-chip-warn{background:color-mix(in srgb,#f79009 12%,var(--app-surface))!important;border-color:color-mix(in srgb,#f79009 38%,transparent)!important;color:#f79009!important}
.nlp-stat-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:8px}
.nlp-stat-grid>div{padding:13px;border:1px solid var(--app-border);border-radius:13px;background:var(--app-surface);display:flex;flex-direction:column;gap:4px}
.nlp-stat-grid span{font-size:.78rem;color:var(--app-muted)!important}
.nlp-stat-grid strong{font-size:1.05rem;color:var(--app-text)!important}
.nlp-suggestion{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;margin:8px 0;border:1px solid var(--app-border);border-radius:13px;background:var(--app-surface);color:var(--app-text)!important}
.nlp-suggestion>span{display:inline-flex;min-width:26px;height:26px;align-items:center;justify-content:center;border-radius:50%;background:var(--app-soft);color:var(--app-primary)!important;font-weight:800}
.nlp-suggestion strong,.nlp-suggestion b{color:var(--app-text)!important}
@media(max-width:760px){.nlp-stat-grid{grid-template-columns:1fr}}
.ats-chart-row{display:grid;grid-template-columns:minmax(150px,1.1fr) minmax(220px,3fr) 48px;gap:14px;align-items:center;margin:11px 0}
.ats-chart-label{font-size:.86rem;font-weight:700;color:var(--app-text)!important;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ats-chart-track{height:13px;border-radius:999px;background:color-mix(in srgb,var(--app-text) 10%,var(--app-surface));overflow:hidden}
.ats-chart-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--app-primary),color-mix(in srgb,var(--app-primary) 68%,#22c55e));min-width:2px}
.ats-chart-value{text-align:right;font-weight:800;color:var(--app-text)!important;font-size:.86rem}
@media(max-width:760px){.ats-chart-row{grid-template-columns:1fr 44px;gap:7px}.ats-chart-track{grid-column:1 / 2}.ats-chart-value{grid-column:2;grid-row:1}.ats-chart-label{grid-column:1 / 2}}

/* Remove only Streamlit heading anchor icons */
.main h1 a,.main h2 a,.main h3 a,.main h4 a,.main h5 a,.main h6 a,
.main h1 button,.main h2 button,.main h3 button,.main h4 button,.main h5 button,.main h6 button{display:none!important;visibility:hidden!important;width:0!important;height:0!important}

@media(max-width:900px){.block-container{padding-left:1rem;padding-right:1rem}.hero-title{font-size:1.75rem}.status-grid{grid-template-columns:1fr}}


/* Native resume PDF preview */
.resume-pdf-preview {
  width: 100%;
  height: 900px;
  border: 1px solid var(--app-border, rgba(128,128,128,.28));
  border-radius: 14px;
  overflow: hidden;
  background: var(--app-surface, #f7f8fc);
  box-sizing: border-box;
}
.resume-pdf-object {
  display: block;
  width: 100%;
  height: 900px;
  border: 0;
  background: var(--app-surface, #f7f8fc);
}
.resume-pdf-fallback {
  padding: 28px;
  text-align: center;
  font-family: Arial, sans-serif;
  color: var(--app-text, #172033);
}

/* =========================================================
   FINAL THEME OVERRIDE — TRUE FULL-PAGE LIGHT / DARK MODE
   ========================================================= */
:root {
  --app-bg: #ffffff;
  --app-surface: #f7f8fc;
  --app-surface-2: #eef1f7;
  --app-text: #172033;
  --app-muted: #667085;
  --app-border: rgba(23,32,51,.16);
  --app-soft: #f0efff;
  --app-primary: #6d5ef5;
}

html[data-theme="dark"], body[data-theme="dark"],
[data-theme="dark"] .stApp, .stApp[data-theme="dark"] {
  --app-bg: #0b1020 !important;
  --app-surface: #121a2b !important;
  --app-surface-2: #182238 !important;
  --app-text: #f3f6ff !important;
  --app-muted: #aab5ca !important;
  --app-border: rgba(203,213,225,.18) !important;
  --app-soft: #1a2340 !important;
  --app-primary: #8b7cff !important;
}
html[data-theme="light"], body[data-theme="light"],
[data-theme="light"] .stApp, .stApp[data-theme="light"] {
  --app-bg: #ffffff !important;
  --app-surface: #f7f8fc !important;
  --app-surface-2: #eef1f7 !important;
  --app-text: #172033 !important;
  --app-muted: #667085 !important;
  --app-border: rgba(23,32,51,.16) !important;
  --app-soft: #f0efff !important;
  --app-primary: #6d5ef5 !important;
}

html, body, #root,
.stApp, [data-testid="stApp"], [data-testid="stAppViewContainer"],
[data-testid="stMainViewContainer"], [data-testid="stMain"],
[data-testid="stAppViewBlockContainer"], [data-testid="stMainBlockContainer"],
[data-testid="stMainBlockContainer"] > div, [data-testid="stBottomBlockContainer"],
section.main, section.main > div, .main, .main > div, .main > div > div,
.block-container, [data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stHorizontalBlock"] {
  background-color: var(--app-bg) !important;
  color: var(--app-text) !important;
}
[data-testid="stAppViewContainer"] > .main,
[data-testid="stAppViewContainer"] > .main > div,
[data-testid="stMainBlockContainer"] > div:first-child,
[data-testid="stVerticalBlockBorderWrapper"] > div {
  background-color: var(--app-bg) !important;
  color: var(--app-text) !important;
}

/* Main page text */
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] label,
[data-testid="stAppViewContainer"] h1,
[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3,
[data-testid="stAppViewContainer"] h4,
[data-testid="stAppViewContainer"] h5,
[data-testid="stAppViewContainer"] h6,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stCaptionContainer"] {
  color: var(--app-text) !important;
  opacity: 1 !important;
}
[data-testid="stCaptionContainer"] { color: var(--app-muted) !important; }

/* Inputs and dropdowns */
[data-testid="stTextInput"] > div,
[data-testid="stTextArea"] > div,
[data-testid="stSelectbox"] > div,
[data-testid="stNumberInput"] > div,
[data-testid="stDateInput"] > div,
[data-testid="stTimeInput"] > div,
[data-testid="stFileUploader"] > div,
[data-testid="stFileUploader"] section,
[data-testid="stMetric"],
[data-testid="stExpander"],
[data-testid="stExpander"] details,
[data-testid="stExpander"] details > div,
[data-testid="stExpander"] details > summary {
  background-color: var(--app-surface) !important;
  color: var(--app-text) !important;
  border-color: var(--app-border) !important;
}
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div,
[data-baseweb="select"] input {
  background-color: var(--app-surface-2) !important;
  color: var(--app-text) !important;
  -webkit-text-fill-color: var(--app-text) !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
  color: var(--app-muted) !important;
  -webkit-text-fill-color: var(--app-muted) !important;
  opacity: 1 !important;
}
[data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="menu"] > div,
[role="listbox"], [role="option"] {
  background-color: var(--app-surface) !important;
  color: var(--app-text) !important;
}
[role="option"]:hover, [role="option"][aria-selected="true"] {
  background-color: var(--app-soft) !important;
  color: var(--app-text) !important;
}

/* Sidebar */
[data-testid="stSidebar"], [data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"], [data-testid="stSidebar"] > div {
  background-color: var(--app-surface) !important;
  color: var(--app-text) !important;
}
[data-testid="stSidebar"] * { color: var(--app-text) !important; }

/* Custom surfaces */
.info-card,.resume-card,.section-head,.section-title-card,
.analysis-table-wrap,.ats-chart,
[data-testid="stMetric"], div[data-testid="stExpander"] {
  background-color: var(--app-surface) !important;
  color: var(--app-text) !important;
  border-color: var(--app-border) !important;
}
.analysis-table th { background-color: var(--app-soft) !important; color: var(--app-text) !important; }
.analysis-table td { background-color: var(--app-surface) !important; color: var(--app-text) !important; border-color: var(--app-border) !important; }
.ats-chart-track { background-color: color-mix(in srgb,var(--app-text) 10%,var(--app-surface)) !important; }

/* Alerts */
[data-testid="stAlert"] { border-color: var(--app-border) !important; }
[data-testid="stAlert"] p,[data-testid="stAlert"] span,[data-testid="stAlert"] div,[data-testid="stAlert"] strong {
  color: var(--app-text) !important;
  -webkit-text-fill-color: var(--app-text) !important;
}

/* AI SUMMARY PREVIEW — theme aware */
.summary-preview-card {
  padding:18px 20px;
  border:1px solid var(--app-border);
  border-radius:14px;
  background:var(--app-surface-2) !important;
  color:var(--app-text) !important;
  line-height:1.65;
  font-size:16px;
  box-sizing:border-box;
}
.summary-preview-card * { color:var(--app-text) !important; }

/* =========================================================
   FINAL NATIVE INPUT FIX — RESPECT STREAMLIT LIGHT/DARK THEME
   Streamlit exposes these variables from the active theme.
   Do not use prefers-color-scheme here because the browser/OS
   theme can differ from the theme selected inside Streamlit.
   ========================================================= */
.stApp [data-testid="stTextArea"] textarea,
.stApp [data-testid="stTextInput"] input,
.stApp [data-testid="stNumberInput"] input,
.stApp [data-testid="stDateInput"] input,
.stApp [data-testid="stTimeInput"] input {
  background-color: var(--secondary-background-color, #ffffff) !important;
  color: var(--text-color, #172033) !important;
  -webkit-text-fill-color: var(--text-color, #172033) !important;
  caret-color: var(--text-color, #172033) !important;
  opacity: 1 !important;
}
.stApp [data-testid="stTextArea"] textarea::placeholder,
.stApp [data-testid="stTextInput"] input::placeholder {
  color: var(--text-color, #667085) !important;
  -webkit-text-fill-color: var(--text-color, #667085) !important;
  opacity: .62 !important;
}
.stApp [data-testid="stTextArea"] > div,
.stApp [data-testid="stTextArea"] > div > div,
.stApp [data-testid="stTextInput"] > div,
.stApp [data-testid="stTextInput"] > div > div {
  background-color: transparent !important;
}
.stApp [data-testid="stTextArea"] textarea,
.stApp [data-testid="stTextInput"] input {
  border-color: var(--primary-color, #6d5ef5) !important;
}

/* Ensure transparent wrappers never expose a white canvas. */
[data-testid="stVerticalBlock"]:has(.premium-hero),
[data-testid="stVerticalBlock"]:has(.section-title-card),
[data-testid="stVerticalBlock"]:has(.analysis-table-wrap),
[data-testid="stVerticalBlock"]:has(.ats-chart) {
  background-color: var(--app-bg) !important;
}

/* =========================================================
   STEP 20 — FINAL POLISH SYSTEM
   ========================================================= */
.section-title-card { transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease; }
.section-title-card:hover { transform:translateY(-1px); border-color:color-mix(in srgb,var(--app-primary) 38%,var(--app-border)) !important; box-shadow:0 10px 28px color-mix(in srgb,var(--app-text) 10%,transparent); }
[data-testid="stMetric"] { border:1px solid var(--app-border) !important; box-shadow:0 7px 22px color-mix(in srgb,var(--app-text) 7%,transparent); }
[data-testid="stMetricValue"] { font-weight:850 !important; letter-spacing:-.4px; }
.stButton > button,.stDownloadButton > button { transition:transform .16s ease,box-shadow .16s ease,filter .16s ease; }
.stButton > button:hover,.stDownloadButton > button:hover { transform:translateY(-1px); box-shadow:0 8px 20px color-mix(in srgb,var(--app-primary) 24%,transparent); filter:brightness(1.03); }
.skill-chip-wrap { display:flex; flex-wrap:wrap; gap:7px; margin:8px 0 4px; }
.skill-chip { display:inline-flex; align-items:center; padding:7px 10px; border-radius:999px; background:var(--app-soft) !important; color:var(--app-text) !important; border:1px solid color-mix(in srgb,var(--app-primary) 28%,var(--app-border)); font-size:.82rem; font-weight:700; }
.pdf-preview-shell { border:1px solid var(--app-border); border-radius:16px; padding:12px; background:var(--app-surface-2) !important; box-shadow:0 10px 26px color-mix(in srgb,var(--app-text) 8%,transparent); }
.pdf-preview-caption { display:flex; justify-content:space-between; align-items:center; gap:10px; padding:4px 4px 12px; color:var(--app-muted) !important; font-size:.82rem; }
.final-readiness { border:1px solid color-mix(in srgb,var(--app-primary) 35%,var(--app-border)); border-radius:18px; padding:20px; background:linear-gradient(135deg,color-mix(in srgb,var(--app-primary) 12%,var(--app-surface)),var(--app-surface)); }
.final-readiness-title { font-size:1.15rem; font-weight:850; color:var(--app-text) !important; margin-bottom:6px; }
.final-readiness-copy { color:var(--app-muted) !important; line-height:1.55; margin-bottom:14px; }
.final-badge-row { display:flex; flex-wrap:wrap; gap:8px; }
.final-badge { padding:6px 10px; border-radius:999px; font-size:.78rem; font-weight:750; background:var(--app-surface-2) !important; color:var(--app-text) !important; border:1px solid var(--app-border); }
@media(max-width:760px){ .hero-title{font-size:1.65rem;} .pdf-preview-shell{padding:8px;} }
</style>
""", unsafe_allow_html=True)

# =========================================================
# PREMIUM THEME LAYER — FULL APP, LIGHT + DARK
# This is intentionally emitted after the existing CSS so it wins
# over Streamlit defaults without changing any application logic.
# =========================================================
if UI_THEME == "dark":
    theme_css = r"""
    :root, .stApp {
      --app-bg:#070b16 !important;
      --app-surface:#0f1728 !important;
      --app-surface-2:#151f34 !important;
      --app-text:#f5f7ff !important;
      --app-muted:#aeb9cf !important;
      --app-border:rgba(148,163,184,.20) !important;
      --app-soft:#1a2550 !important;
      --app-primary:#8b7cff !important;
      --app-accent:#22d3ee !important;
    }
    """
else:
    theme_css = r"""
    :root, .stApp {
      --app-bg:#f6f7fb !important;
      --app-surface:#ffffff !important;
      --app-surface-2:#f0f2f8 !important;
      --app-text:#182033 !important;
      --app-muted:#5f6b80 !important;
      --app-border:rgba(24,32,51,.13) !important;
      --app-soft:#eeecff !important;
      --app-primary:#635bdb !important;
      --app-accent:#0891b2 !important;
    }
    """

st.markdown(f"""
<style>
{theme_css}

/* ---------- GLOBAL SURFACES ---------- */
html, body, #root, .stApp,
[data-testid="stApp"], [data-testid="stAppViewContainer"],
[data-testid="stMainViewContainer"], [data-testid="stMain"],
[data-testid="stAppViewBlockContainer"], [data-testid="stMainBlockContainer"],
[data-testid="stMainBlockContainer"] > div, [data-testid="stBottomBlockContainer"],
section.main, section.main > div, .main, .main > div, .main > div > div,
.block-container, [data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stHorizontalBlock"] {{
  background:var(--app-bg) !important;
  color:var(--app-text) !important;
}}
.block-container {{ max-width:1460px !important; padding:1.25rem 2.25rem 4.5rem !important; }}

/* ---------- SIDEBAR ---------- */
[data-testid="stSidebar"], [data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"], [data-testid="stSidebar"] > div {{
  background:var(--app-surface) !important;
  color:var(--app-text) !important;
}}
[data-testid="stSidebar"] > div:first-child {{ border-right:1px solid var(--app-border) !important; }}
[data-testid="stSidebar"] * {{ color:var(--app-text) !important; }}
[data-testid="stSidebar"] hr {{ border-color:var(--app-border) !important; }}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {{
  font-size:1.15rem !important; font-weight:850 !important; letter-spacing:-.2px !important;
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {{
  font-size:.82rem !important; text-transform:uppercase !important; letter-spacing:1.1px !important;
  color:var(--app-primary) !important;
}}
[data-testid="stSidebar"] [data-testid="stToggle"] {{
  padding:10px 12px !important; border:1px solid var(--app-border) !important;
  border-radius:14px !important; background:var(--app-surface-2) !important;
  margin-bottom:8px !important;
}}

/* ---------- TYPOGRAPHY / READABILITY ---------- */
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2,
.stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp strong, .stApp em,
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stCaptionContainer"] {{
  color:var(--app-text) !important; opacity:1 !important;
}}
.stApp [data-testid="stCaptionContainer"] {{ color:var(--app-muted) !important; }}
.stApp a {{ color:var(--app-primary) !important; }}

/* ---------- HERO ---------- */
.premium-hero {{
  position:relative !important; overflow:hidden !important;
  padding:34px 38px !important; margin:4px 0 24px !important;
  border-radius:26px !important;
  border:1px solid color-mix(in srgb,var(--app-primary) 42%,var(--app-border)) !important;
  background:
    radial-gradient(circle at 92% 8%, color-mix(in srgb,var(--app-accent) 17%,transparent), transparent 32%),
    radial-gradient(circle at 8% 90%, color-mix(in srgb,var(--app-primary) 20%,transparent), transparent 38%),
    linear-gradient(135deg,color-mix(in srgb,var(--app-primary) 13%,var(--app-surface)),var(--app-surface) 62%,var(--app-surface-2)) !important;
  box-shadow:0 18px 48px color-mix(in srgb,var(--app-text) 10%,transparent) !important;
}}
.premium-hero:after {{
  content:""; position:absolute; inset:0; pointer-events:none;
  border-radius:26px; background:linear-gradient(110deg,transparent 0 58%,color-mix(in srgb,var(--app-primary) 5%,transparent));
}}
.hero-kicker {{ color:var(--app-primary) !important; font-weight:850 !important; letter-spacing:1.8px !important; }}
.hero-title {{ font-size:2.45rem !important; line-height:1.08 !important; font-weight:900 !important; letter-spacing:-1.5px !important; }}
.hero-copy {{ color:var(--app-muted) !important; max-width:1040px !important; line-height:1.65 !important; }}

/* ---------- SECTION HEADERS ---------- */
.section-head, .section-title-card {{
  border:1px solid var(--app-border) !important;
  background:linear-gradient(135deg,var(--app-surface),var(--app-surface-2)) !important;
  box-shadow:0 10px 28px color-mix(in srgb,var(--app-text) 6%,transparent) !important;
}}
.section-head .num, .section-title-card .section-icon {{
  background:linear-gradient(135deg,var(--app-primary),var(--app-accent)) !important;
  color:#fff !important; box-shadow:0 6px 16px color-mix(in srgb,var(--app-primary) 25%,transparent) !important;
}}
.section-head .num *, .section-title-card .section-icon * {{ color:#fff !important; }}
.step-chip {{
  background:color-mix(in srgb,var(--app-primary) 14%,var(--app-surface)) !important;
  border:1px solid color-mix(in srgb,var(--app-primary) 24%,var(--app-border)) !important;
}}

/* ---------- CARDS / METRICS ---------- */
.info-card, .resume-card, [data-testid="stMetric"], .analysis-table-wrap, .ats-chart,
.nlp-stat-grid>div, .nlp-suggestion, .pdf-preview-shell, .final-readiness {{
  background:var(--app-surface) !important;
  border:1px solid var(--app-border) !important;
  color:var(--app-text) !important;
  box-shadow:0 9px 26px color-mix(in srgb,var(--app-text) 6%,transparent) !important;
}}
[data-testid="stMetric"] {{
  min-height:118px !important; padding:18px 19px !important; border-radius:18px !important;
}}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {{ color:var(--app-muted) !important; }}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {{ color:var(--app-text) !important; font-weight:900 !important; }}

/* ---------- INPUTS / SELECTBOXES ---------- */
[data-testid="stTextArea"] > div, [data-testid="stTextArea"] > div > div,
[data-testid="stTextInput"] > div, [data-testid="stTextInput"] > div > div,
[data-testid="stSelectbox"] > div, [data-testid="stNumberInput"] > div,
[data-baseweb="select"] > div {{
  background:var(--app-surface-2) !important; color:var(--app-text) !important;
  border-color:color-mix(in srgb,var(--app-primary) 28%,var(--app-border)) !important;
  border-radius:13px !important;
}}
[data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input, [data-baseweb="select"] input {{
  background:var(--app-surface-2) !important; color:var(--app-text) !important;
  -webkit-text-fill-color:var(--app-text) !important; caret-color:var(--app-text) !important;
}}
[data-testid="stTextArea"] textarea::placeholder, [data-testid="stTextInput"] input::placeholder {{
  color:var(--app-muted) !important; -webkit-text-fill-color:var(--app-muted) !important; opacity:.78 !important;
}}
[data-baseweb="select"] svg {{ color:var(--app-muted) !important; fill:var(--app-muted) !important; }}
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"], [role="option"] {{
  background:var(--app-surface) !important; color:var(--app-text) !important;
}}
[role="option"]:hover, [role="option"][aria-selected="true"] {{ background:var(--app-soft) !important; color:var(--app-text) !important; }}

/* ---------- UPLOADER ---------- */
[data-testid="stFileUploader"], [data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"], [data-testid="stFileUploaderDropzone"] > div {{
  background:linear-gradient(145deg,var(--app-surface),var(--app-surface-2)) !important;
  color:var(--app-text) !important; border-color:var(--app-border) !important;
}}
[data-testid="stFileUploader"] section {{
  border:1.5px dashed color-mix(in srgb,var(--app-primary) 58%,var(--app-border)) !important;
  border-radius:17px !important; padding:10px !important;
}}
[data-testid="stFileUploader"] button {{
  background:linear-gradient(135deg,var(--app-primary),var(--app-accent)) !important;
  color:#fff !important; border:0 !important; border-radius:10px !important;
  box-shadow:0 7px 18px color-mix(in srgb,var(--app-primary) 22%,transparent) !important;
}}
[data-testid="stFileUploader"] button * {{ color:#fff !important; fill:#fff !important; stroke:#fff !important; }}

/* ---------- BUTTONS ---------- */
.stButton > button, .stDownloadButton > button {{
  min-height:46px !important; border-radius:13px !important; font-weight:800 !important;
  background:linear-gradient(135deg,var(--app-primary),var(--app-accent)) !important;
  color:#fff !important; -webkit-text-fill-color:#fff !important; border:0 !important;
  box-shadow:0 8px 22px color-mix(in srgb,var(--app-primary) 20%,transparent) !important;
  transition:transform .18s ease,box-shadow .18s ease,filter .18s ease !important;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
  transform:translateY(-2px) !important; filter:brightness(1.06) !important;
  box-shadow:0 12px 28px color-mix(in srgb,var(--app-primary) 28%,transparent) !important;
}}
.stButton > button *, .stDownloadButton > button * {{ color:#fff !important; fill:#fff !important; stroke:#fff !important; }}

/* ---------- EXPANDERS / TABS / ALERTS ---------- */
div[data-testid="stExpander"], div[data-testid="stExpander"] details,
div[data-testid="stExpander"] details > summary, div[data-testid="stExpander"] details > div {{
  background:var(--app-surface) !important; color:var(--app-text) !important;
  border-color:var(--app-border) !important; border-radius:15px !important;
}}
div[data-testid="stExpander"] details > summary:hover {{ background:var(--app-soft) !important; }}
[data-baseweb="tab-list"] {{ background:var(--app-surface) !important; border-radius:12px !important; padding:4px !important; }}
[data-baseweb="tab"] {{ color:var(--app-muted) !important; }}
[aria-selected="true"][data-baseweb="tab"] {{ color:var(--app-primary) !important; font-weight:800 !important; }}
[data-testid="stAlert"] {{ background:var(--app-surface-2) !important; color:var(--app-text) !important; border-color:var(--app-border) !important; border-radius:14px !important; }}
[data-testid="stAlert"] * {{ color:var(--app-text) !important; }}

/* ---------- ANALYSIS TABLES / CHARTS ---------- */
.analysis-table-wrap, .ats-chart {{ overflow:hidden !important; border-radius:17px !important; }}
.analysis-table th {{ background:var(--app-soft) !important; color:var(--app-text) !important; }}
.analysis-table td {{ background:var(--app-surface) !important; color:var(--app-text) !important; }}
.ats-chart-fill {{ background:linear-gradient(90deg,var(--app-primary),var(--app-accent)) !important; }}
.ats-chart-track {{ background:color-mix(in srgb,var(--app-text) 9%,var(--app-surface-2)) !important; }}
.skill-chip, .nlp-chip, .final-badge {{
  background:var(--app-soft) !important; color:var(--app-text) !important;
  border-color:color-mix(in srgb,var(--app-primary) 25%,var(--app-border)) !important;
}}

/* ---------- PDF / IMAGE PREVIEW ---------- */
.pdf-preview-shell {{ background:var(--app-surface-2) !important; border-radius:18px !important; padding:14px !important; }}
.pdf-preview-caption {{ color:var(--app-muted) !important; }}
[data-testid="stImage"] img {{ border-radius:12px !important; box-shadow:0 10px 30px rgba(0,0,0,.18) !important; }}

/* ---------- MOBILE ---------- */
@media(max-width:900px) {{
  .block-container {{ padding:1rem 1rem 3rem !important; }}
  .premium-hero {{ padding:25px 22px !important; border-radius:21px !important; }}
  .hero-title {{ font-size:1.8rem !important; }}
}}
</style>
""", unsafe_allow_html=True)


# =========================================================
# SKILLS DATABASE
# =========================================================

SKILLS_DB = [
    "Python",
    "SQL",
    "MySQL",
    "Pandas",
    "NumPy",
    "Matplotlib",
    "Seaborn",
    "Excel",
    "Power BI",
    "Tableau",
    "Data Analysis",
    "Data Visualization",
    "EDA",
    "Statistics",
    "Machine Learning",
    "Scikit-learn",
    "TensorFlow",
    "PyTorch",
    "Git",
    "GitHub",
    "Jupyter Notebook",
    "Data Cleaning",
    "ETL",
    "Database",
    "Power Query",
    "Dashboard",
    "Reporting",
    "Java", "C++", "C", "JavaScript", "TypeScript", "HTML", "CSS", "React", "Angular", "Node.js", "Express", "Django", "Flask", "FastAPI", "Spring Boot", "REST API", "APIs", "Docker", "AWS", "Azure", "Linux", "MongoDB", "PostgreSQL", "Oracle", "Firebase", "Kotlin", "Swift", "Flutter", "Android", "Figma", "Adobe Photoshop", "Adobe Illustrator", "Canva", "UI Design", "UX Design", "Prototyping", "Wireframing", "Branding", "SEO", "SEM", "Google Analytics", "Google Ads", "Meta Ads", "Content Marketing", "Social Media Marketing", "Email Marketing", "Copywriting", "CRM", "Lead Generation", "Market Research", "Financial Analysis", "Accounting", "Tally", "PowerPoint", "Microsoft Office", "Recruitment", "Talent Acquisition", "Human Resources", "HR", "Payroll", "Performance Management", "Communication", "Project Management", "Operations", "Business Development", "Customer Service", "Sales", "Negotiation"
]


# =========================================================
# IMPORTANT JOB KEYWORDS
# =========================================================

IMPORTANT_JD_KEYWORDS = [
    "dashboard",
    "dashboards",
    "reporting",
    "reports",
    "data cleaning",
    "data analysis",
    "data visualization",
    "exploratory data analysis",
    "statistical analysis",
    "business insights",
    "business intelligence",
    "large datasets",
    "datasets",
    "data quality",
    "data reporting",
    "data-driven",
    "problem solving",
    "problem-solving",
    "data modeling",
    "data management",
    "automation"
]


# =========================================================
# ACTION VERBS
# =========================================================

ACTION_VERBS = [
    "analyzed",
    "developed",
    "created",
    "designed",
    "performed",
    "cleaned",
    "processed",
    "implemented",
    "built",
    "improved",
    "optimized",
    "automated",
    "evaluated",
    "identified",
    "generated",
    "managed",
    "coordinated",
    "led",
    "delivered",
    "researched",
    "organized",
    "presented",
    "interpreted",
    "visualized"
]


WEAK_VERBS = [
    "helped",
    "assisted",
    "worked",
    "used",
    "responsible",
    "involved",
    "participated",
    "supported"
]


# =========================================================
# GENERIC PHRASES
# =========================================================

GENERIC_PHRASES = [
    "hard working",
    "hardworking",
    "quick learner",
    "team player",
    "good communication",
    "passionate",
    "motivated",
    "familiar with",
    "strong communication",
    "detail oriented",
    "problem solving skills",
    "analytical skills"
]


# =========================================================
# STOP WORDS
# =========================================================

JD_STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "are",
    "you", "your", "from", "have", "has", "will", "our",
    "they", "their", "about", "into", "using", "used",
    "work", "working", "role", "job", "candidate",
    "candidates", "looking", "ability", "strong", "good",
    "skills", "skill", "knowledge", "experience",
    "responsibilities", "responsibility", "requirements",
    "required", "preferred", "including", "etc", "should",
    "must", "would", "could", "can", "join", "team",
    "company", "business", "environment", "position",
    "internship", "intern", "employee", "employees",
    "opportunity", "provide", "providing", "ensure",
    "including", "across", "within", "through"
}


GENERIC_JD_WORDS = {
    "data",
    "analyst",
    "analysis",
    "job",
    "role",
    "candidate",
    "experience",
    "skills",
    "work",
    "team",
    "company",
    "responsible",
    "responsibilities",
    "ability",
    "knowledge",
    "looking",
    "strong",
    "good"
}


# =========================================================
# PDF EXTRACTION — COORDINATE-AWARE
# =========================================================

def _group_words_into_lines(words, y_tolerance=3.0):
    """Group PDF words into visual lines while preserving x-order."""
    rows = []
    for word in sorted(words, key=lambda w: (w.get("top", 0), w.get("x0", 0))):
        placed = False
        for row in rows:
            if abs(word.get("top", 0) - row[0]["top"]) <= y_tolerance:
                row.append(word)
                placed = True
                break
        if not placed:
            rows.append([word])

    rows.sort(key=lambda row: min(w.get("top", 0) for w in row))
    return [sorted(row, key=lambda w: w.get("x0", 0)) for row in rows]


def _join_word_fragments(words):
    if not words:
        return ""
    output = ""
    previous = None
    for word in words:
        token = str(word.get("text", "")).strip()
        if not token:
            continue
        if token in {"\uf0b7", "\uf0a7", "•", "●", "▪", "◦", "○", "◉", "‣", "⁃", "∙", "·"}:
            if output and not output.endswith(" "):
                output += " "
            output += "• "
            previous = word
            continue
        if previous is None:
            output = token
        else:
            gap = float(word.get("x0", 0)) - float(previous.get("x1", previous.get("x0", 0)))
            # Tiny gaps are usually letter fragments from tracked/expanded fonts.
            if gap <= 2.8 and not output.endswith(" "):
                output += token
            else:
                output += " " + token
        previous = word
    return re.sub(r"\s+", " ", output).strip()


def _looks_like_heading(line):
    clean = line.strip().strip("•").strip()
    lower = clean.lower()
    headings = {
        "contact", "profile", "summary", "professional summary",
        "education", "experience", "work experience", "internship",
        "technical skills", "skills", "core skills", "projects",
        "certifications", "certification", "achievements", "awards",
        "honors"
    }
    if lower in headings:
        return True
    letters = re.sub(r"[^A-Za-z]", "", clean)
    return bool(letters) and len(letters) >= 4 and letters.isupper() and len(clean.split()) <= 6


def _extract_column_lines(words):
    lines = _group_words_into_lines(words)
    result = []
    for row in lines:
        text = _join_word_fragments(row)
        if text:
            result.append(text)
    # Merge wrapped bullet lines into a single bullet.
    merged = []
    for line in result:
        if line.startswith("•"):
            merged.append(line)
        elif merged and merged[-1].startswith("•") and not _looks_like_heading(line):
            merged[-1] = merged[-1].rstrip() + " " + line.strip()
        else:
            merged.append(line)
    return merged


def _find_column_split(words, page_width):
    """Detect a meaningful two-column split from x coordinates."""
    xs = sorted(set(round(float(w.get("x0", 0)), 1) for w in words))
    if len(xs) < 12:
        return None
    candidates = []
    for a, b in zip(xs, xs[1:]):
        gap = b - a
        if gap < 14:
            continue
        split = (a + b) / 2
        left = sum(1 for w in words if w.get("x0", 0) < split)
        right = sum(1 for w in words if w.get("x0", 0) >= split)
        if left >= max(12, len(words) * 0.18) and right >= max(12, len(words) * 0.18):
            candidates.append((gap, split))
    if not candidates:
        return None
    gap, split = max(candidates)
    if gap >= 18 and page_width * 0.30 < split < page_width * 0.70:
        return split
    return None


def extract_text_from_pdf(uploaded_file):
    text_parts = []
    try:
        uploaded_file.seek(0)
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                words = page.extract_words(
                    x_tolerance=1,
                    y_tolerance=3,
                    keep_blank_chars=False
                )
                if not words:
                    continue

                split = _find_column_split(words, page.width)
                if split is None:
                    lines = _extract_column_lines(words)
                else:
                    left_words = [w for w in words if w.get("x0", 0) < split]
                    right_words = [w for w in words if w.get("x0", 0) >= split]
                    # Header/name is often spread across the full page. Keep top lines first.
                    top_cut = max(135, page.height * 0.18)
                    header_words = [w for w in words if w.get("top", 0) < top_cut]
                    header_lines = _extract_column_lines(header_words)
                    left_body = [w for w in left_words if w.get("top", 0) >= top_cut]
                    right_body = [w for w in right_words if w.get("top", 0) >= top_cut]
                    lines = header_lines + _extract_column_lines(left_body) + _extract_column_lines(right_body)

                text_parts.append("\n".join(lines))
    except Exception as e:
        st.error(f"PDF extraction error: {e}")
        return ""
    return normalize_text("\n".join(text_parts))


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text):

    text = text.replace(
        "\xa0",
        " "
    )

    text = text.replace(
        "\u200b",
        ""
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# =========================================================
# SECTION DETECTION
# =========================================================

def detect_sections(text):

    text_lower = text.lower()

    sections = {

        "Contact": [
            "contact",
            "phone",
            "email",
            "linkedin",
            "github"
        ],

        "Profile / Summary": [
            "profile",
            "summary",
            "objective"
        ],

        "Education": [
            "education",
            "bachelor",
            "bca",
            "degree"
        ],

        "Skills": [
            "skills",
            "technical skills",
            "core skills"
        ],

        "Experience": [
            "experience",
            "work experience",
            "internship"
        ],

        "Projects": [
            "projects",
            "project"
        ],

        "Certifications": [
            "certification",
            "certifications",
            "certificate"
        ],

        "Achievements": [
            "achievement",
            "achievements",
            "awards",
            "honors"
        ]
    }

    detected = {}

    for section, keywords in sections.items():

        detected[section] = any(
            keyword in text_lower
            for keyword in keywords
        )

    return detected


# =========================================================
# CONTACT DETECTION
# =========================================================

def detect_contact(text):

    email = bool(
        re.search(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
            text
        )
    )

    phone = bool(
        re.search(
            r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b",
            text
        )
    )

    linkedin = (
        "linkedin.com"
        in text.lower()
    )

    github = (
        "github.com"
        in text.lower()
    )

    return {
        "Email": email,
        "Phone": phone,
        "LinkedIn": linkedin,
        "GitHub": github
    }


# =========================================================
# ACHIEVEMENT DETECTION
# =========================================================

def detect_achievements(text):

    achievement_patterns = [

        r"\b\d+\s*%",

        r"\+\s*\d+",

        r"\b\d+\s*(users|clients|projects|sales|members|records|rows|employees)\b",

        r"\b(increased|decreased|reduced|improved|saved|generated|achieved)\b"
    ]

    found = []

    for pattern in achievement_patterns:

        matches = re.findall(
            pattern,
            text.lower()
        )

        if matches:
            found.extend(matches)

    return list(
        set(
            map(
                str,
                found
            )
        )
    )


# =========================================================
# RESUME SKILLS
# =========================================================

def detect_skills(text):

    found = []

    text_lower = text.lower()

    for skill in SKILLS_DB:

        pattern = (
            r"(?<!\w)"
            + re.escape(skill.lower())
            + r"(?!\w)"
        )

        if re.search(
            pattern,
            text_lower
        ):

            found.append(skill)

    return sorted(found)


# =========================================================
# JD SKILLS
# =========================================================

def extract_jd_skills(jd_text):

    if not jd_text.strip():
        return []

    found = []

    text_lower = jd_text.lower()

    for skill in SKILLS_DB:

        pattern = (
            r"(?<!\w)"
            + re.escape(skill.lower())
            + r"(?!\w)"
        )

        if re.search(
            pattern,
            text_lower
        ):

            found.append(skill)

    return sorted(found)


# =========================================================
# JD IMPORTANT KEYWORDS
# =========================================================

FIELD_KEYWORDS = {
    "Data / Analytics": ["dashboard", "dashboards", "reporting", "data cleaning", "data analysis", "data visualization", "exploratory data analysis", "statistical analysis", "business insights", "business intelligence", "datasets", "data quality", "data-driven", "data modeling", "automation"],
    "Software / IT": ["software development", "software engineering", "web development", "frontend", "backend", "full stack", "api", "rest api", "database", "testing", "debugging", "version control", "deployment", "cloud", "agile", "object oriented"],
    "Business / Finance": ["business analysis", "financial analysis", "reporting", "forecasting", "budgeting", "financial modeling", "accounting", "operations", "process improvement", "business insights", "stakeholder management"],
    "Marketing / Sales": ["digital marketing", "campaign management", "seo", "sem", "lead generation", "customer acquisition", "social media", "content marketing", "conversion", "market research", "sales target", "customer engagement"],
    "Design / Creative": ["graphic design", "ui design", "ux design", "user experience", "branding", "visual design", "typography", "prototyping", "wireframing", "creative content", "design system", "user research"],
    "HR / Administration": ["recruitment", "talent acquisition", "human resources", "employee engagement", "payroll", "onboarding", "performance management", "documentation", "coordination", "administration", "hr operations"],
    "Student / Fresher": ["internship", "academic projects", "teamwork", "communication", "problem solving", "learning", "research"],
    "Other / Custom": []
}

def extract_important_jd_keywords(jd_text, field=None):
    if not (jd_text or "").strip():
        return []
    text_lower = jd_text.lower()
    keywords = list(FIELD_KEYWORDS.get(field or "Other / Custom", []))
    # Keep the legacy general keywords where relevant, but never force a data-only list.
    keywords += ["problem solving", "problem-solving", "communication", "teamwork", "leadership", "stakeholder", "documentation", "internship"]
    return list(dict.fromkeys([k for k in keywords if k in text_lower]))


# =========================================================
# MATCHING SKILLS
# =========================================================

def get_matching_skills(
    resume_skills,
    jd_skills
):

    resume_lower = {
        skill.lower()
        for skill in resume_skills
    }

    return [
        skill
        for skill in jd_skills
        if skill.lower()
        in resume_lower
    ]


# =========================================================
# MISSING SKILLS
# =========================================================

def get_missing_skills(
    resume_skills,
    jd_skills
):

    resume_lower = {
        skill.lower()
        for skill in resume_skills
    }

    return [
        skill
        for skill in jd_skills
        if skill.lower()
        not in resume_lower
    ]


# =========================================================
# KEYWORD MATCHING
# =========================================================

def get_matching_keywords(
    resume_text,
    jd_keywords
):

    resume_lower = resume_text.lower()

    return [
        keyword
        for keyword in jd_keywords
        if keyword.lower()
        in resume_lower
    ]


def get_missing_keywords(
    resume_text,
    jd_keywords
):

    resume_lower = resume_text.lower()

    return [
        keyword
        for keyword in jd_keywords
        if keyword.lower()
        not in resume_lower
    ]


# =========================================================
# BULLET DETECTION
# =========================================================

BULLET_MARKERS = r"^[•●▪◦○◉‣⁃∙·\uf0b7\uf0a7*]+\s*"

def clean_bullet_line(line):
    line = line.strip()
    original = line
    line = re.sub(BULLET_MARKERS, "", line)
    line = re.sub(r"^\(?\d+[\.)]\s*", "", line)
    return line.strip(), original != line


def get_bullet_points(text):
    bullets = []
    for line in text.splitlines():
        cleaned, changed = clean_bullet_line(line)
        if changed and len(cleaned.split()) >= 4:
            bullets.append(cleaned)

    # Secondary detection: extraction engines sometimes preserve the bullet
    # symbol as a private-use glyph or lose it while keeping strong verb starts.
    if len(bullets) < 3:
        for line in text.splitlines():
            clean = line.strip()
            if not clean or clean.startswith("•"):
                continue
            words = clean.split()
            if words and words[0].lower().rstrip(":") in ACTION_VERBS and len(words) >= 6:
                bullets.append(clean)

    unique = []
    seen = set()
    for bullet in bullets:
        key = re.sub(r"\s+", " ", bullet.lower()).strip()
        if key not in seen:
            seen.add(key)
            unique.append(bullet)
    return unique


# =========================================================
# VERB DETECTION
# =========================================================

def detect_action_verbs(text):

    text_lower = text.lower()

    return [
        verb
        for verb in ACTION_VERBS
        if re.search(
            r"\b"
            + re.escape(verb)
            + r"\b",
            text_lower
        )
    ]


def detect_weak_verbs(text):

    text_lower = text.lower()

    return [
        verb
        for verb in WEAK_VERBS
        if re.search(
            r"\b"
            + re.escape(verb)
            + r"\b",
            text_lower
        )
    ]


def detect_generic_phrases(text):

    text_lower = text.lower()

    return [
        phrase
        for phrase in GENERIC_PHRASES
        if phrase in text_lower
    ]


# =========================================================
# KEYWORD DENSITY
# =========================================================

def calculate_keyword_density(
    text,
    skills
):

    if not text:
        return 0

    total_words = len(
        re.findall(
            r"\b\w+\b",
            text
        )
    )

    if total_words == 0:
        return 0

    skill_count = 0

    for skill in skills:

        skill_count += len(
            re.findall(
                r"(?<!\w)"
                + re.escape(
                    skill.lower()
                )
                + r"(?!\w)",
                text.lower()
            )
        )

    return round(
        (
            skill_count
            / total_words
        ) * 100,
        2
    )


# =========================================================
# READABILITY
# =========================================================

def readability_score(text):

    sentences = re.split(
        r"[.!?]+",
        text
    )

    sentences = [
        s.strip()
        for s in sentences
        if s.strip()
    ]

    if not sentences:
        return 0

    total_words = sum(
        len(sentence.split())
        for sentence in sentences
    )

    avg_words = (
        total_words
        / len(sentences)
    )

    if avg_words <= 15:
        return 95

    elif avg_words <= 20:
        return 85

    elif avg_words <= 25:
        return 75

    elif avg_words <= 30:
        return 65

    else:
        return 50


# =========================================================
# REPEATED WORDS
# =========================================================

def repeated_words(text, focus_terms=None):
    """Find meaningful repeated words without flooding NLP with resume boilerplate."""
    words = re.findall(r"\b[a-zA-Z]{4,}\b", (text or "").lower())
    stop_words = {
        "this", "that", "with", "from", "have", "your", "they", "their",
        "using", "used", "into", "will", "been", "were", "work", "worked",
        "working", "experience", "experiences", "skills", "skill", "resume",
        "candidate", "professional", "professionally", "education", "project",
        "projects", "company", "companies", "organization", "organizations",
        "responsible", "responsibilities", "knowledge", "familiar", "microsoft",
        "present", "current", "member", "members", "college", "university",
        "course", "courses", "degree", "bachelor", "student", "intern",
        "internship", "profile", "summary", "contact", "phone", "email",
        "linkedin", "github", "through", "within", "based", "including",
        "also", "more", "such", "than", "then", "only", "very", "able",
        "good", "strong", "provide", "provided", "providing", "make", "made",
        "improve", "improved", "develop", "developed", "create", "created",
    }
    counts = Counter(word for word in words if word not in stop_words)
    focus = {str(x).lower() for x in (focus_terms or [])}
    ranked = sorted(
        ((word, count) for word, count in counts.items() if count >= 3),
        key=lambda item: (1 if item[0] in focus else 0, item[1], len(item[0])),
        reverse=True,
    )
    return dict(ranked[:10])


# =========================================================
# ATS SCORE
# =========================================================

def calculate_ats_score(
    resume_skills,
    matching_skills,
    jd_skills,
    sections,
    contact,
    has_projects,
    has_experience,
    achievements,
    field="Student / Fresher"
):

    profile_skills = {str(x).lower() for x in FIELD_PROFILES.get(field, {}).get("skills", [])}
    relevant_resume_skills = sum(1 for x in resume_skills if str(x).lower() in profile_skills)
    technical_score = min(
        25,
        max(relevant_resume_skills, min(len(resume_skills), 3)) * 2.0 + min(5, max(0, len(resume_skills)-relevant_resume_skills))
    )

    if jd_skills:

        jd_score = round(
            (
                len(matching_skills)
                / len(jd_skills)
            ) * 25
        )

    else:

        jd_score = 25

    section_count = sum(
        1
        for value
        in sections.values()
        if value
    )

    section_score = round(
        (
            section_count
            / len(sections)
        ) * 20
    )

    contact_score = round(
        (
            sum(
                1
                for value
                in contact.values()
                if value
            )
            / len(contact)
        ) * 10
    )

    project_exp_score = 0

    if has_projects:
        project_exp_score += 5

    if has_experience:
        project_exp_score += 5

    achievement_score = min(
        10,
        len(achievements) * 2
    )

    total = (
        technical_score
        + jd_score
        + section_score
        + contact_score
        + project_exp_score
        + achievement_score
    )

    return min(
        100,
        total
    ), {

        "Technical Skills":
            technical_score,

        "JD Match":
            jd_score,

        "Resume Sections":
            section_score,

        "Contact":
            contact_score,

        "Projects / Experience":
            project_exp_score,

        "Achievements":
            achievement_score
    }


# =========================================================
# QUALITY SCORE
# =========================================================

def calculate_quality_score(
    text,
    sections,
    achievements,
    has_projects,
    has_experience
):

    score = 40

    section_count = sum(
        1
        for value
        in sections.values()
        if value
    )

    score += min(
        20,
        section_count * 2.5
    )

    word_count = len(
        text.split()
    )

    if 200 <= word_count <= 700:

        score += 20

    elif 150 <= word_count <= 900:

        score += 15

    else:

        score += 8

    if achievements:
        score += 10

    if has_projects:
        score += 5

    if has_experience:
        score += 5

    return min(
        100,
        round(score)
    )


# =========================================================
# NLP SCORE
# =========================================================

def calculate_nlp_score(
    action_verbs,
    bullets,
    readability,
    weak_verbs,
    generic_phrases
):

    score = 55

    score += min(
        15,
        len(action_verbs) * 2
    )

    if bullets:

        score += min(
            10,
            len(bullets) * 2
        )

    score += round(
        readability * 0.15
    )

    score -= (
        len(weak_verbs)
        * 2
    )

    score -= (
        len(generic_phrases)
        * 2
    )

    return max(
        0,
        min(
            100,
            round(score)
        )
    )


# =========================================================
# SAFE FILE NAMES / DOWNLOAD HELPERS
# =========================================================

def _safe_filename(value):
    """Return a Windows-safe filename stem for generated downloads."""
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "Candidate")).strip("._-")
    return value or "Candidate"


# =========================================================
# STEP 16
# =========================================================

WEAK_VERB_REPLACEMENTS = {
    "helped": "contributed to",
    "assisted": "supported",
    "worked": "executed",
    "used": "leveraged",
    "participated": "contributed",
    "responsible": "managed",
    "involved": "contributed to",
}


def improve_weak_verbs(text):
    """Return suggestions using a single-pass mapping (prevents chained replacements)."""
    suggestions = []
    lowered = text.lower()
    for weak, strong in WEAK_VERB_REPLACEMENTS.items():
        if re.search(r"\b" + re.escape(weak) + r"\b", lowered):
            suggestions.append({"Original": weak, "Suggested": strong, "Reason": "Stronger and more action-oriented wording."})
    return suggestions


def rewrite_bullet_professionally(bullet):
    """Improve a weak opening without changing the underlying achievement or inventing metrics."""
    original = (bullet or "").strip()
    if not original:
        return original
    text = re.sub(r"^[•\-–—]\s*", "", original).strip()
    replacements = [
        (r"^assisted\s+in\s+", "Supported "),
        (r"^assisted\s+with\s+", "Supported "),
        (r"^helped\s+with\s+", "Contributed to "),
        (r"^helped\s+to\s+", "Contributed to "),
        (r"^participated\s+in\s+", "Contributed to "),
        (r"^was\s+responsible\s+for\s+", "Managed "),
        (r"^responsible\s+for\s+", "Managed "),
        (r"^involved\s+in\s+", "Contributed to "),
        (r"^used\s+", "Leveraged "),
        (r"^worked\s+on\s+", "Executed work on "),
    ]
    changed = False
    for pattern, replacement in replacements:
        text2, count = re.subn(pattern, replacement, text, count=1, flags=re.I)
        if count:
            text = text2
            changed = True
            break
    text = text[:1].upper() + text[1:] if text else text
    return text if changed else original


# =========================================================
# GENERIC PHRASE IMPROVEMENT
# =========================================================

def improve_generic_phrases(text):

    replacements = {

        "hard working":
            "dedicated and results-focused",

        "hardworking":
            "dedicated and results-focused",

        "quick learner":
            "adaptable and eager to learn",

        "team player":
            "collaborative team member",

        "good communication":
            "effective communication",

        "passionate":
            "motivated",

        "familiar with":
            "knowledge of",

        "strong communication":
            "effective communication",

        "detail oriented":
            "detail-oriented",

        "problem solving skills":
            "problem-solving skills"
    }

    suggestions = []

    text_lower = text.lower()

    for phrase, replacement in (
        replacements.items()
    ):

        if phrase in text_lower:

            suggestions.append({

                "Original":
                    phrase,

                "Suggested":
                    replacement,

                "Reason":
                    "More professional and specific phrasing."
            })

    return suggestions


# =========================================================
# BULLET IMPROVEMENT
# =========================================================

def improve_bullets(bullets):
    """Improve only the opening wording of bullets without chained replacements."""
    suggestions = []
    for bullet in bullets:
        original = (bullet or "").strip()
        improved = rewrite_bullet_professionally(original)
        if improved != original:
            suggestions.append({"Original": original, "Improved": improved})
    return suggestions


# =========================================================
# SUMMARY GENERATION
# =========================================================

def generate_summary(resume_skills, target_role="Professional", field="Student / Fresher"):
    """Generate a field-aware summary using only relevant detected skills."""
    role = (target_role or "Professional").strip() or "Professional"
    field = field or "Student / Fresher"
    available = [str(x) for x in (resume_skills or [])]
    available_lower = {x.lower() for x in available}
    profile_skills = [str(x) for x in FIELD_PROFILES.get(field, {}).get("skills", [])]
    relevant = [x for x in profile_skills if x.lower() in available_lower]
    if not relevant:
        relevant = available[:8]
    soft = {"communication", "sales", "customer service", "negotiation", "project management", "teamwork", "leadership"}
    core = [x for x in relevant if x.lower() not in soft]
    relevant = (core + [x for x in relevant if x.lower() in soft])[:8] or ["transferable skills"]
    skill_text = ", ".join(relevant)
    fl = field.lower()
    if "data" in fl or "analytics" in fl:
        focus = "data analysis, data cleaning, exploratory analysis, visualization, and extracting actionable insights"
    elif "software" in fl or "it" in fl:
        focus = "software development, programming, debugging, and building practical technical solutions"
    elif "business" in fl or "finance" in fl:
        focus = "business analysis, reporting, financial and operational analysis, and evidence-based decision making"
    elif "marketing" in fl or "sales" in fl:
        focus = "campaigns, customer engagement, market research, content, and performance-oriented growth"
    elif "design" in fl or "creative" in fl:
        focus = "visual communication, branding, design thinking, digital content, and creative problem solving"
    elif "hr" in fl or "administration" in fl:
        focus = "recruitment, coordination, documentation, communication, and people-focused processes"
    else:
        focus = "practical project work, problem solving, communication, and continuous learning"
    student_prefix = "BCA student and aspiring " if any(x in available_lower for x in {"python", "sql", "mysql"}) else "Motivated candidate and aspiring "
    return (f"{student_prefix}{role} with hands-on knowledge of {skill_text}. "
            f"Focused on {focus} and applying practical skills to real-world challenges. "
            f"Seeking a {role} opportunity to contribute effectively, learn continuously, and deliver meaningful results.")


# =========================================================
# IMPROVED RESUME GENERATOR
# =========================================================

def generate_improved_resume(
    original_text,
    resume_skills,
    bullets,
    missing_skills,
    target_role="Professional",
    field="Student / Fresher"
):

    lines = []

    lines.append(
        "IMPROVED RESUME"
    )

    lines.append(
        "=" * 50
    )

    lines.append("")

    # -----------------------------------------------------
    # Name
    # -----------------------------------------------------

    name = ""

    for line in (
        original_text.splitlines()
    ):

        clean = line.strip()

        if (
            clean
            and len(clean.split()) <= 5
            and "resume"
            not in clean.lower()
            and "contact"
            not in clean.lower()
            and "profile"
            not in clean.lower()
        ):

            name = clean
            break

    if name:

        lines.append(
            name.upper()
        )

        lines.append("")

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    lines.append(
        "PROFESSIONAL SUMMARY"
    )

    lines.append(
        generate_summary(
            resume_skills, target_role, field
        )
    )

    lines.append("")

    # -----------------------------------------------------
    # Skills
    # -----------------------------------------------------

    if resume_skills:

        lines.append(
            "TECHNICAL SKILLS"
        )

        lines.append(
            ", ".join(
                resume_skills
            )
        )

        lines.append("")

    # -----------------------------------------------------
    # Experience / Project
    # -----------------------------------------------------

    if bullets:

        lines.append(
            "EXPERIENCE / PROJECT HIGHLIGHTS"
        )

        improved_bullets = (
            improve_bullets(
                bullets
            )
        )

        if improved_bullets:

            for item in improved_bullets:

                lines.append(
                    "• "
                    + item["Improved"]
                )

        else:

            for bullet in bullets:

                lines.append(
                    "• "
                    + bullet
                )

        lines.append("")

    # -----------------------------------------------------
    # Skills to Consider
    # -----------------------------------------------------

    if missing_skills:

        lines.append(
            "SKILLS TO CONSIDER"
        )

        lines.append(
            "Add these only if you genuinely "
            "have knowledge or experience:"
        )

        for skill in missing_skills:

            lines.append(
                "• "
                + skill
            )

        lines.append("")

    # -----------------------------------------------------
    # Improvement Notes
    # -----------------------------------------------------

    lines.append(
        "RESUME IMPROVEMENT NOTES"
    )

    lines.append(
        "• Add measurable results wherever possible."
    )

    lines.append(
        "• Start bullets with strong action verbs."
    )

    lines.append(
        "• Tailor skills to the target job description."
    )

    lines.append(
        "• Avoid generic phrases without evidence."
    )

    return "\n".join(
        lines
    )


# =========================================================
# RECOMMENDATIONS
# =========================================================

def generate_recommendations(
    missing_skills,
    missing_keywords,
    achievements,
    contact,
    weak_verbs,
    generic_phrases,
    bullets
):

    recommendations = []

    if missing_skills:

        recommendations.append(
            "Consider adding missing technical skills "
            "only if you genuinely know them: "
            + ", ".join(
                missing_skills
            )
            + "."
        )

    if missing_keywords:

        recommendations.append(
            "Try naturally incorporating relevant job "
            "keywords such as: "
            + ", ".join(
                missing_keywords[:5]
            )
            + "."
        )

    if not achievements:

        recommendations.append(
            "Add measurable achievements or project "
            "outcomes using numbers, percentages, "
            "records, users, or measurable impact."
        )

    if not contact["LinkedIn"]:

        recommendations.append(
            "Add a LinkedIn profile to strengthen "
            "your professional presence."
        )

    if weak_verbs:

        recommendations.append(
            "Replace weak verbs such as "
            + ", ".join(
                weak_verbs
            )
            + " with stronger action-oriented verbs."
        )

    if generic_phrases:

        recommendations.append(
            "Replace generic phrases such as "
            + ", ".join(
                generic_phrases
            )
            + " with specific evidence-based statements."
        )

    if len(bullets) < 5:

        recommendations.append(
            "Use concise bullet points for "
            "experience and projects."
        )

    if not recommendations:

        recommendations.append(
            "Resume structure looks strong. Focus "
            "on measurable impact and tailoring "
            "keywords for each job description."
        )

    return recommendations



# =========================================================
# STEP 17 — PROFESSIONAL VECTOR PDF REPORT
# =========================================================

def _safe_pdf_text(value):
    value = "" if value is None else str(value)
    return (value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _score_color(score):
    score = float(score)
    if score >= 80:
        return colors.HexColor("#1B7F5A")
    if score >= 60:
        return colors.HexColor("#B7791F")
    return colors.HexColor("#C53030")


def _score_color(score):
    score=float(score)
    return colors.HexColor("#16A36A" if score>=80 else "#D08A18" if score>=60 else "#D64545")

def _score_cards(data,width=520):
    metrics=[("ATS SCORE",data.get("ats_score",0),"/100"),("JOB MATCH",data.get("job_match",0),"%"),("RESUME QUALITY",data.get("quality_score",0),"/100"),("NLP SCORE",data.get("nlp_score",0),"/100")]
    card_w=(width-18)/4.0; gap=6; d=Drawing(width,78)
    for i,(label,value,suffix) in enumerate(metrics):
        x=i*(card_w+gap); d.add(Rect(x,0,card_w,68,rx=10,ry=10,fillColor=colors.HexColor("#F7F9FC"),strokeColor=colors.HexColor("#D8DEE8"),strokeWidth=.8))
        d.add(String(x+10,50,label,fontName="Helvetica-Bold",fontSize=7.5,fillColor=colors.HexColor("#667085")))
        d.add(String(x+10,22,f"{value}{suffix}",fontName="Helvetica-Bold",fontSize=17,fillColor=_score_color(value)))
    return d

def _horizontal_score_chart(title,rows,width=520):
    normalized=[]
    for row in rows:
        label,earned,maximum=(row[0],row[1],row[2]) if len(row)>=3 else (row[0],row[1],100)
        try: earned=float(earned); maximum=max(1.0,float(maximum))
        except (TypeError,ValueError): continue
        normalized.append((str(label),earned,maximum))
    row_h=29; height=42+max(1,len(normalized))*row_h; d=Drawing(width,height)
    d.add(String(0,height-16,title,fontName="Helvetica-Bold",fontSize=10.5,fillColor=colors.HexColor("#172033")))
    bar_x=158; value_x=width-88; bar_w=value_x-bar_x-10; y=height-44
    for label,earned,maximum in normalized:
        ratio=max(0,min(1,earned/maximum)); d.add(String(0,y+4,label[:27],fontName="Helvetica",fontSize=8.1,fillColor=colors.HexColor("#475467")))
        d.add(Rect(bar_x,y,bar_w,11,rx=5.5,ry=5.5,fillColor=colors.HexColor("#E9EDF3"),strokeColor=None))
        if ratio: d.add(Rect(bar_x,y,bar_w*ratio,11,rx=5.5,ry=5.5,fillColor=_score_color(ratio*100),strokeColor=None))
        d.add(String(value_x,y+1,f"{earned:.0f}/{maximum:.0f}",fontName="Helvetica-Bold",fontSize=8,fillColor=colors.HexColor("#172033"))); y-=row_h
    return d

def _report_table(rows,widths,header=True,zebra=True):
    table=Table(rows,colWidths=widths,repeatRows=1 if header else 0,hAlign="LEFT",splitByRow=1)
    style=[("VALIGN",(0,0),(-1,-1),"TOP"),("FONTNAME",(0,0),(-1,-1),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),8.2),("LEADING",(0,0),(-1,-1),10.5),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),("LINEBELOW",(0,0),(-1,-1),.35,colors.HexColor("#D9E0E8"))]
    start=1 if header else 0
    if header: style += [("BACKGROUND",(0,0),(-1,0),colors.HexColor("#24324A")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold")]
    if zebra:
        for r in range(start,len(rows),2): style.append(("BACKGROUND",(0,r),(-1,r),colors.HexColor("#F8FAFC")))
    table.setStyle(TableStyle(style)); return table

def _report_callout(title,text,fill="#F4F3FF",accent="#635BDB"):
    hd=ParagraphStyle("ReportCalloutHead",fontName="Helvetica-Bold",fontSize=9.2,leading=11,textColor=colors.HexColor(accent),spaceAfter=2)
    tx=ParagraphStyle("ReportCalloutText",fontName="Helvetica",fontSize=8.6,leading=12,textColor=colors.HexColor("#344054"))
    return Table([[Paragraph(_safe_pdf_text(title),hd)],[Paragraph(_safe_pdf_text(text),tx)]],colWidths=[6.85*inch],style=TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor(fill)),("BOX",(0,0),(-1,-1),.7,colors.HexColor(accent)),("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),("TOPPADDING",(0,0),(-1,0),7),("BOTTOMPADDING",(0,0),(-1,0),1),("TOPPADDING",(0,1),(-1,1),1),("BOTTOMPADDING",(0,1),(-1,1),7)]))

def generate_analysis_report(data):
    buffer=BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=36,leftMargin=36,topMargin=48,bottomMargin=42,title="AI Resume Intelligence Report",author="AI Resume Analyzer",allowSplitting=1)
    base=getSampleStyleSheet(); title=ParagraphStyle("RTitle",parent=base["Title"],fontName="Helvetica-Bold",fontSize=22,leading=25,textColor=colors.HexColor("#172033"),alignment=TA_CENTER,spaceAfter=4); subtitle=ParagraphStyle("RSub",parent=base["BodyText"],fontSize=9.5,leading=13,textColor=colors.HexColor("#667085"),alignment=TA_CENTER,spaceAfter=15); h=ParagraphStyle("RH",parent=base["Heading2"],fontName="Helvetica-Bold",fontSize=13,leading=16,textColor=colors.HexColor("#172033"),spaceBefore=8,spaceAfter=7,keepWithNext=True); body=ParagraphStyle("RB",parent=base["BodyText"],fontSize=8.8,leading=12.2,textColor=colors.HexColor("#344054"),spaceAfter=4); small=ParagraphStyle("RS",parent=body,fontSize=7.9,leading=10.7)
    story=[]; candidate=data.get("candidate_name") or extract_candidate_name(data.get("resume_text","")); field=data.get("detected_field") or "Professional Profile"; role=data.get("detected_role") or "Target Role Not Specified"
    def chrome(canvas,doc_obj):
        canvas.saveState(); canvas.setStrokeColor(colors.HexColor("#DCE2EA")); canvas.setLineWidth(.5); canvas.line(36,A4[1]-31,A4[0]-36,A4[1]-31); canvas.setFont("Helvetica-Bold",7.5); canvas.setFillColor(colors.HexColor("#635BDB")); canvas.drawString(36,A4[1]-24,"AI RESUME ANALYZER"); canvas.setFont("Helvetica",7.5); canvas.setFillColor(colors.HexColor("#98A2B3")); canvas.drawRightString(A4[0]-36,A4[1]-24,"RESUME INTELLIGENCE REPORT"); canvas.line(36,28,A4[0]-36,28); canvas.setFont("Helvetica",7.2); canvas.drawString(36,17,"Generated by AI Resume Analyzer"); canvas.drawRightString(A4[0]-36,17,f"Page {doc_obj.page}"); canvas.restoreState()
    story += [Spacer(1,10),Paragraph("RESUME INTELLIGENCE REPORT",title),Paragraph("ATS compatibility • job alignment • resume quality • NLP writing intelligence",subtitle),_report_callout("Candidate snapshot",f"{candidate}  •  {role}  •  {field}"),Spacer(1,10),_score_cards(data),Spacer(1,4)]
    rows=[["Metric","Result","What it measures"],["ATS Score",f"{data.get('ats_score',0)}/100","Structure, skills, keywords and ATS readiness"],["Job Match",f"{data.get('job_match',0)}%","Alignment with the supplied job description"],["Resume Quality",f"{data.get('quality_score',0)}/100","Sections, clarity, content and contact quality"],["NLP Score",f"{data.get('nlp_score',0)}/100","Action language, phrasing and readability"],["Readability",f"{data.get('readability',0)}/100","Estimated writing clarity and sentence readability"]]
    story += [Paragraph("Executive Scorecard",h),_report_table(rows,[1.55*inch,1.25*inch,4.05*inch]),Spacer(1,8),Paragraph("Key Signals",h)]
    sig=[("Skills detected",len(data.get("resume_skills",[]))), ("Achievement signals",len(data.get("achievements",[]))), ("Bullet points",len(data.get("bullets",[]))), ("Important JD keywords",len(data.get("jd_keywords",[])))]
    cells=[]
    for label,val in sig: cells.append(Paragraph(f"<b>{val}</b><br/><font size='7.5'>{label}</font>",ParagraphStyle("sig",fontName="Helvetica",fontSize=10,leading=13,textColor=colors.HexColor("#24324A"),alignment=TA_CENTER)))
    story.append(Table([cells],colWidths=[1.7*inch]*4,style=TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F6F8FB")),("BOX",(0,0),(-1,-1),.6,colors.HexColor("#DCE2EA")),("INNERGRID",(0,0),(-1,-1),.5,colors.HexColor("#DCE2EA")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9)])))
    story.append(PageBreak()); story += [Paragraph("ATS & JOB ALIGNMENT",title),Paragraph("A focused view of how the resume maps to the target role and its requirements.",subtitle)]
    breakdown=data.get("ats_breakdown",{}) or {}
    if breakdown:
        mx={"Skills & Role Relevance":25,"ATS Structure":18,"Contact Information":10,"Projects / Experience":15,"Achievements":10,"Bullet Quality":7,"Readability":5,"Content Density":10}; br=[(k,v,mx.get(k,max(1,v))) for k,v in breakdown.items()]; story += [Paragraph("ATS Category Performance",h),Paragraph("Each category shows points earned against its maximum. The eight category maximums total 100 points.",small),_horizontal_score_chart("Points earned against each ATS category",br),Spacer(1,8)]
    if data.get("jd_skills"):
        story += [Paragraph("Technical Skill Alignment",h),_report_table([["Job-match area","Details"],["JD technical skills",str(len(data.get("jd_skills",[])))],["Matching skills",_safe_pdf_text(", ".join(data.get("matching_skills",[])) or "None")],["Missing skills",_safe_pdf_text(", ".join(data.get("missing_skills",[])) or "None")]], [1.75*inch,5.1*inch]),Spacer(1,8)]
        story += [Paragraph("Job Description Keyword Coverage",h),_report_table([["Keyword group","Terms"],["Present",_safe_pdf_text(", ".join(data.get("matching_keywords",[])) or "None")],["Missing",_safe_pdf_text(", ".join(data.get("missing_keywords",[])) or "None")]], [1.25*inch,5.6*inch])]
    else: story.append(_report_callout("No job description supplied","Add a target job description to unlock job-specific matching, missing-skill analysis and keyword coverage."))
    sec=data.get("sections",{}) or {}; contact=data.get("contact",{}) or {}; story += [Spacer(1,8),Paragraph("Resume Structure & Contact",h),_report_table([["Resume section","Status"]]+[[str(k),"Detected" if v else "Missing"] for k,v in sec.items()],[4.8*inch,2.05*inch]),Spacer(1,6),_report_table([["Contact item","Status"]]+[[str(k),"Available" if v else "Missing"] for k,v in contact.items()],[4.8*inch,2.05*inch])]
    story.append(PageBreak()); story += [Paragraph("NLP & CONTENT INTELLIGENCE",title),Paragraph("Writing quality signals, wording risks and content-level improvement opportunities.",subtitle)]
    nlp=[["Writing signal","Result"],["Strong action verbs",str(len(data.get("action_verbs",[])))],["Weak verbs",_safe_pdf_text(", ".join(data.get("weak_verbs",[])) or "None")],["Generic phrases",_safe_pdf_text(", ".join(data.get("generic_phrases",[])) or "None")],["Bullet points",str(len(data.get("bullets",[])))],["Keyword density",f"{float(data.get('keyword_density',0) or 0):.2f}%"]]; story += [Paragraph("Language Quality",h),_report_table(nlp,[2.25*inch,4.6*inch]),Spacer(1,7)]
    for ttl,key in [("Weak Verb Improvements","weak_verb_suggestions"),("Generic Phrase Improvements","generic_phrase_suggestions")]:
        sug=data.get(key,[]) or []; story.append(Paragraph(ttl,h));
        if sug: story.append(_report_table([["Original","Suggested","Reason"]]+[[_safe_pdf_text(x.get("Original","")),_safe_pdf_text(x.get("Suggested","")),_safe_pdf_text(x.get("Reason",""))] for x in sug[:7]],[1.25*inch,1.65*inch,3.95*inch]))
        else: story.append(Paragraph("No major improvement signals detected in this category.",small))
    repeated=data.get("repeated",{}) or {}
    if repeated: story += [Paragraph("Meaningful Repeated Terms",h),_report_table([["Term","Count"]]+[[str(w).title(),str(c)] for w,c in list(repeated.items())[:8]],[5.8*inch,1.05*inch])]
    story.append(PageBreak()); story += [Paragraph("ACTION PLAN",title),Paragraph("A concise improvement plan based only on the evidence produced by the analysis.",subtitle)]
    recs=data.get("recommendations",[]) or []
    if recs: story += [Paragraph("Priority Recommendations",h),_report_table([["#","Recommendation"]]+[[str(i),_safe_pdf_text(x)] for i,x in enumerate(recs[:10],1)],[.45*inch,6.4*inch])]
    summary=data.get("improved_summary",""); story += [Spacer(1,8),Paragraph("AI-Improved Professional Summary",h),_report_callout("Suggested summary",summary or "No improved summary was generated.",fill="#EEF8F5",accent="#16805A")]
    bullets=data.get("bullets",[]) or []; bs=data.get("bullet_suggestions",[]) or []
    if bullets:
        ex=[["Original resume bullet","Suggested direction"]]
        for i,b in enumerate(bullets[:7]):
            x=bs[i] if i<len(bs) else ""; x=x.get("Suggested") or x.get("suggested") or x.get("Improved") or "" if isinstance(x,dict) else str(x)
            ex.append([_safe_pdf_text(b),_safe_pdf_text(x) or "Strengthen with action + task + evidence."])
        story += [Spacer(1,8),Paragraph("Content-Level Examples",h),_report_table(ex,[3.35*inch,3.5*inch])]
    ats=float(data.get("ats_score",0) or 0); quality=float(data.get("quality_score",0) or 0); nlpv=float(data.get("nlp_score",0) or 0)
    assessment="The analysis indicates a solid resume foundation. Focus on the specific gaps shown above, especially measurable impact and role-specific terminology." if min(ats,quality,nlpv)>=60 else "The analysis identifies several areas that can be strengthened. Prioritize the highest-impact recommendations and re-run the analysis after evidence-based edits."
    story += [Spacer(1,8),Paragraph("Overall Analysis",h),_report_callout("Interpretation",assessment),Spacer(1,10),Paragraph("Scores are analytical indicators based on the uploaded resume and optional job description; they are not guarantees of hiring outcomes.",small)]
    groups=[]; current=[]
    for flow in story:
        if isinstance(flow, PageBreak): groups.append(current); current=[]
        else: current.append(flow)
    if current: groups.append(current)
    page_height=A4[1]-doc.topMargin-doc.bottomMargin
    final_story=[]
    for idx, group in enumerate(groups):
        final_story.append(KeepInFrame(doc.width,page_height,group,mode="shrink",mergeSpace=True))
        if idx < len(groups)-1: final_story.append(PageBreak())
    doc.build(final_story,onFirstPage=chrome,onLaterPages=chrome); buffer.seek(0); return buffer

FIELD_PROFILES = {
    "Data / Analytics": {
        "roles": ["Data Analyst", "Business Analyst", "BI Analyst", "Data Science Intern"],
        "skills": ["Python", "SQL", "Pandas", "NumPy", "Excel", "Power BI", "Tableau", "Data Analysis", "Data Visualization", "EDA", "Statistics", "Matplotlib", "Seaborn", "Jupyter Notebook", "GitHub"],
        "section_order": ["Summary", "Skills", "Projects", "Experience", "Education", "Certifications", "Achievements"],
        "summary": "Analytical candidate with hands-on knowledge of {skills}. Skilled in data cleaning, exploratory data analysis, visualization, and translating data into actionable insights. Seeking a {role} opportunity to apply analytical skills to real-world business problems."
    },
    "Software / IT": {
        "roles": ["Software Developer", "Python Developer", "Web Developer", "IT Intern"],
        "skills": ["Python", "Java", "C++", "C", "JavaScript", "TypeScript", "HTML", "CSS", "React", "Angular", "Node.js", "Express", "Django", "Flask", "FastAPI", "Spring Boot", "SQL", "MySQL", "MongoDB", "PostgreSQL", "Git", "GitHub", "Docker", "AWS", "Azure", "Linux", "REST API", "APIs", "Scikit-learn", "TensorFlow", "PyTorch"],
        "section_order": ["Summary", "Skills", "Projects", "Experience", "Education", "Certifications", "Achievements"],
        "summary": "Technology-focused candidate with knowledge of {skills}. Comfortable developing practical solutions, working with software tools, and learning new technologies. Seeking a {role} opportunity to contribute to real-world technical projects."
    },
    "Business / Finance": {
        "roles": ["Business Analyst", "Finance Intern", "Operations Analyst", "Business Intern"],
        "skills": ["Excel", "SQL", "MySQL", "Data Analysis", "Power BI", "Tableau", "Statistics", "Reporting", "Data Visualization", "PowerPoint", "Financial Analysis", "Accounting", "Tally", "Forecasting", "Project Management", "Operations"],
        "section_order": ["Summary", "Skills", "Experience", "Projects", "Education", "Certifications", "Achievements"],
        "summary": "Business-focused candidate with knowledge of {skills}. Interested in reporting, analysis, process improvement, and evidence-based decision making. Seeking a {role} opportunity to turn information into practical business insights."
    },
    "Marketing / Sales": {
        "roles": ["Marketing Intern", "Digital Marketing Executive", "Sales Intern", "Marketing Analyst"],
        "skills": ["Excel", "Data Analysis", "Data Visualization", "Reporting", "Power BI", "SEO", "SEM", "Google Analytics", "Google Ads", "Meta Ads", "Content Marketing", "Social Media Marketing", "Email Marketing", "Copywriting", "CRM", "Lead Generation", "Market Research", "Sales", "Negotiation"],
        "section_order": ["Summary", "Skills", "Experience", "Projects", "Education", "Certifications", "Achievements"],
        "summary": "Creative and analytical candidate with knowledge of {skills}. Interested in customer insights, campaign performance, reporting, and data-informed marketing decisions. Seeking a {role} opportunity to support measurable growth."
    },
    "Design / Creative": {
        "roles": ["Graphic Designer", "Creative Intern", "Content Designer", "Social Media Designer"],
        "skills": ["Figma", "Adobe Photoshop", "Adobe Illustrator", "Canva", "UI Design", "UX Design", "Prototyping", "Wireframing", "Branding", "Data Visualization", "Creative Content"],
        "section_order": ["Summary", "Skills", "Projects", "Experience", "Education", "Certifications", "Achievements"],
        "summary": "Creative candidate with practical experience in visual communication, digital content, presentations, and collaborative projects. Seeking a {role} opportunity to create clear, engaging, and audience-focused work."
    },
    "HR / Administration": {
        "roles": ["HR Intern", "HR Executive", "Operations Intern", "Administrative Intern"],
        "skills": ["Excel", "Data Analysis", "Reporting", "SQL", "Microsoft Office", "Recruitment", "Talent Acquisition", "Human Resources", "HR", "Payroll", "Performance Management", "Communication", "Project Management", "Operations"],
        "section_order": ["Summary", "Skills", "Experience", "Education", "Projects", "Certifications", "Achievements"],
        "summary": "Organized and detail-focused candidate with knowledge of {skills}. Interested in coordination, documentation, reporting, and process support. Seeking a {role} opportunity to contribute to efficient team operations."
    },
    "Student / Fresher": {
        "roles": ["Graduate Intern", "Business Intern", "Technical Intern", "Management Trainee"],
        "skills": ["Python", "SQL", "Excel", "Data Analysis"],
        "section_order": ["Summary", "Skills", "Projects", "Education", "Experience", "Certifications", "Achievements"],
        "summary": "Motivated student with knowledge of {skills} and hands-on academic project experience. Eager to learn, contribute to practical projects, and build professional experience in a structured internship environment."
    },
    "Other / Custom": {
        "roles": ["Professional", "Intern", "Entry-Level Candidate"],
        "skills": [],
        "section_order": ["Summary", "Skills", "Experience", "Projects", "Education", "Certifications", "Achievements"],
        "summary": "Motivated candidate with transferable skills and practical project experience. Seeking a {role} opportunity to contribute, learn quickly, and deliver high-quality work."
    }
}


def extract_resume_sections(text):
    aliases = {
        "profile / summary": "Summary", "profile": "Summary", "summary": "Summary", "professional summary": "Summary",
        "education": "Education", "experience": "Experience", "work experience": "Experience", "internship": "Experience",
        "technical skills": "Skills", "skills": "Skills", "core skills": "Skills",
        "projects": "Projects", "project": "Projects", "certifications": "Certifications", "certification": "Certifications",
        "achievements": "Achievements", "achievement": "Achievements", "awards": "Achievements", "honors": "Achievements"
    }
    sections = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        key = line.lower().strip(":- ")
        if key in aliases:
            current = aliases[key]
            sections.setdefault(current, [])
            continue
        if current and line:
            sections[current].append(line)
    return sections


def extract_candidate_name(text):
    """Robustly extract a person's name from the top of a resume."""
    lines = [re.sub(r"\s+", " ", x.strip().replace("•", "")).strip() for x in text.splitlines()]
    blocked = re.compile(
        r"resume|curriculum vitae|contact|profile|summary|objective|education|experience|projects?|skills?|"
        r"certifications?|achievements?|awards?|university|college|institute|school|academy|department|"
        r"bca|b\.\s?tech|btech|mca|mba|degree|student|email|phone|github|linkedin|intern|developer|"
        r"analyst|manager|engineer|designer|marketing|sales|data science|business analyst",
        re.I
    )
    contact_re = re.compile(r"@|https?://|www\.|\+?\d[\d\s().-]{7,}|\b\d{7,}\b")

    # Highest-confidence explicit labels.
    for line in lines[:12]:
        m = re.match(r"^(?:name|candidate)\s*[:\-]\s*([A-Za-z][A-Za-z'’.-]*(?:\s+[A-Za-z][A-Za-z'’.-]*){1,4})$", line, re.I)
        if m:
            return m.group(1).strip().title()

    candidates = []
    for idx, line in enumerate(lines[:12]):
        words = re.findall(r"[A-Za-z][A-Za-z'’.-]*", line)
        if not (2 <= len(words) <= 4):
            continue
        if contact_re.search(line) or blocked.search(line):
            continue
        if any(len(w) > 22 for w in words):
            continue
        # Names usually have no punctuation-heavy tokens and are near the top.
        score = 100 - idx * 8
        if all(w[0].isupper() for w in words):
            score += 18
        if line.isupper():
            score += 6
        if any(len(w) <= 1 for w in words):
            score -= 8
        if re.search(r"[,;|:/()\[\]]", line):
            score -= 15
        candidates.append((score, " ".join(words).title()))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    return "Candidate"


FIELD_SIGNALS = {
    "Data / Analytics": ["data analyst", "data analytics", "data analysis", "business intelligence", "bi analyst", "data scientist", "machine learning", "statistics", "power bi", "tableau", "pandas", "numpy", "sql", "eda", "data visualization", "data cleaning", "dashboard", "reporting"],
    "Software / IT": ["software engineer", "software developer", "developer", "programmer", "web developer", "full stack", "frontend", "backend", "java", "javascript", "typescript", "react", "node.js", "django", "flask", "api", "docker", "cloud", "aws", "azure", "git"],
    "Business / Finance": ["business analyst", "finance", "financial analyst", "accounting", "accounts", "operations analyst", "financial analysis", "forecasting", "budgeting", "tally", "audit", "business development"],
    "Marketing / Sales": ["marketing", "digital marketing", "marketing analyst", "sales", "sales executive", "campaign", "seo", "sem", "google ads", "meta ads", "lead generation", "content marketing", "social media marketing", "customer acquisition"],
    "Design / Creative": ["graphic designer", "graphic design", "ui designer", "ux designer", "ui/ux", "product designer", "creative", "branding", "illustration", "figma", "photoshop", "illustrator", "canva", "prototyping", "wireframing"],
    "HR / Administration": ["human resources", "human resource", "hr", "recruitment", "talent acquisition", "hr executive", "hr intern", "payroll", "administration", "administrative", "employee relations"],
    "Student / Fresher": ["student", "fresher", "undergraduate", "internship", "intern"]
}

ROLE_PATTERNS = {
    "Data / Analytics": [("data analyst", 100), ("business analyst", 90), ("bi analyst", 88), ("data scientist", 92), ("data science intern", 85), ("business intelligence analyst", 88)],
    "Software / IT": [("software engineer", 100), ("software developer", 98), ("full stack developer", 96), ("frontend developer", 94), ("backend developer", 94), ("web developer", 92), ("python developer", 92), ("java developer", 92), ("mobile developer", 90), ("it intern", 70)],
    "Business / Finance": [("business analyst", 100), ("financial analyst", 98), ("finance intern", 90), ("operations analyst", 92), ("business development", 88), ("accounting intern", 85)],
    "Marketing / Sales": [("digital marketing", 100), ("marketing analyst", 96), ("marketing intern", 92), ("sales executive", 95), ("sales intern", 90), ("business development executive", 90)],
    "Design / Creative": [("graphic designer", 100), ("ui/ux designer", 98), ("ui designer", 95), ("ux designer", 95), ("product designer", 94), ("content designer", 90), ("creative intern", 85)],
    "HR / Administration": [("hr executive", 100), ("human resources", 98), ("hr intern", 95), ("recruiter", 94), ("talent acquisition", 92), ("administrative assistant", 88)],
    "Student / Fresher": [("graduate intern", 90), ("technical intern", 85), ("business intern", 80), ("intern", 60)]
}

def infer_field_from_text(text, skills=None):
    text = (text or "").lower()
    skill_set = {str(x).lower() for x in (skills or [])}
    scores = {field: 0 for field in FIELD_PROFILES}
    for field, signals in FIELD_SIGNALS.items():
        for sig in signals:
            if re.search(r"(?<![a-z])" + re.escape(sig) + r"(?![a-z])", text):
                scores[field] += 9 if " " in sig else 4
        profile = {str(x).lower() for x in FIELD_PROFILES.get(field, {}).get("skills", [])}
        scores[field] += 3 * sum(1 for sk in skill_set if sk in profile)
    scores["Student / Fresher"] = max(0, scores.get("Student / Fresher", 0) - 6)
    return max(scores, key=scores.get) if scores else "Student / Fresher"


def infer_role_from_text(text, field):
    text=(text or "").lower()
    best_role,best_score=None,-1
    for role,weight in ROLE_PATTERNS.get(field,[]):
        if role in text and weight>best_score:
            best_role,best_score=role,weight
    if best_role:
        role_title = best_role.title()
        if re.search(r"\b(intern|trainee|associate)\b", text) and role_title.lower() not in {"intern", "student"}:
            role_title += " Intern" if "intern" in text else ""
        return role_title
    return FIELD_PROFILES.get(field,FIELD_PROFILES["Student / Fresher"])["roles"][0]

def infer_field_and_role(resume_text, jd_text, resume_skills, jd_skills):
    """Use both resume and JD; an explicit target role in the JD has highest priority."""
    resume_field = infer_field_from_text(resume_text, resume_skills)
    resume_role = infer_role_from_text(resume_text, resume_field)
    jd_text_l = (jd_text or "").lower()
    if jd_text_l.strip():
        role_hits = []
        for field, patterns in ROLE_PATTERNS.items():
            for role, weight in patterns:
                if re.search(r"(?<![a-z])" + re.escape(role) + r"(?![a-z])", jd_text_l):
                    role_hits.append((weight, field, role))
        if role_hits:
            _, jd_field, jd_role = max(role_hits, key=lambda x: x[0])
            title = jd_role.title()
            if "intern" in jd_text_l and "intern" not in title.lower():
                title += " Intern"
            return jd_field, title
        jd_field = infer_field_from_text(jd_text, jd_skills)
        if jd_field != "Student / Fresher":
            return jd_field, infer_role_from_text(jd_text, jd_field)
    return resume_field, resume_role


def infer_resume_field(resume_text, resume_skills):
    return infer_field_from_text(resume_text, resume_skills)

def infer_target_role(resume_text, field, resume_skills):
    return infer_role_from_text(resume_text, field)

def build_template_resume_data(data, field, target_role):
    profile = FIELD_PROFILES[field]
    sections = extract_resume_sections(data.get("resume_text", ""))
    skills = data.get("resume_skills", [])

    preferred = [s for s in profile["skills"] if s in skills]
    if not preferred:
        preferred = skills[:10]

    role = target_role.strip() if target_role.strip() else profile["roles"][0]
    summary = generate_summary(
        preferred if preferred else skills[:10],
        role,
        field
    )

    return {
        "name": data.get("candidate_name") or extract_candidate_name(data.get("resume_text", "")),
        "email": re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", data.get("resume_text", ""))[:1],
        "phone": re.findall(r"(?:\+91[\s-]?)?[6-9]\d{9}", data.get("resume_text", ""))[:1],
        "linkedin": re.findall(r"https?://(?:www\.)?linkedin\.com/[^\s]+", data.get("resume_text", ""), re.I)[:1],
        "github": re.findall(r"https?://(?:www\.)?github\.com/[^\s]+", data.get("resume_text", ""), re.I)[:1],
        "role": role,
        "summary": summary,
        "skills": preferred,
        "education": sections.get("Education", []),
        "experience": sections.get("Experience", []),
        "projects": sections.get("Projects", []),
        "certifications": sections.get("Certifications", []),
        "achievements": sections.get("Achievements", []),
        "section_order": profile["section_order"],
        "field": field,
    }


def _resume_section_paragraphs(title, items, styles):
    flow = [Paragraph(title.upper(), styles["section"])]
    if not items:
        return flow
    for item in items:
        clean, changed = clean_bullet_line(item)
        if changed or item.startswith("•"):
            flow.append(Paragraph("• " + _safe_pdf_text(clean), styles["bullet"]))
        else:
            flow.append(Paragraph(_safe_pdf_text(item), styles["body"]))
    return flow


def _skill_chips(skills, accent):
    """Create responsive, wrap-safe skill chips for A4 width.

    Skill labels are Paragraphs rather than raw strings, so long names wrap
    inside their cells instead of pushing columns outside the page.
    """
    skills = [str(x).strip() for x in (skills or []) if str(x).strip()]
    if not skills:
        return Paragraph("Not specified", getSampleStyleSheet()["BodyText"])

    chip_style = ParagraphStyle(
        "ChipTextFinalV3",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.2,
        textColor=colors.HexColor("#344054"),
        alignment=TA_CENTER,
        splitLongWords=1,
    )
    rows, row = [], []
    col_width = 1.72 * inch
    for skill in skills[:20]:
        chip = Table(
            [[Paragraph(_safe_pdf_text(skill), chip_style)]],
            colWidths=[1.60 * inch],
            hAlign="CENTER",
            splitByRow=1,
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2F4F7")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D5DD")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]),
        )
        row.append(chip)
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        while len(row) < 4:
            row.append("")
        rows.append(row)

    return Table(
        rows,
        colWidths=[col_width] * 4,
        hAlign="LEFT",
        splitByRow=1,
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]),
    )


def generate_resume_pdf(resume,template_name,variant=None):
    """Generate a polished ATS-conscious one-page resume. KeepInFrame guarantees no second-page spill."""
    buffer=BytesIO(); variant=random.randint(1,5) if variant is None else variant
    doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=30,leftMargin=30,topMargin=26,bottomMargin=24,title=f"{resume.get('name','Candidate')} Resume",author="AI Resume Analyzer")
    base=getSampleStyleSheet(); palettes={
        "ATS Professional":("#24324A","#4F46E5","#EEF2FF"),"Data Analyst Pro":("#0B6E99","#12A4D9","#E8F7FC"),"Modern Sidebar":("#3347B0","#6675E8","#EEF0FF"),"Executive Minimal":("#252A34","#5C677D","#F2F4F7"),"Creative Modern":("#7C3AED","#EC4899","#F7EEFF"),"Academic Pro":("#1D4ED8","#2563EB","#EFF6FF"),"Tech Compact":("#087F5B","#20A36A","#EAF8F2"),"Portfolio Accent":("#B45309","#F59E0B","#FFF7E6"),"Editorial Luxe":("#8B1E3F","#C23B68","#FFF0F4"),"Minimal Mono":("#111827","#4B5563","#F3F4F6"),"Corporate Grid":("#4338CA","#6366F1","#EEF2FF"),"Creative Portfolio":("#BE185D","#EC4899","#FCE7F3"),"Swiss Modern":("#0F172A","#475569","#F1F5F9"),"Nordic Executive":("#155E75","#0891B2","#ECFEFF"),"Tech Aurora":("#115E59","#14B8A6","#E8FFFB"),"Finance Elite":("#1E3A5F","#B38B2E","#FBF7EA"),"Creative Studio":("#5B21B6","#F97316","#FFF1E8"),"OnePage Classic":("#1F2937","#374151","#F8FAFC")}
    ah,bh,sh=palettes.get(template_name,palettes["ATS Professional"]); accent=colors.HexColor(ah); accent2=colors.HexColor(bh); soft=colors.HexColor(sh); dark=colors.HexColor("#111827"); body=colors.HexColor("#344054"); muted=colors.HexColor("#667085")
    ns={1:24,2:22,3:25,4:21,5:23}.get(variant,23); bs={1:8.45,2:8.25,3:8.15,4:8.05,5:8.25}.get(variant,8.25); name=str(resume.get("name","Candidate")); ns-=2 if len(name)>25 else 0
    styles={"name":ParagraphStyle("RN",fontName="Helvetica-Bold",fontSize=ns,leading=ns+2,textColor=dark,spaceAfter=1,keepWithNext=True),"role":ParagraphStyle("RR",fontName="Helvetica-Bold",fontSize=9.6,leading=11,textColor=accent,spaceAfter=2,keepWithNext=True),"contact":ParagraphStyle("RC",fontName="Helvetica",fontSize=7.2,leading=8.8,textColor=muted,spaceAfter=3,keepWithNext=True),"section":ParagraphStyle("RSec",fontName="Helvetica-Bold",fontSize=9.7,leading=11.7,textColor=accent,spaceBefore=6.5,spaceAfter=3.2,keepWithNext=True),"body":ParagraphStyle("RB",fontName="Helvetica",fontSize=bs,leading=bs+2.25,textColor=body,spaceAfter=2.7,splitLongWords=1),"bullet":ParagraphStyle("RBu",fontName="Helvetica",fontSize=bs,leading=bs+2.15,leftIndent=10,firstLineIndent=-6,textColor=body,spaceAfter=2.5,splitLongWords=1),"small":ParagraphStyle("RSm",fontName="Helvetica",fontSize=7.1,leading=8.6,textColor=muted),"chip":ParagraphStyle("RChip",fontName="Helvetica-Bold",fontSize=6.7,leading=8,textColor=colors.HexColor("#334155"),alignment=TA_CENTER,splitLongWords=1)}
    def para(x,sty): return Paragraph(_safe_pdf_text(str(x or "").strip()) or " ",sty)
    def bar(t):
        if template_name in {"Creative Modern","Creative Portfolio","Creative Studio","Portfolio Accent"} or variant==3: return Table([[Paragraph(_safe_pdf_text(t.upper()),styles["section"]),""]],colWidths=[6.15*inch,.7*inch],style=TableStyle([("BACKGROUND",(0,0),(0,0),soft),("BACKGROUND",(1,0),(1,0),accent),("LEFTPADDING",(0,0),(0,0),6),("TOPPADDING",(0,0),(-1,-1),1.5),("BOTTOMPADDING",(0,0),(-1,-1),1.5)]))
        return Table([[Paragraph(_safe_pdf_text(t.upper()),styles["section"])]],colWidths=[6.85*inch],style=TableStyle([("LINEBELOW",(0,0),(-1,-1),1.1,accent),("BOTTOMPADDING",(0,0),(-1,-1),1.5)]))
    def rule(h=1.5): return Table([[""]],colWidths=[6.85*inch],rowHeights=[h],style=TableStyle([("BACKGROUND",(0,0),(-1,-1),accent)]))
    contacts=[]
    for key in ("email","phone","linkedin","github"):
        vals=resume.get(key,[]) or []; vals=[vals] if isinstance(vals,str) else vals; contacts += [str(v).strip() for v in vals if str(v).strip()]
    sec={"Summary":[resume.get("summary","")] if resume.get("summary") else [],"Skills":resume.get("skills",[]) or [],"Experience":resume.get("experience",[]) or [],"Projects":resume.get("projects",[]) or [],"Education":resume.get("education",[]) or [],"Certifications":resume.get("certifications",[]) or [],"Achievements":resume.get("achievements",[]) or []}
    role=str(resume.get("role","Professional")); field=str(resume.get("field","Professional Profile")); story=[]
    if template_name in {"Creative Modern","Creative Portfolio","Creative Studio","Editorial Luxe"} or variant==4:
        story += [Table([[para(name,ParagraphStyle("CName",parent=styles["name"],alignment=TA_CENTER)),para(field,ParagraphStyle("CField",parent=styles["small"],alignment=TA_CENTER))]],colWidths=[4.8*inch,2.05*inch],style=TableStyle([("BACKGROUND",(1,0),(1,0),soft),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)])),para(role,ParagraphStyle("CRole",parent=styles["role"],alignment=TA_CENTER)),para("  •  ".join(contacts),ParagraphStyle("CC",parent=styles["contact"],alignment=TA_CENTER)) if contacts else Spacer(1,1),rule()]
    else:
        story += [Table([[[para(name,styles["name"]),para(role,styles["role"])] ,para(field,styles["small"])]],colWidths=[5.15*inch,1.7*inch],style=TableStyle([("BACKGROUND",(1,0),(1,0),soft),("BOX",(1,0),(1,0),.65,accent),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(1,0),(1,0),7),("RIGHTPADDING",(1,0),(1,0),7),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)])),para("  •  ".join(contacts),styles["contact"]) if contacts else Spacer(1,1),rule()]
    if template_name in {"Data Analyst Pro","Tech Compact","Tech Aurora","Corporate Grid","Finance Elite","Nordic Executive"} or variant in {2,5}: story.append(Table([[para(f"FOCUS  •  {field}  •  {role}",styles["small"])]],colWidths=[6.85*inch],style=TableStyle([("BACKGROUND",(0,0),(-1,-1),soft),("BOX",(0,0),(-1,-1),.55,accent2),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)])))
    def add_section(t,items,bullets=True):
        items=[str(x).strip() for x in (items or []) if str(x).strip()]
        if not items:return
        story.append(bar(t))
        for item in items:
            clean,changed=clean_bullet_line(item); isb=bullets and (changed or item.startswith(("•","-","–","—")))
            story.append(Paragraph(("• "+_safe_pdf_text(rewrite_bullet_professionally(clean))) if isb else _safe_pdf_text(clean),styles["bullet"] if isb else styles["body"]))
    def add_skills(t="SKILLS & TOOLS"):
        skills=[str(x).strip() for x in sec["Skills"] if str(x).strip()][:20]
        if not skills:return
        story.append(bar(t)); rows=[]; row=[]
        for skill in skills:
            row.append(Table([[Paragraph(_safe_pdf_text(skill),styles["chip"])]],colWidths=[1.62*inch],style=TableStyle([("BACKGROUND",(0,0),(-1,-1),soft),("BOX",(0,0),(-1,-1),.45,colors.HexColor("#CBD5E1")),("TOPPADDING",(0,0),(-1,-1),2.5),("BOTTOMPADDING",(0,0),(-1,-1),2.5)])))
            if len(row)==4:rows.append(row);row=[]
        if row:
            while len(row)<4: row.append("")
            rows.append(row)
        story.append(Table(rows,colWidths=[1.70*inch]*4,style=TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),1.5),("RIGHTPADDING",(0,0),(-1,-1),1.5),("TOPPADDING",(0,0),(-1,-1),1.5),("BOTTOMPADDING",(0,0),(-1,-1),1.5)])))
    if template_name=="Academic Pro": add_section("Professional Summary",sec["Summary"],False);add_section("Education",sec["Education"]);add_section("Projects",sec["Projects"]);add_skills("Technical Skills");add_section("Experience",sec["Experience"]);add_section("Certifications",sec["Certifications"]);add_section("Achievements",sec["Achievements"])
    elif template_name in {"Tech Compact","Tech Aurora"}: add_section("Professional Summary",sec["Summary"],False);add_skills("Technical Stack");add_section("Experience",sec["Experience"]);add_section("Projects",sec["Projects"]);add_section("Education",sec["Education"]);add_section("Certifications",sec["Certifications"]);add_section("Achievements",sec["Achievements"])
    elif template_name in {"Finance Elite","Corporate Grid","Executive Minimal","Nordic Executive"}: add_section("Professional Summary",sec["Summary"],False);add_skills("Core Competencies");add_section("Experience",sec["Experience"]);add_section("Projects",sec["Projects"]);add_section("Education",sec["Education"]);add_section("Certifications",sec["Certifications"]);add_section("Achievements",sec["Achievements"])
    elif template_name in {"Creative Modern","Creative Portfolio","Creative Studio","Portfolio Accent","Editorial Luxe"}: add_section("Profile",sec["Summary"],False);add_skills("Skills & Tools");add_section("Projects",sec["Projects"]);add_section("Experience",sec["Experience"]);add_section("Education",sec["Education"]);add_section("Certifications",sec["Certifications"]);add_section("Achievements",sec["Achievements"])
    else:
        add_section("Professional Summary",sec["Summary"],False)
        for t in resume.get("section_order",["Skills","Experience","Projects","Education","Certifications","Achievements"]):
            if t == "Summary":
                continue
            add_skills("Skills & Tools") if t=="Skills" else add_section(t,sec[t]) if t in sec else None
    frame_h=A4[1]-doc.topMargin-doc.bottomMargin; story=[KeepInFrame(doc.width,frame_h,story,mode="shrink",mergeSpace=True)]
    def footer(canvas,doc_obj):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor("#DCE2EA"));canvas.line(30,18,A4[0]-30,18);canvas.setFont("Helvetica",6.7);canvas.setFillColor(colors.HexColor("#98A2B3"));canvas.drawString(30,8,"AI Resume Analyzer  •  ATS-conscious professional format");canvas.drawRightString(A4[0]-30,8,"1 page");canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer);buffer.seek(0);return buffer



def render_analysis_table(headers, rows, numeric_last=False):
    """Render a lightweight theme-aware HTML table without Streamlit's grid/canvas UI."""
    def esc(value):
        return (str(value if value is not None else "")
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

    header_html = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body_html = []
    for row in rows:
        cells = []
        for idx, value in enumerate(row):
            if numeric_last and idx == len(row) - 1:
                cells.append(f'<td><span class="score-pill">{esc(value)}</span></td>')
            else:
                cells.append(f"<td>{esc(value)}</td>")
        body_html.append("<tr>" + "".join(cells) + "</tr>")
    st.markdown(
        '<div class="analysis-table-wrap"><table class="analysis-table">'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(body_html)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def render_pdf_preview(pdf_bytes, label="PDF preview"):
    """Reliable Streamlit-native PDF preview using rendered page images."""
    if not pdf_bytes:
        st.info("No PDF is available for preview yet.")
        return
    if fitz is None:
        st.error("PDF preview engine could not be loaded. Please restart Streamlit once after installing PyMuPDF with: pip install PyMuPDF")
        return
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = doc.page_count
        if page_count == 0:
            doc.close(); st.info("The generated PDF contains no pages to preview."); return
        st.markdown(
            f'<div class="pdf-preview-caption"><span>📄 <strong>{_safe_pdf_text(label)}</strong></span><span>Page 1 of {page_count}</span></div>',
            unsafe_allow_html=True,
        )
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.65, 1.65), alpha=False)
        st.image(pix.tobytes("png"), use_container_width=True)
        if page_count > 1:
            st.caption(f"Previewing page 1 of {page_count}. Download the PDF to view all pages at full quality.")
        doc.close()
    except Exception as exc:
        st.warning(f"Preview could not be rendered in-app. Please use the download button. ({type(exc).__name__})")



# =========================================================
# AI INTELLIGENCE ENGINE v2.0
# Analysis-only upgrade: UI, theme, report layout and resume
# template rendering are intentionally left untouched.
# =========================================================

FIELD_INTELLIGENCE = {
    "Data / Analytics": {
        "roles": ["Data Analyst", "Business Analyst", "BI Analyst", "Data Scientist", "Data Science Intern", "Analytics Intern"],
        "skills": ["Python", "SQL", "MySQL", "Pandas", "NumPy", "Excel", "Power BI", "Tableau", "Data Analysis", "Data Visualization", "EDA", "Statistics", "Matplotlib", "Seaborn", "Jupyter Notebook", "Git", "GitHub", "Data Cleaning", "ETL", "Database", "Power Query", "Dashboard", "Reporting", "Machine Learning", "Scikit-learn"],
        "synonyms": {"powerbi":"Power BI", "power-bi":"Power BI", "ms excel":"Excel", "microsoft excel":"Excel", "exploratory data analysis":"EDA", "business intelligence":"Business Intelligence", "bi":"Business Intelligence", "data viz":"Data Visualization", "data visualization":"Data Visualization", "machine-learning":"Machine Learning", "ml":"Machine Learning"},
        "domains": ["analytics", "business intelligence", "reporting", "insights", "datasets", "data-driven", "data quality", "forecasting", "experimentation"],
        "responsibilities": ["analyze data", "clean data", "build dashboards", "create reports", "identify trends", "generate insights", "query data", "visualize data", "automate reporting", "present insights"],
        "achievement_terms": ["increased", "reduced", "improved", "automated", "saved", "accuracy", "growth", "conversion", "time", "records", "rows", "dashboard", "report"],
    },
    "Software / IT": {
        "roles": ["Software Engineer", "Software Developer", "Python Developer", "Web Developer", "Frontend Developer", "Backend Developer", "Full Stack Developer", "IT Intern"],
        "skills": ["Python", "Java", "C++", "C", "JavaScript", "TypeScript", "HTML", "CSS", "React", "Angular", "Node.js", "Express", "Django", "Flask", "FastAPI", "Spring Boot", "SQL", "MySQL", "MongoDB", "PostgreSQL", "Git", "GitHub", "Docker", "AWS", "Azure", "Linux", "REST API", "APIs", "Firebase", "Scikit-learn", "TensorFlow", "PyTorch"],
        "synonyms": {"js":"JavaScript", "ts":"TypeScript", "reactjs":"React", "react.js":"React", "nodejs":"Node.js", "node.js":"Node.js", "restful api":"REST API", "restful apis":"REST API", "postgres":"PostgreSQL", "mongo":"MongoDB", "version control":"Git", "cloud computing":"Cloud"},
        "domains": ["software development", "web development", "application development", "backend", "frontend", "deployment", "testing", "debugging", "agile", "cloud"],
        "responsibilities": ["develop software", "build applications", "write code", "debug issues", "design APIs", "develop features", "test applications", "deploy applications", "maintain code", "review code"],
        "achievement_terms": ["performance", "latency", "bugs", "uptime", "users", "features", "deployment", "automation", "test coverage", "response time"],
    },
    "Business / Finance": {
        "roles": ["Business Analyst", "Financial Analyst", "Finance Intern", "Operations Analyst", "Business Development Executive", "Business Intern"],
        "skills": ["Excel", "SQL", "MySQL", "Data Analysis", "Power BI", "Tableau", "Statistics", "Reporting", "Data Visualization", "PowerPoint", "Financial Analysis", "Accounting", "Tally", "Project Management", "Operations", "Business Development", "CRM", "Microsoft Office"],
        "synonyms": {"financial modelling":"Financial Modeling", "financial modeling":"Financial Modeling", "ms office":"Microsoft Office", "business intelligence":"Business Intelligence", "stakeholder management":"Stakeholder Management", "process improvement":"Process Improvement"},
        "domains": ["finance", "business analysis", "operations", "forecasting", "budgeting", "accounting", "stakeholders", "process improvement", "business development"],
        "responsibilities": ["analyze business data", "prepare reports", "forecast performance", "support budgeting", "analyze financials", "improve processes", "work with stakeholders", "track performance", "prepare presentations"],
        "achievement_terms": ["revenue", "cost", "profit", "savings", "forecast accuracy", "efficiency", "growth", "budget", "conversion", "turnaround"],
    },
    "Marketing / Sales": {
        "roles": ["Marketing Intern", "Digital Marketing Executive", "Marketing Analyst", "Sales Executive", "Sales Intern", "Business Development Executive"],
        "skills": ["Excel", "Data Analysis", "Data Visualization", "Reporting", "Power BI", "SEO", "SEM", "Google Analytics", "Google Ads", "Meta Ads", "Content Marketing", "Social Media Marketing", "Email Marketing", "Copywriting", "CRM", "Lead Generation", "Market Research", "Sales", "Negotiation"],
        "synonyms": {"digital advertising":"Digital Marketing", "social media":"Social Media Marketing", "paid search":"SEM", "search engine optimization":"SEO", "search engine marketing":"SEM", "google analytics 4":"Google Analytics", "ga4":"Google Analytics", "customer acquisition":"Lead Generation"},
        "domains": ["campaigns", "marketing", "sales", "customers", "acquisition", "engagement", "content", "conversion", "brand", "pipeline"],
        "responsibilities": ["manage campaigns", "analyze campaign performance", "generate leads", "create content", "manage social media", "conduct market research", "track conversions", "support sales", "engage customers"],
        "achievement_terms": ["leads", "conversion", "engagement", "reach", "clicks", "revenue", "sales", "customers", "roi", "growth"],
    },
    "Design / Creative": {
        "roles": ["Graphic Designer", "UI Designer", "UX Designer", "Product Designer", "Content Designer", "Creative Intern", "Social Media Designer"],
        "skills": ["Figma", "Adobe Photoshop", "Adobe Illustrator", "Canva", "UI Design", "UX Design", "Prototyping", "Wireframing", "Branding", "Creative Content", "Data Visualization"],
        "synonyms": {"ui/ux":"UI/UX", "user interface":"UI Design", "user experience":"UX Design", "adobe ps":"Adobe Photoshop", "illustrator":"Adobe Illustrator", "visual design":"Visual Design", "design systems":"Design System"},
        "domains": ["branding", "visual design", "user experience", "user interface", "creative", "content", "typography", "layout", "visual communication"],
        "responsibilities": ["design graphics", "create visual assets", "develop layouts", "create prototypes", "design interfaces", "build brand assets", "create social media content", "conduct user research"],
        "achievement_terms": ["engagement", "reach", "assets", "campaigns", "deliverables", "clients", "projects", "turnaround", "brand"],
    },
    "HR / Administration": {
        "roles": ["HR Intern", "HR Executive", "Recruiter", "Talent Acquisition Specialist", "Operations Intern", "Administrative Intern"],
        "skills": ["Excel", "Microsoft Office", "Recruitment", "Talent Acquisition", "Human Resources", "HR", "Payroll", "Performance Management", "Communication", "Project Management", "Operations", "Reporting", "CRM"],
        "synonyms": {"human resource management":"Human Resources", "talent acquisition":"Talent Acquisition", "employee relations":"Employee Relations", "hr operations":"HR Operations", "ms office":"Microsoft Office"},
        "domains": ["recruitment", "hiring", "employees", "onboarding", "payroll", "people", "administration", "hr operations", "coordination"],
        "responsibilities": ["screen candidates", "coordinate interviews", "support recruitment", "manage employee records", "support onboarding", "prepare reports", "coordinate teams", "maintain documentation"],
        "achievement_terms": ["hires", "candidates", "time-to-hire", "retention", "onboarding", "employees", "records", "events", "training"],
    },
    "Student / Fresher": {
        "roles": ["Graduate Intern", "Technical Intern", "Business Intern", "Management Trainee", "General Intern"],
        "skills": ["Python", "SQL", "Excel", "Data Analysis", "Microsoft Office", "Communication", "Project Management", "Git", "GitHub"],
        "synonyms": {},
        "domains": ["academic projects", "internship", "coursework", "research", "teamwork", "learning"],
        "responsibilities": ["complete projects", "conduct research", "analyze information", "prepare presentations", "collaborate with teams", "document work"],
        "achievement_terms": ["projects", "presentations", "events", "members", "competition", "award", "percentage", "grade"],
    },
    "Other / Custom": {
        "roles": ["Professional", "Intern", "Entry-Level Candidate"], "skills": [], "synonyms": {},
        "domains": [], "responsibilities": [], "achievement_terms": []
    },
}

# Keep the existing UI-facing profile structure, but make its data field-aware.
for _field, _profile in FIELD_INTELLIGENCE.items():
    if _field in FIELD_PROFILES:
        FIELD_PROFILES[_field]["roles"] = _profile["roles"][:]
        FIELD_PROFILES[_field]["skills"] = _profile["skills"][:]

SKILL_ALIAS_GLOBAL = {}
for _profile in FIELD_INTELLIGENCE.values():
    SKILL_ALIAS_GLOBAL.update({str(k).lower(): v for k, v in _profile.get("synonyms", {}).items()})
SKILL_ALIAS_GLOBAL.update({
    "powerbi": "Power BI", "power-bi": "Power BI", "react.js": "React", "reactjs": "React",
    "nodejs": "Node.js", "node.js": "Node.js", "postgres": "PostgreSQL", "mongo": "MongoDB",
    "ms excel": "Excel", "microsoft excel": "Excel", "microsoft office": "Microsoft Office",
    "github": "GitHub", "git hub": "GitHub", "scikit learn": "Scikit-learn", "scikit learn library": "Scikit-learn",
})


def _norm_ai(text):
    text = (text or "").lower().replace("&", " and ")
    text = re.sub(r"[/|_\-]+", " ", text)
    text = re.sub(r"[^a-z0-9+#. ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _phrase_present(text, phrase):
    t = _norm_ai(text); p = _norm_ai(phrase)
    if not p: return False
    return re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", t) is not None


def _canonical_skill(skill):
    s = str(skill or "").strip()
    return SKILL_ALIAS_GLOBAL.get(_norm_ai(s), s)


def _skill_evidence(text, skill):
    """Return evidence strength without inferring an unsupported skill."""
    if not _phrase_present(text, skill):
        aliases = [k for k, v in SKILL_ALIAS_GLOBAL.items() if str(v).lower() == str(skill).lower()]
        if not any(_phrase_present(text, a) for a in aliases):
            return 0
    lower = (text or "").lower()
    score = 1
    if re.search(r"\b(skills?|technical skills?|tools?|technologies?|proficienc|competenc)\b", lower):
        score += 1
    if re.search(r"\b(experience|developed|built|created|analyzed|designed|implemented|managed|used|worked|project|internship)\b", lower):
        score += 1
    return score


def _all_known_skills(field=None):
    if field and field in FIELD_INTELLIGENCE:
        base = FIELD_INTELLIGENCE[field]["skills"][:]
    else:
        base = []
        for p in FIELD_INTELLIGENCE.values(): base.extend(p["skills"])
        base.extend(SKILLS_DB)
    return list(dict.fromkeys(base))


def detect_skills(text):
    found = []
    seen = set()
    for skill in _all_known_skills():
        canonical = _canonical_skill(skill)
        if canonical.lower() in seen: continue
        if _skill_evidence(text, skill) > 0:
            found.append(canonical); seen.add(canonical.lower())
    return sorted(found, key=lambda x: x.lower())


def _extract_jd_requirements(jd_text, field=None):
    """Parse a JD into weighted, evidence-backed requirement buckets."""
    jd = jd_text or ""
    if not jd.strip():
        return {"skills": [], "must_skills": [], "preferred_skills": [], "keywords": [], "responsibilities": [], "education": [], "experience": [], "soft_skills": [], "role": None, "seniority": None}
    f = field if field in FIELD_INTELLIGENCE else infer_field_from_text(jd, [])
    known = _all_known_skills(f)
    skills = []
    for skill in known:
        canonical = _canonical_skill(skill)
        if _phrase_present(jd, skill) and canonical not in skills:
            skills.append(canonical)
    # Include globally known skills that may be outside the inferred field only when explicitly present.
    for skill in SKILLS_DB:
        canonical = _canonical_skill(skill)
        if _phrase_present(jd, skill) and canonical not in skills:
            skills.append(canonical)
    lines = [x.strip(" •\t") for x in jd.splitlines() if x.strip()]
    must_blob, preferred_blob = [], []
    in_pref = False
    for line in lines:
        ll = line.lower()
        if re.search(r"\b(preferred|nice to have|good to have|plus|bonus)\b", ll): in_pref = True
        if re.search(r"\b(required|must have|required skills|qualifications|minimum)\b", ll): in_pref = False
        (preferred_blob if in_pref else must_blob).append(line)
    must_skills = [s for s in skills if _phrase_present(" ".join(must_blob), s)] if must_blob else []
    preferred_skills = [s for s in skills if any(_phrase_present(" ".join(preferred_blob), s))] if preferred_blob else []
    # Strong modal language upgrades importance even when the JD has no headings.
    must_blob_text = " ".join(must_blob).lower()
    for s in skills:
        if s not in must_skills and re.search(r"(?:must|required|essential|mandatory).{0,80}" + re.escape(_norm_ai(s)), must_blob_text, re.I):
            must_skills.append(s)
    responsibilities = []
    profile = FIELD_INTELLIGENCE.get(f, {})
    for phrase in profile.get("responsibilities", []):
        if _phrase_present(jd, phrase): responsibilities.append(phrase)
    # Generic responsibility extraction from action-led lines.
    for line in lines:
        if re.match(r"^(develop|build|create|analy[sz]e|manage|design|support|coordinate|prepare|maintain|drive|lead|monitor|track|deliver|optimize|implement|conduct)\b", line, re.I):
            if len(line.split()) >= 4 and len(line) <= 220: responsibilities.append(line)
    responsibilities = list(dict.fromkeys(responsibilities))[:15]
    education = re.findall(r"\b(?:bachelor(?:'s)?|master(?:'s)?|b\.? ?tech|bca|mca|mba|degree|diploma|computer science|engineering|commerce|finance|marketing|design|human resources)\b", jd, re.I)
    exp = re.findall(r"\b(?:\d+\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience|entry[- ]level|fresher|internship|intern|graduate)\b", jd, re.I)
    seniority = "Entry-Level" if re.search(r"\b(entry[- ]level|fresher|intern|internship|graduate|trainee)\b", jd, re.I) else ("Senior" if re.search(r"\b(senior|lead|manager|principal|head)\b", jd, re.I) else "Experienced")
    soft_candidates = ["communication", "teamwork", "leadership", "problem solving", "stakeholder management", "time management", "collaboration", "presentation", "negotiation"]
    soft_skills = [x for x in soft_candidates if _phrase_present(jd, x)]
    important = []
    for phrase in profile.get("domains", []) + profile.get("responsibilities", []):
        if _phrase_present(jd, phrase): important.append(phrase)
    words = re.findall(r"\b[a-zA-Z][a-zA-Z+#.-]{3,}\b", jd.lower())
    counts = Counter(w for w in words if w not in JD_STOP_WORDS and w not in GENERIC_JD_WORDS)
    lexical = [w for w,c in counts.most_common(25) if c >= 1]
    keywords = list(dict.fromkeys([*skills, *important, *soft_skills, *lexical]))[:45]
    role = infer_role_from_text(jd, f)
    return {"skills": skills, "must_skills": list(dict.fromkeys(must_skills)), "preferred_skills": list(dict.fromkeys(preferred_skills)), "keywords": keywords, "responsibilities": responsibilities, "education": list(dict.fromkeys(education))[:8], "experience": list(dict.fromkeys(exp))[:8], "soft_skills": soft_skills, "role": role, "seniority": seniority}


def extract_jd_skills(jd_text):
    if not (jd_text or "").strip(): return []
    # Keep this function signature for the existing UI; field inference is done again safely.
    req = _extract_jd_requirements(jd_text)
    return req["skills"]


def extract_important_jd_keywords(jd_text, field=None):
    if not (jd_text or "").strip(): return []
    req = _extract_jd_requirements(jd_text, field)
    return req["keywords"]


def get_matching_skills(resume_skills, jd_skills):
    r = {_canonical_skill(x).lower() for x in (resume_skills or [])}
    return [s for s in (jd_skills or []) if _canonical_skill(s).lower() in r]


def get_missing_skills(resume_skills, jd_skills):
    r = {_canonical_skill(x).lower() for x in (resume_skills or [])}
    return [s for s in (jd_skills or []) if _canonical_skill(s).lower() not in r]


def get_matching_keywords(resume_text, jd_keywords):
    return [k for k in (jd_keywords or []) if _phrase_present(resume_text, k)]


def get_missing_keywords(resume_text, jd_keywords):
    return [k for k in (jd_keywords or []) if not _phrase_present(resume_text, k)]


def _role_similarity(resume_text, role, field):
    if not role: return 0
    if _phrase_present(resume_text, role): return 100
    aliases = {"data analyst":["analytics", "data analysis"], "software developer":["software development", "programming"], "graphic designer":["graphic design", "visual design"], "marketing analyst":["marketing", "campaign analysis"], "business analyst":["business analysis", "process improvement"], "hr intern":["human resources", "recruitment"]}
    hits = sum(_phrase_present(resume_text, x) for x in aliases.get(role.lower(), []))
    return min(100, hits * 50)


def infer_field_from_text(text, skills=None):
    text_l = _norm_ai(text)
    skill_set = {_canonical_skill(x).lower() for x in (skills or [])}
    scores = {}
    for field, profile in FIELD_INTELLIGENCE.items():
        score = 0.0
        for sig in profile.get("domains", []):
            if _phrase_present(text_l, sig): score += 7 if " " in sig else 3
        for role in profile.get("roles", []):
            if _phrase_present(text_l, role): score += 14
        for sk in profile.get("skills", []):
            if _canonical_skill(sk).lower() in skill_set: score += 2.5
        scores[field] = score
    # Avoid classifying a clearly technical resume as generic fresher merely because it says "student".
    if scores and max(scores.values()) < 8:
        return "Student / Fresher"
    scores["Student / Fresher"] = scores.get("Student / Fresher", 0) - (5 if max(scores.values(), default=0) > 12 else 0)
    return max(scores, key=scores.get)


def infer_role_from_text(text, field):
    tl = _norm_ai(text)
    profile = FIELD_INTELLIGENCE.get(field, FIELD_INTELLIGENCE["Student / Fresher"])
    best, best_score = None, 0
    for role in profile.get("roles", []):
        score = 0
        if _phrase_present(tl, role): score += 100
        # Role words are useful only as weak supporting evidence.
        for token in re.findall(r"[a-z]+", role.lower()):
            if len(token) > 3 and re.search(r"\b" + re.escape(token) + r"\b", tl): score += 8
        if score > best_score: best, best_score = role, score
    return best or profile.get("roles", ["Professional"])[0]


def infer_field_and_role(resume_text, jd_text, resume_skills, jd_skills):
    resume_field = infer_field_from_text(resume_text, resume_skills)
    resume_role = infer_role_from_text(resume_text, resume_field)
    if (jd_text or "").strip():
        jd_req = _extract_jd_requirements(jd_text)
        jd_field = infer_field_from_text(jd_text, jd_req.get("skills", []))
        # Explicit JD role wins; field follows the role when confidently identified.
        jd_role = infer_role_from_text(jd_text, jd_field)
        if jd_req.get("role") and jd_req["role"] in FIELD_INTELLIGENCE.get(jd_field, {}).get("roles", []):
            jd_role = jd_req["role"]
        return jd_field, jd_role
    return resume_field, resume_role


def infer_resume_field(resume_text, resume_skills):
    return infer_field_from_text(resume_text, resume_skills)


def infer_target_role(resume_text, field, resume_skills):
    return infer_role_from_text(resume_text, field)


def calculate_ats_score(resume_skills, matching_skills, jd_skills, sections, contact, has_projects, has_experience, achievements, field="Student / Fresher", resume_text="", bullets=None, readability=0):
    """General ATS compatibility score, independent of JD presence."""
    profile = FIELD_INTELLIGENCE.get(field, FIELD_INTELLIGENCE["Student / Fresher"])
    profile_skills = {_canonical_skill(x).lower() for x in profile.get("skills", [])}
    resume_skill_set = {_canonical_skill(x).lower() for x in (resume_skills or [])}
    relevant = len(resume_skill_set & profile_skills)
    skills_score = min(25, round(8 + relevant * 1.7 + min(5, max(0, len(resume_skills or []) - relevant) * 0.5))) if resume_skills else 0
    section_count = sum(bool(v) for v in (sections or {}).values())
    structure_score = round(min(18, 18 * section_count / max(1, len(sections))))
    contact_score = round(sum(bool(v) for v in (contact or {}).values()) / max(1, len(contact)) * 10)
    evidence_score = (8 if has_projects else 0) + (7 if has_experience else 0)
    achievement_score = min(10, len(achievements or []) * 2)
    bullet_score = min(7, round(len(bullets or []) * 0.8))
    readability_component = min(5, round(max(0, float(readability or 0)) / 20))
    words = len((resume_text or "").split())
    if 250 <= words <= 750: density_score = 10
    elif 150 <= words <= 1000: density_score = 8
    elif words > 0: density_score = 5
    else: density_score = 0
    total = min(100, round(skills_score + structure_score + contact_score + evidence_score + achievement_score + bullet_score + readability_component + density_score))
    return total, {
        "Skills & Role Relevance": skills_score,
        "ATS Structure": structure_score,
        "Contact Information": contact_score,
        "Projects / Experience": evidence_score,
        "Achievements": achievement_score,
        "Bullet Quality": bullet_score,
        "Readability": readability_component,
        "Content Density": density_score,
    }

def _weighted_job_match(resume_text, resume_skills, jd_text, field, role):
    if not (jd_text or "").strip(): return 0, {}
    req = _extract_jd_requirements(jd_text, field)
    rskills = {_canonical_skill(x).lower() for x in (resume_skills or [])}
    must = req["must_skills"]; all_skills = req["skills"]
    must_hit = [s for s in must if _canonical_skill(s).lower() in rskills]
    skill_hit = [s for s in all_skills if _canonical_skill(s).lower() in rskills]
    must_cov = len(must_hit) / len(must) if must else (len(skill_hit) / len(all_skills) if all_skills else 0.0)
    skill_cov = len(skill_hit) / len(all_skills) if all_skills else 0.0
    present_keywords = [k for k in req["keywords"] if _phrase_present(resume_text, k)]
    keyword_cov = len(present_keywords) / len(req["keywords"]) if req["keywords"] else 0.0
    resp_hits = [r for r in req["responsibilities"] if _phrase_present(resume_text, r)]
    resp_cov = len(resp_hits) / len(req["responsibilities"]) if req["responsibilities"] else (keyword_cov * .6)
    role_cov = _role_similarity(resume_text, role, field) / 100
    education_cov = 1.0 if not req["education"] else min(1.0, sum(_phrase_present(resume_text, x) for x in req["education"]) / len(req["education"]))
    experience_cov = 1.0 if not req["experience"] else min(1.0, sum(_phrase_present(resume_text, x) for x in req["experience"]) / len(req["experience"]))
    soft_cov = 1.0 if not req["soft_skills"] else sum(_phrase_present(resume_text, x) for x in req["soft_skills"]) / len(req["soft_skills"])
    score = 100 * (0.30*must_cov + 0.18*skill_cov + 0.18*keyword_cov + 0.16*resp_cov + 0.10*role_cov + 0.04*education_cov + 0.04*experience_cov)
    if req["soft_skills"]: score = score * .95 + 5 * soft_cov
    details = {"must_required": must, "must_matched": must_hit, "skills": all_skills, "skill_matched": skill_hit, "keywords": req["keywords"], "keywords_matched": present_keywords, "responsibilities": req["responsibilities"], "responsibilities_matched": resp_hits, "role": req["role"], "seniority": req["seniority"], "education": req["education"], "experience": req["experience"], "soft_skills": req["soft_skills"], "confidence": min(100, round(45 + min(25,len(all_skills)*4) + min(20,len(req["keywords"])*1.5) + (10 if req["role"] else 0)))}
    return max(0, min(100, round(score))), details


def calculate_quality_score(text, sections, achievements, has_projects, has_experience):
    """Evidence/content quality, independent from target JD."""
    score = 35
    section_count = sum(bool(v) for v in (sections or {}).values())
    score += min(20, round(section_count * 2.5))
    words = len((text or "").split())
    if 250 <= words <= 750: score += 15
    elif 150 <= words <= 1000: score += 10
    if achievements: score += min(10, len(achievements)*2)
    if has_projects: score += 5
    if has_experience: score += 5
    bullets = get_bullet_points(text)
    if len(bullets) >= 5: score += 5
    return min(100, round(score))


def calculate_nlp_score(action_verbs, bullets, readability, weak_verbs, generic_phrases):
    strong = min(20, len(action_verbs) * 2)
    bullet_score = min(15, len(bullets) * 1.5)
    read = round(readability * .20)
    penalties = min(20, len(weak_verbs)*2 + len(generic_phrases)*2)
    return max(0, min(100, round(45 + strong + bullet_score + read - penalties)))


def generate_summary(resume_skills, target_role="Professional", field="Student / Fresher", jd_text="", resume_text=""):
    role = (target_role or "Professional").strip() or "Professional"
    profile = FIELD_INTELLIGENCE.get(field, FIELD_INTELLIGENCE["Student / Fresher"])
    available = [_canonical_skill(x) for x in (resume_skills or [])]
    relevant = [x for x in profile.get("skills", []) if _canonical_skill(x).lower() in {a.lower() for a in available}]
    if not relevant: relevant = available[:8]
    relevant = list(dict.fromkeys(relevant))[:7]
    skill_text = ", ".join(relevant) if relevant else "transferable skills"
    focus_map = {
        "Data / Analytics":"data analysis, data cleaning, exploratory analysis, visualization, reporting, and evidence-based insights",
        "Software / IT":"software development, programming, testing, debugging, and building reliable technical solutions",
        "Business / Finance":"business analysis, reporting, financial/operational analysis, process improvement, and decision support",
        "Marketing / Sales":"campaign execution, customer engagement, market research, content, lead generation, and performance analysis",
        "Design / Creative":"visual communication, branding, interface/content design, prototyping, and audience-focused creative work",
        "HR / Administration":"recruitment support, coordination, documentation, reporting, and people-focused operations",
        "Student / Fresher":"academic projects, practical problem solving, collaboration, and continuous professional learning",
        "Other / Custom":"practical projects, problem solving, communication, and continuous learning",
    }
    jd_req = _extract_jd_requirements(jd_text, field) if (jd_text or "").strip() else None
    jd_focus = [] if not jd_req else [s for s in jd_req.get("skills", []) if _canonical_skill(s).lower() in {a.lower() for a in available}][:4]
    if jd_focus:
        focus = ", ".join(jd_focus)
        return (f"Aspiring {role} with hands-on knowledge of {skill_text}. Focused on applying {focus} to practical {field.lower()} work, while contributing through structured problem solving, collaboration, and evidence-based execution. Seeking a {role} opportunity to apply existing skills and continue building professional impact.")
    prefix = "BCA student and aspiring" if field in {"Data / Analytics","Software / IT","Business / Finance","Marketing / Sales","Design / Creative","HR / Administration","Student / Fresher"} else "Motivated candidate and aspiring"
    return f"{prefix} {role} with hands-on knowledge of {skill_text}. Focused on {focus_map.get(field, focus_map['Other / Custom'])} and applying practical skills to real-world challenges. Seeking a {role} opportunity to contribute effectively, learn continuously, and build measurable professional impact."


def generate_recommendations(missing_skills, missing_keywords, achievements, contact, weak_verbs, generic_phrases, bullets, field="Student / Fresher", job_details=None):
    rec = []
    if job_details and job_details.get("must_required"):
        missing_must = [s for s in job_details["must_required"] if s not in job_details.get("must_matched", [])]
        if missing_must:
            rec.append("Priority JD requirements not evidenced in the resume: " + ", ".join(missing_must[:6]) + ". Add them only if you genuinely have the skill or experience.")
    elif missing_skills:
        rec.append("Potential skill gaps for the target role: " + ", ".join(missing_skills[:8]) + ". Add only skills you genuinely know.")
    if not achievements:
        rec.append("Add evidence of impact where truthful: percentages, counts, time saved, accuracy, revenue, users, deliverables, or other measurable outcomes.")
    if not contact.get("LinkedIn"):
        rec.append("Add LinkedIn if available to make professional contact information easier to verify.")
    if weak_verbs:
        rec.append("Strengthen weak openings such as " + ", ".join(weak_verbs[:6]) + " by naming the action you personally performed.")
    if generic_phrases:
        rec.append("Replace generic phrases such as " + ", ".join(generic_phrases[:5]) + " with specific evidence or examples.")
    if len(bullets) < 5:
        rec.append("Use concise bullets for experience and projects; structure them as action + task + method/tool + evidence when the evidence exists.")
    if job_details and job_details.get("confidence", 0) < 65:
        rec.append("Job-description confidence is limited because the supplied JD contains relatively few structured requirements. Treat the match score as directional and review the source JD manually.")
    return rec or ["Resume structure is reasonably complete. Keep each application role-specific and support claims with concrete evidence."]


def improve_generic_phrases(text):
    replacements = {
        "hard working":"results-focused", "hardworking":"results-focused", "quick learner":"adaptable learner",
        "team player":"collaborative team member", "good communication":"effective communication", "passionate":"motivated",
        "familiar with":"knowledge of", "strong communication":"effective communication", "detail oriented":"detail-oriented",
        "problem solving skills":"problem-solving skills", "analytical skills":"analytical capability"
    }
    found=[]; tl=(text or "").lower()
    for phrase,replacement in replacements.items():
        if phrase in tl: found.append({"Original":phrase,"Suggested":replacement,"Reason":"More specific, professional wording; replace only when it accurately reflects the candidate."})
    return found


def build_template_resume_data(data, field, target_role):
    profile = FIELD_INTELLIGENCE.get(field, FIELD_INTELLIGENCE["Other / Custom"])
    sections = extract_resume_sections(data.get("resume_text", ""))
    skills = data.get("resume_skills", [])
    allowed = {_canonical_skill(x).lower() for x in profile.get("skills", [])}
    preferred = [s for s in skills if _canonical_skill(s).lower() in allowed]
    # Preserve real detected skills even when a selected custom field has a small profile.
    if not preferred: preferred = skills[:12]
    role = target_role.strip() if target_role.strip() else profile["roles"][0]
    summary = generate_summary(skills, role, field, data.get("jd_text", ""), data.get("resume_text", ""))
    return {
        "name": data.get("candidate_name") or extract_candidate_name(data.get("resume_text", "")),
        "email": re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", data.get("resume_text", ""))[:1],
        "phone": re.findall(r"(?:\+91[\s-]?)?[6-9]\d{9}", data.get("resume_text", ""))[:1],
        "linkedin": re.findall(r"https?://(?:www\.)?linkedin\.com/[^\s]+", data.get("resume_text", ""), re.I)[:1],
        "github": re.findall(r"https?://(?:www\.)?github\.com/[^\s]+", data.get("resume_text", ""), re.I)[:1],
        "role": role, "summary": summary, "skills": preferred[:20],
        "education": sections.get("Education", []), "experience": sections.get("Experience", []), "projects": sections.get("Projects", []),
        "certifications": sections.get("Certifications", []), "achievements": sections.get("Achievements", []),
        "section_order": profile.get("section_order", ["Summary","Skills","Experience","Projects","Education","Certifications","Achievements"]), "field": field,
    }

# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.markdown("## ◈ AI Resume Analyzer")
    st.caption("Professional resume intelligence workspace")
    st.markdown("---")
    st.markdown("### 🧭 Workspace")
    st.markdown("""
    **01**  Upload & Analyze  

    **02**  ATS & Job Match  

    **03**  Resume Quality  

    **04**  AI Improvement  

    **05**  PDF Analysis Report  

    **06**  Professional Resume Generator  

    **07**  NLP & Keywords
    """)
    st.markdown("---")
    st.markdown("### ✨ Built-in Intelligence")
    st.markdown("Skill detection • ATS scoring • JD matching • NLP writing checks • field detection • professional resume generation")
    st.markdown("---")
    st.caption("💡 Tip: Use a clean, text-based PDF and add the target job description for the most useful results.")


# =========================================================
# PREMIUM HEADER + INPUT
# =========================================================

st.markdown("""
<div class="premium-hero">
  <div class="hero-kicker">AI-Powered Career Toolkit</div>
  <div class="hero-title">◈ AI Resume Analyzer</div>
  <div class="hero-copy">Analyze ATS compatibility, match your resume with a job description, identify skill gaps, improve your writing, and generate a professional resume — all in one workspace.</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-head"><div class="num">01</div><h2>Upload & Target</h2></div>', unsafe_allow_html=True)
st.caption("Start with your current resume. Adding a job description unlocks deeper keyword and job-match analysis.")

input_col1, input_col2 = st.columns([1, 1.35], gap="large")
with input_col1:
    st.markdown('<span class="step-chip">RESUME</span>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("📤 Upload Resume PDF", type=["pdf"], help="Upload a text-based PDF resume for best extraction accuracy.")
    if uploaded_file:
        st.success(f"✓ Ready: {uploaded_file.name}")
with input_col2:
    st.markdown('<span class="step-chip">OPTIONAL JOB DESCRIPTION</span>', unsafe_allow_html=True)
    jd_text = st.text_area("🎯 Paste Job Description", height=158, placeholder="Paste the target job description here to calculate job match, missing skills and important keywords...")

analyze_button = st.button("🔍 Analyze Resume", use_container_width=True, type="primary")


# =========================================================
# ANALYSIS
# =========================================================

if analyze_button:

    if uploaded_file is None:

        st.warning(
            "Please upload a resume PDF first."
        )

    else:

        with st.spinner(
            "Analyzing your resume..."
        ):

            resume_text = (
                extract_text_from_pdf(
                    uploaded_file
                )
            )

            if not resume_text:

                st.error(
                    "Could not extract text from the PDF."
                )

                st.stop()

            # -------------------------------------------------
            # Analysis
            # -------------------------------------------------

            resume_skills = detect_skills(
                resume_text
            )

            jd_skills = extract_jd_skills(
                jd_text
            )

            detected_field, detected_role = infer_field_and_role(
                resume_text, jd_text, resume_skills, jd_skills
            )

            jd_keywords = (
                extract_important_jd_keywords(
                    jd_text, detected_field
                )
            )

            matching_skills = (
                get_matching_skills(
                    resume_skills,
                    jd_skills
                )
            )

            missing_skills = (
                get_missing_skills(
                    resume_skills,
                    jd_skills
                )
            )

            matching_keywords = (
                get_matching_keywords(
                    resume_text,
                    jd_keywords
                )
            )

            missing_keywords = (
                get_missing_keywords(
                    resume_text,
                    jd_keywords
                )
            )

            sections = detect_sections(
                resume_text
            )

            contact = detect_contact(
                resume_text
            )

            achievements = detect_achievements(
                resume_text
            )

            bullets = get_bullet_points(
                resume_text
            )

            action_verbs = detect_action_verbs(
                resume_text
            )

            weak_verbs = detect_weak_verbs(
                resume_text
            )

            generic_phrases = (
                detect_generic_phrases(
                    resume_text
                )
            )

            readability = readability_score(
                resume_text
            )

            keyword_density = (
                calculate_keyword_density(
                    resume_text,
                    resume_skills
                )
            )

            repeated = repeated_words(
                resume_text,
                focus_terms=(resume_skills + jd_keywords)
            )

            # -------------------------------------------------
            # Scores
            # -------------------------------------------------

            ats_score, ats_breakdown = (
                calculate_ats_score(
                    resume_skills, matching_skills, jd_skills, sections, contact,
                    sections["Projects"], sections["Experience"], achievements, detected_field,
                    resume_text=resume_text, bullets=bullets, readability=readability
                )
            )

            quality_score = (
                calculate_quality_score(
                    resume_text,
                    sections,
                    achievements,
                    sections["Projects"],
                    sections["Experience"]
                )
            )

            nlp_score = (
                calculate_nlp_score(
                    action_verbs,
                    bullets,
                    readability,
                    weak_verbs,
                    generic_phrases
                )
            )

            # -------------------------------------------------
            # Job Match — weighted, JD-specific, separate from ATS
            # -------------------------------------------------

            job_match, job_match_details = _weighted_job_match(
                resume_text, resume_skills, jd_text, detected_field, detected_role
            )

            # -------------------------------------------------
            # Step 16
            # -------------------------------------------------

            weak_verb_suggestions = (
                improve_weak_verbs(
                    resume_text
                )
            )

            generic_phrase_suggestions = (
                improve_generic_phrases(
                    resume_text
                )
            )

            bullet_suggestions = (
                improve_bullets(
                    bullets
                )
            )

            candidate_name = extract_candidate_name(resume_text)
            improved_summary = generate_summary(resume_skills, detected_role, detected_field, jd_text, resume_text)

            recommendations = (
                generate_recommendations(
                    missing_skills, missing_keywords, achievements, contact, weak_verbs,
                    generic_phrases, bullets, detected_field, job_match_details if jd_text.strip() else None
                )
            )

            improved_resume = (
                generate_improved_resume(
                    resume_text,
                    resume_skills,
                    bullets,
                    missing_skills,
                    detected_role,
                    detected_field
                )
            )

            # -------------------------------------------------
            # Session State
            # -------------------------------------------------

            for _key in ["generated_resume_pdf", "generated_resume_field", "generated_resume_template", "generated_resume_role", "generated_resume_name"]:
                st.session_state.pop(_key, None)

            st.session_state.analysis = {

                "resume_text":
                    resume_text,

                "candidate_name": candidate_name,
                "detected_field": detected_field,
                "detected_role": detected_role,
                "jd_text": jd_text or "",
                "original_resume_pdf": uploaded_file.getvalue(),

                "resume_skills":
                    resume_skills,

                "jd_skills":
                    jd_skills,

                "jd_keywords":
                    jd_keywords,

                "matching_skills":
                    matching_skills,

                "missing_skills":
                    missing_skills,

                "matching_keywords":
                    matching_keywords,

                "missing_keywords":
                    missing_keywords,

                "sections":
                    sections,

                "contact":
                    contact,

                "achievements":
                    achievements,

                "bullets":
                    bullets,

                "action_verbs":
                    action_verbs,

                "weak_verbs":
                    weak_verbs,

                "generic_phrases":
                    generic_phrases,

                "readability":
                    readability,

                "keyword_density":
                    keyword_density,

                "repeated":
                    repeated,

                "ats_score":
                    ats_score,

                "ats_breakdown":
                    ats_breakdown,

                "quality_score":
                    quality_score,

                "nlp_score":
                    nlp_score,

                "job_match":
                    job_match,

                "job_match_details":
                    job_match_details,

                "analysis_confidence":
                    (job_match_details.get("confidence", 0) if jd_text.strip() else min(100, 60 + min(35, len(resume_skills) * 2))),

                "weak_verb_suggestions":
                    weak_verb_suggestions,

                "generic_phrase_suggestions":
                    generic_phrase_suggestions,

                "bullet_suggestions":
                    bullet_suggestions,

                "improved_summary":
                    improved_summary,

                "recommendations":
                    recommendations,

                "improved_resume":
                    improved_resume
            }


# =========================================================
# RESULTS
# =========================================================

if "analysis" in st.session_state:

    data = st.session_state.analysis

    st.markdown("---")

    st.markdown("""<div class="section-title-card"><div class="section-icon">📊</div><div><div class="section-kicker">ANALYSIS DASHBOARD</div><div class="section-title">Resume Analysis</div></div></div>""", unsafe_allow_html=True)

    # =====================================================
    # METRICS
    # =====================================================

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "ATS Score",
        f"{data['ats_score']}/100"
    )

    col2.metric(
        "Job Match",
        f"{data['job_match']}%"
    )

    col3.metric(
        "Skills Found",
        len(data["resume_skills"])
    )

    col4.metric(
        "Achievements",
        len(data["achievements"])
    )

    col5, col6, col7, col8 = st.columns(4)

    col5.metric(
        "Resume Quality",
        f"{data['quality_score']}/100"
    )

    col6.metric(
        "Sections",
        sum(
            data["sections"].values()
        )
    )

    col7.metric(
        "NLP Score",
        f"{data['nlp_score']}/100"
    )

    col8.metric(
        "Keyword Density",
        f"{data['keyword_density']}%"
    )


    # =====================================================
    # STATUS
    # =====================================================

    if data["ats_score"] >= 80:

        st.success(
            "🟢 Strong ATS performance"
        )

    elif data["ats_score"] >= 60:

        st.warning(
            "🟡 Resume has room for improvement"
        )

    else:

        st.error(
            "🔴 Resume needs significant improvement"
        )


    # =====================================================
    # ATS BREAKDOWN
    # =====================================================

    st.markdown("---")

    st.markdown("""<div class="section-title-card"><div class="section-icon">📈</div><div><div class="section-kicker">SCORING INSIGHTS</div><div class="section-title">ATS Score Breakdown</div></div></div>""", unsafe_allow_html=True)

    breakdown_rows = [
        (str(category), int(round(float(score))))
        for category, score in data.get("ats_breakdown", {}).items()
    ]

    component_max = {
        "Skills & Role Relevance": 25,
        "ATS Structure": 18,
        "Contact Information": 10,
        "Projects / Experience": 15,
        "Achievements": 10,
        "Bullet Quality": 7,
        "Readability": 5,
        "Content Density": 10,
    }
    st.info(
        f"ATS Compatibility: {int(data.get('ats_score', 0))}/100 — "
        "each bar shows points earned out of that category's maximum. "
        "ATS measures resume compatibility; Job Match is calculated separately from the JD."
    )
    chart_rows = []
    for label, score in breakdown_rows:
        maximum = component_max.get(label, max(1, score))
        pct = max(0, min(100, (score / maximum) * 100))
        row = ('<div class="ats-chart-row">'
               f'<div class="ats-chart-label">{label}</div>'
               f'<div class="ats-chart-track"><div class="ats-chart-fill" style="width:{pct:.1f}%"></div></div>'
               f'<div class="ats-chart-value">{score}/{maximum}</div></div>')
        chart_rows.append(row)
    st.markdown('<div class="ats-chart">' + ''.join(chart_rows) + '</div>', unsafe_allow_html=True)

    # Transparent ATS calculation: show exactly how the displayed total is built.
    st.markdown("#### How the ATS score is built")
    score_table_rows = []
    total_earned = 0
    total_max = sum(component_max.values())
    for label, score in breakdown_rows:
        maximum = component_max.get(label, max(1, score))
        total_earned += score
        score_table_rows.append([label, f"{score}/{maximum}", f"{(score / maximum * 100):.0f}%"])
    score_table_rows.append(["Total ATS Compatibility", f"{int(data.get('ats_score', 0))}/100", f"{int(data.get('ats_score', 0))}%"])
    render_analysis_table(["Category", "Points", "Category coverage"], score_table_rows, numeric_last=True)
    st.caption("The total is the sum of the eight ATS components above, capped at 100. Job Match is intentionally separate and uses the supplied job description.")



    # =====================================================
    # QUALITY
    # =====================================================

    st.markdown("---")

    st.markdown("""<div class="section-title-card"><div class="section-icon">⭐</div><div><div class="section-kicker">QUALITY REVIEW</div><div class="section-title">Resume Quality</div></div></div>""", unsafe_allow_html=True)

    word_count = len(
        data["resume_text"].split()
    )

    q1, q2, q3, q4 = st.columns(4)

    q1.metric(
        "Quality Score",
        f"{data['quality_score']}/100"
    )

    q2.metric(
        "Word Count",
        word_count
    )

    q3.metric(
        "Readability",
        f"{data['readability']}/100"
    )

    q4.metric(
        "Bullet Points",
        len(data["bullets"])
    )


    # =====================================================
    # SECTIONS + CONTACT
    # =====================================================

    st.markdown("---")

    left, right = st.columns(2)

    with left:

        st.subheader(
            "📚 Resume Sections"
        , anchor=False)

        st.markdown('<div class="status-grid">', unsafe_allow_html=True)
        for section, detected in data["sections"].items():
            cls = "ok" if detected else "missing"
            icon = "✓" if detected else "✗"
            st.markdown(f'<div class="status-item {cls}"><span class="status-icon">{icon}</span><span>{section}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:

        st.subheader(
            "📞 Contact Information"
        , anchor=False)

        st.markdown('<div class="status-grid">', unsafe_allow_html=True)
        for item, detected in data["contact"].items():
            cls = "ok" if detected else "missing"
            icon = "✓" if detected else "✗"
            st.markdown(f'<div class="status-item {cls}"><span class="status-icon">{icon}</span><span>{item}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


    # =====================================================
    # SKILLS
    # =====================================================

    st.markdown("---")

    st.header(
        "🛠️ Skills Analysis"
    , anchor=False)

    if data["resume_skills"]:

        st.write(
            "**Skills detected in resume:**"
        )

        st.write(
            ", ".join(
                data["resume_skills"]
            )
        )

    else:

        st.warning(
            "No technical skills detected."
        )


    # =====================================================
    # JOB MATCH
    # =====================================================

    if data["jd_skills"]:

        st.markdown("---")

        st.header(
            "🎯 Job Description Match"
        , anchor=False)

        m1, m2, m3 = st.columns(3)

        m1.metric(
            "JD Technical Skills",
            len(data["jd_skills"])
        )

        m2.metric(
            "Matching Skills",
            len(data["matching_skills"])
        )

        m3.metric(
            "Missing Skills",
            len(data["missing_skills"])
        )

        st.subheader(
            "✅ Matching Skills"
        , anchor=False)

        if data["matching_skills"]:

            st.success(
                ", ".join(
                    data["matching_skills"]
                )
            )

        else:

            st.warning(
                "No matching technical skills detected."
            )

        st.subheader(
            "❌ Missing Technical Skills"
        , anchor=False)

        if data["missing_skills"]:

            st.warning(
                ", ".join(
                    data["missing_skills"]
                )
            )

        else:

            st.success(
                "Excellent! No major technical skill gaps detected."
            )


    # =====================================================
    # JOB KEYWORDS
    # =====================================================

    if data["jd_keywords"]:

        st.subheader(
            "🔑 Important Job Keywords"
        , anchor=False)

        k1, k2 = st.columns(2)

        with k1:

            st.markdown(
                "**Present in Resume**"
            )

            if data["matching_keywords"]:

                st.success(
                    ", ".join(
                        data["matching_keywords"]
                    )
                )

            else:

                st.info(
                    "No additional job keywords detected."
                )

        with k2:

            st.markdown(
                "**Missing Keywords**"
            )

            if data["missing_keywords"]:

                st.warning(
                    ", ".join(
                        data["missing_keywords"]
                    )
                )

            else:

                st.success(
                    "No major keyword gaps detected."
                )


    # =====================================================
    # RECOMMENDATIONS
    # =====================================================

    st.markdown("---")

    st.header(
        "💡 Recommendations"
    , anchor=False)

    for recommendation in (
        data["recommendations"]
    ):

        st.info(
            recommendation
        )


    # =====================================================
    # STEP 16
    # =====================================================

    st.markdown("---")

    st.header(
        "◈ Step 16 — AI Resume Improvement"
    , anchor=False)

    st.write(
        "Improve weak wording, strengthen resume "
        "bullets, optimize your summary, and "
        "generate a cleaner resume version."
    )


    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    st.subheader(
        "📝 Improved Professional Summary"
    , anchor=False)

    summary_value = (data.get("improved_summary") or "").strip() or generate_summary(data.get("resume_skills", []), data.get("detected_role", "Data Analyst"), data.get("detected_field", "Data / Analytics"))
    st.markdown(
        f"<div class=\"summary-preview-card\">{_safe_pdf_text(summary_value)}</div>",
        unsafe_allow_html=True
    )
    st.text_area("Copy Summary", value=summary_value, height=120, key="improved_summary_copy_v3", label_visibility="collapsed")


    # -----------------------------------------------------
    # Weak Verbs
    # -----------------------------------------------------

    st.subheader(
        "🔥 Weak Verb Improvements"
    , anchor=False)

    if data["weak_verb_suggestions"]:

        for item in (
            data["weak_verb_suggestions"]
        ):

            st.write(
                f"**{item['Original']}** → "
                f"**{item['Suggested']}**"
            )

            st.caption(
                item["Reason"]
            )

    else:

        st.success(
            "No major weak action verbs detected."
        )


    # -----------------------------------------------------
    # Generic Phrases
    # -----------------------------------------------------

    st.subheader(
        "✍️ Generic Phrase Improvements"
    , anchor=False)

    if data["generic_phrase_suggestions"]:

        for item in (
            data["generic_phrase_suggestions"]
        ):

            st.write(
                f"**{item['Original']}** → "
                f"**{item['Suggested']}**"
            )

            st.caption(
                item["Reason"]
            )

    else:

        st.success(
            "No major generic phrases detected."
        )


    # -----------------------------------------------------
    # Bullet Improvement
    # -----------------------------------------------------

    st.subheader(
        "📌 Bullet Point Improvements"
    , anchor=False)

    if data["bullet_suggestions"]:

        for index, item in enumerate(
            data["bullet_suggestions"],
            start=1
        ):

            st.markdown(
                f"**Bullet {index} — Before**"
            )

            st.write(
                item["Original"]
            )

            st.markdown(
                f"**Bullet {index} — Improved**"
            )

            st.success(
                item["Improved"]
            )

    else:

        st.info(
            "No bullet improvements could be generated. "
            "The PDF extraction may have removed bullet "
            "formatting. We will fix this later."
        )


    # -----------------------------------------------------
    # Job-Specific Improvement
    # -----------------------------------------------------

    st.subheader(
        "🎯 Job-Specific Improvement"
    , anchor=False)

    if data["missing_skills"]:

        st.warning(
            "Consider adding these technical skills "
            "only if you genuinely have knowledge "
            "or experience with them:"
        )

        for skill in (
            data["missing_skills"]
        ):

            st.write(
                f"• {skill}"
            )

    else:

        st.success(
            "Your resume already covers the major "
            "detected technical skills."
        )


    # =====================================================
    # GENERATE IMPROVED RESUME
    # =====================================================

    st.markdown("---")

    st.subheader(
        "🚀 Generate Improved Resume"
    , anchor=False)

    st.write(
        "Generate a cleaner text-based resume "
        "using the information detected from "
        "your current resume."
    )

    if st.button(
        "✨ Generate Improved Resume",
        use_container_width=True
    ):

        st.session_state.generated_resume = (
            data["improved_resume"]
        )

    if (
        "generated_resume"
        in st.session_state
    ):

        st.success(
            "Improved resume generated successfully!"
        )

        st.text_area(
            "Generated Resume",
            value=st.session_state.generated_resume,
            height=600
        )

        st.download_button(
            label="⬇️ Download Improved Resume",
            data=st.session_state.generated_resume,
            file_name="improved_resume.txt",
            mime="text/plain",
            use_container_width=True
        )


    # =====================================================
    # STEP 17 — DOWNLOADABLE PDF REPORT
    # =====================================================

    st.markdown("---")
    st.header("📄 Step 17 — Download Analysis Report", anchor=False)
    st.write(
        "Download a professional PDF containing your complete "
        "resume analysis, scores, skills gap, NLP findings, "
        "recommendations, and AI improvement summary."
    )

    report_pdf = generate_analysis_report(data)

    report_preview_tab, report_download_tab = st.tabs(["👀 Preview Report", "📥 Download Report"])
    with report_preview_tab:
        render_pdf_preview(report_pdf.getvalue(), label="AI resume analysis report")
    with report_download_tab:
        st.download_button(
            label="📥 Download Professional Analysis Report",
            data=report_pdf,
            file_name="AI_Resume_Analysis_Report.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="download_analysis_report_v20",
        )


    # =====================================================
    # RESUME TEMPLATE GENERATOR — STEP 18
    # =====================================================

    st.markdown("---")
    st.header("🧩 Step 18 — Professional Resume Generator", anchor=False)
    st.write("Build a polished resume using the candidate’s field, target role, resume evidence, and job description — without inventing skills or experience.")
    field_options=list(FIELD_PROFILES.keys())
    detected_field=data.get("detected_field") or infer_resume_field(data.get("resume_text",""),data.get("resume_skills",[]))
    detected_role=data.get("detected_role") or infer_target_role(data.get("resume_text",""),detected_field,data.get("resume_skills",[]))
    fi=field_options.index(detected_field) if detected_field in field_options else 0
    c1,c2=st.columns(2)
    with c1: selected_field=st.selectbox("🎯 Target field",field_options,index=fi,key="resume_field_selector_v3")
    with c2:
        templates=["ATS Professional","Data Analyst Pro","Modern Sidebar","Executive Minimal","Creative Modern","Academic Pro","Tech Compact","Portfolio Accent","Editorial Luxe","Minimal Mono","Corporate Grid","Creative Portfolio","Swiss Modern","Nordic Executive","Tech Aurora","Finance Elite","Creative Studio","OnePage Classic"]
        recommended_templates={
            "Data / Analytics":"Data Analyst Pro",
            "Software / IT":"Tech Compact",
            "Design / Creative":"Creative Portfolio",
            "Marketing / Sales":"Editorial Luxe",
            "Business / Finance":"Corporate Grid",
            "HR / Administration":"Executive Minimal",
            "Student / Fresher":"Academic Pro",
            "Other / Custom":"ATS Professional",
        }
        default_template=recommended_templates.get(selected_field,"ATS Professional")
        selected_template=st.selectbox("🎨 Professional template",templates,index=templates.index(default_template),key="resume_template_selector_v3")
    st.caption(f"◈ AI target detected from Resume + JD: **{detected_field}** • **{detected_role}**. You can override the field/title.")
    st.info(f"⭐ Recommended template for **{selected_field}**: **{recommended_templates.get(selected_field, 'ATS Professional')}**. You can still choose any of the 18 professional designs.")
    roles=list(FIELD_PROFILES[selected_field]["roles"])
    if detected_role and detected_role not in roles:
        roles.insert(0, detected_role)
    ri=roles.index(detected_role) if detected_role in roles else 0
    r1,r2=st.columns(2)
    with r1: selected_role=st.selectbox("💼 Target job title",roles,index=ri,key="resume_role_selector_v3")
    with r2: custom_role=st.text_input("Optional custom title",placeholder="e.g. Data Analyst Intern",key="resume_custom_role_v3")
    target_role=custom_role.strip() or selected_role
    notes={"ATS Professional":"Maximum ATS readability with clean hierarchy.","Data Analyst Pro":"Premium analytics layout with structured toolkit and profile panel.","Modern Sidebar":"Compact sidebar-inspired profile architecture.","Executive Minimal":"Elegant corporate typography and restrained styling.","Creative Modern":"Bold visual presentation with creative hierarchy.","Academic Pro":"Education and projects first for students/internships.","Tech Compact":"Dense modern technical layout for software/IT profiles.","Portfolio Accent":"Portfolio-inspired visual layout with strong accent language.","Editorial Luxe":"Editorial-style premium typography and asymmetric accents.","Minimal Mono":"Ultra-clean monochrome hierarchy for universal roles.","Corporate Grid":"Structured corporate profile with competency-first presentation.","Creative Portfolio":"Visual portfolio-style presentation for creative roles.","Swiss Modern":"Swiss-inspired grid, restrained typography and strong information hierarchy.","Nordic Executive":"Clean Nordic corporate design with calm spacing and modern structure.","Tech Aurora":"Technical profile with modern teal accents and compact information architecture.","Finance Elite":"Premium finance and corporate styling with restrained gold detailing.","Creative Studio":"Bold studio aesthetic with polished creative hierarchy.","OnePage Classic":"Traditional executive one-page layout with refined typography and maximum readability."}
    st.info("💡 "+notes[selected_template])
    st.caption("ATS Safety: missing skills are never presented as claimed experience; no achievements or metrics are invented.")
    if st.button("✨ Generate Professional Resume",use_container_width=True,type="primary",key="generate_field_resume_v3"):
        with st.spinner("Building your professional resume..."):
            rd=build_template_resume_data(data,selected_field,target_role)
            # Never repeat the immediately previous visual variant for the same
            # template. This means clicking Generate repeatedly produces a
            # genuinely different visual treatment even with the same selection.
            variant_history=st.session_state.get("resume_variant_history_v3", {})
            used_variants=list(variant_history.get(selected_template, []))
            all_variants=list(range(1,6))
            # Do not repeat a design until every variant of the selected
            # template has been used. This makes repeated generation visibly
            # different even when the user never changes the dropdown.
            available_variants=[v for v in all_variants if v not in used_variants]
            if not available_variants:
                used_variants=[]
                available_variants=all_variants[:]
            chosen_variant=random.choice(available_variants)
            used_variants.append(chosen_variant)
            variant_history[selected_template]=used_variants
            st.session_state.resume_variant_history_v3=variant_history
            st.session_state.generated_resume_pdf=generate_resume_pdf(rd,selected_template,chosen_variant)
            st.session_state.generated_resume_variant=chosen_variant
            st.session_state.generated_resume_field=selected_field; st.session_state.generated_resume_template=selected_template; st.session_state.generated_resume_role=target_role; st.session_state.generated_resume_name=rd.get("name","Candidate")
    if st.session_state.get("generated_resume_pdf"):
        st.success(f"✅ Resume generated — {st.session_state.get('generated_resume_template','Professional')} • {st.session_state.get('generated_resume_role','Professional')} • Design Variant {st.session_state.get('generated_resume_variant','1')}")
        pdf_bytes=st.session_state.generated_resume_pdf.getvalue(); fname=_safe_filename(st.session_state.get("generated_resume_name") or data.get("candidate_name") or "Candidate")
        resume_preview_tab, resume_download_tab = st.tabs(["👀 Preview Resume", "📥 Download Resume"])
        with resume_preview_tab:
            render_pdf_preview(
                st.session_state.generated_resume_pdf.getvalue(),
                label="Generated professional resume",
            )
        with resume_download_tab:
            st.download_button(
                "⬇️ Download Professional Resume",
                pdf_bytes,
                file_name=f"{fname}_Professional_Resume.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_generated_resume_v20",
            )


    # =====================================================
    # STEP 19 — NLP & KEYWORDS
    # =====================================================

    st.markdown("---")
    st.markdown("""<div class="section-title-card"><div class="section-icon">🧠</div><div><div class="section-kicker">LANGUAGE INTELLIGENCE</div><div class="section-title">Step 19 — NLP & Keywords</div></div></div>""", unsafe_allow_html=True)
    st.write(
        "Evaluate resume language quality, action verbs, readability, keyword usage, "
        "repeated terms, and wording improvements using the same analysis already used "
        "for your ATS score."
    )

    n1, n2, n3, n4 = st.columns(4)
    n1.metric("NLP Score", f"{data.get('nlp_score', 0)}/100")
    n2.metric("Strong Verbs", len(data.get("action_verbs", [])))
    n3.metric("Weak Verbs", len(data.get("weak_verbs", [])))
    n4.metric("Readability", f"{data.get('readability', 0)}/100")

    # NLP score interpretation
    nlp_value = int(data.get("nlp_score", 0))
    if nlp_value >= 80:
        st.success("🟢 Strong resume language. Your writing is generally clear, action-oriented, and ATS-friendly.")
    elif nlp_value >= 60:
        st.info("🟡 Good foundation. Strengthen action verbs, specificity, and sentence clarity to improve the NLP score.")
    else:
        st.warning("🔴 Resume language needs improvement. Focus on stronger verbs, concise bullets, and specific evidence.")

    verb_col, writing_col = st.columns(2)

    with verb_col:
        st.subheader("🔥 Action Verb Analysis", anchor=False)
        strong = data.get("action_verbs", [])
        weak = data.get("weak_verbs", [])
        if strong:
            st.markdown('<div class="nlp-chip-wrap">' + ''.join(f'<span class="nlp-chip nlp-chip-good">{_safe_pdf_text(v.title())}</span>' for v in strong[:20]) + '</div>', unsafe_allow_html=True)
        else:
            st.caption("No strong action verbs were detected.")
        if weak:
            st.markdown("**Weak verbs detected:**")
            st.markdown('<div class="nlp-chip-wrap">' + ''.join(f'<span class="nlp-chip nlp-chip-warn">{_safe_pdf_text(v.title())}</span>' for v in weak[:12]) + '</div>', unsafe_allow_html=True)
        else:
            st.success("No major weak action verbs detected.")

    with writing_col:
        st.subheader("✍️ Writing Quality", anchor=False)
        generic = data.get("generic_phrases", [])
        readability = int(data.get("readability", 0))
        density = float(data.get("keyword_density", 0) or 0)
        st.markdown(
            f'<div class="nlp-stat-grid">'
            f'<div><span>Readability</span><strong>{readability}/100</strong></div>'
            f'<div><span>Keyword Density</span><strong>{density:.2f}%</strong></div>'
            f'<div><span>Bullets</span><strong>{len(data.get("bullets", []))}</strong></div>'
            f'<div><span>Generic Phrases</span><strong>{len(generic)}</strong></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if generic:
            st.markdown("**Generic phrases detected:** " + ", ".join(generic[:8]))
        else:
            st.success("No major generic phrases detected.")

    st.subheader("🔁 Meaningful Repeated Words", anchor=False)
    repeated = data.get("repeated", {}) or {}
    if repeated:
        repeated_rows = [(str(word).title(), int(count)) for word, count in list(repeated.items())[:10]]
        render_analysis_table(["Word", "Count"], repeated_rows, numeric_last=True)
        if max(repeated.values()) >= 5:
            st.warning("Some terms appear frequently. Keep important keywords, but avoid unnatural repetition.")
        else:
            st.caption("These are meaningful repeated terms only; common resume boilerplate is filtered out.")
    else:
        st.success("No major repeated content words detected.")

    st.subheader("🛠️ NLP Improvement Suggestions", anchor=False)
    suggestions = []
    if data.get("weak_verb_suggestions"):
        for item in data["weak_verb_suggestions"][:8]:
            suggestions.append(f"Replace **{item['Original']}** with **{item['Suggested']}** — {item['Reason']}")
    if data.get("generic_phrase_suggestions"):
        for item in data["generic_phrase_suggestions"][:8]:
            suggestions.append(f"Improve **{item['Original']}** → **{item['Suggested']}** — {item['Reason']}")
    if readability < 70:
        suggestions.append("Shorten long sentences and keep resume bullets concise for better readability.")
    if density > 15:
        suggestions.append("Keyword density is high; keep important keywords but avoid repeating them unnaturally.")
    elif density < 5:
        suggestions.append("Keyword usage is relatively low; naturally include relevant role and JD terminology where truthful.")
    if len(data.get("bullets", [])) < 5:
        suggestions.append("Use concise bullet points for projects and experience, starting with strong action verbs.")

    if suggestions:
        for idx, suggestion in enumerate(suggestions[:10], 1):
            st.markdown(f'<div class="nlp-suggestion"><span>{idx}</span><div>{suggestion}</div></div>', unsafe_allow_html=True)
    else:
        st.success("Your NLP writing checks look strong. Keep tailoring keywords to each target job.")


    # =====================================================
    # ORIGINAL RESUME + RESET
    # =====================================================

    st.markdown("---")
    st.subheader("📄 Original Resume", anchor=False)
    original_pdf = data.get("original_resume_pdf")
    if original_pdf:
        st.caption("View the exact PDF that was analyzed. No changes are made to the original file.")
        render_pdf_preview(original_pdf, label="Original uploaded resume")

    if st.button("🗑️ Remove Analysis", use_container_width=True, key="remove_analysis_v21"):
        for _key in [
            "analysis", "generated_resume_pdf", "generated_resume_field",
            "generated_resume_template", "generated_resume_role", "generated_resume_name",
            "generated_resume_variant"
        ]:
            st.session_state.pop(_key, None)
        st.rerun()

    # =====================================================
    # STEP 20 — FINAL UI / APPLICATION READINESS
    # =====================================================

    st.markdown("---")
    st.markdown(
        '<div class="section-title-card"><div class="section-icon">✨</div><div><div class="section-kicker">FINAL POLISH</div><div class="section-title">Step 20 — Application Readiness</div></div></div>',
        unsafe_allow_html=True,
    )
    ats=int(data.get("ats_score",0)); match=int(data.get("job_match",0)); quality=int(data.get("quality_score",0)); nlp=int(data.get("nlp_score",0))
    readiness=round((ats+match+quality+nlp)/4)
    if readiness>=85:
        readiness_text="Your resume is in a strong position. Do a final role-specific review before applying."
    elif readiness>=70:
        readiness_text="Good foundation. Address the highest-impact recommendations before your next application."
    else:
        readiness_text="Use the recommendations above to strengthen the resume before applying."
    badges=[f"ATS {ats}/100",f"Job Match {match}%",f"Quality {quality}/100",f"NLP {nlp}/100"]
    badge_html=''.join(f'<span class="final-badge">{b}</span>' for b in badges)
    st.markdown(
        f'<div class="final-readiness"><div class="final-readiness-title">🚀 Overall application readiness: {readiness}/100</div><div class="final-readiness-copy">{readiness_text}</div><div class="final-badge-row">{badge_html}</div></div>',
        unsafe_allow_html=True,
    )
