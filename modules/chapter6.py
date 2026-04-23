import json
import re
import streamlit as st
from datetime import date
from openai import OpenAI
from config import get_openai_api_key

MODEL_COACH = "gpt-4.1-mini"
TEMP_COACH = 0.3

# ---------------------------------------------------------------------------
# Channel and scenario data
# ---------------------------------------------------------------------------

CHANNELS = {
    "email": {
        "label": "Email",
        "word_limit": 150,
        "textarea_label": "Write your email",
        "mission_rule": "Research-grounded, specific, under 150 words. No generic templates.",
        "mission_tip": "Reference something concrete about the prospect's company or situation.",
    },
    "linkedin": {
        "label": "LinkedIn Message",
        "word_limit": 75,
        "textarea_label": "Write your LinkedIn message",
        "mission_rule": "No pitch in first message. One specific observation. Under 75 words.",
        "mission_tip": "Start with a genuine observation, not a compliment or a product mention.",
    },
    "cold_call": {
        "label": "Cold Call Script",
        "word_limit": 200,
        "textarea_label": "Write your call opener/script",
        "mission_rule": "First 10 seconds determine everything. No scripts — authenticity wins. Under 200 words.",
        "mission_tip": "Open with a pattern interrupt. Avoid 'Hi, my name is X and I work at Y.'",
    },
    "event_followup": {
        "label": "Event Follow-up",
        "word_limit": 100,
        "textarea_label": "Write your follow-up message",
        "mission_rule": "Reference something specific from your conversation. Under 100 words.",
        "mission_tip": "Name one specific thing they said. Generic follow-ups get ignored.",
    },
}

SCENARIOS = {
    "cold": {
        "label": "Scenario 1 — Cold Outreach",
        "prospect_name": "David Park",
        "prospect_title": "VP Operations",
        "company": "Synthex Manufacturing",
        "company_size": "500 employees",
        "seller_product": "supply chain analytics software",
        "seller_company": "DataFlow Solutions",
        "context": (
            "No prior contact. Found them via LinkedIn. "
            "They recently opened a new distribution center in Texas."
        ),
    },
    "warm": {
        "label": "Scenario 2 — Warm Outreach (Mutual Connection)",
        "prospect_name": "Maria Santos",
        "prospect_title": "CFO",
        "company": "Greenfield Energy",
        "company_size": "320 employees",
        "seller_product": "financial planning software",
        "seller_company": "ClearView Analytics",
        "context": (
            "Your colleague Jake worked with Maria 2 years ago and suggested you reach out. "
            "She values relationships before business."
        ),
    },
    "event": {
        "label": "Scenario 3 — Event Follow-up",
        "prospect_name": "James Kim",
        "prospect_title": "Director of IT",
        "company": "Apex Healthcare",
        "company_size": "800 employees",
        "seller_product": "cybersecurity software",
        "seller_company": "ShieldTech Solutions",
        "context": (
            "You met briefly at a conference yesterday. "
            "He mentioned data security concerns but you only had 5 minutes."
        ),
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _word_count(text: str) -> int:
    return len(text.split()) if text.strip() else 0


# ---------------------------------------------------------------------------
# Coach prompt + API
# ---------------------------------------------------------------------------

def get_coach_prompt(message: str, student_name: str, channel_key: str, scenario_key: str) -> str:
    ch = CHANNELS[channel_key]
    sc = SCENARIOS[scenario_key]
    word_limit = ch["word_limit"]

    channel_guidance = {
        "email": (
            "Evaluate as a B2B sales email. Assess research depth, specificity, "
            "and whether it avoids generic templates."
        ),
        "linkedin": (
            "Evaluate as a LinkedIn first-touch message. Assess relationship-first approach "
            "— no pitch in the first message."
        ),
        "cold_call": (
            "Evaluate as a spoken cold call opener/script. Assess the pattern interrupt, "
            "authenticity, and whether it avoids the clichéd "
            "'Hi my name is X and I work at Y' opener."
        ),
        "event_followup": (
            "Evaluate as an event follow-up message. Assess whether it references something "
            "specific from the conversation rather than being generic."
        ),
    }[channel_key]

    return f"""You are a B2B sales coach evaluating a student's outreach message.

STUDENT NAME: {student_name}
CHANNEL: {ch['label']} (word limit: {word_limit} words)
CHANNEL GUIDANCE: {channel_guidance}

PROSPECT: {sc['prospect_name']}, {sc['prospect_title']} at {sc['company']} ({sc['company_size']})
SELLER PRODUCT: {sc['seller_product']} (sold by {sc['seller_company']})
CONTEXT: {sc['context']}

STUDENT MESSAGE:
\"\"\"
{message}
\"\"\"

Word count: {_word_count(message)} / {word_limit}

Evaluate the message on exactly 6 dimensions. Return ONLY valid JSON — start with {{ and end with }}.

JSON structure:
{{
  "dimensions": [
    {{
      "name": "Personalization",
      "score": <0|5|15|25>,
      "max_points": 25,
      "evidence": "<exact quote from student message, or 'Not present'>",
      "coaching_note": "<specific, actionable feedback referencing this scenario>"
    }},
    {{
      "name": "Value Proposition Clarity",
      "score": <0|5|12|20>,
      "max_points": 20,
      "evidence": "<exact quote or 'Not present'>",
      "coaching_note": "<specific feedback>"
    }},
    {{
      "name": "Call to Action",
      "score": <0|5|10|15>,
      "max_points": 15,
      "evidence": "<exact quote or 'Not present'>",
      "coaching_note": "<specific feedback>"
    }},
    {{
      "name": "Professional Tone & Authenticity",
      "score": <0|6|12|20>,
      "max_points": 20,
      "evidence": "<exact quote or 'Not present'>",
      "coaching_note": "<specific feedback>"
    }},
    {{
      "name": "Length & Format",
      "score": <0|5|10|15>,
      "max_points": 15,
      "evidence": "<brief note on word count and structure>",
      "coaching_note": "<specific feedback>"
    }},
    {{
      "name": "Ethical Framing",
      "score": <0|3|5>,
      "max_points": 5,
      "evidence": "<exact quote or 'Not present'>",
      "coaching_note": "<specific feedback>"
    }}
  ],
  "total_score": <sum of all scores, 0-100>,
  "tier": "<Ready to Send|Strong Draft|Needs Work|Rewrite Recommended>",
  "plain_english_summary": "<exactly 2 sentences summarizing performance>",
  "rewritten_example": "<full rewritten version of the message — strong, specific, appropriate for this channel and scenario>",
  "one_thing_to_change": "<single most impactful improvement the student should make>"
}}

SCORING RUBRIC:

Personalization (25 pts):
  25 = References specific researched details about THIS prospect or company
  15 = Some personalization but partially generic
   5 = Could have been sent to anyone
   0 = Completely generic template

Value Proposition Clarity (20 pts):
  20 = Clear specific value tied to prospect's likely pain points — not features
  12 = Value mentioned but vague or generic
   5 = Features listed but no clear value
   0 = No value proposition

Call to Action (15 pts):
  15 = Specific, low-friction CTA (15-min call, specific question)
  10 = CTA present but vague ("let me know")
   5 = Implied CTA but not stated clearly
   0 = No CTA or aggressive ask

Professional Tone & Authenticity (20 pts):
  For Email / LinkedIn / Event Follow-up:
    20 = Authentic, professional, not salesy
    12 = Mostly professional, minor issues
     6 = Too formal/stiff OR too casual/pushy
     0 = Sounds like a template or AI-generated
  For Cold Call:
    20 = Strong pattern interrupt opener, not "Hi my name is X and I work at Y"
    12 = Decent opener but predictable
     6 = Generic opener ("How are you today?")
     0 = Leading immediately with product pitch

Length & Format (15 pts):
  15 = Within {word_limit}-word limit, well structured, easy to read
  10 = Slightly over limit or minor formatting issues
   5 = Significantly over limit
   0 = Way over limit or unreadable

Ethical Framing (5 pts):
  5 = Message implies genuine research and a real reason for reaching out to THIS prospect
  3 = Somewhat genuine but feels quota-driven
  0 = No clear reason why THIS prospect — feels like mass outreach

Tier thresholds: 90-100 = "Ready to Send", 75-89 = "Strong Draft", 60-74 = "Needs Work", below 60 = "Rewrite Recommended"

Return ONLY the JSON object. No markdown, no explanation, no code fences."""


def call_coach_api(message: str, student_name: str, channel_key: str, scenario_key: str) -> dict:
    client = OpenAI(api_key=get_openai_api_key())
    prompt = get_coach_prompt(message, student_name, channel_key, scenario_key)
    response = client.chat.completions.create(
        model=MODEL_COACH,
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
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "dimensions": [],
            "total_score": 0,
            "tier": "Error",
            "plain_english_summary": "Could not parse the evaluation. Please try again.",
            "rewritten_example": "",
            "one_thing_to_change": "Please resubmit your message.",
            "_error": True,
        }


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def _init_state() -> None:
    defaults = {
        "ch6_phase": "setup",
        "ch6_student_name": "",
        "ch6_channel": "email",
        "ch6_scenario": "cold",
        "ch6_message": "",
        "ch6_scorecard": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset_state() -> None:
    keys = [k for k in st.session_state if k.startswith("ch6_")]
    for k in keys:
        del st.session_state[k]
    _init_state()


# ---------------------------------------------------------------------------
# Screen 1 — Setup
# ---------------------------------------------------------------------------

def screen_setup() -> None:
    st.title("Chapter 6 — Prospecting & Outreach Evaluator")
    st.markdown("### Simulation Setup")
    st.markdown("---")

    student_name = st.text_input(
        "Your full name",
        value=st.session_state["ch6_student_name"],
        placeholder="e.g. Ana García",
        key="ch6_name_input",
    )

    st.markdown("#### Select outreach channel")
    channel_options = list(CHANNELS.keys())
    channel_labels = [CHANNELS[k]["label"] for k in channel_options]
    selected_channel_label = st.radio(
        "Outreach channel",
        channel_labels,
        index=channel_options.index(st.session_state.get("ch6_channel", "email")),
        key="ch6_channel_radio",
        label_visibility="collapsed",
    )
    selected_channel = channel_options[channel_labels.index(selected_channel_label)]

    st.markdown("#### Select prospect scenario")
    scenario_options = list(SCENARIOS.keys())
    scenario_labels = [SCENARIOS[k]["label"] for k in scenario_options]
    selected_scenario_label = st.radio(
        "Prospect scenario",
        scenario_labels,
        index=scenario_options.index(st.session_state.get("ch6_scenario", "cold")),
        key="ch6_scenario_radio",
        label_visibility="collapsed",
    )
    selected_scenario = scenario_options[scenario_labels.index(selected_scenario_label)]

    ch = CHANNELS[selected_channel]
    sc = SCENARIOS[selected_scenario]

    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:8px; padding:1rem 1.2rem;
             margin-top:0.75rem; margin-bottom:0.5rem;">
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.5rem;">
            &#128203; Your Prospect
          </div>
          <div style="color:#FAFAFA; margin-bottom:0.4rem;">
            <strong>{sc['prospect_name']}</strong>,
            {sc['prospect_title']} &mdash;
            <strong>{sc['company']}</strong> ({sc['company_size']})
          </div>
          <div style="color:#ddd; margin-bottom:0.4rem;">
            You sell: <strong>{sc['seller_product']}</strong>
            at <strong>{sc['seller_company']}</strong>
          </div>
          <div style="color:#aaa; font-style:italic;">{sc['context']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #4A90D9;
             border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.75rem;">
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.4rem;">
            &#127919; Your Mission &mdash; {ch['label']}
          </div>
          <div style="color:#FAFAFA; margin-bottom:0.4rem;">{ch['mission_rule']}</div>
          <div style="color:#aaa; font-style:italic;">&#128161; {ch['mission_tip']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ready = bool(student_name.strip())
    if not ready:
        st.caption("Enter your name above to enable the Start button.")
    else:
        st.caption("⚠️ Write your outreach message on the next screen, then get AI evaluation.")

    if st.button(
        "Start Writing →",
        disabled=not ready,
        type="primary",
        use_container_width=True,
    ):
        st.session_state["ch6_student_name"] = student_name.strip()
        st.session_state["ch6_channel"] = selected_channel
        st.session_state["ch6_scenario"] = selected_scenario
        st.session_state["ch6_message"] = ""
        st.session_state["ch6_phase"] = "write"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 2 — Write & Evaluate
# ---------------------------------------------------------------------------

def screen_write() -> None:
    channel_key = st.session_state["ch6_channel"]
    scenario_key = st.session_state["ch6_scenario"]
    ch = CHANNELS[channel_key]
    sc = SCENARIOS[scenario_key]
    word_limit = ch["word_limit"]

    st.title("Chapter 6 — Prospecting & Outreach Evaluator")

    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:6px; padding:0.5rem 0.8rem; margin-bottom:0.75rem;
             font-size:0.88rem; color:#ddd;">
          <strong style="color:#FAFAFA;">{ch['label']}</strong>
          &nbsp;&middot;&nbsp;
          {sc['prospect_name']}, {sc['prospect_title']} at {sc['company']}
          &nbsp;&middot;&nbsp;
          <span style="color:#aaa;">Limit: {word_limit} words</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    message = st.text_area(
        ch["textarea_label"],
        value=st.session_state.get("ch6_message", ""),
        height=260,
        placeholder=f"Write your {ch['label'].lower()} here…",
        key="ch6_message_input",
    )

    wc = _word_count(message)
    over = wc > word_limit
    wc_color = "#E74C3C" if over else ("#27AE60" if wc >= 20 else "#888")
    st.markdown(
        f'<div style="font-size:0.85rem; color:{wc_color}; margin-bottom:0.5rem;">'
        f'Word count: <strong>{wc}</strong> / {word_limit}'
        + (" &nbsp;⚠️ Over limit" if over else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    ready = wc >= 20
    if not ready:
        st.caption(f"Write at least 20 words to unlock evaluation (currently {wc}).")

    if st.button(
        "Get Evaluation →",
        disabled=not ready,
        type="primary",
        use_container_width=True,
        key="ch6_btn_evaluate",
    ):
        st.session_state["ch6_message"] = message
        with st.spinner("Evaluating your message — this may take 10–20 seconds…"):
            data = call_coach_api(
                message,
                st.session_state["ch6_student_name"],
                channel_key,
                scenario_key,
            )
        st.session_state["ch6_scorecard"] = data
        st.session_state["ch6_phase"] = "scorecard"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 3 — Scorecard
# ---------------------------------------------------------------------------

def screen_scorecard() -> None:
    data: dict = st.session_state["ch6_scorecard"]
    student_name: str = st.session_state["ch6_student_name"]
    channel_key = st.session_state["ch6_channel"]
    scenario_key = st.session_state["ch6_scenario"]
    ch = CHANNELS[channel_key]
    sc = SCENARIOS[scenario_key]

    total = data.get("total_score", 0)
    tier = data.get("tier", "")
    if total >= 90:
        tier_color = "#27AE60"
    elif total >= 75:
        tier_color = "#4A90D9"
    elif total >= 60:
        tier_color = "#F39C12"
    else:
        tier_color = "#E74C3C"

    st.title("Scorecard — Prospecting & Outreach")
    st.markdown("---")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Student", student_name)
    with col_b:
        st.metric("Channel · Scenario", f"{ch['label']} · {sc['prospect_name']}")
    with col_c:
        st.metric("Date", str(date.today()))

    st.markdown("")

    if data.get("plain_english_summary"):
        st.info(data["plain_english_summary"])

    st.markdown(
        f"""
        <div style="background:#1A2332; border:2px solid {tier_color};
             border-radius:12px; padding:1.5rem; text-align:center;
             margin:0.75rem 0 1rem 0;">
          <div style="font-size:2.4rem; font-weight:800; color:{tier_color};">
            {total} / 100
          </div>
          <div style="font-size:1.05rem; color:#FAFAFA; font-weight:600;">{tier}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### Dimension Breakdown")

    for dim in data.get("dimensions", []):
        name = dim.get("name", "")
        score = dim.get("score", 0)
        max_pts = dim.get("max_points", 0)
        evidence = dim.get("evidence", "")
        coaching_note = dim.get("coaching_note", "")
        pct = score / max_pts if max_pts else 0

        with st.expander(f"{name} — {score} / {max_pts} pts", expanded=True):
            st.progress(pct)
            if evidence and evidence.lower() not in ("not present", ""):
                st.caption(f'Evidence: "{evidence}"')
            if pct < 0.70 and coaching_note:
                st.warning(f"**Coaching note:** {coaching_note}")
            elif coaching_note:
                st.caption(f"Note: {coaching_note}")

    rewrite = data.get("rewritten_example", "")
    if rewrite:
        st.markdown("---")
        with st.expander("✍️ Rewritten Example", expanded=False):
            st.markdown(rewrite)

    one_thing = data.get("one_thing_to_change", "")
    if one_thing:
        st.markdown("---")
        st.markdown(
            f"""
            <div style="background:#1A2332; border:1px solid #4A90D9;
                 border-radius:8px; padding:0.9rem 1.1rem;">
              <div style="font-weight:700; color:#4A90D9; margin-bottom:0.3rem;">
                &#128161; One Thing to Change
              </div>
              <div style="color:#FAFAFA;">{one_thing}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    if st.button("✍️ Try Again — Same Scenario", use_container_width=True):
        st.session_state["ch6_message"] = ""
        st.session_state["ch6_scorecard"] = None
        st.session_state["ch6_phase"] = "write"
        st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_chapter6() -> None:
    _init_state()
    phase = st.session_state["ch6_phase"]
    if phase == "setup":
        screen_setup()
    elif phase == "write":
        screen_write()
    else:
        screen_scorecard()
