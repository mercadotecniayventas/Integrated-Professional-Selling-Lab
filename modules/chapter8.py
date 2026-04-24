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
