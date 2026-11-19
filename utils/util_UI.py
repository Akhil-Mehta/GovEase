"""UI helpers for GovEase: styling, brand header and result sheet."""
import base64
import html
import re
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


# ---------- small helpers ----------

def esc(text):
    return html.escape(str(text), quote=True)


def domain_of(url):
    host = urlparse(url.strip()).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def plain_text_for_speech(markdown_text):
    """Strip Markdown so the voice does not read symbols or long URLs aloud."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", markdown_text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[*\-+]\s+", "", text, flags=re.M)
    text = text.replace("**", "").replace("__", "").replace("*", "").replace("`", "")
    return re.sub(r"\n{2,}", "\n", text).strip()


# ---------- parsing the model's Markdown ----------

# Checked in this order. Hindi keys have the nukta (U+093C) removed.
_KIND_KEYS = (
    ("docs", ("document", "दस्तावेज")),
    ("steps", ("procedure", "how to apply", "steps", "प्रक्रिया")),
    ("elig", ("eligib", "criteria", "पात्रता")),
    ("dept", ("department", "authority", "विभाग")),
)
_EMPTY_HINTS = ("not available", "उपलब्ध नहीं")


def _kind_of(heading):
    h = heading.lower().replace("\u093c", "")
    for kind, keys in _KIND_KEYS:
        if any(k in h for k in keys):
            return kind
    return "other"


def parse_result(markdown_text):
    """Split the answer into a title and sections. Never raises.

    Returns {"title": str | None, "sections": [{"kind", "heading", "body"}], "raw": str}
    Falls back to an empty sections list when the answer has no headings,
    so the caller can show the raw Markdown instead.
    """
    raw = (markdown_text or "").strip()
    cleaned = re.sub(r"^```(?:markdown|md)?\s*\n", "", raw)
    cleaned = re.sub(r"\n```\s*$", "", cleaned)

    title = None
    sections = []
    current = None
    for line in cleaned.splitlines():
        m = re.match(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            level, text = len(m.group(1)), m.group(2).strip()
            if level == 1 and title is None and current is None:
                title = text
                continue
            current = {"heading": text, "lines": []}
            sections.append(current)
        elif current is not None:
            current["lines"].append(line)

    out = []
    for sec in sections:
        body = "\n".join(sec["lines"]).strip()
        if not body:
            continue
        out.append({"kind": _kind_of(sec["heading"]), "heading": sec["heading"], "body": body})
    return {"title": title, "sections": out, "raw": raw}


# ---------- styling ----------

@st.cache_resource(show_spinner=False)
def _logo_b64():
    return base64.b64encode((DATA_DIR / "logo_mark.png").read_bytes()).decode("ascii")


def load_css():
    css = (DATA_DIR / "style.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ---------- page pieces ----------

def brand(t):
    st.markdown(
        '<div class="gv-brand">'
        f'<img src="data:image/png;base64,{_logo_b64()}" alt="">'
        '<div>'
        '<div class="gv-name">Gov<span>Ease</span></div>'
        f'<div class="gv-tag">{esc(t["tagline"])}</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )


def hero(t):
    st.markdown(
        f'<h1 class="gv-hero">{esc(t["hero_title"])}</h1>'
        f'<p class="gv-sub">{esc(t["hero_sub"])}</p>',
        unsafe_allow_html=True,
    )


def how_it_works(t):
    items = "".join(
        f'<li><strong>{esc(title)}</strong><span>{esc(text)}</span></li>'
        for title, text in t["how_steps"]
    )
    st.markdown(
        f'<div class="gv-sec-title gv-how-title">{esc(t["how_title"])}</div>'
        f'<ol class="gv-how">{items}</ol>',
        unsafe_allow_html=True,
    )


def footer(t):
    st.markdown(f'<div class="gv-footer">{esc(t["footer"])}</div>', unsafe_allow_html=True)


def notice(t):
    st.markdown(f'<div class="gv-notice">{esc(t["notice"])}</div>', unsafe_allow_html=True)


def result_header(title, url, t):
    st.markdown(
        f'<div class="gv-result-title">{esc(title)}</div>'
        f'<div class="gv-source"><span class="gv-dot"></span>'
        f'<span>{esc(t["source"])}</span><b>{esc(domain_of(url))}</b></div>',
        unsafe_allow_html=True,
    )


def _section(kind, heading, body, idx):
    # Keys are alphanumeric on purpose: Streamlit turns them into the CSS class st-key-<key>
    with st.container(key=f"sec{kind}{idx}"):
        st.markdown(f'<div class="gv-sec-title">{esc(heading)}</div>', unsafe_allow_html=True)
        if len(body) < 140 and any(h in body.lower() for h in _EMPTY_HINTS):
            st.markdown(f'<p class="gv-empty">{esc(body)}</p>', unsafe_allow_html=True)
        else:
            # Model output is rendered as plain Markdown (no raw HTML) on purpose.
            st.markdown(body)


def render_sections(parsed):
    sections = parsed["sections"]
    if not sections:
        # The answer did not follow the expected headings: show it as-is.
        with st.container(key="secother0"):
            st.markdown(parsed["raw"])
        return

    by_kind = {}
    for i, sec in enumerate(sections):
        by_kind.setdefault(sec["kind"], []).append((i, sec))

    def show(kind):
        for i, sec in by_kind.get(kind, []):
            _section(kind, sec["heading"], sec["body"], i)

    show("dept")
    show("steps")

    if "elig" in by_kind and "docs" in by_kind:
        left, right = st.columns(2, gap="large")
        with left:
            show("elig")
        with right:
            show("docs")
    else:
        show("elig")
        show("docs")

    show("other")
