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


def render_sidebar() -> int | None:
    with st.sidebar:
        st.markdown(f"## 🎯 {APP_NAME}")
        st.markdown("---")
        st.markdown("### Chapters")

        selected = st.session_state.get("selected_chapter", None)

        for num, info in CHAPTERS.items():
            label = f"Ch. {num} — {info['title']}"
            if info["active"]:
                if st.button(label, key=f"ch_{num}", use_container_width=True):
                    st.session_state["selected_chapter"] = num
                    # Reset chapter state when switching chapters
                    for key in list(st.session_state.keys()):
                        if key.startswith("ch7_"):
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
    st.title(f"🎯 {APP_NAME}")
    st.markdown(
        """
        Welcome to the **Integrated Professional Selling Lab** — an interactive simulation
        platform designed to build real B2B sales skills through deliberate practice.

        ### How it works
        Each chapter lab places you in a live sales scenario with a simulated buyer powered
        by AI. You'll practice core selling techniques, receive evidence-based feedback,
        and build the habits that separate top performers.

        ### Get started
        Select **Chapter 7 — Discovery & SPIN Questioning** from the sidebar to begin
        your first simulation.
        """
    )

    cols = st.columns(3)
    with cols[0]:
        st.info("**Active now**\n\nCh. 7 — Discovery & SPIN Questioning")
    with cols[1]:
        st.warning("**Coming soon**\n\n10 additional chapter simulations")
    with cols[2]:
        st.success("**Your goal**\n\nScore 75+ to earn a Strong Foundation rating")


def main():
    selected = render_sidebar()

    if selected is None:
        render_home()
    elif selected == 7:
        from modules.chapter7 import run_chapter7
        run_chapter7()
    else:
        info = CHAPTERS[selected]
        st.title(f"Chapter {selected} — {info['title']}")
        st.info("This chapter simulation is coming soon. Check back later!")


if __name__ == "__main__":
    main()
