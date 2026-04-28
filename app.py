import os
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
    .coming-soon {{
        color: #888;
        font-style: italic;
        font-size: 0.88rem;
        padding: 0.25rem 0;
        display: block;
    }}
    .stButton > button {{
        border-radius: 8px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


_EXTERNAL_CHAPTERS: dict = {}


def _go_home():
    st.session_state["selected_chapter"] = None


def _go_chapter(num: int):
    st.session_state["selected_chapter"] = num
    for key in list(st.session_state.keys()):
        if key[:2] == "ch" and key[2:3].isdigit():
            del st.session_state[key]


def render_sidebar() -> int | None:
    with st.sidebar:
        # Home button — top of sidebar
        if st.button("🏠 Home", key="sidebar_home", use_container_width=True):
            _go_home()
            st.rerun()

        st.markdown("---")
        st.markdown("### Chapters")

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
                    _go_chapter(num)
                    st.rerun()
            else:
                st.markdown(
                    f'<span class="coming-soon">Ch. {num} — {info["title"]} (Coming soon)</span>',
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.caption(
            "Developed by Carlos Valdez, Ph.D.\n"
            "For educational purposes only."
        )

    return st.session_state.get("selected_chapter", None)


# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------

_MODULES = [
    (1,  "The Selling Profession",    "Practice a job interview with an AI recruiter"),
    (2,  "The B2B Sales Process",     "Navigate a buying center — 10 decisions, $180K deal"),
    (3,  "Human Competencies",        "Active listening roleplay with a B2B buyer"),
    (4,  "AI Competencies",           "Write and fix AI prompts across 4 sales scenarios"),
    (5,  "Know Your Market",          "Calculate TAM/SAM/SOM for an assigned B2B company"),
    (6,  "Prospecting & Outreach",    "Write and get evaluated on 4 outreach messages"),
    (7,  "Discovery & SPIN",          "Live SPIN questioning roleplay with a B2B buyer"),
    (8,  "Proposal & Value Framing",  "Build a full value proposition for a real company"),
    (9,  "Objections & Closing",      "Handle objections and close a live B2B deal"),
    (10, "Sales Technology Stack",    "Build and present a real sales tech stack"),
    (11, "Personal Branding Lab",     "Resume + LinkedIn + Elevator Pitch with AI recruiter"),
]


def render_home():
    # ── Section 1 — Hero ────────────────────────────────────────────────────
    _, img_col, _ = st.columns([1, 1, 1])
    with img_col:
        cover = "assets/images/Cover.png"
        if os.path.exists(cover):
            st.image(cover, width=320)

    st.title("Integrated Professional Selling Lab")
    st.markdown(
        "*B2B Sales in the Age of AI* — AI-powered simulations based on the textbook by "
        "**Dr. Carlos Valdez** | University of Central Florida"
    )

    st.markdown("---")

    # ── Section 2 — What is IPS Lab ─────────────────────────────────────────
    st.markdown(
        "IPS Lab is an AI-powered simulation platform built around "
        "*Integrated Professional Selling: B2B Sales in the Age of AI*. "
        "Each module gives you a hands-on activity — roleplay with an AI recruiter, "
        "navigate a live deal, practice discovery conversations, and more. "
        "You get instant feedback and a score you can report to your instructor. "
        "Select any chapter from the left sidebar to begin."
    )

    st.markdown("---")

    # ── Section 3 — How it works ─────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            """
            <div style="text-align:center; padding:1rem;">
              <div style="font-size:2rem;">🤖</div>
              <div style="font-weight:700; font-size:1rem; margin:0.4rem 0;">Practice</div>
              <div style="color:#aaa; font-size:0.88rem;">Complete an AI-powered simulation</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div style="text-align:center; padding:1rem;">
              <div style="font-size:2rem;">📊</div>
              <div style="font-weight:700; font-size:1rem; margin:0.4rem 0;">Get scored</div>
              <div style="color:#aaa; font-size:0.88rem;">Receive instant feedback and a score</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """
            <div style="text-align:center; padding:1rem;">
              <div style="font-size:2rem;">📋</div>
              <div style="font-weight:700; font-size:1rem; margin:0.4rem 0;">Report it</div>
              <div style="color:#aaa; font-size:0.88rem;">Screenshot your score and submit to Webcourses</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Section 4 — How to submit ────────────────────────────────────────────
    with st.expander("📋 How to submit your score to Webcourses"):
        st.markdown(
            "1. Complete the activity and reach the score screen\n"
            "2. Take a screenshot of your full score\n"
            "3. Go to Webcourses → find the assignment for that chapter\n"
            "4. Upload your screenshot as your submission\n"
            "5. You may repeat each activity as many times as you want — "
            "only submit your best score"
        )

    st.markdown("---")

    # ── Section 5 — The 11 Modules ───────────────────────────────────────────
    st.markdown("## The 11 Modules")

    for row_start in range(0, len(_MODULES), 2):
        cols = st.columns(2, gap="medium")
        for col_idx in range(2):
            idx = row_start + col_idx
            if idx >= len(_MODULES):
                break
            num, title, desc = _MODULES[idx]
            with cols[col_idx]:
                with st.container():
                    img_path = f"assets/images/Chapter {num}.png"
                    if os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)
                    st.markdown(
                        f"""
                        <div style="background:#1A2332; border:1px solid #2E5FA3;
                             border-radius:0 0 10px 10px; padding:0.9rem 1rem;
                             margin-bottom:1rem;">
                          <div style="font-size:0.75rem; color:#4A90D9; font-weight:700;
                               text-transform:uppercase; letter-spacing:0.05em;
                               margin-bottom:0.2rem;">Chapter {num}</div>
                          <div style="color:#FAFAFA; font-weight:700; font-size:0.98rem;
                               margin-bottom:0.3rem;">{title}</div>
                          <div style="color:#bbb; font-size:0.85rem;">{desc}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------

def main():
    selected = render_sidebar()

    if selected is None:
        render_home()
    elif selected == 1:
        from modules.chapter1 import run_chapter1
        run_chapter1()
    elif selected == 2:
        from modules.chapter2 import run_chapter2
        run_chapter2()
    elif selected == 3:
        from modules.chapter3 import run_chapter3
        run_chapter3()
    elif selected == 4:
        from modules.chapter4 import run_chapter4
        run_chapter4()
    elif selected == 5:
        from modules.chapter5 import run_chapter5
        run_chapter5()
    elif selected == 6:
        from modules.chapter6 import run_chapter6
        run_chapter6()
    elif selected == 7:
        from modules.chapter7 import run_chapter7
        run_chapter7()
    elif selected == 8:
        from modules.chapter8 import run_chapter8
        run_chapter8()
    elif selected == 9:
        from modules.chapter9 import run_chapter9
        run_chapter9()
    elif selected == 10:
        from modules.chapter10 import run_chapter10
        run_chapter10()
    elif selected == 11:
        from modules.chapter11 import run_chapter11
        run_chapter11()
    else:
        info = CHAPTERS[selected]
        st.title(f"Chapter {selected} — {info['title']}")
        st.info("This chapter simulation is coming soon. Check back later!")


if __name__ == "__main__":
    main()
