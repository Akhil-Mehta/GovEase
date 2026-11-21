import streamlit as st
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Must be the first Streamlit command on the page.
st.set_page_config(
    page_title="GovEase",
    page_icon=str(BASE_DIR / "data" / "logo_mark.png"),
    layout="centered",
    initial_sidebar_state="collapsed",
)

from utils import util_StateDist as uSD  # noqa: E402
from utils import util_Google as uGO  # noqa: E402
from utils import util_TinyFish as uTF  # noqa: E402
from utils import util_UrlManager as uUM  # noqa: E402
from utils import util_EnglishHindi as uEH  # noqa: E402
from utils import util_Speak as uSP  # noqa: E402
from utils import util_UI as ui  # noqa: E402

RESULT_LANG = {"English": "English", "हिंदी": "Hindi"}
TEXT = uEH.EngToHin()

@st.cache_data(show_spinner=False)
def load_geo(language):
    return uSD.geo_data(language)

def clear_result():
    st.session_state.pop("result", None)

def pick_example():
    pick = st.session_state.get("example_pick")
    if pick:
        st.session_state["need"] = pick
        st.session_state["example_pick"] = None

def run_search(need, state, dist, language, mode, t):
    """Find the website, read it, translate if needed. Returns a result dict or None."""
    with st.status(t["finding"], expanded=True) as status:
        try:
            url = uUM.get_url(need, state.lower(), dist.lower())
            if not url:
                url = uGO.find_website(need, state, dist)
                if "https:" not in url:
                    raise ValueError(t["error_url"])
                uUM.save_url(need, state, dist, url)
            url = url.strip()
        except Exception as e:
            print(e)
            status.update(label=t["error_url"], state="error")
            st.error(t["error_url"])
            st.caption(t["error_url_help"])
            return None

        st.write(t["found"].format(domain=ui.domain_of(url)))
        status.update(label=t["reading"].format(url=ui.domain_of(url)))

        try:
            temp = uTF.ask_tinyfish(url, need, state, dist, RESULT_LANG[language], mode)
            response = temp.result["result"]

            if language == "हिंदी":
                status.update(label=t["translating"])
                response = uGO.ensure_hindi(response)
        except Exception as e:
            print(e)
            status.update(label=t["error"], state="error")
            st.error(t["error"])
            st.caption(t["error_help"])
            return None

        status.update(label=t["done"], state="complete", expanded=False)

    return {"url": url, "text": response, "lang": RESULT_LANG[language], "need": need}


def show_result(result, t):
    parsed = ui.parse_result(result["text"])
    title = parsed["title"] or result["need"].title()

    with st.container(key="sheet"):
        ui.result_header(title, result["url"], t)
        ui.render_sections(parsed)

        with st.container(key="actions"):
            left, right = st.columns(2)
            with left:
                st.link_button(t["open_site"], result["url"])
            with right:
                if st.button(t["listen"], key="listen", help=t["listen_help"]):
                    if not result.get("audio"):
                        with st.spinner(t["audio"]):
                            try:
                                result["audio"] = uSP.speak(
                                    ui.plain_text_for_speech(result["text"]), result["lang"]
                                )
                            except Exception as e:
                                print(e)
                                st.error(t["error"])

        if result.get("audio"):
            st.audio(result["audio"], format="audio/mpeg")

        ui.notice(t)


# ---------------- page ----------------

ui.load_css()

top_left, top_right = st.columns([3, 2], vertical_alignment="center")

with top_right:
    choice = st.segmented_control(
        "Language / भाषा",
        list(RESULT_LANG.keys()),
        default="English",
        key="language",
        label_visibility="collapsed",
        on_change=clear_result,
    )
if choice:
    st.session_state["lang_last"] = choice
language = st.session_state.get("lang_last", "English")
lang_key = RESULT_LANG[language]
t = TEXT[language]

with top_left:
    ui.brand(t)

ui.hero(t)

statedistDict = load_geo(language)

with st.container(key="panel"):
    need_raw = st.text_input(t["need"], key="need", placeholder=t["need_placeholder"])

    st.pills(
        t["need"],
        t["examples"],
        selection_mode="single",
        key="example_pick",
        on_change=pick_example,
        label_visibility="collapsed",
    )

    col_state, col_dist = st.columns(2)
    with col_state:
        state = st.selectbox(
            t["state"],
            options=list(statedistDict.keys()),
            index=None,
            placeholder=t["state_placeholder"],
            key=f"state_{lang_key}",
        )
    with col_dist:
        dist = st.selectbox(
            t["district"],
            options=list(statedistDict[state]) if state else [],
            index=None,
            placeholder=t["district_placeholder"] if state else t["district_first"],
            disabled=not state,
            key=f"dist_{lang_key}_{state}",
        )

    with st.expander(t["options"]):
        response_speed = st.radio(
            t["mode"],
            ["Stealth", "Lite"],
            format_func=lambda v: t["mode_" + v.lower()],
            key="mode",
        )

    need = (need_raw or "").strip().lower()
    ready = bool(need and state and dist)
    clicked = st.button(t["search"], type="primary", disabled=not ready, key="search")
    if not ready:
        st.caption(t["info"])

if clicked:
    st.session_state.pop("result", None)
    outcome = run_search(need, state, dist, language, response_speed, t)
    if outcome:
        st.session_state["result"] = outcome

result = st.session_state.get("result")
if result:
    show_result(result, t)
elif not clicked:
    ui.how_it_works(t)

ui.footer(t)
