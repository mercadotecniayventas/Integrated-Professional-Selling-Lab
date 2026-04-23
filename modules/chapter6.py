import json
import random
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

CHANNEL_ORDER = ["linkedin", "email", "cold_call", "event_followup"]

LINKEDIN_CASES = {
    "L1": {
        "prospect_name": "David Park",
        "prospect_title": "VP Operations",
        "company": "Synthex Manufacturing",
        "company_size": "500 employees",
        "seller_product": "supply chain analytics",
        "seller_company": "DataFlow Solutions",
        "context": (
            "You found them via LinkedIn search. "
            "They just posted about supply chain challenges."
        ),
    },
    "L2": {
        "prospect_name": "Jennifer Wu",
        "prospect_title": "Director of HR",
        "company": "NovaCorp Tech",
        "company_size": "300 employees",
        "seller_product": "HR analytics",
        "seller_company": "TalentIQ",
        "context": (
            "Mutual connection suggested you connect. "
            "She recently liked a post about employee retention."
        ),
    },
    "L3": {
        "prospect_name": "Robert Chen",
        "prospect_title": "CFO",
        "company": "Meridian Healthcare",
        "company_size": "600 employees",
        "seller_product": "financial planning software",
        "seller_company": "ClearView Analytics",
        "context": (
            "No prior contact. "
            "Company recently announced expansion to 3 new cities."
        ),
    },
}

EMAIL_CASES = {
    "E1": {
        "prospect_name": "Maria Santos",
        "prospect_title": "CFO",
        "company": "Greenfield Energy",
        "company_size": "320 employees",
        "seller_product": "financial planning software",
        "seller_company": "ClearView Analytics",
        "context": (
            "Colleague Jake worked with her before and suggested you reach out."
        ),
    },
    "E2": {
        "prospect_name": "James Kim",
        "prospect_title": "Director of IT",
        "company": "Apex Healthcare",
        "company_size": "800 employees",
        "seller_product": "cybersecurity software",
        "seller_company": "ShieldTech Solutions",
        "context": (
            "No prior contact. "
            "Company had a data breach reported in the news last month."
        ),
    },
    "E3": {
        "prospect_name": "Patricia Moore",
        "prospect_title": "VP Sales",
        "company": "FastGrow Retail",
        "company_size": "450 employees",
        "seller_product": "CRM analytics",
        "seller_company": "DataFlow Solutions",
        "context": (
            "Met briefly at an industry webinar. "
            "She mentioned pipeline visibility as a challenge."
        ),
    },
}

COLDCALL_CASES = {
    "C1": {
        "prospect_name": "Thomas Rivera",
        "prospect_title": "COO",
        "company": "BuildRight Construction",
        "company_size": "700 employees",
        "seller_product": "project management software",
        "seller_company": "BuildRight Solutions",
        "context": (
            "No prior contact. "
            "Company recently won a $50M government contract."
        ),
    },
    "C2": {
        "prospect_name": "Sarah Mitchell",
        "prospect_title": "VP Operations",
        "company": "PrimePack Logistics",
        "company_size": "400 employees",
        "seller_product": "route optimization software",
        "seller_company": "FleetIQ",
        "context": (
            "Found via LinkedIn, no connection yet. "
            "Industry facing driver shortage challenges."
        ),
    },
    "C3": {
        "prospect_name": "Michael Torres",
        "prospect_title": "Director of Finance",
        "company": "SunState Energy",
        "company_size": "550 employees",
        "seller_product": "financial analytics",
        "seller_company": "ClearView Analytics",
        "context": (
            "No prior contact. "
            "Company expanding into renewable energy division."
        ),
    },
}

EVENT_CASES = {
    "EV1": {
        "prospect_name": "James Kim",
        "prospect_title": "Director of IT",
        "company": "Apex Healthcare",
        "company_size": "800 employees",
        "seller_product": "cybersecurity software",
        "seller_company": "ShieldTech Solutions",
        "context": (
            "Met at CyberSec Conference yesterday. "
            "He mentioned concerns about ransomware attacks. "
            "Had 5 minutes — no business cards exchanged."
        ),
    },
    "EV2": {
        "prospect_name": "Laura Nguyen",
        "prospect_title": "VP Marketing",
        "company": "TechVentures Inc",
        "company_size": "250 employees",
        "seller_product": "sales intelligence software",
        "seller_company": "LeadGenius",
        "context": (
            "Met at B2B Sales Summit this morning. "
            "She was interested in AI-powered lead scoring. "
            "Had a 10-minute conversation at the networking lunch."
        ),
    },
    "EV3": {
        "prospect_name": "Daniel Park",
        "prospect_title": "COO",
        "company": "MedSupply Corp",
        "company_size": "480 employees",
        "seller_product": "supply chain software",
        "seller_company": "DataFlow Solutions",
        "context": (
            "Met at Healthcare Operations Conference today. "
            "He mentioned supply chain visibility as a top priority. "
            "Brief conversation — he gave you his card."
        ),
    },
}

CASES = {
    "linkedin":       LINKEDIN_CASES,
    "email":          EMAIL_CASES,
    "cold_call":      COLDCALL_CASES,
    "event_followup": EVENT_CASES,
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

_CHANNEL_ICONS = {
    "email": "📧",
    "linkedin": "💼",
    "cold_call": "📞",
    "event_followup": "🤝",
}


def _init_state() -> None:
    # Persistent rotation tracker — survives resets
    if "ch6_last_case_per_channel" not in st.session_state:
        st.session_state["ch6_last_case_per_channel"] = {
            "linkedin": None,
            "email": None,
            "cold_call": None,
            "event_followup": None,
        }

    # Assign one case index (0/1/2) per channel, never the same as last time
    if "ch6_case_per_channel" not in st.session_state:
        last = st.session_state["ch6_last_case_per_channel"]
        assignments = {}
        for ch_key in CHANNEL_ORDER:
            available = [i for i in range(3) if i != last[ch_key]]
            if not available:
                available = [0, 1, 2]
            assignments[ch_key] = random.choice(available)
        st.session_state["ch6_case_per_channel"] = assignments
        # Record immediately so next session rotates away from these
        st.session_state["ch6_last_case_per_channel"] = dict(assignments)

    defaults = {
        "ch6_phase": "setup",
        "ch6_student_name": "",
        "ch6_channel_order": list(CHANNEL_ORDER),
        "ch6_current_round": 0,
        "ch6_round_scores": [],
        "ch6_message": "",
        "ch6_scorecard": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset_state() -> None:
    # Preserve rotation data before clearing
    last_cases = st.session_state.get(
        "ch6_last_case_per_channel",
        {"linkedin": None, "email": None, "cold_call": None, "event_followup": None},
    )
    # Wipe session-specific keys only
    for key in [
        "ch6_phase", "ch6_student_name", "ch6_current_round",
        "ch6_round_scores", "ch6_case_per_channel",
        "ch6_channel_order", "ch6_message", "ch6_scorecard",
    ]:
        st.session_state.pop(key, None)
    # Restore rotation tracker so _init_state picks different cases
    st.session_state["ch6_last_case_per_channel"] = last_cases
    _init_state()


# ---------------------------------------------------------------------------
# Screen 1 — Setup
# ---------------------------------------------------------------------------

def screen_setup() -> None:
    st.title("Chapter 6 — Prospecting & Outreach Practice")

    # Section 1 — How it works
    st.markdown(
        """
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.75rem;">
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.6rem;">
            &#128203; How this activity works
          </div>
          <div style="color:#FAFAFA; margin-bottom:0.6rem;">
            In real B2B selling, outreach typically follows this sequence:
          </div>
          <div style="color:#FAFAFA; margin-bottom:0.25rem;">&#128188; <strong>LinkedIn</strong> — connect and establish presence first</div>
          <div style="color:#FAFAFA; margin-bottom:0.25rem;">&#128231; <strong>Email</strong> — follow up with a specific value message</div>
          <div style="color:#FAFAFA; margin-bottom:0.25rem;">&#128222; <strong>Cold Call</strong> — reach out by phone if no response</div>
          <div style="color:#FAFAFA; margin-bottom:0.6rem;">&#129309; <strong>Event Follow-up</strong> — reconnect after meeting in person</div>
          <div style="color:#ddd; margin-bottom:0.6rem;">
            In this activity you will practice all 4 channels.
            Your assigned order for this session will appear below.
          </div>
          <div style="color:#ddd; margin-bottom:0.4rem;">After each round you will receive:</div>
          <div style="color:#FAFAFA; margin-bottom:0.2rem;">&#9989; A score across 6 dimensions</div>
          <div style="color:#FAFAFA; margin-bottom:0.2rem;">&#9989; Specific feedback on what worked</div>
          <div style="color:#FAFAFA; margin-bottom:0.2rem;">&#9989; A rewritten example showing what great looks like</div>
          <div style="color:#FAFAFA; margin-bottom:0.5rem;">&#9989; One specific thing to improve</div>
          <div style="color:#ddd;">
            At the end you will see your overall score across all 4 channels
            and your strongest and weakest channel.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section 2 — Channel order preview for this session
    channel_order = st.session_state["ch6_channel_order"]
    rows_html = ""
    for i, ck in enumerate(channel_order):
        icon = _CHANNEL_ICONS[ck]
        label = CHANNELS[ck]["label"]
        rows_html += (
            f'<div style="padding:0.3rem 0; color:#FAFAFA; font-size:0.93rem;">'
            f'<span style="color:#4A90D9; font-weight:700;">Round {i + 1}:</span>'
            f'&nbsp; {icon} {label}</div>'
        )
    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:8px; padding:0.9rem 1.1rem; margin:0.5rem 0 1rem 0;">
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.5rem;">
            Your channel order for this session:
          </div>
          {rows_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section 3 — Name input
    st.markdown("**Your full name (appears on your scorecard):**")
    student_name = st.text_input(
        "Your full name",
        value=st.session_state["ch6_student_name"],
        placeholder="e.g. Ana García",
        key="ch6_name_input",
        label_visibility="collapsed",
    )

    # Section 4 — Start button
    ready = bool(student_name.strip())
    if not ready:
        st.caption("Enter your name above to enable the Start button.")

    if st.button(
        "Start Round 1 →",
        disabled=not ready,
        type="primary",
        use_container_width=True,
    ):
        st.session_state["ch6_student_name"] = student_name.strip()
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
