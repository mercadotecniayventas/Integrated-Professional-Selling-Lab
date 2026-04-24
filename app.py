import streamlit as st
from config import APP_NAME, CHAPTERS, COLOR_PRIMARY

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
    <style>
    .sidebar-title {{
        font-size: 1.1rem;
        font-weight: 700;
        color: {COLOR_PRIMARY};
        padding: 0.5rem 0;
    }}
    .chapter-badge {{
        display: inline-block;
        background: {COLOR_PRIMARY};
        color: white;
        border-radius: 12px;
        padding: 2px 8px;
        font-size: 0.75rem;
        margin-left: 4px;
    }}
    .coming-soon {{
        color: #888;
        font-style: italic;
    }}
    .stButton > button {{
        border-radius: 8px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


_EXTERNAL_CHAPTERS = {
    5:  {"label": "Ch. 5 — TAM/SAM/SOM Agent ↗",   "url": "https://tam-agent.streamlit.app"},
    11: {"label": "Ch. 11 — Personal Branding ↗",   "url": "https://personal-branding-chatbot.streamlit.app"},
}


def render_sidebar() -> int | None:
    with st.sidebar:
        st.markdown(f"## 🎯 {APP_NAME}")
        st.markdown("---")
        st.markdown("### Chapters")

        selected = st.session_state.get("selected_chapter", None)

        for num, info in CHAPTERS.items():
            if num in _EXTERNAL_CHAPTERS:
                st.link_button(
                    _EXTERNAL_CHAPTERS[num]["label"],
                    _EXTERNAL_CHAPTERS[num]["url"],
                    use_container_width=True,
                )
            elif info["active"]:
                label = f"Ch. {num} — {info['title']}"
                if st.button(label, key=f"ch_{num}", use_container_width=True):
                    st.session_state["selected_chapter"] = num
                    for key in list(st.session_state.keys()):
                        if key[:2] == "ch" and key[2:3].isdigit():
                            del st.session_state[key]
                    st.rerun()
            else:
                st.markdown(
                    f'<span class="coming-soon">Ch. {num} — {info["title"]} *(Coming soon)*</span>',
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.caption(f"v1.0.0 · B2B Sales Course")

    return st.session_state.get("selected_chapter", None)


def render_home():
    st.title("🎯 IPS Lab")
    st.markdown(
        "Welcome to **IPS Lab** — practice B2B sales skills through AI-powered simulations. "
        "Select a module below to begin."
    )
    st.markdown("---")
    st.markdown("### Active Modules")

    _MODULES = [
        {
            "num": 1,
            "title": "The Selling Profession",
            "desc": "Practice a job interview with an AI recruiter",
            "badge": "🎤 Voice + Text",
            "external": False,
        },
        {
            "num": 3,
            "title": "Human Competencies",
            "desc": "Active listening roleplay with a B2B buyer",
            "badge": "🎤 Voice",
            "external": False,
        },
        {
            "num": 5,
            "title": "Know Your Market",
            "desc": "Calculate TAM/SAM/SOM for a B2B company",
            "badge": "💬 Text · ↗ External",
            "external": True,
            "url": _EXTERNAL_CHAPTERS[5]["url"],
        },
        {
            "num": 6,
            "title": "Prospecting & Outreach",
            "desc": "Write and get evaluated on 4 outreach messages",
            "badge": "💬 Text",
            "external": False,
        },
        {
            "num": 7,
            "title": "Discovery & SPIN",
            "desc": "Run a discovery call with an AI buyer",
            "badge": "🎤 Voice",
            "external": False,
        },
        {
            "num": 9,
            "title": "Objections & Closing",
            "desc": "Handle 5 objections and close the deal",
            "badge": "🎤 Voice",
            "external": False,
        },
        {
            "num": 10,
            "title": "Sales Technology Stack",
            "desc": "Navigate a CRM pipeline — make the right calls",
            "badge": "🎮 Game",
            "external": False,
        },
        {
            "num": 11,
            "title": "Personal Branding",
            "desc": "Build your professional brand and LinkedIn",
            "badge": "💬 Text · ↗ External",
            "external": True,
            "url": _EXTERNAL_CHAPTERS[11]["url"],
        },
    ]

    # 2-column grid
    for row_start in range(0, len(_MODULES), 2):
        cols = st.columns(2, gap="medium")
        for col_idx, mod in enumerate(_MODULES[row_start: row_start + 2]):
            with cols[col_idx]:
                st.markdown(
                    f"""
                    <div style="background:#1A2332; border:1px solid #2E5FA3;
                         border-radius:10px; padding:1rem 1.1rem; margin-bottom:0.25rem;
                         min-height:100px;">
                      <div style="font-size:0.78rem; color:#4A90D9; font-weight:700;
                           text-transform:uppercase; letter-spacing:0.04em;
                           margin-bottom:0.25rem;">
                        Chapter {mod['num']}
                      </div>
                      <div style="color:#FAFAFA; font-weight:700; font-size:1rem;
                           margin-bottom:0.3rem;">
                        {mod['title']}
                      </div>
                      <div style="color:#ddd; font-size:0.88rem; margin-bottom:0.5rem;">
                        {mod['desc']}
                      </div>
                      <div style="display:inline-block; background:#0E1117;
                           border:1px solid #2E5FA3; border-radius:12px;
                           padding:2px 10px; font-size:0.78rem; color:#4A90D9;">
                        {mod['badge']}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if mod["external"]:
                    st.link_button(
                        "Open →",
                        mod["url"],
                        use_container_width=True,
                    )
                else:
                    if st.button(
                        "Start →",
                        key=f"home_ch{mod['num']}",
                        use_container_width=True,
                        type="primary",
                    ):
                        st.session_state["selected_chapter"] = mod["num"]
                        for key in list(st.session_state.keys()):
                            if key[:2] == "ch" and key[2:3].isdigit():
                                del st.session_state[key]
                        st.rerun()


def main():
    selected = render_sidebar()

    if selected is None:
        render_home()
    elif selected == 1:
        from modules.chapter1 import run_chapter1
        run_chapter1()
    elif selected == 6:
        from modules.chapter6 import run_chapter6
        run_chapter6()
    elif selected == 3:
        from modules.chapter3 import run_chapter3
        run_chapter3()
    elif selected == 7:
        from modules.chapter7 import run_chapter7
        run_chapter7()
    elif selected == 9:
        from modules.chapter9 import run_chapter9
        run_chapter9()
    elif selected == 10:
        from modules.chapter10 import run_chapter10
        run_chapter10()
    else:
        info = CHAPTERS[selected]
        st.title(f"Chapter {selected} — {info['title']}")
        st.info("This chapter simulation is coming soon. Check back later!")


if __name__ == "__main__":
    main()
