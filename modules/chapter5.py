import json
import re
import random
import streamlit as st
from datetime import date
from openai import OpenAI
from config import get_openai_api_key

MODEL_COACH = "gpt-4.1-mini"
TEMP_COACH = 0.3

# ---------------------------------------------------------------------------
# Company data
# ---------------------------------------------------------------------------

COMPANIES = {
    "dataflow": {
        "name": "DataFlow Solutions",
        "product": "Supply chain analytics software",
        "industry": "Logistics & freight brokerage",
        "target_customer": "Mid-size freight brokers",
        "geo_hint": "US Southeast",
        "price_min": 45_000,
        "price_max": 95_000,
        "context": (
            "DataFlow helps freight brokers get real-time carrier visibility. "
            "Your job: estimate how big this market is."
        ),
    },
    "talentiq": {
        "name": "TalentIQ",
        "product": "HR analytics and workforce planning software",
        "industry": "HR technology",
        "target_customer": "Mid-size companies scaling rapidly (200–500 employees)",
        "geo_hint": "US major metros",
        "price_min": 25_000,
        "price_max": 65_000,
        "context": (
            "TalentIQ helps fast-growing companies make data-driven HR decisions. "
            "Your job: estimate how big this market is."
        ),
    },
    "qualitypro": {
        "name": "QualityPro",
        "product": "Quality management and compliance software",
        "industry": "Medical device manufacturing",
        "target_customer": "FDA-regulated manufacturers (100–500 employees)",
        "geo_hint": "US nationwide",
        "price_min": 60_000,
        "price_max": 120_000,
        "context": (
            "QualityPro helps medical device manufacturers prepare for FDA audits. "
            "Your job: estimate how big this market is."
        ),
    },
}

# ---------------------------------------------------------------------------
# Scoring dimensions (used in coach prompt and scorecard)
# ---------------------------------------------------------------------------

DIMENSIONS = [
    {
        "name": "Assumption Quality",
        "max_points": 30,
        "description": "Are your assumptions reasonable for this specific industry?",
        "rubric": (
            "30 pts: Numbers are well-grounded with clear industry logic; geography and segment make sense.\n"
            "22–29 pts: Reasonable with some justification; minor gaps.\n"
            "12–21 pts: Plausible but thin — assumptions not connected to the industry.\n"
            "0–11 pts: Arbitrary numbers, no justification, or nonsensical geography/segment choice."
        ),
    },
    {
        "name": "TAM→SAM→SOM Logic",
        "max_points": 30,
        "description": "Does each level narrow correctly? Is SOM realistic for Year 1?",
        "rubric": (
            "30 pts: Each step narrows correctly; SOM ≤ 10% of SAM (realistic for early stage).\n"
            "22–29 pts: Narrowing logic mostly sound; minor gap in one step.\n"
            "12–21 pts: Narrowing present but SOM > 10% of SAM, or one step doesn't narrow.\n"
            "0–11 pts: SOM ≥ SAM, or SAM ≥ TAM, or fundamental misunderstanding of the framework."
        ),
    },
    {
        "name": "Price × Volume Consistency",
        "max_points": 25,
        "description": "Do your numbers make mathematical sense?",
        "rubric": (
            "25 pts: Price within assigned range; volume numbers internally consistent; math checks out.\n"
            "18–24 pts: Price close to range or minor inconsistency.\n"
            "10–17 pts: Price outside range OR volume numbers don't add up.\n"
            "0–9 pts: Price significantly outside range AND/OR clear math errors."
        ),
    },
    {
        "name": "Strategic Thinking",
        "max_points": 15,
        "description": "Do your notes show you understand WHY market sizing matters for B2B sales?",
        "rubric": (
            "15 pts: Notes explicitly connect sizing to sales strategy (reps needed, prospecting volume, etc.).\n"
            "11–14 pts: Awareness of what the numbers mean, even if not fully developed.\n"
            "6–10 pts: Notes focus on numbers but don't connect to sales implications.\n"
            "0–5 pts: Minimal notes or bare restatement of inputs without reasoning."
        ),
    },
]

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def _init_state() -> None:
    if "ch5_company_key" not in st.session_state:
        last = st.session_state.get("ch5_last_company")
        opts = (
            [k for k in COMPANIES if k != last]
            if (last and len(COMPANIES) > 1)
            else list(COMPANIES.keys())
        )
        st.session_state["ch5_company_key"] = random.choice(opts)

    defaults = {
        "ch5_phase": "setup",
        "ch5_student_name": "",
        "ch5_results": {},
        "ch5_scorecard": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset_state() -> None:
    last = st.session_state.get("ch5_last_company")
    keys = [k for k in st.session_state if k.startswith("ch5_")]
    for k in keys:
        del st.session_state[k]
    if last is not None:
        st.session_state["ch5_last_company"] = last
    _init_state()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(n: int | float) -> str:
    return f"${int(n):,}"


def _word_count(text: str) -> int:
    return len(text.strip().split()) if text.strip() else 0


# ---------------------------------------------------------------------------
# Screen 1 — Setup
# ---------------------------------------------------------------------------

def screen_setup() -> None:
    company_key = st.session_state["ch5_company_key"]
    c = COMPANIES[company_key]

    st.title("Chapter 5 — Know Your Market")
    st.markdown("### TAM / SAM / SOM Calculator")
    st.markdown("---")

    # Scoring rubric expander — ABOVE name input
    with st.expander("📊 How you'll be scored (100 pts)", expanded=False):
        st.markdown(
            "| Dimension | Points |\n"
            "|-----------|--------|\n"
            "| Assumption Quality | 30 |\n"
            "| TAM→SAM→SOM Logic | 30 |\n"
            "| Price × Volume Consistency | 25 |\n"
            "| Strategic Thinking | 15 |"
        )
        st.markdown("")
        for dim in DIMENSIONS:
            st.markdown(f"**{dim['name']}** — {dim['description']}")
            st.caption(dim["rubric"])

    # Company card
    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:10px; padding:1.2rem 1.4rem; margin-bottom:0.75rem;">
          <div style="font-size:0.75rem; color:#4A90D9; font-weight:700;
               text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.6rem;">
            🏢 Your Assigned Company
          </div>
          <div style="font-size:1.25rem; font-weight:700; color:#FAFAFA; margin-bottom:0.6rem;">
            {c['name']}
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem 1.4rem;
               margin-bottom:0.75rem;">
            <div>
              <div style="color:#888; font-size:0.8rem;">Product</div>
              <div style="color:#FAFAFA; font-size:0.9rem;">{c['product']}</div>
            </div>
            <div>
              <div style="color:#888; font-size:0.8rem;">Industry</div>
              <div style="color:#FAFAFA; font-size:0.9rem;">{c['industry']}</div>
            </div>
            <div>
              <div style="color:#888; font-size:0.8rem;">Target customer</div>
              <div style="color:#FAFAFA; font-size:0.9rem;">{c['target_customer']}</div>
            </div>
            <div>
              <div style="color:#888; font-size:0.8rem;">Price range</div>
              <div style="color:#FAFAFA; font-size:0.9rem;">${c['price_min']:,}–${c['price_max']:,}/year</div>
            </div>
          </div>
          <div style="border-top:1px solid #2E5FA3; padding-top:0.65rem;
               color:#ddd; font-size:0.9rem; font-style:italic;">
            {c['context']}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Instruction box
    st.markdown(
        """
        <div style="background:#0E1117; border:1px solid #4A90D9;
             border-radius:8px; padding:1.1rem 1.3rem; margin-bottom:0.75rem;">
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.6rem;">📊 Your Task</div>
          <div style="color:#FAFAFA; font-size:0.92rem; line-height:1.65;">
            Estimate the <strong>TAM, SAM, and SOM</strong> for your assigned company.<br><br>
            <strong>TAM — Total Addressable Market</strong><br>
            Every company that could ever buy this product in your geography.<br><br>
            <strong>SAM — Serviceable Addressable Market</strong><br>
            The portion of TAM you can realistically reach with your sales model.<br><br>
            <strong>SOM — Serviceable Obtainable Market</strong><br>
            What you can realistically capture in Year 1 given your resources.<br><br>
            <strong>Use the top-down method:</strong><br>
            Start with total market size → narrow by segment → narrow by capacity.<br><br>
            Show your assumptions clearly — the AI evaluates your
            <strong>REASONING</strong>, not just your numbers.<br><br>
            🤖 You may use AI to research market size estimates. The evaluation
            focuses on whether your logic is sound, not whether your numbers are perfect.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    student_name = st.text_input(
        "Your full name",
        value=st.session_state.get("ch5_student_name", ""),
        placeholder="e.g. Ana García",
        key="ch5_name_input",
    )

    ready = bool(student_name.strip())
    if not ready:
        st.caption("Enter your name above to enable the Start button.")

    if st.button(
        "Start Calculator →",
        disabled=not ready,
        type="primary",
        use_container_width=True,
    ):
        st.session_state["ch5_student_name"] = student_name.strip()
        st.session_state["ch5_last_company"] = company_key
        st.session_state["ch5_phase"] = "calculator"
        st.rerun()


# ---------------------------------------------------------------------------
# Entry point (calculator and scorecard added in Part 2)
# ---------------------------------------------------------------------------

def run_chapter5() -> None:
    _init_state()
    phase = st.session_state["ch5_phase"]
    if phase == "setup":
        screen_setup()
    else:
        st.info("Calculator coming soon — Part 2 not yet loaded.")
