import html as _html
import json
import random
import re
import streamlit as st
from datetime import date
from openai import OpenAI
from config import get_openai_api_key

MODEL = "gpt-4.1-mini"
TEMP_COACH = 0.3

# ---------------------------------------------------------------------------
# Scenario data
# ---------------------------------------------------------------------------

SCENARIOS = {
    "logistics": {
        "key": "logistics",
        "buyer_name": "Marcus Reid",
        "buyer_title": "VP Operations",
        "company": "Nexbridge Logistics",
        "seller_product": "VisionTrack",
        "seller_product_type": "supply chain visibility software",
        "transcript": (
            "Marcus: We have visibility issues with carriers — data arrives 4–6 hours late.\n"
            "Rep: What impact does that have on your team?\n"
            "Marcus: My ops team manually chases updates 3 times a day. It's killing productivity.\n"
            "Rep: Has this affected your clients?\n"
            "Marcus: Last quarter two enterprise clients escalated. One threatened to pull $2.1M "
            "in annual business. My COO is watching.\n"
            "Rep: If you had real-time visibility, what would that mean for you?\n"
            "Marcus: We could offer proactive exception management. None of our competitors do that."
        ),
        "key_numbers": (
            "4–6 hour delays, $2.1M at risk, 3 manual check-ins per day, "
            "competitive differentiation opportunity"
        ),
    },
    "hr_saas": {
        "key": "hr_saas",
        "buyer_name": "Diana Pham",
        "buyer_title": "VP People",
        "company": "CoreBridge Solutions",
        "seller_product": "TalentIQ",
        "seller_product_type": "HR analytics software",
        "transcript": (
            "Diana: We're scaling fast — 3 new offices this year — and our HR data is a mess.\n"
            "Rep: What does that mean day to day?\n"
            "Diana: I'm making hiring decisions based on gut feeling, not data. We had 34% turnover "
            "last year in our sales team.\n"
            "Rep: What's the cost of that turnover?\n"
            "Diana: Each sales rep costs us about $45K to replace. With 12 reps turning over, "
            "that's $540K last year alone.\n"
            "Rep: What would better data change for you?\n"
            "Diana: I could finally show the CEO that HR decisions drive business outcomes, "
            "not just headcount."
        ),
        "key_numbers": (
            "34% turnover, $540K cost, 12 reps, 3 new offices, CEO visibility"
        ),
    },
    "medical": {
        "key": "medical",
        "buyer_name": "Robert Salinas",
        "buyer_title": "VP Operations",
        "company": "MedVantex Medical Devices",
        "seller_product": "QualityPro",
        "seller_product_type": "compliance software",
        "transcript": (
            "Robert: We have an FDA audit in Q3 and our documentation process is manual.\n"
            "Rep: How long does audit prep typically take?\n"
            "Robert: Last time it took 6 weeks of full-time work from 3 people. It nearly "
            "derailed our product launch.\n"
            "Rep: What's the risk if documentation isn't audit-ready?\n"
            "Robert: A warning letter could freeze our operations. We have $8M in revenue "
            "tied to products under review.\n"
            "Rep: What would automated documentation change for your team?\n"
            "Robert: We could redirect those 3 people to product work. And I could sleep at night."
        ),
        "key_numbers": (
            "6 weeks prep, 3 people, $8M at risk, Q3 deadline"
        ),
    },
}

SCENARIO_KEYS = list(SCENARIOS.keys())

# ---------------------------------------------------------------------------
# Coach prompt
# ---------------------------------------------------------------------------

def get_coach_prompt(sections: dict, student_name: str, scenario_key: str) -> str:
    sc = SCENARIOS[scenario_key]
    full_proposal = (
        f"EXECUTIVE SUMMARY:\n{sections.get('exec_summary', '')}\n\n"
        f"PROPOSED SOLUTION:\n{sections.get('solution', '')}\n\n"
        f"VALUE STATEMENT:\n{sections.get('value', '')}\n\n"
        f"RECOMMENDED NEXT STEP:\n{sections.get('next_step', '')}"
    )
    return f"""You are a B2B sales coach evaluating a student's proposal.

IMPORTANT: Do NOT penalize spelling, grammar, or syntax errors. This is a B2B sales course, not an English writing course. Many students are non-native English speakers. Evaluate only the strategic thinking — whether the student used buyer language, buyer numbers, and buyer priorities.

BUYER LANGUAGE TEST: Check if the proposal mirrors the buyer's own words and priorities from the discovery transcript. Generic phrases like "our solution offers great ROI" or "industry-leading platform" that could apply to any buyer should be penalized under Buyer Language and Specificity.

STUDENT: {student_name}
BUYER: {sc['buyer_name']}, {sc['buyer_title']} at {sc['company']}
PRODUCT: {sc['seller_product']} ({sc['seller_product_type']})

DISCOVERY TRANSCRIPT (what the buyer actually said):
{sc['transcript']}

KEY NUMBERS FROM DISCOVERY: {sc['key_numbers']}

STUDENT PROPOSAL:
\"\"\"
{full_proposal}
\"\"\"

Evaluate on exactly 5 dimensions. Return ONLY valid JSON — start with {{ end with }}. No markdown, no explanation.

{{
  "dimensions": [
    {{
      "name": "Buyer Language",
      "score": <0|8|15|25>,
      "max_points": 25,
      "evidence": "<exact quote from proposal showing buyer language use, or 'Not present'>",
      "coaching_note": "<specific feedback>"
    }},
    {{
      "name": "Problem-Solution Fit",
      "score": <0|8|15|25>,
      "max_points": 25,
      "evidence": "<exact quote or 'Not present'>",
      "coaching_note": "<specific feedback>"
    }},
    {{
      "name": "Value Quantification",
      "score": <0|6|12|20>,
      "max_points": 20,
      "evidence": "<exact quote showing numbers used, or 'Generic ROI language' or 'Not present'>",
      "coaching_note": "<specific feedback>"
    }},
    {{
      "name": "Specificity",
      "score": <0|6|12|20>,
      "max_points": 20,
      "evidence": "<quote showing specificity or note that it's generic>",
      "coaching_note": "<specific feedback>"
    }},
    {{
      "name": "Next Step Clarity",
      "score": <0|4|7|10>,
      "max_points": 10,
      "evidence": "<exact quote of next step, or 'Not present'>",
      "coaching_note": "<specific feedback>"
    }}
  ],
  "total_score": <sum of all scores, 0-100>,
  "tier": "<Proposal Ready|Strong Draft|Needs Refinement|Rewrite Recommended>",
  "plain_english_summary": "<exactly 2 sentences summarizing overall performance>",
  "strongest_section": "<which of the 4 sections was strongest and why — one sentence>",
  "weakest_section_name": "<Executive Summary|Proposed Solution|Value Statement|Next Step>",
  "weakest_section_rewrite": "<full rewrite of the weakest section using the buyer's actual language and numbers from the transcript — should feel like it was written by a senior rep who took notes in the meeting>",
  "one_thing_to_change": "<single most impactful change the student should make>"
}}

SCORING RUBRIC:

Buyer Language (25 pts):
  25 = Consistently uses buyer's own words and phrases from transcript
  15 = Some buyer language but mixes in generic sales language
   8 = Mostly generic — could apply to any buyer in this industry
   0 = Pure seller language — features, capabilities, solutions with no buyer echo

Problem-Solution Fit (25 pts):
  25 = Solution directly addresses each problem discovered in the call
  15 = Addresses main problem but misses secondary issues raised
   8 = Loosely connected — solution mentioned but not tied to specific problems
   0 = No connection between discovered problems and proposed solution

Value Quantification (20 pts):
  20 = Uses buyer's actual numbers (delays, costs, revenue at risk, headcount)
  12 = Mentions impact but without specifics from the transcript
   6 = Vague value ("saves time", "reduces costs") — no numbers
   0 = No value statement or pure generic ROI language

Specificity (20 pts):
  20 = This proposal could only have been written for THIS buyer after THIS call
  12 = Mostly specific with one or two generic elements
   6 = Could have been sent to a competitor in the same industry
   0 = Completely generic template that fits any buyer

Next Step Clarity (10 pts):
  10 = Concrete next step with action, timing, or both
   7 = Next step present but vague ("let's connect")
   4 = Implied but not stated
   0 = No next step

Tier thresholds: 90-100 = "Proposal Ready", 75-89 = "Strong Draft", 60-74 = "Needs Refinement", below 60 = "Rewrite Recommended"
CRITICAL: total_score must equal sum of all dimension scores."""


# ---------------------------------------------------------------------------
# API function
# ---------------------------------------------------------------------------

def call_coach_api(sections: dict, student_name: str, scenario_key: str) -> dict:
    _fallback = {
        "dimensions": [],
        "total_score": 0,
        "tier": "Error",
        "plain_english_summary": "Could not generate evaluation. Please try again.",
        "strongest_section": "",
        "weakest_section_name": "",
        "weakest_section_rewrite": "",
        "one_thing_to_change": "Please resubmit your proposal.",
        "_error": True,
    }
    try:
        client = OpenAI(api_key=get_openai_api_key())
        prompt = get_coach_prompt(sections, student_name, scenario_key)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMP_COACH,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'```\s*$', '', raw)
        raw = raw.strip()
        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        return json.loads(raw)
    except json.JSONDecodeError:
        return _fallback
    except Exception:
        return _fallback


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def _init_state() -> None:
    # Scenario rotation — persists across resets, never consecutive repeats
    if "ch8_scenario" not in st.session_state:
        last = st.session_state.get("ch8_last_scenario", None)
        options = [k for k in SCENARIO_KEYS if k != last]
        chosen = random.choice(options)
        st.session_state["ch8_scenario"] = chosen
        st.session_state["ch8_last_scenario"] = chosen

    defaults = {
        "ch8_phase": "setup",
        "ch8_student_name": "",
        "ch8_sections": {
            "exec_summary": "",
            "solution": "",
            "value": "",
            "next_step": "",
        },
        "ch8_scorecard": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset_state() -> None:
    # Preserve rotation tracker
    last = st.session_state.get("ch8_last_scenario", None)
    keys = [k for k in st.session_state if k.startswith("ch8_")]
    for k in keys:
        del st.session_state[k]
    if last is not None:
        st.session_state["ch8_last_scenario"] = last
    _init_state()


# ---------------------------------------------------------------------------
# Screen 1 — Setup
# ---------------------------------------------------------------------------

def screen_setup() -> None:
    _init_state()
    sc = SCENARIOS[st.session_state["ch8_scenario"]]

    st.title("Chapter 8 — Proposal & Value Framing")

    # Buyer card
    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #2E5FA3; border-radius:10px;
             padding:1rem 1.2rem; margin-bottom:1rem; color:#FAFAFA;">
          <div style="font-size:0.78rem; font-weight:700; color:#4A90D9;
               text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.5rem;">
            Your Buyer
          </div>
          <div style="font-size:1.05rem; font-weight:700; margin-bottom:0.2rem;">
            {_html.escape(sc['buyer_name'])}
          </div>
          <div style="color:#ddd; font-size:0.9rem; margin-bottom:0.2rem;">
            {_html.escape(sc['buyer_title'])} · {_html.escape(sc['company'])}
          </div>
          <div style="color:#4A90D9; font-size:0.88rem; margin-top:0.4rem;">
            You sell: {_html.escape(sc['seller_product'])} ({_html.escape(sc['seller_product_type'])})
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Instruction box
    st.markdown(
        """
        <div style="background:#1A2332; border:1px solid #2E5FA3; border-radius:10px;
             padding:1.1rem 1.3rem; margin-bottom:1.2rem; color:#FAFAFA;
             font-size:0.93rem; line-height:1.75;">
          <div style="font-size:1rem; font-weight:700; color:#4A90D9; margin-bottom:0.6rem;">
            📋 Your Task
          </div>
          <div style="margin-bottom:0.5rem;">
            Read the discovery transcript carefully. Then write a one-page proposal with
            these 4 sections:
          </div>
          <div style="margin-left:0.5rem; margin-bottom:0.4rem;">
            <strong>1. Executive Summary</strong> (2–3 sentences)<br>
            <span style="color:#ddd; font-size:0.88rem;">What problem are you solving and for whom?</span>
          </div>
          <div style="margin-left:0.5rem; margin-bottom:0.4rem;">
            <strong>2. Proposed Solution</strong> (3–4 sentences)<br>
            <span style="color:#ddd; font-size:0.88rem;">What specifically will you provide?</span>
          </div>
          <div style="margin-left:0.5rem; margin-bottom:0.4rem;">
            <strong>3. Value Statement</strong> (2–3 sentences)<br>
            <span style="color:#ddd; font-size:0.88rem;">Why is this worth the investment?
            Use their numbers, not generic ROI claims.</span>
          </div>
          <div style="margin-left:0.5rem; margin-bottom:0.8rem;">
            <strong>4. Recommended Next Step</strong> (1–2 sentences)<br>
            <span style="color:#ddd; font-size:0.88rem;">What happens after they say yes?</span>
          </div>
          <div style="border-top:1px solid #2E5FA3; padding-top:0.7rem; color:#F39C12;
               font-size:0.88rem;">
            🤖 <strong>AI note:</strong> You may use AI to help write this proposal.
            Give AI the discovery transcript — a proposal written without transcript
            context will score poorly, AI or not.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Scoring expander ABOVE name input
    with st.expander("📊 How you'll be scored (100 pts)"):
        st.markdown(
            """
            <div style="color:#ddd; font-size:0.9rem; line-height:1.7;">
              <div style="font-weight:700; color:#4A90D9; margin-bottom:0.5rem;">100 pts total</div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Buyer Language</strong>
                <span style="color:#4A90D9;"> — 25 pts</span><br>
                Does your proposal use the buyer's own words and priorities?
              </div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Problem-Solution Fit</strong>
                <span style="color:#4A90D9;"> — 25 pts</span><br>
                Does your solution directly address the problems discovered?
              </div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Value Quantification</strong>
                <span style="color:#4A90D9;"> — 20 pts</span><br>
                Do you use the buyer's actual numbers?
              </div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Specificity</strong>
                <span style="color:#4A90D9;"> — 20 pts</span><br>
                Is this proposal specific to THIS buyer or could it be sent to anyone?
              </div>
              <div>
                <strong style="color:#FAFAFA;">Next Step Clarity</strong>
                <span style="color:#4A90D9;"> — 10 pts</span><br>
                Does it end with a concrete next step?
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("**Your full name (appears on your scorecard):**")
    student_name = st.text_input(
        "Your full name",
        value=st.session_state["ch8_student_name"],
        placeholder="e.g. Ana García",
        key="ch8_name_input",
        label_visibility="collapsed",
    )

    ready = bool(student_name.strip())
    if not ready:
        st.caption("Enter your name above to enable the Start button.")

    if st.button(
        "Begin Proposal →",
        disabled=not ready,
        type="primary",
        use_container_width=True,
    ):
        st.session_state["ch8_student_name"] = student_name.strip()
        st.session_state["ch8_phase"] = "write"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 2 — Write
# ---------------------------------------------------------------------------

_SECTIONS = [
    {
        "key": "exec_summary",
        "label": "1. Executive Summary",
        "sublabel": "What problem are you solving and for whom?",
        "word_limit": 50,
        "min_words": 10,
        "height": 120,
    },
    {
        "key": "solution",
        "label": "2. Proposed Solution",
        "sublabel": "What specifically will you provide?",
        "word_limit": 75,
        "min_words": 10,
        "height": 140,
    },
    {
        "key": "value",
        "label": "3. Value Statement",
        "sublabel": "Why is this worth the investment? Use their numbers.",
        "word_limit": 50,
        "min_words": 10,
        "height": 120,
    },
    {
        "key": "next_step",
        "label": "4. Recommended Next Step",
        "sublabel": "What happens after they say yes?",
        "word_limit": 30,
        "min_words": 10,
        "height": 90,
    },
]


def _wc(text: str) -> int:
    return len(text.split()) if text.strip() else 0


def screen_write() -> None:
    _init_state()
    sc = SCENARIOS[st.session_state["ch8_scenario"]]

    st.markdown(f"### Proposal for {sc['buyer_name']}, {sc['buyer_title']} — {sc['company']}")

    # Transcript expander
    with st.expander("📋 Discovery Transcript (reference)"):
        st.markdown(
            f"<div style='font-size:0.9rem; color:#ddd; white-space:pre-wrap; line-height:1.7;'>"
            f"{_html.escape(sc['transcript'])}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown(
        "<div style='color:#aaa; font-size:0.88rem; margin-bottom:0.8rem;'>"
        "Write each section below. Use the buyer's actual words and numbers from the transcript.</div>",
        unsafe_allow_html=True,
    )

    sections = dict(st.session_state["ch8_sections"])
    all_ready = True

    for sec in _SECTIONS:
        k = sec["key"]
        st.markdown(
            f"<div style='font-weight:700; color:#FAFAFA; margin-bottom:2px;'>{sec['label']}</div>"
            f"<div style='color:#aaa; font-size:0.85rem; margin-bottom:4px;'>{sec['sublabel']}</div>",
            unsafe_allow_html=True,
        )
        val = st.text_area(
            sec["label"],
            value=sections.get(k, ""),
            height=sec["height"],
            key=f"ch8_{k}",
            label_visibility="collapsed",
            placeholder="Write here…",
        )
        sections[k] = val
        wc = _wc(val)
        limit = sec["word_limit"]
        wc_color = "#E74C3C" if wc > limit else ("#27AE60" if wc >= sec["min_words"] else "#888")
        st.markdown(
            f"<div style='font-size:0.8rem; color:{wc_color}; text-align:right; margin-bottom:0.8rem;'>"
            f"{wc} / {limit} words</div>",
            unsafe_allow_html=True,
        )
        if wc < sec["min_words"]:
            all_ready = False

    # Persist section text continuously
    st.session_state["ch8_sections"] = sections

    if not all_ready:
        st.caption("Each section needs at least 10 words to enable evaluation.")

    if st.button(
        "Get Evaluation →",
        disabled=not all_ready,
        type="primary",
        use_container_width=True,
        key="ch8_btn_evaluate",
    ):
        with st.spinner("Evaluating your proposal — this may take 10–20 seconds…"):
            data = call_coach_api(
                sections,
                st.session_state["ch8_student_name"],
                st.session_state["ch8_scenario"],
            )
        st.session_state["ch8_scorecard"] = data
        st.session_state["ch8_phase"] = "scorecard"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 3 — Scorecard
# ---------------------------------------------------------------------------

def screen_scorecard() -> None:
    _init_state()
    data: dict = st.session_state.get("ch8_scorecard", {})
    student_name: str = st.session_state.get("ch8_student_name", "Student")
    sc = SCENARIOS[st.session_state["ch8_scenario"]]

    if not data or data.get("_error"):
        st.title("Chapter 8 — Proposal Evaluation")
        st.error(
            "We couldn't generate your evaluation. This is usually a temporary issue. "
            "Click 'Try Again' to resubmit."
        )
        if st.button("Try Again →", use_container_width=True):
            st.session_state["ch8_phase"] = "write"
            st.session_state["ch8_scorecard"] = None
            st.rerun()
        return

    total = data.get("total_score", 0)
    tier = data.get("tier", "")
    summary = data.get("plain_english_summary", "")
    strongest = data.get("strongest_section", "")
    weakest_name = data.get("weakest_section_name", "")
    weakest_rewrite = data.get("weakest_section_rewrite", "")
    one_thing = data.get("one_thing_to_change", "")

    if total >= 90:
        tier_color = "#27AE60"
    elif total >= 75:
        tier_color = "#4A90D9"
    elif total >= 60:
        tier_color = "#F39C12"
    else:
        tier_color = "#E74C3C"

    # --- 3-col header ---
    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown(
            f"<div style='color:#FAFAFA; font-weight:700;'>{_html.escape(student_name)}</div>",
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(
            f"<div style='color:#4A90D9; font-weight:700; text-align:center;'>"
            f"{_html.escape(sc['buyer_name'])}</div>",
            unsafe_allow_html=True,
        )
    with h3:
        st.markdown(
            f"<div style='color:#aaa; text-align:right;'>{date.today().strftime('%B %d, %Y')}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("## Chapter 8 — Proposal Evaluation")

    # --- Plain English summary ---
    st.markdown(
        f"<div style='color:#ddd; font-size:0.95rem; line-height:1.7; margin-bottom:1rem;'>"
        f"{_html.escape(summary)}</div>",
        unsafe_allow_html=True,
    )

    # --- Score banner ---
    st.markdown(
        f'<div style="background:#1A2332; border:2px solid {tier_color}; border-radius:10px;'
        f' padding:1rem 1.2rem; text-align:center; margin-bottom:1.2rem;">'
        f'<div style="font-size:2rem; font-weight:700; color:{tier_color};">{total}/100</div>'
        f'<div style="font-size:1.1rem; font-weight:700; color:#FAFAFA; margin-top:0.2rem;">{_html.escape(tier)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # --- 5 dimension expanders ---
    st.markdown("### Dimension Breakdown")
    for dim in data.get("dimensions", []):
        d_name = dim.get("name", "")
        d_score = dim.get("score", 0)
        d_max = dim.get("max_points", 0)
        d_evidence = dim.get("evidence", "")
        d_coaching = dim.get("coaching_note", "")
        pct = int(d_score / d_max * 100) if d_max else 0
        bar_c = "#27AE60" if pct >= 70 else ("#F39C12" if pct >= 40 else "#E74C3C")

        with st.expander(f"{d_name} — {d_score}/{d_max}"):
            st.markdown(
                f'<div style="background:#0E1117; border-radius:4px; height:8px; margin-bottom:0.6rem;">'
                f'<div style="background:{bar_c}; width:{pct}%; height:8px; border-radius:4px;"></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if d_evidence and d_evidence.lower() != "not present":
                st.markdown(
                    f'<div style="font-size:0.85rem; color:#aaa; margin-bottom:0.4rem;">'
                    f'<em>Evidence: "{_html.escape(d_evidence)}"</em></div>',
                    unsafe_allow_html=True,
                )
            if pct < 70 and d_coaching:
                st.markdown(
                    f'<div style="font-size:0.88rem; color:#F39C12;">'
                    f'💬 {_html.escape(d_coaching)}</div>',
                    unsafe_allow_html=True,
                )
            elif d_coaching:
                st.markdown(
                    f'<div style="font-size:0.88rem; color:#ddd;">{_html.escape(d_coaching)}</div>',
                    unsafe_allow_html=True,
                )

    # --- Weakest section rewrite ---
    if weakest_rewrite:
        st.markdown("---")
        with st.expander(f"📝 What a stronger {_html.escape(weakest_name)} looks like"):
            st.markdown(
                f'<div style="background:#0D1B2E; border-left:3px solid #4A90D9;'
                f' padding:0.8rem 1rem; border-radius:0 6px 6px 0;">'
                f'<div style="font-size:0.82rem; font-weight:700; color:#4A90D9; margin-bottom:0.4rem;">'
                f'Written using {_html.escape(sc["buyer_name"])}\'s language and numbers</div>'
                f'<div style="color:#ddd; font-size:0.9rem; line-height:1.7; white-space:pre-wrap;">'
                f'{_html.escape(weakest_rewrite)}</div></div>',
                unsafe_allow_html=True,
            )

    # --- Strongest section note ---
    if strongest:
        st.markdown(
            f'<div style="background:#0D1F14; border:1px solid #27AE60; border-radius:8px;'
            f' padding:0.75rem 1rem; margin-bottom:0.6rem;">'
            f'<div style="font-size:0.82rem; font-weight:700; color:#27AE60; margin-bottom:0.2rem;">'
            f'⭐ Strongest Section</div>'
            f'<div style="color:#ddd; font-size:0.88rem;">{_html.escape(strongest)}</div></div>',
            unsafe_allow_html=True,
        )

    # --- One thing to change ---
    if one_thing:
        st.markdown(
            f'<div style="background:#1A2332; border:1px solid #F39C12; border-radius:8px;'
            f' padding:0.75rem 1rem; margin-bottom:1rem;">'
            f'<div style="font-weight:700; color:#F39C12; margin-bottom:0.3rem; font-size:0.9rem;">'
            f'🎯 One Thing to Change</div>'
            f'<div style="color:#ddd; font-size:0.9rem;">{_html.escape(one_thing)}</div></div>',
            unsafe_allow_html=True,
        )

    if st.button("Try Again →", use_container_width=True):
        _reset_state()
        st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_chapter8() -> None:
    _init_state()
    phase = st.session_state["ch8_phase"]
    if phase == "setup":
        screen_setup()
    elif phase == "write":
        screen_write()
    elif phase == "scorecard":
        screen_scorecard()
    else:
        screen_setup()
