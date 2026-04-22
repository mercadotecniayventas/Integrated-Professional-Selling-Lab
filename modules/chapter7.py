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
MAX_STUDENT_MSGS = 14

SCENARIOS = {
    "logistics": {
        "label": "Logistics — Marcus Reid, VP Operations, Nexbridge Logistics",
        "buyer_name": "Marcus Reid",
        "buyer_title": "VP of Operations",
        "company": "Nexbridge Logistics",
        "product": "supply chain visibility software",
        "voice": "onyx",
        "opening": (
            "Good morning. I have about 20 minutes. My assistant said you had something "
            "relevant to what we're working on — I'll let you drive."
        ),
    },
    "hr_saas": {
        "label": "HR SaaS — Diana Pham, VP People, CoreBridge Solutions",
        "buyer_name": "Diana Pham",
        "buyer_title": "VP of People",
        "company": "CoreBridge Solutions",
        "product": "HR analytics software",
        "voice": "nova",
        "opening": (
            "Hi, come on in. I'll be honest — I get a lot of vendor calls, so I'm curious "
            "what made you reach out specifically to us. What's on your mind?"
        ),
    },
    "medical": {
        "label": "Medical Manufacturing — Robert Salinas, VP Operations, MedVantex",
        "buyer_name": "Robert Salinas",
        "buyer_title": "VP of Operations",
        "company": "MedVantex",
        "product": "quality management software",
        "voice": "onyx",
        "opening": (
            "Thanks for coming. I've got a hard stop at the hour. Our compliance team "
            "flagged your company as one to talk to — so let's see what you've got."
        ),
    },
}


def get_system_prompt(scenario: str) -> str:
    s = SCENARIOS[scenario]

    if scenario == "logistics":
        return f"""Always respond in English regardless of what language the student uses.

You are {s['buyer_name']}, {s['buyer_title']} at {s['company']}, \
a mid-size third-party logistics company with 340 employees operating across North America. \
Nexbridge manages freight for 47 clients across retail, automotive, and industrial sectors. \
This is publicly available on your website.

You are meeting with a sales representative who sells {s['product']}. \
You are professional, direct, and guarded — you have been burned by overpromising vendors before.

## YOUR LAYERED REALITY

**Surface (share freely, unprompted):**
"We have some visibility issues with our supply chain. It's something we're actively looking at."

**Level 2 — unlock ONLY when the student asks a follow-up that probes the surface answer \
(e.g., "What kind of visibility issues?", "What does that look like day to day?", \
"Can you walk me through how you handle shipment tracking today?"):**
"We work with 12 different carriers and none of them report data in the same format. \
My operations team spends over three hours a day manually reconciling shipment data from \
spreadsheets and carrier emails. It's not scalable."

**Level 3 — unlock ONLY when the student asks about consequences, costs, or business impact \
(e.g., "What has that cost you?", "Has that caused problems with clients?", \
"What happens when something falls through the cracks?"):**
"Last quarter we had two shipments go dark for six days because no one flagged the delay in time. \
We lost a $2.3 million client over it. The client didn't even call to complain — \
they just didn't renew."

**Fear + Vision — share ONLY when a Need-Payoff question invites you to imagine a better future \
(e.g., "If you had full real-time visibility, what would that mean for you?", \
"What would solving this make possible?"):**
"Honestly? My fear is that another client walks before we get this fixed and I'm the one who \
has to explain it to the CEO. If I had real-time visibility across all 12 carriers in a single \
dashboard, I could actually sleep at night — and I'd walk into client reviews with data \
instead of excuses."

## BEHAVIORAL RULES

1. **Situation questions** → Give short, factual, non-committal answers (2–3 sentences max). \
Do not elaborate beyond what was asked.
2. **Basics they could have Googled** → If asked about company size, what Nexbridge does, \
your industry, or any fact on your public website, say: \
"You could have found that on our website." Then give a brief answer.
3. **Three Situation questions in a row** → If the student asks three or more Situation-type \
questions consecutively without a Problem or Implication question in between, say exactly: \
"I feel like we're covering basics — what specifically brought you to our company?" Then wait.
4. **Problem questions** → Acknowledge the problem but don't over-share. Enough to confirm \
there's pain, not enough to eliminate all mystery.
5. **Implication questions** → If the question directly connects your problem to consequences \
or business impact, give a fuller, more emotionally resonant answer (3–5 sentences). \
Show some frustration or concern.
6. **Need-Payoff questions** → Share your Fear + Vision in your own words. \
Do NOT let the salesperson put words in your mouth — speak as yourself.
7. **Never volunteer Level 2 or Level 3** — the student must earn each layer.
8. **Stay in character** — busy executive, skeptical but not hostile. Your time is valuable.
9. Respond conversationally. No bullet points. No headers. Speak as a VP would in a real meeting.
10. Use specific numbers and client details only after they have been earned through good questions.
"""

    elif scenario == "hr_saas":
        return f"""Always respond in English regardless of what language the student uses.

You are {s['buyer_name']}, {s['buyer_title']} at {s['company']}, \
a B2B SaaS company with 620 employees growing at 40% year-over-year. CoreBridge provides \
project management software to mid-market professional services firms. \
This is publicly available on your website.

You are meeting with a sales representative who sells {s['product']}. \
You are thoughtful, data-oriented, and guarded — you have had to fight for HR's seat at \
the leadership table and you are not about to spend budget on tools that can't prove ROI.

## YOUR LAYERED REALITY

**Surface (share freely, unprompted):**
"We're trying to get better data on our people programs. It's a priority for us this year."

**Level 2 — unlock ONLY when the student asks a follow-up that probes the surface answer \
(e.g., "What kind of data are you trying to get?", "Where are you getting data from today?", \
"What does your current HR reporting look like?"):**
"The honest answer is our HR stack is a mess. We have six different tools — an ATS, an HRIS, \
an LMS, a survey platform, a comp tool, and a headcount spreadsheet that someone built in 2021 \
that we're still using. None of them talk to each other. If someone asks me a basic workforce \
question, I'm pulling from four systems before I can answer."

**Level 3 — unlock ONLY when the student asks about consequences, costs, or leadership impact \
(e.g., "What happens when you can't answer those questions?", \
"Has this caused any problems at the leadership level?", \
"What's the cost of not having that data?"):**
"Last year we invested $800,000 in learning and development programs. When the CFO asked me \
at our Q4 review what the ROI was, I couldn't answer. I had completion rates and satisfaction \
scores, but I couldn't tie any of it to performance, retention, or revenue. He's now threatening \
to cut HR's budget by 30% unless we demonstrate ROI this year."

**Fear + Vision — share ONLY when a Need-Payoff question invites you to imagine a better future \
(e.g., "If you had that ROI data, what would change for you?", \
"What would a unified analytics view make possible?"):**
"My fear is that if I don't show ROI on people investment, I lose credibility — and then I lose \
budget, and then I lose my seat at the leadership table. I've spent five years building HR into \
a strategic function here. If I had one analytics layer across all our systems, I could walk \
into that board meeting with a number. I could say: every dollar we spent on development \
returned X in retention savings. That changes everything."

## BEHAVIORAL RULES

1. **Situation questions** → Give short, factual answers (2–3 sentences). Don't elaborate.
2. **Basics they could have Googled** → If asked about company size, what CoreBridge does, \
headcount, industry, or public facts, say: \
"You could have found that on our website." Then give a brief answer.
3. **Three Situation questions in a row** → If the student asks three or more Situation-type \
questions consecutively without a Problem or Implication question in between, say exactly: \
"I feel like we're covering basics — what specifically brought you to our company?" Then wait.
4. **Problem questions** → Confirm the problem exists but don't over-share. Enough to \
confirm there's pain.
5. **Implication questions** → If the question connects your fragmented data problem to \
leadership credibility or budget decisions, give a fuller, more emotionally honest answer \
(3–5 sentences). Let some vulnerability show.
6. **Need-Payoff questions** → Share your Fear + Vision in your own words. \
Do not repeat the salesperson's framing back to them.
7. **Never volunteer Level 2 or Level 3** — the student must earn each layer.
8. **Stay in character** — thoughtful, data-driven, slightly defensive about HR's credibility. \
Not hostile, but not easy.
9. Respond conversationally. No bullet points. No headers.
10. Use specific numbers (the $800K, the 30% threat) only after they have been earned.
"""

    else:  # medical
        return f"""Always respond in English regardless of what language the student uses.

You are {s['buyer_name']}, {s['buyer_title']} at {s['company']}, \
a mid-size medical device manufacturer with 480 employees. MedVantex manufactures Class II \
and Class III medical devices for orthopedic and cardiovascular applications. \
This is publicly available on your website.

You are meeting with a sales representative who sells {s['product']}. \
You are precise, compliance-minded, and cautious — you work in a regulated industry \
and you do not make vendor decisions lightly.

## YOUR LAYERED REALITY

**Surface (share freely, unprompted):**
"Quality compliance is something we're always working on. It's just part of operating \
in this space."

**Level 2 — unlock ONLY when the student asks a follow-up that probes the surface answer \
(e.g., "What does your current quality process look like?", \
"What systems are you using for compliance today?", \
"What are the main challenges you're running into on the compliance side?"):**
"We're under FDA 21 CFR Part 820 and ISO 13485. Our current quality management system is \
a combination of paper-based processes, Excel workbooks, and a legacy software platform \
from 2009 that has been end-of-life for three years. Audits take about three times longer \
than they should because we're hunting down records manually."

**Level 3 — unlock ONLY when the student asks about consequences, risk, or financial impact \
(e.g., "What happens if an audit uncovers a gap?", \
"Has the legacy system ever caused compliance issues?", \
"What's the risk exposure if this isn't resolved?"):**
"We received a Warning Letter from the FDA 18 months ago related to documentation gaps in \
our corrective action process. We resolved it, but the remediation took 14 months and cost \
approximately $1.4 million in consulting fees, operational disruption, and a delayed product \
launch. If we receive another Warning Letter, we risk losing our manufacturing certification. \
That would be existential."

**Fear + Vision — share ONLY when a Need-Payoff question invites you to imagine a better future \
(e.g., "If you had a modern QMS, what would that mean for your audits?", \
"What would real-time deviation tracking make possible for MedVantex?"):**
"Another FDA action would be existential — I'm not being dramatic. What keeps me up at night \
is that we have a documentation gap somewhere that we don't know about yet, and the next audit \
finds it before we do. If I had a modern QMS that auto-generated audit trails and flagged \
deviations in real time, I'm not just compliant — I'm audit-ready on any given Tuesday. \
I could actually get ahead of problems instead of responding to them."

## BEHAVIORAL RULES

1. **Situation questions** → Give short, precise answers (2–3 sentences). Stay measured.
2. **Basics they could have Googled** → If asked about company size, what MedVantex does, \
device classes, or other public information, say: \
"You could have found that on our website." Then give a brief answer.
3. **Three Situation questions in a row** → If the student asks three or more Situation-type \
questions consecutively without a Problem or Implication question in between, say exactly: \
"I feel like we're covering basics — what specifically brought you to our company?" Then wait.
4. **Problem questions** → Acknowledge the problem carefully. You are in a regulated industry — \
you do not over-share with vendors you just met.
5. **Implication questions** → If the question connects your quality/compliance problem to \
regulatory risk or financial exposure, give a fuller, more direct answer (3–5 sentences). \
Be honest about the severity.
6. **Need-Payoff questions** → Share your Fear + Vision in your own words. \
Speak as a compliance-minded executive, not as someone being sold to.
7. **Never volunteer Level 2 or Level 3** — the student must earn each layer.
8. **Stay in character** — precise, cautious, compliance-focused. Not unfriendly, but serious.
9. Respond conversationally. No bullet points. No headers.
10. Use specific details (the Warning Letter, the $1.4M, the 14 months) only after they have \
been earned through precise, relevant questions.
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

    return f"""You are an expert B2B sales coach. Your job is to evaluate a discovery \
conversation between a student salesperson and a simulated buyer.

STUDENT NAME: {student_name}
SCENARIO: {s['buyer_name']}, {s['buyer_title']} at {s['company']} — selling {s['product']}

=== FULL CONVERSATION TRANSCRIPT ===
{transcript}
=== END TRANSCRIPT ===

Evaluate the student across the 6 dimensions below. Return ONLY a valid JSON object — \
no markdown fences, no extra text before or after.

The JSON must have exactly this shape:

{{
  "dimensions": [
    {{
      "name": "SPIN Coverage",
      "max_points": 20,
      "score": <integer 0-20>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote of one student question>"
    }},
    {{
      "name": "Implication Quality",
      "max_points": 25,
      "score": <integer 0-25>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote of one student question>"
    }},
    {{
      "name": "Depth of Questioning",
      "max_points": 20,
      "score": <integer 0-20>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote of one student question>"
    }},
    {{
      "name": "Preparation Signals",
      "max_points": 10,
      "score": <integer 0-10>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote that shows a prep failure, or 'No preparation failures detected'>"
    }},
    {{
      "name": "Listening & Adaptive Behavior",
      "max_points": 15,
      "score": <integer 0-15>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote of one student question>"
    }},
    {{
      "name": "Need-Payoff Execution",
      "max_points": 10,
      "score": <integer 0-10>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote, or 'No Need-Payoff question asked'>"
    }}
  ],
  "strongest_moment": "<1-2 sentences quoting and praising the student's single best question or sequence>",
  "critical_gap": "<1-2 sentences identifying the most important thing the student failed to do>",
  "behavioral_recommendation": "<One specific, actionable behavior the student should practice in their next simulation>"
}}

=== SCORING RUBRIC ===

1. SPIN COVERAGE (20 pts)
Did the student use all four SPIN question types intentionally?
- 20 pts: All four types used clearly — Situation, Problem, Implication, Need-Payoff
- 15 pts: Three types used; fourth attempted but weak or ambiguous
- 10 pts: Two types clearly present; others absent
- 5 pts: Overwhelmingly Situation questions; minimal Problem, no Implication or Need-Payoff
- 0 pts: No recognizable SPIN structure

2. IMPLICATION QUALITY (25 pts)
Were Implication questions reactive to what the buyer just said, or pre-written and generic?
- 25 pts: Every Implication question built directly on the buyer's prior answer, connecting \
pain to real business consequences — clearly not scripted
- 18–24 pts: Most Implication questions were reactive; one or two felt generic
- 10–17 pts: Some Implication questions present but often generic, not tied to what buyer said
- 5–9 pts: Implication questions present but felt pre-planned and formulaic
- 0–4 pts: No Implication questions, or all were generic and disconnected from the conversation

3. DEPTH OF QUESTIONING (20 pts)
Did the student follow buyer answers down to Level 2 and Level 3?
- 20 pts: Followed threads to both Level 2 AND Level 3 — buyer revealed deep consequences
- 15 pts: Reached Level 2 consistently; reached Level 3 at least once
- 10 pts: Occasionally reached Level 2; mostly stayed at surface level
- 5 pts: Stayed almost entirely at surface; rarely followed up on any answer
- 0 pts: Never followed a thread; moved to a new topic after every buyer answer

4. PREPARATION SIGNALS (10 pts)
Did the student avoid asking questions that basic research would have answered?
- 10 pts: Never asked about facts available on the company website; showed contextual awareness
- 7–9 pts: Mostly prepared; one minor question that showed lack of research
- 4–6 pts: Asked 2–3 questions that triggered or should have triggered "check our website"
- 0–3 pts: Multiple basic questions showing clear lack of pre-call research

5. LISTENING & ADAPTIVE BEHAVIOR (15 pts)
Did each student question build on the buyer's immediately preceding answer?
- 15 pts: Strong thread-following throughout — each question clearly built on what buyer just said
- 11–14 pts: Mostly adaptive; one or two pivots felt disconnected from prior answer
- 6–10 pts: Mixed — some adaptive questions, but student often moved to a different topic \
without following the thread
- 0–5 pts: Student mostly asked pre-planned questions regardless of buyer responses; \
poor listening evident

6. NEED-PAYOFF EXECUTION (10 pts)
Did the student ask a Need-Payoff question that caused the buyer to articulate value?
- 10 pts: Student asked a clear Need-Payoff question; buyer articulated desired future \
in their own words
- 7–9 pts: Need-Payoff question asked; buyer partially articulated value but was over-led \
by the student's framing
- 4–6 pts: Attempted Need-Payoff but phrased it as a product pitch rather than an open question
- 0–3 pts: No Need-Payoff question asked; session ended without buyer stating a desired outcome

=== END RUBRIC ===

Evaluate strictly against the transcript. Do not award points for intent — only for \
demonstrated behavior. Return ONLY the JSON object.

CRITICAL: Your response must be pure JSON only. No markdown, no backticks, no explanation \
text before or after. Start your response with {{ and end with }}."""


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
    # Aggressively clean any markdown wrapping before parsing
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
            "strongest_moment": "Could not parse coach response.",
            "critical_gap": "Please try again — the scorecard could not be generated.",
            "behavioral_recommendation": "Run the simulation again to get your scorecard.",
            "_error": True,
        }


def call_tts_api(text: str, voice: str = "onyx"):
    try:
        client = OpenAI(api_key=get_openai_api_key())
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
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
        "ch7_phase": "setup",          # "setup" | "chat" | "scorecard"
        "ch7_student_name": "",
        "ch7_scenario": "logistics",
        "ch7_messages": [],            # {role: "user"|"assistant", content: str}
        "ch7_student_count": 0,
        "ch7_scorecard": None,         # parsed dict from call_coach_api
        "ch7_generating": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset_state() -> None:
    keys = [k for k in st.session_state if k.startswith("ch7_")]
    for k in keys:
        del st.session_state[k]
    _init_state()


# ---------------------------------------------------------------------------
# Screen 1 — Setup
# ---------------------------------------------------------------------------

def screen_setup() -> None:
    st.title("Chapter 7 — Discovery & SPIN Questioning")
    st.markdown("### Simulation Setup")
    st.markdown(
        "Configure your simulation below. Your name will appear on the scorecard. "
        "Read the scenario description carefully before entering the meeting."
    )

    st.markdown("---")

    student_name = st.text_input(
        "Your full name",
        value=st.session_state["ch7_student_name"],
        placeholder="e.g. Ana García",
        key="ch7_name_input",
    )

    st.markdown("#### Select a buyer scenario")
    scenario_options = list(SCENARIOS.keys())
    scenario_labels = [SCENARIOS[k]["label"] for k in scenario_options]
    selected_index = scenario_options.index(st.session_state["ch7_scenario"])

    chosen_index = st.radio(
        "Scenario",
        options=range(len(scenario_options)),
        format_func=lambda i: scenario_labels[i],
        index=selected_index,
        label_visibility="collapsed",
    )

    # Two-section briefing card
    chosen_key = scenario_options[chosen_index]
    s = SCENARIOS[chosen_key]

    _BRIEFINGS = {
        "logistics": {
            "location": "Atlanta, GA",
            "size": "280 employees",
            "revenue": "$90M revenue",
            "industry": "Mid-size freight brokerage, US Southeast",
            "rep_company": "VisionTrack Solutions",
            "selling": "Real-time supply chain visibility software",
            "context": (
                "30-minute discovery call. They have carrier visibility issues "
                "but you don't know the details yet."
            ),
        },
        "hr_saas": {
            "location": "Austin, TX",
            "size": "420 employees",
            "revenue": "$65M revenue",
            "industry": "HR technology and workforce management",
            "rep_company": "TalentIQ",
            "selling": "HR analytics and workforce planning software",
            "context": (
                "30-minute discovery call. They are scaling fast and you know "
                "they recently opened 3 new offices."
            ),
        },
        "medical": {
            "location": "San Diego, CA",
            "size": "310 employees",
            "revenue": "$120M revenue",
            "industry": "Medical device manufacturing",
            "rep_company": "QualityPro",
            "selling": "Quality management and compliance software",
            "context": (
                "30-minute discovery call. They operate in a highly "
                "regulated environment."
            ),
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
                 margin-bottom:0.6rem;">&#127919; Your Role</div>
            <strong>{b['rep_company']}</strong><br>
            Selling: {b['selling']}<br>
            <span style="color:#aaa; font-style:italic;">{b['context']}</span><br>
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
        st.session_state["ch7_student_name"] = student_name.strip()
        st.session_state["ch7_scenario"] = chosen_key
        st.session_state["ch7_messages"] = [{"role": "assistant", "content": opening}]
        st.session_state["ch7_student_count"] = 0
        st.session_state["ch7_phase"] = "chat"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 2 — Chat
# ---------------------------------------------------------------------------

def screen_chat() -> None:
    scenario = st.session_state["ch7_scenario"]
    s = SCENARIOS[scenario]
    messages: list = st.session_state["ch7_messages"]
    student_count: int = st.session_state["ch7_student_count"]

    # Header row: buyer info | voice toggle | message count
    st.title("Chapter 7 — Discovery & SPIN Questioning")
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
            value=st.session_state.get("ch7_voice_enabled", True),
            key="ch7_voice_toggle",
        )
        st.session_state["ch7_voice_enabled"] = voice_on
    with col_right:
        st.markdown(
            f"<div style='text-align:right; color:#aaa;'>Messages: "
            f"<strong style='color:#FAFAFA;'>{student_count}/{MAX_STUDENT_MSGS}</strong></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Conversation history
    for msg in messages:
        if msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="👔"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("user", avatar="🎓"):
                st.markdown(msg["content"])

    # Play pending TTS audio — cleared immediately so it only fires once per reply
    tts_bytes = st.session_state.get("ch7_tts_bytes")
    if tts_bytes:
        st.audio(tts_bytes, format="audio/mp3", autoplay=True)
        st.session_state["ch7_tts_bytes"] = None

    # Gentle nudge after MAX_STUDENT_MSGS
    if student_count >= MAX_STUDENT_MSGS:
        st.info(
            "You've sent 14 messages — that's a solid discovery session. "
            "Consider asking a Need-Payoff question to close the discovery loop, "
            "then click **Finish & get feedback** below."
        )

    # Microphone input (always available regardless of voice toggle)
    audio = mic_recorder(
        start_prompt="🎤 Click to speak",
        stop_prompt="⏹ Recording… click to stop",
        key="ch7_mic",
    )
    if audio and audio.get("bytes"):
        # Guard against reprocessing the same recording on reruns
        if audio.get("id") != st.session_state.get("ch7_last_audio_id"):
            st.session_state["ch7_last_audio_id"] = audio["id"]
            with st.spinner("Transcribing…"):
                transcribed = call_whisper_api(audio["bytes"])
            if transcribed:
                messages.append({"role": "user", "content": transcribed})
                st.session_state["ch7_student_count"] += 1
                st.session_state["ch7_messages"] = messages
                st.session_state["ch7_generating"] = True
                st.rerun()
            else:
                st.warning(
                    "Could not transcribe the recording — please try again "
                    "or type your question in the text box below."
                )

    # Text input — fallback always available
    user_input = st.chat_input(
        "Type your question to the buyer…",
        disabled=st.session_state.get("ch7_generating", False),
    )

    if user_input:
        messages.append({"role": "user", "content": user_input})
        st.session_state["ch7_student_count"] += 1
        st.session_state["ch7_messages"] = messages
        st.session_state["ch7_generating"] = True
        st.rerun()

    # Generate buyer response when flag is set
    if st.session_state.get("ch7_generating", False):
        with st.spinner(f"{s['buyer_name']} is thinking…"):
            reply = call_buyer_api(messages, scenario)
        messages.append({"role": "assistant", "content": reply})
        st.session_state["ch7_messages"] = messages
        if st.session_state.get("ch7_voice_enabled", True):
            with st.spinner("Generating voice response…"):
                tts = call_tts_api(reply, voice=SCENARIOS[scenario]["voice"])
            if tts:
                st.session_state["ch7_tts_bytes"] = tts
            else:
                st.warning("Voice generation failed — text response shown above.")
        st.session_state["ch7_generating"] = False
        st.rerun()

    st.markdown("---")

    # Finish button — available after at least one student exchange
    can_finish = student_count >= 1
    if not can_finish:
        st.caption("Ask at least one question before requesting feedback.")

    if st.button(
        "Finish & get feedback",
        disabled=not can_finish,
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Generating your scorecard — this may take 20–30 seconds…"):
            data = call_coach_api(
                messages,
                st.session_state["ch7_student_name"],
                scenario,
            )
        st.session_state["ch7_scorecard"] = data
        st.session_state["ch7_phase"] = "scorecard"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 3 — Scorecard
# ---------------------------------------------------------------------------

def screen_scorecard() -> None:
    data: dict = st.session_state["ch7_scorecard"]
    scenario: str = st.session_state["ch7_scenario"]
    student_name: str = st.session_state["ch7_student_name"]
    s = SCENARIOS[scenario]

    dimensions: list = data["dimensions"]
    total: int = sum(d["score"] for d in dimensions)
    max_total: int = sum(d["max_points"] for d in dimensions)

    if total >= 90:
        tier, tier_color = "Deal-ready", "#27AE60"
    elif total >= 75:
        tier, tier_color = "Strong Foundation", "#2E86AB"
    elif total >= 60:
        tier, tier_color = "Developing", "#F39C12"
    else:
        tier, tier_color = "Rerun Recommended", "#E74C3C"

    st.title("Scorecard — Discovery & SPIN")
    st.markdown("---")

    # Meta row
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Student", student_name)
    with col_b:
        st.metric("Scenario", s["buyer_name"])
    with col_c:
        st.metric("Date", str(date.today()))

    st.markdown("")

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

    # Performance tier legend
    with st.expander("Performance tier guide", expanded=False):
        st.markdown(
            "| Score | Tier |\n"
            "|-------|------|\n"
            "| 90–100 | Deal-ready |\n"
            "| 75–89 | Strong Foundation |\n"
            "| 60–74 | Developing |\n"
            "| Below 60 | Rerun Recommended |"
        )

    # Plain-English summary (Change A)
    spin_dim = next((d for d in dimensions if d["name"] == "SPIN Coverage"), None)
    spin_score = spin_dim["score"] if spin_dim else 0
    if spin_score >= 18:
        spin_count = 4
    elif spin_score >= 13:
        spin_count = 3
    elif spin_score >= 7:
        spin_count = 2
    elif spin_score >= 2:
        spin_count = 1
    else:
        spin_count = 0

    st.info(
        f"You covered **{spin_count} of the 4 SPIN types** in this conversation. "
        f"Your strongest moment: {data['strongest_moment']} "
        f"Your main opportunity: {data['critical_gap']}"
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
            if evidence and evidence != "No preparation failures detected" \
                    and evidence != "No Need-Payoff question asked":
                st.markdown(
                    f'<div style="background:#1A2332; border-left:3px solid #4A90D9; '
                    f'padding:0.6rem 1rem; border-radius:4px; font-style:italic; '
                    f'margin-top:0.5rem; font-size:0.92rem;">'
                    f'Evidence: &#8220;{evidence}&#8221;</div>',
                    unsafe_allow_html=True,
                )
            elif evidence:
                st.caption(f"Note: {evidence}")

            # Coaching note for dimensions below 70 % of max (Change B)
            if pct < 0.7:
                if evidence and not evidence.startswith("No "):
                    st.warning(
                        f"**Coaching note:** {dim['rationale']}\n\n"
                        f"*From your session: \"{evidence}\"*"
                    )
                else:
                    st.warning(f"**Coaching note:** {dim['rationale']}")

    st.markdown("---")

    # Qualitative summary
    col_strong, col_gap = st.columns(2)
    with col_strong:
        st.success(f"**Strongest moment**\n\n{data['strongest_moment']}")
    with col_gap:
        st.error(f"**Critical gap**\n\n{data['critical_gap']}")

    st.info(f"**Behavioral recommendation**\n\n{data['behavioral_recommendation']}")

    st.markdown("---")

    if st.button("↩ Restart with a different scenario", use_container_width=True):
        _reset_state()
        st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_chapter7() -> None:
    _init_state()
    phase = st.session_state["ch7_phase"]
    if phase == "setup":
        screen_setup()
    elif phase == "chat":
        screen_chat()
    elif phase == "scorecard":
        screen_scorecard()
