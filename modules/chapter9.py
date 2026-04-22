import io
import json
import re
import streamlit as st
from datetime import date
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
from config import get_openai_api_key

MODEL_BUYER = "gpt-4.1-mini"
MODEL_COACH = "gpt-4.1-mini"
TEMP_BUYER = 0.7
TEMP_COACH = 0.3
MAX_STUDENT_MSGS = 16

SCENARIOS = {
    "logistics": {
        "label": "Logistics — Marcus Reid, VP Operations, Nexbridge Logistics",
        "buyer_name": "Marcus Reid",
        "buyer_title": "VP of Operations",
        "company": "Nexbridge Logistics",
        "product": "supply chain visibility software",
        "rep_company": "VisionTrack Solutions",
        "opening": (
            "Thanks for walking me through this. I've reviewed the proposal summary. "
            "Before we go further, I have a few concerns I need to raise."
        ),
    },
    "hr_saas": {
        "label": "HR SaaS — Diana Pham, VP People, CoreBridge Solutions",
        "buyer_name": "Diana Pham",
        "buyer_title": "VP of People",
        "company": "CoreBridge Solutions",
        "product": "HR analytics software",
        "rep_company": "TalentIQ",
        "opening": (
            "Thanks for walking me through this. I've reviewed the proposal summary. "
            "Before we go further, I have a few concerns I need to raise."
        ),
    },
    "medical": {
        "label": "Medical Manufacturing — Robert Salinas, VP Operations, MedVantex",
        "buyer_name": "Robert Salinas",
        "buyer_title": "VP of Operations",
        "company": "MedVantex",
        "product": "quality management software",
        "rep_company": "QualityPro",
        "opening": (
            "Thanks for walking me through this. I've reviewed the proposal summary. "
            "Before we go further, I have a few concerns I need to raise."
        ),
    },
}


def get_system_prompt(scenario: str) -> str:
    s = SCENARIOS[scenario]

    if scenario == "logistics":
        return f"""Always respond in English regardless of what language the student uses.

You are {s['buyer_name']}, {s['buyer_title']} at {s['company']}, a mid-size \
third-party logistics company. You have just reviewed a one-page proposal summary \
from a sales representative at {s['rep_company']} selling {s['product']}. \
You previously had a discovery conversation where you shared details about carrier \
visibility challenges, manual reconciliation, and a $2.3M client loss.

You are now in a proposal review meeting. You are skeptical but open. \
You have 4 concerns to raise in sequence. Do NOT move to the next concern until \
the current one is genuinely addressed — meaning the student has responded with a \
substantive answer, ideally by asking a clarifying question first.

## YOUR 4 CONCERNS IN SEQUENCE

### CONCERN 1 — PRICE (raise this first)
Open with: "Your pricing is almost double what I was expecting. \
I can't justify this to my CFO."
Stay on this concern until the student asks what you were expecting, \
why it's hard to justify, or what ROI would be needed — AND then addresses \
it substantively (ROI framing, payment terms, phasing, or value reframe). \
A bare counter-offer without exploration does NOT satisfy this concern.

### CONCERN 2 — TIMING (raise only after Concern 1 is genuinely addressed)
Say: "Even if the price worked, we're entering our busiest season. \
This isn't the right time."
Stay on this concern until the student asks about the timeline or what \
the busy season looks like — AND offers a concrete solution such as a \
phased rollout, a post-season start date, or a parallel implementation plan.

### CONCERN 3 — STATUS QUO (raise only after Concern 2 is genuinely addressed)
Say: "Our current system isn't perfect but it works. \
I'm not sure the disruption is worth it."
Stay on this concern until the student acknowledges the change risk, \
asks what "works" means to you, or asks about the cost of not changing — \
AND references the pain points you shared in discovery \
(the $2.3M client loss, the three hours of daily manual reconciliation).

### CONCERN 4 — FALSE OBJECTION (raise only after Concern 3 is genuinely addressed)
Say: "I need to think about it and discuss with my team before moving forward."

This masks a political risk: you championed the current tracking system \
18 months ago and fear admitting it needs replacing.

BEHAVIOR FOR CONCERN 4:
- If the student accepts this at face value ("of course, take your time") → \
  become noticeably more distant. Responses get shorter. \
  The window is closing and you are not going to chase them.
- If the student asks a clarifying question \
  (e.g., "What specifically would you want to discuss?" or \
  "Is there something beyond the proposal that's giving you pause?") → \
  reveal Layer 1: "Honestly... I was the one who pushed for our current \
  system 18 months ago. Recommending we replace it now is a conversation \
  I need to be ready for."
- If the student follows Layer 1 with empathy and a thoughtful question \
  (e.g., "What would make that conversation easier for you?" or \
  "How can I help you build the internal case?") → \
  reveal your full concern and open the door to close: you need internal \
  cover, a strong ROI summary, and ideally a reference customer in logistics \
  you can point to. If the student can provide these, you are ready to move forward.

## BEHAVIORAL RULES

1. If the student rebuts without asking a clarifying question first → \
   give a shorter, more defensive response. Canned rebuttals do not impress you.
2. If the student asks a thoughtful clarifying question before responding → \
   open up and give more context. You reward genuine curiosity.
3. If the student immediately offers a price discount without exploring value → \
   say exactly: "If you can drop the price that easily, I wonder what else \
   has margin in this deal."
4. If the student shows frustration or impatience → become more guarded and formal.
5. If the student is composed, curious, and professional → \
   reward them with candor and additional detail.
6. Never skip a concern — each must be raised and genuinely resolved before the next.
7. Do not use the words: objection, BATNA, integrative bargaining, \
   negotiation tactic.
8. Respond conversationally. No bullet points. No headers. \
   Speak as a VP would in a proposal review meeting.
9. Keep responses 2–4 sentences for bare rebuttals, \
   3–5 sentences for good clarifying questions.
10. After all 4 concerns are addressed, you are willing to discuss next steps \
    but do not close yourself — let the student propose the path forward.
"""

    elif scenario == "hr_saas":
        return f"""Always respond in English regardless of what language the student uses.

You are {s['buyer_name']}, {s['buyer_title']} at {s['company']}, a B2B SaaS company \
with 620 employees. You have just reviewed a one-page proposal summary from a sales \
representative at {s['rep_company']} selling {s['product']}. You previously had a \
discovery conversation where you shared details about fragmented HR tools, an \
$800K L&D investment you couldn't prove ROI on, and a CFO threatening to cut \
HR's budget by 30%.

You are now in a proposal review meeting. You are data-oriented and guarded. \
You have 4 concerns to raise in sequence. Do NOT move to the next concern until \
the current one is genuinely addressed — meaning the student has responded with a \
substantive answer, ideally by asking a clarifying question first.

## YOUR 4 CONCERNS IN SEQUENCE

### CONCERN 1 — PRICE (raise this first)
Open with: "This investment is significantly above our budget range \
for this quarter."
Stay on this concern until the student asks about your budget range, \
what "significantly above" means, or what the approval process looks like — \
AND then addresses it substantively (ROI framing, quarterly phasing, \
or multi-year pricing). A bare discount offer without exploration \
does NOT satisfy this concern.

### CONCERN 2 — TIMING (raise only after Concern 1 is genuinely addressed)
Say: "We just finished a major systems migration. \
Our team doesn't have bandwidth right now."
Stay on this concern until the student asks about the migration, \
what bandwidth looks like for your team, or what a realistic start \
window would be — AND offers a phased onboarding or a deferred \
implementation timeline.

### CONCERN 3 — STATUS QUO (raise only after Concern 2 is genuinely addressed)
Say: "Our people have adapted to the current process. \
Change management is expensive."
Stay on this concern until the student asks what "adapted" means, \
what the change management cost concern is specifically, or what \
adoption support you would need — AND references the discovery pain \
(the $800K you couldn't account for, the fragmented six-tool stack, \
the CFO pressure).

### CONCERN 4 — FALSE OBJECTION (raise only after Concern 3 is genuinely addressed)
Say: "I need to think about it and discuss with my team \
before moving forward."

This masks a political risk: HR's credibility is already under scrutiny \
from the CFO and you cannot afford to sponsor a tool that underdelivers.

BEHAVIOR FOR CONCERN 4:
- If the student accepts this at face value → \
  become more distant. Responses get shorter. The opportunity is slipping.
- If the student asks a clarifying question \
  (e.g., "What would your team need to see to feel confident?" or \
  "Is there a specific concern behind that?") → \
  reveal Layer 1: "Honestly... HR is already under the microscope from \
  the CFO. If I bring in a new platform and it doesn't deliver measurable \
  ROI within two quarters, I've made my situation worse, not better."
- If the student follows Layer 1 with empathy and a thoughtful question \
  (e.g., "What would 'delivering ROI' look like in your CFO's eyes?" or \
  "How can we structure this so you have proof points at 90 days?") → \
  reveal your full concern and open the door to close: you need a \
  90-day ROI milestone plan, a named success metric tied to the CFO's \
  concern, and optionally a reference from a similar-stage SaaS company. \
  If the student can provide these, you are ready to move forward.

## BEHAVIORAL RULES

1. If the student rebuts without asking a clarifying question first → \
   give a shorter, more defensive response.
2. If the student asks a thoughtful clarifying question before responding → \
   open up and give more context.
3. If the student immediately offers a price discount without exploring value → \
   say exactly: "If you can drop the price that easily, I wonder what else \
   has margin in this deal."
4. If the student shows frustration or impatience → become more guarded and formal.
5. If the student is composed, curious, and professional → \
   reward them with candor and additional detail.
6. Never skip a concern — each must be raised and genuinely resolved before the next.
7. Do not use the words: objection, BATNA, integrative bargaining, \
   negotiation tactic.
8. Respond conversationally. No bullet points. No headers.
9. Keep responses 2–4 sentences for bare rebuttals, \
   3–5 sentences for good clarifying questions.
10. After all 4 concerns are addressed, you are willing to discuss next steps \
    but do not close yourself — let the student propose the path forward.
"""

    else:  # medical
        return f"""Always respond in English regardless of what language the student uses.

You are {s['buyer_name']}, {s['buyer_title']} at {s['company']}, a medical device \
manufacturer with 480 employees. You have just reviewed a one-page proposal summary \
from a sales representative at {s['rep_company']} selling {s['product']}. You \
previously had a discovery conversation where you shared details about a legacy \
QMS from 2009, an FDA Warning Letter that cost $1.4M and delayed a product launch \
by 14 months, and the risk of losing your manufacturing certification.

You are now in a proposal review meeting. You are precise and compliance-minded. \
You have 4 concerns to raise in sequence. Do NOT move to the next concern until \
the current one is genuinely addressed — meaning the student has responded with a \
substantive answer, ideally by asking a clarifying question first.

## YOUR 4 CONCERNS IN SEQUENCE

### CONCERN 1 — PRICE (raise this first)
Open with: "The total cost here is more than we allocated \
for this initiative."
Stay on this concern until the student asks what was allocated, \
how the budget decision was made, or what the approval process looks like — \
AND then addresses it substantively (ROI vs. Warning Letter remediation cost, \
phased implementation, or executive sponsorship framing). A bare discount \
offer without exploration does NOT satisfy this concern.

### CONCERN 2 — TIMING (raise only after Concern 1 is genuinely addressed)
Say: "We have an FDA audit coming up in Q3. \
We can't take on new implementations now."
Stay on this concern until the student asks about the audit scope, \
what "can't take on" means operationally, or what the post-audit \
window looks like — AND offers a concrete plan (pre-audit prep module, \
post-audit go-live, or a read-only pilot that doesn't touch production systems).

### CONCERN 3 — STATUS QUO (raise only after Concern 2 is genuinely addressed)
Say: "We've been compliant for 12 years with what we have. \
Why fix what isn't broken?"
Stay on this concern until the student asks what "compliant" means \
given the Warning Letter, challenges the 12-year framing thoughtfully, \
or asks what it would take for you to feel confident in making a change — \
AND references the discovery pain (the $1.4M remediation, the legacy \
end-of-life system, the manual audit trail process).

### CONCERN 4 — FALSE OBJECTION (raise only after Concern 3 is genuinely addressed)
Say: "I need to think about it and discuss with my team \
before moving forward."

This masks a political risk: you approved the current legacy QMS \
and recommending its replacement means admitting it contributed to \
the Warning Letter.

BEHAVIOR FOR CONCERN 4:
- If the student accepts this at face value → \
  become more distant. Responses become formal and brief. \
  The opportunity is closing.
- If the student asks a clarifying question \
  (e.g., "What part of the decision do you want to pressure-test \
  with your team?" or "Is there something specific that's \
  giving you pause beyond the proposal?") → \
  reveal Layer 1: "Honestly... I signed off on the current QMS \
  implementation four years ago. If I now tell the executive team \
  we need to replace it because it contributed to the Warning Letter, \
  that's a difficult conversation. I need to be sure I can defend this."
- If the student follows Layer 1 with empathy and a thoughtful question \
  (e.g., "What would make that conversation defensible for you?" or \
  "What evidence would help you walk into that meeting with confidence?") → \
  reveal your full concern and open the door to close: you need a \
  documented comparison of the legacy system's gaps vs. the new platform's \
  controls, a reference from an FDA-regulated manufacturer who passed \
  an audit post-implementation, and a clear change narrative you can \
  present to the executive team. If the student can provide these, \
  you are ready to move forward.

## BEHAVIORAL RULES

1. If the student rebuts without asking a clarifying question first → \
   give a shorter, more measured response.
2. If the student asks a thoughtful clarifying question before responding → \
   open up and give more context.
3. If the student immediately offers a price discount without exploring value → \
   say exactly: "If you can drop the price that easily, I wonder what else \
   has margin in this deal."
4. If the student shows frustration or impatience → become more guarded and formal.
5. If the student is composed, curious, and professional → \
   reward them with candor and additional detail.
6. Never skip a concern — each must be raised and genuinely resolved before the next.
7. Do not use the words: objection, BATNA, integrative bargaining, \
   negotiation tactic.
8. Respond conversationally. No bullet points. No headers. \
   Speak as a compliance-minded VP would in a proposal review.
9. Keep responses 2–4 sentences for bare rebuttals, \
   3–5 sentences for good clarifying questions.
10. After all 4 concerns are addressed, you are willing to discuss next steps \
    but do not close yourself — let the student propose the path forward.
"""


# ---------------------------------------------------------------------------
# Coach prompt
# ---------------------------------------------------------------------------

def get_coach_prompt(conversation_history: list, student_name: str, scenario: str) -> str:
    s = SCENARIOS[scenario]

    lines = []
    for msg in conversation_history:
        speaker = s["buyer_name"] if msg["role"] == "assistant" else f"STUDENT ({student_name})"
        lines.append(f"{speaker}: {msg['content']}")
    transcript = "\n\n".join(lines)

    return f"""You are an expert B2B sales coach evaluating a proposal review and \
objection-handling conversation.

STUDENT NAME: {student_name}
SCENARIO: {s['buyer_name']}, {s['buyer_title']} at {s['company']} — \
selling {s['product']} for {s['rep_company']}

The buyer raised 4 concerns in sequence:
  C1 — Price
  C2 — Timing
  C3 — Status Quo / Change Risk
  C4 — "I need to think about it" (false objection masking political risk)

=== FULL CONVERSATION TRANSCRIPT ===
{transcript}
=== END TRANSCRIPT ===

Evaluate the student across the 5 dimensions below. \
Return ONLY a valid JSON object — no markdown, no backticks, \
no text before or after the JSON.

CRITICAL: Start your response with {{ and end with }}.

The JSON must have exactly this shape:

{{
  "dimensions": [
    {{
      "name": "First Response Quality",
      "max_points": 25,
      "score": <integer 0-25>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote of one student message>"
    }},
    {{
      "name": "False Objection Detection",
      "max_points": 20,
      "score": <integer 0-20>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote, or 'Student did not probe C4'>"
    }},
    {{
      "name": "Price Handling",
      "max_points": 20,
      "score": <integer 0-20>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote of student's price response>"
    }},
    {{
      "name": "Emotional Composure",
      "max_points": 20,
      "score": <integer 0-20>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote showing composure or its absence>"
    }},
    {{
      "name": "Closing Orientation",
      "max_points": 15,
      "score": <integer 0-15>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote of close attempt, or 'No close attempted'>"
    }}
  ],
  "plain_english_summary": "<2 sentences: overall performance in plain language, no jargon>",
  "strongest_moment": "<1-2 sentences quoting the student's single best response>",
  "critical_gap": "<1-2 sentences on the most important thing the student failed to do>",
  "behavioral_recommendation": "<One specific, actionable behavior to practice in the next simulation>",
  "process_insight": "<1-2 sentences on what the pattern of concerns revealed about upstream discovery — what should the student have surfaced in discovery to make this conversation easier?>"
}}

=== SCORING RUBRIC ===

1. FIRST RESPONSE QUALITY (25 pts)
Did the student ask a clarifying question before responding to each concern?
- 25 pts: Asked a clarifying question before responding to 3 or 4 of the 4 concerns
- 18 pts: Asked a clarifying question before responding to 2 of the 4 concerns
- 10 pts: Asked a clarifying question before responding to 1 of the 4 concerns
- 0 pts: Rebuttals only — launched into responses without asking anything first

2. FALSE OBJECTION DETECTION (20 pts)
Did the student recognize C4 as a surface response masking a deeper concern?
- 20 pts: Identified it as a surface response, asked a probing question, \
  and fully uncovered the political risk beneath it
- 12 pts: Sensed something deeper but did not fully uncover the real concern
- 5 pts: Asked one clarifying question but accepted the first follow-up answer \
  without digging further
- 0 pts: Accepted "I need to think about it" at face value without any follow-up

3. PRICE HANDLING (20 pts)
How did the student respond to the price concern?
- 20 pts: Reframed value using specific pain points and numbers the buyer \
  shared in discovery (cost of inaction, remediation costs, client losses, etc.)
- 14 pts: Used ROI logic or value arguments but not tied to this buyer's situation
- 8 pts: Offered a discount or concession before having a value conversation
- 0 pts: Immediately discounted or capitulated without any value defense

4. EMOTIONAL COMPOSURE (20 pts)
Did the student stay calm, curious, and professional throughout?
- 20 pts: Calm and curious across all 4 concerns — no defensiveness, \
  no urgency pressure, no frustration
- 14 pts: Mostly composed, with one moment of defensiveness or mild pressure
- 8 pts: Noticeable frustration or use of pressure tactics in 2 or more exchanges
- 0 pts: Argumentative, defensive throughout, or used false urgency

5. CLOSING ORIENTATION (15 pts)
Did the student attempt to close, and how well was it handled?
- 15 pts: Natural collaborative close after all concerns addressed — \
  asked for a specific next step, framed as joint progress
- 10 pts: Close attempted but framed as the seller winning rather than mutual progress
- 5 pts: Close attempted prematurely, before all concerns were resolved
- 0 pts: No close attempt, or the student abandoned the deal

=== END RUBRIC ===

Score strictly against the transcript. Award points only for demonstrated \
behavior, not intent. Quote the student directly in every evidence field.

CRITICAL: Return ONLY the JSON object. Start with {{ and end with }}."""


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def call_buyer_api(messages: list, scenario: str) -> str:
    client = OpenAI(api_key=get_openai_api_key())
    system_msg = {"role": "system", "content": get_system_prompt(scenario)}
    response = client.chat.completions.create(
        model=MODEL_BUYER,
        messages=[system_msg] + messages,
        temperature=TEMP_BUYER,
    )
    return response.choices[0].message.content.strip()


def call_coach_api(conversation_history: list, student_name: str, scenario: str) -> dict:
    client = OpenAI(api_key=get_openai_api_key())
    prompt = get_coach_prompt(conversation_history, student_name, scenario)
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
            "plain_english_summary": "Could not parse coach response.",
            "strongest_moment": "Please try again.",
            "critical_gap": "Scorecard could not be generated — run simulation again.",
            "behavioral_recommendation": "Re-run the simulation to receive feedback.",
            "process_insight": "",
            "_error": True,
        }


def call_tts_api(text: str):
    try:
        client = OpenAI(api_key=get_openai_api_key())
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=text,
        )
        return response.content
    except Exception:
        return None


def call_whisper_api(audio_bytes: bytes):
    try:
        client = OpenAI(api_key=get_openai_api_key())
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "recording.webm"
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
        return result.text.strip() or None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def _init_state() -> None:
    defaults = {
        "ch9_phase": "setup",
        "ch9_student_name": "",
        "ch9_scenario": "logistics",
        "ch9_messages": [],
        "ch9_student_count": 0,
        "ch9_scorecard": None,
        "ch9_generating": False,
        "ch9_voice_enabled": True,
        "ch9_tts_bytes": None,
        "ch9_last_audio_id": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset_state() -> None:
    keys = [k for k in st.session_state if k.startswith("ch9_")]
    for k in keys:
        del st.session_state[k]
    _init_state()


# ---------------------------------------------------------------------------
# Screen 1 — Setup
# ---------------------------------------------------------------------------

def screen_setup() -> None:
    st.title("Chapter 9 — Objections, Negotiation & Closing")
    st.markdown("### Simulation Setup")
    st.markdown(
        "Configure your simulation below. "
        "Your name will appear on the scorecard."
    )
    st.markdown("---")

    student_name = st.text_input(
        "Your full name",
        value=st.session_state["ch9_student_name"],
        placeholder="e.g. Ana García",
        key="ch9_name_input",
    )

    st.markdown("#### Select a buyer scenario")
    scenario_options = list(SCENARIOS.keys())
    scenario_labels = [SCENARIOS[k]["label"] for k in scenario_options]
    selected_index = scenario_options.index(st.session_state["ch9_scenario"])

    chosen_index = st.radio(
        "Scenario",
        options=range(len(scenario_options)),
        format_func=lambda i: scenario_labels[i],
        index=selected_index,
        label_visibility="collapsed",
    )

    chosen_key = scenario_options[chosen_index]
    s = SCENARIOS[chosen_key]

    _BRIEFINGS = {
        "logistics": {
            "location": "Atlanta, GA",
            "size": "280 employees",
            "revenue": "$90M revenue",
            "industry": "Mid-size freight brokerage, US Southeast",
        },
        "hr_saas": {
            "location": "Austin, TX",
            "size": "420 employees",
            "revenue": "$65M revenue",
            "industry": "HR technology and workforce management",
        },
        "medical": {
            "location": "San Diego, CA",
            "size": "310 employees",
            "revenue": "$120M revenue",
            "industry": "Medical device manufacturing",
        },
    }

    b = _BRIEFINGS[chosen_key]
    st.markdown(
        f"""
        <div style="margin-top:0.75rem;">
          <div style="background:#1A2332; border:1px solid #2E5FA3;
               border-radius:8px 8px 0 0; padding:1rem 1.2rem;">
            <div style="font-weight:700; color:#4A90D9;
                 margin-bottom:0.6rem;">&#128203; Your Prospect</div>
            <strong>{s['buyer_name']}</strong> &nbsp;&middot;&nbsp; {s['buyer_title']}<br>
            {s['company']} &nbsp;&middot;&nbsp; {b['location']}<br>
            <span style="color:#aaa;">{b['size']} &nbsp;&middot;&nbsp; {b['revenue']}</span><br>
            <span style="color:#aaa;">{b['industry']}</span>
          </div>
          <div style="background:#112030; border:1px solid #2E5FA3; border-top:none;
               border-radius:0 0 8px 8px; padding:1rem 1.2rem;">
            <div style="font-weight:700; color:#27AE60;
                 margin-bottom:0.6rem;">&#127919; Your Situation</div>
            You completed discovery with this buyer last week.<br>
            You are presenting a proposal today — the buyer has read your one-page summary.<br>
            <span style="color:#aaa; font-style:italic;">
              Your job: address their concerns professionally and move toward close.
            </span><br>
            <span style="color:#F39C12; font-size:0.85rem;
                 display:block; margin-top:0.5rem;">
              Read carefully — this briefing disappears once the meeting starts.
            </span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("")
    ready = bool(student_name.strip())
    if not ready:
        st.caption("Enter your name above to enable the Start button.")

    if st.button(
        "Enter the meeting →",
        disabled=not ready,
        type="primary",
        use_container_width=True,
    ):
        opening = SCENARIOS[chosen_key]["opening"]
        st.session_state["ch9_student_name"] = student_name.strip()
        st.session_state["ch9_scenario"] = chosen_key
        st.session_state["ch9_messages"] = [{"role": "assistant", "content": opening}]
        st.session_state["ch9_student_count"] = 0
        st.session_state["ch9_phase"] = "chat"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 2 — Chat
# ---------------------------------------------------------------------------

def screen_chat() -> None:
    scenario = st.session_state["ch9_scenario"]
    s = SCENARIOS[scenario]
    messages: list = st.session_state["ch9_messages"]
    student_count: int = st.session_state["ch9_student_count"]

    st.title("Chapter 9 — Objections, Negotiation & Closing")
    col_left, col_mid, col_right = st.columns([3, 1.2, 0.9])
    with col_left:
        st.markdown(
            f"**Buyer:** {s['buyer_name']}, {s['buyer_title']} &nbsp;·&nbsp; "
            f"*{s['company']}*",
            unsafe_allow_html=True,
        )
    with col_mid:
        voice_on = st.toggle(
            "🔊 Voice",
            value=st.session_state.get("ch9_voice_enabled", True),
            key="ch9_voice_toggle",
        )
        st.session_state["ch9_voice_enabled"] = voice_on
    with col_right:
        st.markdown(
            f"<div style='text-align:right; color:#aaa;'>Messages: "
            f"<strong style='color:#FAFAFA;'>{student_count}/{MAX_STUDENT_MSGS}</strong></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    for msg in messages:
        if msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="👔"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("user", avatar="🎓"):
                st.markdown(msg["content"])

    tts_bytes = st.session_state.get("ch9_tts_bytes")
    if tts_bytes:
        st.audio(tts_bytes, format="audio/mp3", autoplay=True)
        st.session_state["ch9_tts_bytes"] = None

    if student_count >= 12:
        st.info(
            "You've sent 12 messages — you should be working through the final concerns. "
            "Look for an opportunity to summarize the value and propose a clear next step."
        )

    audio = mic_recorder(
        start_prompt="🎤 Click to speak",
        stop_prompt="⏹ Recording… click to stop",
        key="ch9_mic",
    )
    if audio and audio.get("bytes"):
        if audio.get("id") != st.session_state.get("ch9_last_audio_id"):
            st.session_state["ch9_last_audio_id"] = audio["id"]
            with st.spinner("Transcribing…"):
                transcribed = call_whisper_api(audio["bytes"])
            if transcribed:
                messages.append({"role": "user", "content": transcribed})
                st.session_state["ch9_student_count"] += 1
                st.session_state["ch9_messages"] = messages
                st.session_state["ch9_generating"] = True
                st.rerun()
            else:
                st.warning(
                    "Could not transcribe the recording — please try again "
                    "or type your response below."
                )

    user_input = st.chat_input(
        "Type your response to the buyer…",
        disabled=st.session_state.get("ch9_generating", False),
    )

    if user_input:
        messages.append({"role": "user", "content": user_input})
        st.session_state["ch9_student_count"] += 1
        st.session_state["ch9_messages"] = messages
        st.session_state["ch9_generating"] = True
        st.rerun()

    if st.session_state.get("ch9_generating", False):
        with st.spinner(f"{s['buyer_name']} is thinking…"):
            reply = call_buyer_api(messages, scenario)
        messages.append({"role": "assistant", "content": reply})
        st.session_state["ch9_messages"] = messages
        if st.session_state.get("ch9_voice_enabled", True):
            with st.spinner("Generating voice response…"):
                tts = call_tts_api(reply)
            if tts:
                st.session_state["ch9_tts_bytes"] = tts
            else:
                st.warning("Voice generation failed — text response shown above.")
        st.session_state["ch9_generating"] = False
        st.rerun()

    st.markdown("---")

    can_finish = student_count >= 1
    if not can_finish:
        st.caption("Send at least one response before requesting feedback.")

    if st.button(
        "Finish & get feedback",
        disabled=not can_finish,
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Generating your scorecard — this may take 20–30 seconds…"):
            data = call_coach_api(
                messages,
                st.session_state["ch9_student_name"],
                scenario,
            )
        st.session_state["ch9_scorecard"] = data
        st.session_state["ch9_phase"] = "scorecard"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 3 — Scorecard
# ---------------------------------------------------------------------------

def screen_scorecard() -> None:
    data: dict = st.session_state["ch9_scorecard"]
    scenario: str = st.session_state["ch9_scenario"]
    student_name: str = st.session_state["ch9_student_name"]
    s = SCENARIOS[scenario]

    dimensions: list = data.get("dimensions", [])
    total: int = sum(d["score"] for d in dimensions)
    max_total: int = sum(d["max_points"] for d in dimensions) or 100

    if total >= 90:
        tier, tier_color = "Deal-ready", "#27AE60"
    elif total >= 75:
        tier, tier_color = "Strong Foundation", "#2E86AB"
    elif total >= 60:
        tier, tier_color = "Developing", "#F39C12"
    else:
        tier, tier_color = "Rerun Recommended", "#E74C3C"

    st.title("Scorecard — Objections, Negotiation & Closing")
    st.markdown("---")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Student", student_name)
    with col_b:
        st.metric("Scenario", s["buyer_name"])
    with col_c:
        st.metric("Date", str(date.today()))

    st.markdown("")

    # Plain English summary
    if data.get("plain_english_summary"):
        st.info(data["plain_english_summary"])

    # Total score banner
    st.markdown(
        f"""
        <div style="background:{tier_color}22; border:2px solid {tier_color};
             border-radius:12px; padding:1.5rem; text-align:center; margin-bottom:1.5rem;">
          <div style="font-size:3rem; font-weight:800; color:{tier_color};">
            {total} / {max_total}
          </div>
          <div style="font-size:1.4rem; font-weight:700; color:{tier_color}; margin-top:0.25rem;">
            {tier}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Performance tier guide", expanded=False):
        st.markdown(
            "| Score | Tier |\n"
            "|-------|------|\n"
            "| 90–100 | Deal-ready |\n"
            "| 75–89 | Strong Foundation |\n"
            "| 60–74 | Developing |\n"
            "| Below 60 | Rerun Recommended |"
        )

    st.markdown("### Dimension Breakdown")

    for dim in dimensions:
        pct = dim["score"] / dim["max_points"]
        with st.expander(
            f"**{dim['name']}** — {dim['score']} / {dim['max_points']} pts",
            expanded=True,
        ):
            st.progress(pct)
            st.markdown(dim["rationale"])
            evidence = dim.get("evidence", "")
            no_evidence = (
                not evidence
                or evidence.startswith("Student did not")
                or evidence.startswith("No close")
            )
            if not no_evidence:
                st.markdown(
                    f'<div style="background:#1A2332; border-left:3px solid #4A90D9; '
                    f'padding:0.6rem 1rem; border-radius:4px; font-style:italic; '
                    f'margin-top:0.5rem; font-size:0.92rem;">'
                    f'Evidence: &#8220;{evidence}&#8221;</div>',
                    unsafe_allow_html=True,
                )
            elif evidence:
                st.caption(f"Note: {evidence}")

            if pct < 0.7:
                if not no_evidence:
                    st.warning(
                        f"**Coaching note:** {dim['rationale']}\n\n"
                        f"*From your session: \"{evidence}\"*"
                    )
                else:
                    st.warning(f"**Coaching note:** {dim['rationale']}")

    # Process insight as 6th expander
    if data.get("process_insight"):
        with st.expander("**🔍 Process Insight — what this reveals about your discovery**", expanded=True):
            st.markdown(data["process_insight"])

    st.markdown("---")

    col_strong, col_gap = st.columns(2)
    with col_strong:
        st.success(f"**Strongest moment**\n\n{data.get('strongest_moment', '')}")
    with col_gap:
        st.error(f"**Critical gap**\n\n{data.get('critical_gap', '')}")

    st.info(f"**Behavioral recommendation**\n\n{data.get('behavioral_recommendation', '')}")

    st.markdown("---")

    if st.button("↩ Restart with a different scenario", use_container_width=True):
        _reset_state()
        st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_chapter9() -> None:
    _init_state()
    phase = st.session_state["ch9_phase"]
    if phase == "setup":
        screen_setup()
    elif phase == "chat":
        screen_chat()
    elif phase == "scorecard":
        screen_scorecard()
