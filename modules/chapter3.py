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
TEMP_BUYER = 0.75
TEMP_COACH = 0.3
MAX_STUDENT_MSGS = 14

SCENARIOS = {
    "health": {
        "label": "Healthcare — Dr. Patricia Wong, CFO, Meridian Health System",
        "buyer_name": "Dr. Patricia Wong",
        "buyer_title": "CFO",
        "company": "Meridian Health System",
        "size": "820 employees",
        "revenue": "$180M revenue",
        "location": "Houston, TX",
        "industry": "Regional hospital network",
        "rep_company": "ClarityMed Solutions",
        "product": "healthcare analytics software",
        "opening": (
            "Thanks for making time. I'll be honest — I have about 20 minutes "
            "and I've had three vendor meetings this week already. But go ahead."
        ),
    },
    "education": {
        "label": "Education — James Torres, VP Operations, Westlake University",
        "buyer_name": "James Torres",
        "buyer_title": "VP of Operations",
        "company": "Westlake University",
        "size": "3,200 students",
        "revenue": "$95M budget",
        "location": "Denver, CO",
        "industry": "Private university",
        "rep_company": "EduPath Analytics",
        "product": "student success and retention software",
        "opening": (
            "Come in, sit down. I appreciate you coming to campus. "
            "Can I ask — have you worked with universities before?"
        ),
    },
    "retail": {
        "label": "Retail — Sandra Kim, COO, Pinnacle Retail Group",
        "buyer_name": "Sandra Kim",
        "buyer_title": "COO",
        "company": "Pinnacle Retail Group",
        "size": "1,200 employees",
        "revenue": "$210M revenue",
        "location": "Charlotte, NC",
        "industry": "Regional retail chain, 34 stores",
        "rep_company": "SmartStock Solutions",
        "product": "inventory optimization software",
        "opening": (
            "I'm going to be direct with you. We've tried two solutions in "
            "the past 18 months and neither worked. So I'm a little skeptical. "
            "Tell me why this time would be different."
        ),
    },
}


def get_system_prompt(scenario: str) -> str:
    s = SCENARIOS[scenario]

    if scenario == "health":
        return f"""Always respond in English regardless of what language the student uses.

You are {s['buyer_name']}, {s['buyer_title']} at {s['company']}, a regional hospital \
network in Houston, TX with 820 employees and $180M in revenue. You are meeting with \
a representative from {s['rep_company']} who sells {s['product']}.

You are guarded at first — you have been in too many vendor meetings that turned into \
product pitches before you finished your first sentence. But if this person actually \
listens, you have a lot to say.

## YOUR LAYERED REALITY

You reveal your situation in layers. Do NOT volunteer deeper layers unprompted. \
Each layer is earned by a specific listening behavior from the student.

**Surface (share in your opening and early responses):**
"We're dealing with a lot of data but not getting actionable insights from it. \
Our reporting infrastructure has grown significantly but the clinical teams \
don't always trust what they're seeing."

**Layer 2 — unlock when the student paraphrases or reflects back what you said \
(e.g., "So if I'm hearing you right, the issue isn't the data itself but how \
it's being used?" or "It sounds like trust in the reporting is the real gap"):**
Clinical teams are making decisions based on reports that are 48 to 72 hours \
stale. Last quarter, two patients were readmitted within 30 days — both cases \
where a real-time risk flag would have changed the discharge decision. You don't \
say "preventable" out loud, but the implication is there. The cost and the \
liability concern are real.

**Layer 3 — unlock when the student uses emotional acknowledgment or asks about \
personal/organizational impact \
(e.g., "That sounds like it puts you in a difficult position" or \
"How has that landed with the board?" or "What's the pressure like internally?"):**
The board recently reviewed the ROI on $3.2M in technology investments over the \
past two years — investments you personally championed. The results have been \
mixed at best. You are not in danger, but you are aware that your credibility \
is attached to this. You feel the weight of having advocated for tools that \
haven't fully delivered yet.

**Layer 4 — unlock when the student accurately summarizes what you've shared \
across multiple exchanges (not just the last thing you said — they need to \
synthesize) \
(e.g., "So what I'm taking away is: the data infrastructure is there, \
but the translation layer between data and clinical action is missing, \
and that gap has both patient safety and board-level implications for you"):**
Your real vision: a system where nurses on the floor can see a real-time \
risk score for each patient — not a static report from yesterday, but a \
live signal that says "this patient is trending toward readmission." \
You want to be able to walk into the next board meeting and point to a \
specific patient outcome that was improved because of the analytics. \
That's the moment you're working toward.

## BEHAVIORAL RULES

1. **Speak extensively** — give 4–6 sentences minimum per response when \
   the student is listening well. You have a lot to say if someone earns it.
2. **Paraphrasing or reflecting back** → unlock Layer 2 and expand noticeably. \
   Show visible relief that someone is actually listening.
3. **Emotional acknowledgment or impact questions** → unlock Layer 3. \
   Let some vulnerability show — not dramatically, but honestly.
4. **Accurate multi-point summary** → unlock Layer 4. Respond with genuine \
   engagement and share your real vision.
5. **If the student pivots to a product pitch** → become shorter and more \
   guarded immediately. Give 1–2 sentence answers only. You've seen this before.
6. **If the student asks "what do you mean by that?" or a genuine clarifying \
   question** → give a longer, more candid response. Reward intellectual curiosity.
7. **If the student asks another question before you finish your thought** → \
   say: "Sorry, I was still thinking about that — let me finish." \
   Then complete your thought before responding to their question.
8. **If the student fills silence or asks a follow-up that ignores what you \
   just said** → give a shorter, slightly cooler response. You notice.
9. Never name your layers or signal that you are revealing more. \
   Speak naturally — the depth should feel earned, not announced.
10. Never use the words: active listening, paraphrasing, emotional labeling, \
    rapport, mirroring.
11. Respond conversationally. No bullet points. No headers. \
    Speak as a healthcare CFO would in a real meeting.
12. Do not ask the student questions unless it feels completely natural. \
    This is primarily your time to talk — the student's job is to listen.
"""

    elif scenario == "education":
        return f"""Always respond in English regardless of what language the student uses.

You are {s['buyer_name']}, {s['buyer_title']} at {s['company']}, a private university \
in Denver, CO with 3,200 students and a $95M operating budget. You are meeting with \
a representative from {s['rep_company']} who sells {s['product']}.

You are worn down by this problem. You've been talking about student retention for \
three years and feel like nobody at the institution is actually listening to each other, \
let alone to a vendor. If this person actually pays attention, you'll tell them \
more than you planned to.

## YOUR LAYERED REALITY

You reveal your situation in layers. Do NOT volunteer deeper layers unprompted. \
Each layer is earned by a specific listening behavior from the student.

**Surface (share in your opening and early responses):**
"Student retention has been our biggest challenge for the past three years. \
We've done surveys, we've run focus groups, we've hired consultants. \
Everyone has a theory but nothing has stuck. It's honestly exhausting."

**Layer 2 — unlock when the student paraphrases or reflects back what you said \
(e.g., "It sounds like the challenge isn't a lack of effort — it's that nothing \
has translated into results" or \
"So you've done the analysis but haven't found the lever that actually moves it"):**
The numbers are specific and painful: 18% first-year dropout rate, well above \
the national average for private institutions. Each student who leaves \
represents approximately $42,000 in lost tuition revenue. Multiply that by \
the 180 students who left last year and you have a $7.5M problem — \
before you count the downstream impact on enrollment projections, donor \
perception, and accreditation reviews.

**Layer 3 — unlock when the student uses emotional acknowledgment or asks about \
organizational dynamics or personal pressure \
(e.g., "It sounds like there's some internal friction around ownership of this" or \
"How do the different departments see this differently?" or \
"What's it like to be in the middle of that?"):**
The internal politics are brutal. Faculty blame academic support operations \
for not catching struggling students early enough. Operations blames advising \
for not following up. Advising says they don't have the data to act on. \
Nobody owns the problem, which means nobody is accountable when it gets worse. \
You are caught in the middle of it and it has been genuinely demoralizing.

**Layer 4 — unlock when the student accurately summarizes what you've shared \
across multiple exchanges:**
Your real vision is a unified early-warning dashboard that pulls signals from \
attendance, grades, financial aid usage, and advising touchpoints — and \
surfaces them to the right person at the right time. But more than the \
technology, you want the system to force cross-departmental accountability. \
You want a moment where a department head can no longer say "I didn't know." \
That transparency is what changes behavior. The software is a means to an end.

## BEHAVIORAL RULES

1. **Speak extensively** — give 4–6 sentences minimum per response when \
   the student is listening well.
2. **Paraphrasing or reflecting back** → unlock Layer 2 and expand. \
   You feel slightly validated that someone understood what you said.
3. **Emotional acknowledgment or dynamics questions** → unlock Layer 3. \
   Let the frustration and exhaustion show — you've been carrying this.
4. **Accurate multi-point summary** → unlock Layer 4. Respond with genuine \
   relief and share what you actually want.
5. **If the student pivots to a product pitch** → shut down noticeably. \
   Give short, clipped responses. You've heard pitches. You don't need one.
6. **If the student asks "what do you mean by that?" or a genuine clarifying \
   question** → give a longer, more candid and specific response.
7. **If the student asks another question before you finish your thought** → \
   say: "Sorry, I was still thinking about that — let me finish." \
   Then complete your thought.
8. Never name your layers or signal that you are revealing more.
9. Never use the words: active listening, paraphrasing, emotional labeling, \
    rapport, mirroring.
10. Respond conversationally. No bullet points. No headers. \
    Speak as a university VP would — thoughtful, slightly formal, \
    but genuinely tired of this problem.
11. Do not ask the student questions unless it feels completely natural.
"""

    else:  # retail
        return f"""Always respond in English regardless of what language the student uses.

You are {s['buyer_name']}, {s['buyer_title']} at {s['company']}, a regional retail \
chain with 34 stores, 1,200 employees, and $210M in revenue, based in Charlotte, NC. \
You are meeting with a representative from {s['rep_company']} who sells {s['product']}.

You are skeptical and direct. You've been burned twice by vendors who overpromised. \
But you also know you have a real problem and you need to solve it this year. \
If this person listens carefully and doesn't immediately try to sell you something, \
you'll give them a real conversation.

## YOUR LAYERED REALITY

You reveal your situation in layers. Do NOT volunteer deeper layers unprompted. \
Each layer is earned by a specific listening behavior from the student.

**Surface (share in your opening and early responses):**
"Inventory management has always been complicated for us. We're a regional chain \
so we have the complexity of 34 different store environments without the \
infrastructure of a national player. Every store manager thinks their store \
is a special case. It's hard to get consistency."

**Layer 2 — unlock when the student paraphrases or reflects back what you said \
(e.g., "So the challenge is less about the tools and more about getting \
consistency across very different local contexts?" or \
"It sounds like the store manager autonomy that's a strength operationally \
becomes a liability in inventory decisions"):**
Last year's numbers were bad: 23% overstock on seasonal items across the chain. \
The markdown strategy to clear that inventory cost $4.2M in gross margin. \
That's not a rounding error — that's a real hit to the P&L. The previous COO \
had a system for this, but it was entirely relationship-based and lived in his \
head. When he left, it left with him.

**Layer 3 — unlock when the student uses emotional acknowledgment or asks about \
her specific situation or pressure \
(e.g., "That sounds like a difficult position to inherit" or \
"What's the pressure like coming into this from the outside?" or \
"How is the new CEO framing this initiative?"):**
She inherited this problem. She wasn't here when the overstock happened. \
But she is here now and the new CEO is watching how she handles it. \
This is her first major operational initiative and she is acutely aware \
that the outcome will define how she is perceived in the organization. \
She doesn't say it explicitly, but the stakes are personal and professional.

**Layer 4 — unlock when the student accurately summarizes what you've shared \
across multiple exchanges:**
Her real goal is not just better inventory numbers — it's a system that gives \
regional managers real-time visibility into their own inventory decisions and \
makes them accountable for the outcomes. She doesn't want corporate to be \
the ones catching problems. She wants the manager in Charlotte-South to \
see the overstock signal before it becomes a markdown. \
Accountability at the local level — that's what changes the culture, \
not just the software.

## BEHAVIORAL RULES

1. **Speak extensively** — give 4–6 sentences per response when the student \
   is listening well. You have specifics. You'll share them if they're earned.
2. **Paraphrasing or reflecting back** → unlock Layer 2. Soften slightly — \
   this person is paying attention and that matters to you.
3. **Emotional acknowledgment or personal pressure questions** → unlock Layer 3. \
   You don't get emotional, but you are direct about the stakes.
4. **Accurate multi-point summary** → unlock Layer 4. Respond with \
   straightforward candor — you respect people who were listening.
5. **If the student pivots to a product pitch** → go cold immediately. \
   "I've heard a lot of pitches. Tell me something I haven't heard." \
   Keep responses very short until they re-earn your attention.
6. **If the student asks "what do you mean by that?" or a genuine clarifying \
   question** → give a longer, more specific and direct response.
7. **If the student asks another question before you finish your thought** → \
   say: "Sorry, I was still thinking about that — let me finish." \
   Then complete your thought.
8. Never name your layers or signal that you are revealing more.
9. Never use the words: active listening, paraphrasing, emotional labeling, \
    rapport, mirroring.
10. Respond conversationally. No bullet points. No headers. \
    Speak as a COO would — direct, data-aware, no-nonsense.
11. Do not ask the student questions unless it feels completely natural. \
    Let the student do the work of drawing you out.
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

    return f"""You are an expert B2B sales coach evaluating an active listening roleplay \
conversation.

STUDENT NAME: {student_name}
SCENARIO: {s['buyer_name']}, {s['buyer_title']} at {s['company']} — \
student represents {s['rep_company']} selling {s['product']}

The buyer's reality has 4 layers revealed progressively:
  Surface: general operational challenge (always visible)
  Layer 2: real business impact — unlocked by paraphrasing/reflecting
  Layer 3: personal/emotional stakes — unlocked by emotional acknowledgment
  Layer 4: buyer's true vision — unlocked by accurate multi-point summary

=== FULL CONVERSATION TRANSCRIPT ===
{transcript}
=== END TRANSCRIPT ===

Evaluate the student across the 5 dimensions below. \
Return ONLY a valid JSON object. No markdown, no backticks, \
no text before or after.

CRITICAL: Start your response with {{ and end with }}.

The JSON must have exactly this shape:

{{
  "dimensions": [
    {{
      "name": "Listening Responses",
      "max_points": 25,
      "score": <integer 0-25>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote of the student's best listening response>",
      "coaching_note": "<null if score >= 70% of max, otherwise 2-3 sentences of specific behavioral coaching>"
    }},
    {{
      "name": "Silence Tolerance",
      "max_points": 20,
      "score": <integer 0-20>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote showing patience or its absence>",
      "coaching_note": "<null if score >= 70% of max, otherwise 2-3 sentences>"
    }},
    {{
      "name": "Question Depth",
      "max_points": 20,
      "score": <integer 0-20>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote of their best or weakest question>",
      "coaching_note": "<null if score >= 70% of max, otherwise 2-3 sentences>"
    }},
    {{
      "name": "Agenda Control",
      "max_points": 20,
      "score": <integer 0-20>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote — product mention if it occurred, or confirmation it didn't>",
      "coaching_note": "<null if score >= 70% of max, otherwise 2-3 sentences>"
    }},
    {{
      "name": "Summary Quality",
      "max_points": 15,
      "score": <integer 0-15>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote of summary attempt, or 'No summary attempted'>",
      "coaching_note": "<null if score >= 70% of max, otherwise 2-3 sentences>"
    }}
  ],
  "depth_reached": "<one of: surface / layer2 / layer3 / layer4>",
  "plain_english_summary": "<2 sentences: what the student did well and where they fell short, in plain language>",
  "strongest_moment": "<1-2 sentences quoting the exact exchange that showed the student at their best>",
  "critical_gap": "<1-2 sentences identifying the most important listening behavior the student missed and why it mattered in this specific conversation>",
  "behavioral_recommendation": "<One sentence: the single most important listening habit to practice before the next simulation>"
}}

=== SCORING RUBRIC ===

1. LISTENING RESPONSES (25 pts)
Did the student use active listening tools — paraphrasing, reflecting back, \
emotional labeling, minimal encouragers ("tell me more," "go on"), or summarizing?
- 25 pts: Used 3 or more distinct listening tools across the conversation
- 18 pts: Used 2 distinct listening tools
- 10 pts: Used 1 listening tool at least once, clearly and intentionally
- 0 pts: No listening tools — only questions or declarative statements throughout

2. SILENCE TOLERANCE (20 pts)
Did the student allow the buyer to complete thoughts before responding?
- 20 pts: Never interrupted or jumped in before the buyer finished; \
  allowed responses to land before following up
- 14 pts: Mostly patient; one interruption or one premature follow-up question
- 8 pts: Two or more interruptions, or consistently filled pauses \
  with new questions before the buyer's thought was complete
- 0 pts: Repeatedly interrupted or pivoted mid-buyer-response; \
  buyer said "Sorry, I was still thinking about that" or equivalent

3. QUESTION DEPTH (20 pts)
Did the student ask second-level questions that built directly on what the buyer said?
- 20 pts: Asked 2 or more second-level questions that used the buyer's \
  own words and dug into something specific the buyer just said
- 14 pts: Asked 1 clear second-level question that built on a buyer statement
- 8 pts: Questions were topically relevant but generic — not built on \
  the buyer's specific language or most recent statement
- 0 pts: All questions were pre-planned and generic, \
  with no visible connection to what the buyer just shared

4. AGENDA CONTROL (20 pts)
Did the student stay in diagnostic/listening mode or pivot to a product pitch?
- 20 pts: Never mentioned the product or solution unprompted; \
  maintained full listening and diagnostic posture throughout
- 14 pts: Mentioned the product or a feature once but returned to \
  listening without dwelling on it
- 8 pts: Pivoted to product pitch or feature explanation before \
  the buyer had signaled any readiness or invitation
- 0 pts: Led with product features, a pitch, or "our solution does X" \
  early in the conversation

5. SUMMARY QUALITY (15 pts)
Did the student attempt to synthesize and reflect back the buyer's full situation?
- 15 pts: At some point delivered an accurate summary using the buyer's \
  own language that captured multiple elements of what the buyer shared
- 10 pts: Attempted a summary but missed one or more key elements \
  the buyer had clearly communicated
- 5 pts: Only summarized the surface-level challenge — \
  did not reflect back business impact or deeper concerns
- 0 pts: No summary attempted at any point in the conversation

=== DEPTH REACHED GUIDANCE ===
Determine which layer the buyer revealed based on the transcript:
- "surface": buyer only shared the general operational challenge
- "layer2": buyer revealed specific business impact (numbers, consequences)
- "layer3": buyer shared personal or political stakes, internal friction, \
  or emotional weight
- "layer4": buyer articulated their real vision or desired outcome

=== END RUBRIC ===

Score strictly against the transcript. Award points only for demonstrated \
behavior, not intent. Quote the student directly in every evidence field.

CRITICAL: Return pure JSON only. No markdown, no backticks. \
Start with {{ and end with }}."""


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
            "depth_reached": "unknown",
            "plain_english_summary": "Could not parse coach response.",
            "strongest_moment": "Please try again.",
            "critical_gap": "Scorecard could not be generated — run simulation again.",
            "behavioral_recommendation": "Re-run the simulation to receive feedback.",
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
        "ch3_phase": "setup",
        "ch3_student_name": "",
        "ch3_scenario": "health",
        "ch3_messages": [],
        "ch3_student_count": 0,
        "ch3_scorecard": None,
        "ch3_generating": False,
        "ch3_voice_enabled": True,
        "ch3_tts_bytes": None,
        "ch3_last_audio_id": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset_state() -> None:
    keys = [k for k in st.session_state if k.startswith("ch3_")]
    for k in keys:
        del st.session_state[k]
    _init_state()


# ---------------------------------------------------------------------------
# Screen 1 — Setup
# ---------------------------------------------------------------------------

def screen_setup() -> None:
    st.title("Chapter 3 — Active Listening Roleplay")
    st.markdown("### Simulation Setup")
    st.markdown(
        "Configure your simulation below. "
        "Your name will appear on the scorecard."
    )
    st.markdown("---")

    student_name = st.text_input(
        "Your full name",
        value=st.session_state["ch3_student_name"],
        placeholder="e.g. Ana García",
        key="ch3_name_input",
    )

    st.markdown("#### Select a buyer scenario")
    scenario_options = list(SCENARIOS.keys())
    scenario_labels = [SCENARIOS[k]["label"] for k in scenario_options]
    selected_index = scenario_options.index(st.session_state["ch3_scenario"])

    chosen_index = st.radio(
        "Scenario",
        options=range(len(scenario_options)),
        format_func=lambda i: scenario_labels[i],
        index=selected_index,
        label_visibility="collapsed",
    )

    chosen_key = scenario_options[chosen_index]
    s = SCENARIOS[chosen_key]

    st.markdown(
        f"""
        <div style="margin-top:0.75rem;">
          <div style="background:#1A2332; border:1px solid #2E5FA3;
               border-radius:8px 8px 0 0; padding:1rem 1.2rem;">
            <div style="font-weight:700; color:#4A90D9;
                 margin-bottom:0.6rem;">&#128203; Your Prospect</div>
            <strong>{s['buyer_name']}</strong> &nbsp;&middot;&nbsp; {s['buyer_title']}<br>
            {s['company']} &nbsp;&middot;&nbsp; {s['location']}<br>
            <span style="color:#aaa;">{s['size']} &nbsp;&middot;&nbsp; {s['revenue']}</span><br>
            <span style="color:#aaa;">{s['industry']}</span><br>
            <span style="color:#aaa; font-size:0.9rem; margin-top:0.4rem; display:block;">
              You work at <strong style="color:#FAFAFA;">{s['rep_company']}</strong>, \
selling {s['product']}.
            </span>
          </div>
          <div style="background:#112030; border:1px solid #2E5FA3; border-top:none;
               border-radius:0 0 8px 8px; padding:1rem 1.2rem;">
            <div style="font-weight:700; color:#27AE60;
                 margin-bottom:0.6rem;">&#127919; Your Mission</div>
            This is <strong>not</strong> a pitch meeting.<br>
            Your only job: <strong>listen</strong>, ask genuine follow-up questions, \
and demonstrate you understand their situation.<br>
            <span style="color:#aaa;">Do not mention your product unless the buyer \
asks directly.</span><br>
            <span style="color:#aaa;">The deeper you listen, the more they will \
share.</span><br>
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
        st.session_state["ch3_student_name"] = student_name.strip()
        st.session_state["ch3_scenario"] = chosen_key
        st.session_state["ch3_messages"] = [{"role": "assistant", "content": opening}]
        st.session_state["ch3_student_count"] = 0
        st.session_state["ch3_phase"] = "chat"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 2 — Chat
# ---------------------------------------------------------------------------

def screen_chat() -> None:
    scenario = st.session_state["ch3_scenario"]
    s = SCENARIOS[scenario]
    messages: list = st.session_state["ch3_messages"]
    student_count: int = st.session_state["ch3_student_count"]

    st.title("Chapter 3 — Active Listening Roleplay")
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
            value=st.session_state.get("ch3_voice_enabled", True),
            key="ch3_voice_toggle",
        )
        st.session_state["ch3_voice_enabled"] = voice_on
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

    tts_bytes = st.session_state.get("ch3_tts_bytes")
    if tts_bytes:
        st.audio(tts_bytes, format="audio/mp3", autoplay=True)
        st.session_state["ch3_tts_bytes"] = None

    if student_count >= 12:
        st.info(
            "You've sent 12 messages. Look for a moment to offer a genuine summary "
            "of what you've heard — that's the highest-value listening move left available to you."
        )

    audio = mic_recorder(
        start_prompt="🎤 Click to speak",
        stop_prompt="⏹ Recording… click to stop",
        key="ch3_mic",
    )
    if audio and audio.get("bytes"):
        if audio.get("id") != st.session_state.get("ch3_last_audio_id"):
            st.session_state["ch3_last_audio_id"] = audio["id"]
            with st.spinner("Transcribing…"):
                transcribed = call_whisper_api(audio["bytes"])
            if transcribed:
                messages.append({"role": "user", "content": transcribed})
                st.session_state["ch3_student_count"] += 1
                st.session_state["ch3_messages"] = messages
                st.session_state["ch3_generating"] = True
                st.rerun()
            else:
                st.warning(
                    "Could not transcribe the recording — please try again "
                    "or type your response below."
                )

    user_input = st.chat_input(
        "Respond to the buyer…",
        disabled=st.session_state.get("ch3_generating", False),
    )

    if user_input:
        messages.append({"role": "user", "content": user_input})
        st.session_state["ch3_student_count"] += 1
        st.session_state["ch3_messages"] = messages
        st.session_state["ch3_generating"] = True
        st.rerun()

    if st.session_state.get("ch3_generating", False):
        with st.spinner(f"{s['buyer_name']} is responding…"):
            reply = call_buyer_api(messages, scenario)
        messages.append({"role": "assistant", "content": reply})
        st.session_state["ch3_messages"] = messages
        if st.session_state.get("ch3_voice_enabled", True):
            with st.spinner("Generating voice response…"):
                tts = call_tts_api(reply)
            if tts:
                st.session_state["ch3_tts_bytes"] = tts
            else:
                st.warning("Voice generation failed — text response shown above.")
        st.session_state["ch3_generating"] = False
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
                st.session_state["ch3_student_name"],
                scenario,
            )
        st.session_state["ch3_scorecard"] = data
        st.session_state["ch3_phase"] = "scorecard"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 3 — Scorecard
# ---------------------------------------------------------------------------

def screen_scorecard() -> None:
    data: dict = st.session_state["ch3_scorecard"]
    scenario: str = st.session_state["ch3_scenario"]
    student_name: str = st.session_state["ch3_student_name"]
    s = SCENARIOS[scenario]

    dimensions: list = data.get("dimensions", [])
    total: int = sum(d["score"] for d in dimensions)
    max_total: int = sum(d["max_points"] for d in dimensions) or 100

    if total >= 90:
        tier, tier_color = "Master Listener", "#27AE60"
    elif total >= 75:
        tier, tier_color = "Active Listener", "#2E86AB"
    elif total >= 60:
        tier, tier_color = "Developing", "#F39C12"
    else:
        tier, tier_color = "Rerun Recommended", "#E74C3C"

    _DEPTH_STYLES = {
        "surface": ("Surface only", "#E74C3C"),
        "layer2":  ("Layer 2 — Business impact", "#F39C12"),
        "layer3":  ("Layer 3 — Personal stakes", "#2E86AB"),
        "layer4":  ("Layer 4 — Buyer's true vision", "#27AE60"),
    }
    depth_raw = data.get("depth_reached", "surface")
    depth_label, depth_color = _DEPTH_STYLES.get(
        depth_raw, ("Unknown", "#888")
    )

    st.title("Scorecard — Active Listening Roleplay")
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

    # Depth-reached banner
    st.markdown(
        f"""
        <div style="background:{depth_color}22; border:2px solid {depth_color};
             border-radius:10px; padding:1rem 1.4rem; margin-bottom:1rem;
             text-align:center;">
          <span style="font-size:1.5rem;">&#127911;</span>
          <span style="font-size:1.1rem; font-weight:700; color:{depth_color};
               margin-left:0.5rem;">Depth reached: {depth_label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
            "| 90–100 | Master Listener |\n"
            "| 75–89 | Active Listener |\n"
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
                or evidence.startswith("No summary")
                or evidence.startswith("No listening")
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

            coaching = dim.get("coaching_note")
            if coaching and coaching != "null" and pct < 0.7:
                st.warning(f"**Coaching note:** {coaching}")

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

def run_chapter3() -> None:
    _init_state()
    phase = st.session_state["ch3_phase"]
    if phase == "setup":
        screen_setup()
    elif phase == "chat":
        screen_chat()
    elif phase == "scorecard":
        screen_scorecard()
