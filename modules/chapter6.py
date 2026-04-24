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
        "research_tip": (
            "Synthex Manufacturing is fictional. To personalize your message, spend 5 minutes "
            "researching a real manufacturing or supply chain company. Use what you find to make "
            "your message specific and credible — generic messages score poorly."
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
        "research_tip": (
            "NovaCorp Tech is fictional. To personalize your message, spend 5 minutes "
            "researching a real mid-size tech company's HR challenges. Use what you find to make "
            "your message specific and credible — generic messages score poorly."
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
        "research_tip": (
            "Meridian Healthcare is fictional. To personalize your message, spend 5 minutes "
            "researching a real healthcare system expanding operations. Use what you find to make "
            "your message specific and credible — generic messages score poorly."
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
        "research_tip": (
            "Greenfield Energy is fictional. To personalize your message, spend 5 minutes "
            "researching a real energy company's financial operations. Use what you find to make "
            "your message specific and credible — generic messages score poorly."
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
        "research_tip": (
            "Apex Healthcare is fictional. To personalize your message, spend 5 minutes "
            "researching a real healthcare organization's recent cybersecurity news. Use what you find to make "
            "your message specific and credible — generic messages score poorly."
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
        "research_tip": (
            "FastGrow Retail is fictional. To personalize your message, spend 5 minutes "
            "researching a real retail company's sales pipeline challenges. Use what you find to make "
            "your message specific and credible — generic messages score poorly."
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
        "research_tip": (
            "BuildRight Construction is fictional. To personalize your message, spend 5 minutes "
            "researching a real construction company that recently won a large contract. Use what you find to make "
            "your message specific and credible — generic messages score poorly."
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
        "research_tip": (
            "PrimePack Logistics is fictional. To personalize your message, spend 5 minutes "
            "researching a real logistics company facing driver or capacity challenges. Use what you find to make "
            "your message specific and credible — generic messages score poorly."
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
        "research_tip": (
            "SunState Energy is fictional. To personalize your message, spend 5 minutes "
            "researching a real energy company expanding into renewables. Use what you find to make "
            "your message specific and credible — generic messages score poorly."
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
        "research_tip": (
            "Apex Healthcare is fictional. To personalize your message, spend 5 minutes "
            "researching recent ransomware attacks on healthcare organizations. Use what you find to make "
            "your message specific and credible — generic messages score poorly."
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
        "research_tip": (
            "TechVentures Inc is fictional. To personalize your message, spend 5 minutes "
            "researching AI-powered lead scoring trends in B2B marketing. Use what you find to make "
            "your message specific and credible — generic messages score poorly."
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
        "research_tip": (
            "MedSupply Corp is fictional. To personalize your message, spend 5 minutes "
            "researching supply chain challenges in medical device distribution. Use what you find to make "
            "your message specific and credible — generic messages score poorly."
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

def get_coach_prompt(message: str, student_name: str, channel_key: str, case: dict) -> str:
    ch = CHANNELS[channel_key]
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

IMPORTANT: Do NOT penalize spelling, grammar, or syntax errors in the student's message. This is a B2B sales course, not an English writing course. Many students are non-native English speakers. Evaluate only:
- The strategic thinking behind the message
- The personalization and research evident
- The value proposition and CTA quality
- The authenticity and tone intent
A message with spelling errors but genuine personalization should score higher than a perfect message with no research.

AI POLICY: Students may use AI to help write their messages. This is encouraged. Evaluate the final message quality regardless of whether AI was used. If the message shows genuine research and personalization, it scores well — even if AI helped write it.

STUDENT NAME: {student_name}
CHANNEL: {ch['label']} (word limit: {word_limit} words)
CHANNEL GUIDANCE: {channel_guidance}

PROSPECT: {case['prospect_name']}, {case['prospect_title']} at {case['company']} ({case['company_size']})
SELLER PRODUCT: {case['seller_product']} (sold by {case['seller_company']})
CONTEXT: {case['context']}

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


def call_coach_api(message: str, student_name: str, channel_key: str, case: dict) -> dict:
    _fallback = {
        "dimensions": [],
        "total_score": 0,
        "tier": "Error",
        "plain_english_summary": "Could not generate evaluation. Please try again.",
        "rewritten_example": "",
        "one_thing_to_change": "Please resubmit your message.",
        "_error": True,
    }
    try:
        client = OpenAI(api_key=get_openai_api_key())
        prompt = get_coach_prompt(message, student_name, channel_key, case)
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
        return json.loads(raw)
    except json.JSONDecodeError:
        return _fallback
    except Exception:
        return _fallback


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

    st.markdown(
        """
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.75rem;">
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.6rem;">
            &#128203; How this activity works
          </div>
          <div style="color:#FAFAFA; margin-bottom:0.5rem;">
            In professional B2B selling, outreach follows a natural sequence:
          </div>
          <div style="color:#FAFAFA; margin-bottom:0.2rem;">&#128188; <strong>Round 1 &mdash; LinkedIn:</strong> establish presence first</div>
          <div style="color:#FAFAFA; margin-bottom:0.2rem;">&#128231; <strong>Round 2 &mdash; Email:</strong> follow up with specific value</div>
          <div style="color:#FAFAFA; margin-bottom:0.2rem;">&#128222; <strong>Round 3 &mdash; Cold Call:</strong> reach out by phone</div>
          <div style="color:#FAFAFA; margin-bottom:0.6rem;">&#129309; <strong>Round 4 &mdash; Event Follow-up:</strong> reconnect after meeting</div>
          <div style="color:#ddd; margin-bottom:0.6rem;">
            You will practice all 4 channels in this order.
            Each time you practice, you will face different prospects
            &mdash; so you can never memorize the answers.
          </div>
          <div style="color:#ddd; margin-bottom:0.35rem;">After each round you will receive:</div>
          <div style="color:#FAFAFA; margin-bottom:0.2rem;">&#9989; A score across 6 dimensions</div>
          <div style="color:#FAFAFA; margin-bottom:0.2rem;">&#9989; Specific feedback on what worked</div>
          <div style="color:#FAFAFA; margin-bottom:0.2rem;">&#9989; A rewritten example showing what great looks like</div>
          <div style="color:#FAFAFA; margin-bottom:0.5rem;">&#9989; One specific thing to improve</div>
          <div style="color:#ddd;">
            At the end you will see your overall score across all 4 channels
            and your strongest and weakest channel.
          </div>
          <div style="margin-top:0.75rem; padding-top:0.65rem; border-top:1px solid #2E5FA3;">
            <div style="font-weight:700; color:#4A90D9; margin-bottom:0.4rem;">
              &#129504; Can I use AI?
            </div>
            <div style="color:#FAFAFA; margin-bottom:0.5rem;">
              Yes &mdash; for all 4 channels. But AI alone scores poorly. The evaluator checks
              for genuine personalization and authentic voice.
            </div>
            <div style="color:#ddd; margin-bottom:0.25rem; font-weight:600;">Best approach:</div>
            <div style="color:#FAFAFA; margin-bottom:0.15rem;">1. Research a real company in that industry first</div>
            <div style="color:#FAFAFA; margin-bottom:0.15rem;">2. Use AI to draft a starting point</div>
            <div style="color:#FAFAFA; margin-bottom:0.15rem;">3. Edit with what YOU found</div>
            <div style="color:#FAFAFA; margin-bottom:0.4rem;">4. Make it sound like you, not a template</div>
            <div style="color:#aaa; font-style:italic;">AI suggests. You decide.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📊 How you'll be scored"):
        st.markdown(
            """
            <div style="color:#ddd; font-size:0.9rem; line-height:1.7;">
              <div style="font-weight:700; color:#4A90D9; margin-bottom:0.5rem;">
                100 pts per round
              </div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Personalization</strong>
                <span style="color:#4A90D9;"> — 25 pts</span><br>
                Does your message reference specific research?
              </div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Value Proposition</strong>
                <span style="color:#4A90D9;"> — 20 pts</span><br>
                Is your value clear and prospect-specific?
              </div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Call to Action</strong>
                <span style="color:#4A90D9;"> — 15 pts</span><br>
                Is your CTA specific and low-friction?
              </div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Tone &amp; Authenticity</strong>
                <span style="color:#4A90D9;"> — 20 pts</span><br>
                Does it sound human, not like a template?
              </div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Length &amp; Format</strong>
                <span style="color:#4A90D9;"> — 15 pts</span><br>
                Are you within the word limit?
              </div>
              <div>
                <strong style="color:#FAFAFA;">Ethical Framing</strong>
                <span style="color:#4A90D9;"> — 5 pts</span><br>
                Do you have a genuine reason to reach out?
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("**Your full name (appears on your scorecard):**")
    student_name = st.text_input(
        "Your full name",
        value=st.session_state["ch6_student_name"],
        placeholder="e.g. Ana García",
        key="ch6_name_input",
        label_visibility="collapsed",
    )

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
    current_round = st.session_state["ch6_current_round"]
    channel_key = CHANNEL_ORDER[current_round]
    case_idx = st.session_state["ch6_case_per_channel"][channel_key]
    case_key = list(CASES[channel_key].keys())[case_idx]
    sc = CASES[channel_key][case_key]
    ch = CHANNELS[channel_key]
    word_limit = ch["word_limit"]
    icon = _CHANNEL_ICONS[channel_key]

    st.title("Chapter 6 — Prospecting & Outreach Practice")

    # Round header
    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:6px; padding:0.45rem 0.8rem; margin-bottom:0.65rem;
             font-size:0.92rem;">
          <span style="color:#4A90D9; font-weight:700;">
            Round {current_round + 1} of 4 &mdash; {icon} {ch['label']}
          </span>
          <span style="color:#aaa; font-size:0.82rem;">
            &nbsp;&middot;&nbsp; {word_limit}-word limit
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Prospect briefing card
    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:8px; padding:0.9rem 1.1rem; margin-bottom:0.5rem;">
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.4rem;">
            &#128203; Your Prospect
          </div>
          <div style="color:#FAFAFA; margin-bottom:0.3rem;">
            <strong>{sc['prospect_name']}</strong>,
            {sc['prospect_title']} &mdash;
            <strong>{sc['company']}</strong> ({sc['company_size']})
          </div>
          <div style="color:#ddd; margin-bottom:0.3rem;">
            You sell: <strong>{sc['seller_product']}</strong>
            at <strong>{sc['seller_company']}</strong>
          </div>
          <div style="color:#aaa; font-style:italic;">{sc['context']}</div>
          <div style="margin-top:0.55rem; padding-top:0.5rem; border-top:1px solid #2E5FA3;
               color:#F39C12; font-size:0.88rem;">
            &#128269; <strong>Research tip:</strong> {sc['research_tip']}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Mission card
    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #4A90D9;
             border-radius:8px; padding:0.8rem 1rem; margin-bottom:0.75rem;">
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.3rem;">
            &#127919; Your Mission
          </div>
          <div style="color:#FAFAFA; margin-bottom:0.25rem;">{ch['mission_rule']}</div>
          <div style="color:#aaa; font-style:italic;">&#128161; {ch['mission_tip']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    message = st.text_area(
        ch["textarea_label"],
        value=st.session_state.get("ch6_message", ""),
        height=240,
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
                sc,          # case dict — get_coach_prompt updated in step 4
            )
        st.session_state["ch6_scorecard"] = data
        st.session_state["ch6_current_round"] += 1
        st.session_state["ch6_phase"] = "scorecard"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 3 — Per-round scorecard
# ---------------------------------------------------------------------------

def screen_round_scorecard() -> None:
    data: dict = st.session_state["ch6_scorecard"]
    student_name: str = st.session_state["ch6_student_name"]
    current_round: int = st.session_state["ch6_current_round"]   # already incremented
    channel_key = CHANNEL_ORDER[current_round - 1]
    case_idx = st.session_state["ch6_case_per_channel"][channel_key]
    case_key = list(CASES[channel_key].keys())[case_idx]
    sc = CASES[channel_key][case_key]
    ch = CHANNELS[channel_key]
    icon = _CHANNEL_ICONS[channel_key]

    if not data or data.get("_error"):
        st.title(f"Round {current_round} — Evaluation")
        st.error(
            "We couldn't generate your evaluation. This is usually a temporary issue. "
            "Click 'Try Again' to resubmit your message."
        )
        if st.button("Try Again →", use_container_width=True):
            st.session_state["ch6_current_round"] -= 1
            st.session_state["ch6_phase"] = "write"
            st.session_state["ch6_scorecard"] = None
            st.rerun()
        return

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

    # Accumulate round scores (guard against double-append on rerun)
    round_scores: list = st.session_state["ch6_round_scores"]
    if len(round_scores) < current_round:
        round_scores.append({
            "round": current_round,
            "channel": channel_key,
            "channel_label": ch["label"],
            "icon": icon,
            "prospect": sc["prospect_name"],
            "company": sc["company"],
            "score": total,
            "tier": tier,
        })
        st.session_state["ch6_round_scores"] = round_scores

    st.title("Scorecard — Prospecting & Outreach")
    st.markdown("---")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Student", student_name)
    with col_b:
        st.metric(
            f"Round {current_round} of 4",
            f"{icon} {ch['label']} · {sc['prospect_name']}",
        )
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
    is_last = (current_round >= len(CHANNEL_ORDER))
    btn_label = "See Final Results →" if is_last else f"Next Round →"
    if st.button(btn_label, type="primary", use_container_width=True):
        st.session_state["ch6_message"] = ""
        st.session_state["ch6_scorecard"] = None
        st.session_state["ch6_phase"] = "final" if is_last else "write"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 4 — Final scorecard
# ---------------------------------------------------------------------------

def screen_final_scorecard() -> None:
    student_name: str = st.session_state["ch6_student_name"]
    round_scores: list = st.session_state["ch6_round_scores"]

    scores = [r["score"] for r in round_scores]
    avg = round(sum(scores) / len(scores)) if scores else 0

    if avg >= 90:
        tier, tier_color = "Ready to Send", "#27AE60"
    elif avg >= 75:
        tier, tier_color = "Strong Draft", "#4A90D9"
    elif avg >= 60:
        tier, tier_color = "Needs Work", "#F39C12"
    else:
        tier, tier_color = "Rewrite Recommended", "#E74C3C"

    best = max(round_scores, key=lambda r: r["score"])
    worst = min(round_scores, key=lambda r: r["score"])

    st.title("Final Scorecard — Prospecting & Outreach")
    st.markdown("---")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Student", student_name)
    with col_b:
        st.metric("Activity", "4 Channels")
    with col_c:
        st.metric("Date", str(date.today()))

    st.markdown("")

    st.markdown(
        f"""
        <div style="background:#1A2332; border:2px solid {tier_color};
             border-radius:12px; padding:1.5rem; text-align:center;
             margin:0.75rem 0 1rem 0;">
          <div style="font-size:2.4rem; font-weight:800; color:{tier_color};">
            {avg} / 100
          </div>
          <div style="font-size:1.05rem; color:#FAFAFA; font-weight:600;">
            Overall Average &mdash; {tier}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### Round Summary")

    header_html = (
        '<div style="display:grid; grid-template-columns:1fr 2fr 2fr 1fr;'
        ' gap:0.5rem; padding:0.4rem 0.6rem; font-weight:700;'
        ' color:#4A90D9; font-size:0.85rem; border-bottom:1px solid #2E5FA3;">'
        "<div>Round</div><div>Channel</div><div>Prospect</div><div>Score</div></div>"
    )
    rows_html = ""
    for r in round_scores:
        s = r["score"]
        sc_color = "#27AE60" if s >= 75 else ("#F39C12" if s >= 60 else "#E74C3C")
        rows_html += (
            f'<div style="display:grid; grid-template-columns:1fr 2fr 2fr 1fr;'
            f' gap:0.5rem; padding:0.35rem 0.6rem; font-size:0.88rem;'
            f' border-bottom:1px solid #1A2332; color:#ddd;">'
            f'<div style="color:#FAFAFA;">{r["round"]}</div>'
            f'<div>{r["icon"]} {r["channel_label"]}</div>'
            f'<div>{r["prospect"]}</div>'
            f'<div style="color:{sc_color}; font-weight:700;">{s}</div></div>'
        )
    st.markdown(
        f'<div style="background:#112030; border:1px solid #2E5FA3;'
        f' border-radius:8px; margin-bottom:1rem; overflow:hidden;">'
        f"{header_html}{rows_html}</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.success(
            f"**Strongest: {best['icon']} {best['channel_label']}**\n\n"
            f"Score: {best['score']} / 100 — {best['tier']}\n\n"
            f"Prospect: {best['prospect']} at {best['company']}"
        )
    with col2:
        st.error(
            f"**Needs Work: {worst['icon']} {worst['channel_label']}**\n\n"
            f"Score: {worst['score']} / 100 — {worst['tier']}\n\n"
            f"Prospect: {worst['prospect']} at {worst['company']}"
        )

    st.markdown("---")
    if st.button("🔄 Practice Again", type="primary", use_container_width=True):
        _reset_state()
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
    elif phase == "scorecard":
        screen_round_scorecard()
    else:
        screen_final_scorecard()
