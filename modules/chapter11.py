import io
import json
import re
import streamlit as st
from datetime import date
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
from config import get_openai_api_key

MODEL_COACH = "gpt-4.1-mini"
TEMP_COACH = 0.3

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def _init_state() -> None:
    defaults = {
        "ch11_phase": "setup",
        "ch11_student_name": "",
        "ch11_job_title": "",
        "ch11_company": "",
        "ch11_job_posting": "",
        "ch11_resume": "",
        "ch11_linkedin": "",
        "ch11_pitch_written": "",
        "ch11_pitch_voice_transcript": "",
        "ch11_scores": {
            "resume": None,
            "linkedin": None,
            "pitch_written": None,
            "pitch_voice": None,
        },
        "ch11_locked": {
            "resume": False,
            "linkedin": False,
            "pitch_written": False,
            "pitch_voice": False,
        },
        "ch11_feedback": {},
        "ch11_iterations": {
            "resume": 0,
            "linkedin": 0,
            "pitch_written": 0,
            "pitch_voice": 0,
        },
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset_state() -> None:
    keys = [k for k in st.session_state if k.startswith("ch11_")]
    for k in keys:
        del st.session_state[k]
    _init_state()


# ---------------------------------------------------------------------------
# Helper — score tier label
# ---------------------------------------------------------------------------

def _tier(score: int | float) -> str:
    if score >= 90:
        return "Outstanding"
    if score >= 75:
        return "Strong"
    if score >= 60:
        return "Developing"
    return "Needs Work — keep improving"


# ---------------------------------------------------------------------------
# Coach prompt builders
# ---------------------------------------------------------------------------

def get_resume_coach_prompt(
    resume: str,
    job_posting: str,
    student_name: str,
    job_title: str,
    company: str,
) -> str:
    return f"""You are an expert career coach evaluating a student's resume for a specific job.
Student: {student_name}
Target role: {job_title} at {company}

JOB POSTING:
{job_posting}

STUDENT RESUME:
{resume}

Evaluate this resume on THREE things ONLY:
1. Does it use keywords from the job posting? (not whether the experience is identical)
2. Does it show quantified achievements? (any numbers count — students, businesses, courses, revenue, percentages)
3. Is the experience relevant or transferable? (teaching sales = sales experience, consulting businesses = client management, academic leadership = executive presence)

CRITICAL: Do NOT penalize for:
- Academic vs corporate experience
- Teaching vs direct selling
- Different industry background

DO penalize for:
- Missing keywords that ARE in the resume but not connected to job requirements
- Vague claims with zero numbers
- No connection made to target role

A resume with strong transferable experience, good keyword alignment, and some metrics should score 16-18/20.

Scoring per dimension: award points based on how well the content meets the criterion.
Overall tiers: 90–100 = Outstanding, 75–89 = Strong, 60–74 = Developing, below 60 = Needs Work.

Respond with ONLY a JSON object — no markdown, no explanation, just the raw JSON from {{ to }}:
{{
  "dimensions": [
    {{
      "name": "Keyword Alignment",
      "score": <int 0–8>,
      "max_points": 8,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }},
    {{
      "name": "Impact & Metrics",
      "score": <int 0–7>,
      "max_points": 7,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }},
    {{
      "name": "Role Relevance",
      "score": <int 0–5>,
      "max_points": 5,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }}
  ],
  "total_score": <int 0–20>,
  "tier": "<Outstanding | Strong | Developing | Needs Work — keep improving>",
  "plain_english_summary": "<3–4 sentences on overall resume quality for this role>",
  "top_3_improvements": ["<improvement 1>", "<improvement 2>", "<improvement 3>"],
  "strongest_element": "<what the student did best>",
  "improved_version": "<Rewrite the student's resume completely optimized for this specific job posting. Rules: (1) Keep all real facts, experiences, and credentials from the original — never invent achievements. (2) Reframe their actual experience using the exact language and keywords from the job posting. (3) Add specific metrics where the student mentioned vague outcomes (e.g. 'helped businesses grow' → 'consulted 100+ businesses, driving measurable revenue improvements'). (4) Lead with the most relevant experience first. (5) Mirror the job posting's terminology throughout — use their exact phrases for skills and competencies. (6) Add a strong professional summary at the top that directly addresses what the job posting asks for. (7) Make it sound like this person was MADE for this specific role. (8) Write in first person, professional tone. (9) This improved version should score 85+ if re-evaluated — make it substantially better, not just marginally tweaked. CRITICAL: The improved version you generate MUST score at least 80/100 if evaluated against this exact same rubric. This means: for resume — it must have explicit keywords from the job posting, quantified achievements, and clear role relevance; for linkedin — headline must directly target this role, about must tell a compelling story; for pitch written — must have clear hook, value prop tied to job posting, strong CTA; for pitch voice — must sound natural, have clear structure, be 60-90 seconds. Do not generate a version that you would score below 80. If the student's original content is limited, add reasonable professional context that elevates it — always keeping their real facts but framing them at their best possible light. You are the coach AND the evaluator — your improved version must pass your own test.>"
}}"""


def get_linkedin_coach_prompt(
    linkedin: str,
    job_posting: str,
    student_name: str,
    job_title: str,
    company: str,
) -> str:
    return f"""You are an expert LinkedIn profile coach evaluating a student's profile for a specific job.
Student: {student_name}
Target role: {job_title} at {company}

JOB POSTING:
{job_posting}

STUDENT LINKEDIN PROFILE:
{linkedin}

Evaluate this LinkedIn profile on THREE things ONLY:
1. Does the headline use keywords from the job posting and signal this target role? (not whether it matches a senior professional's headline — any clear targeting counts)
2. Does the About section tell a connected story? (academic projects, part-time work, volunteering all count — any narrative that links background to the role)
3. Does the profile use the employer's language? (any keywords from the job posting present anywhere = full credit for that criterion)

CRITICAL: Do NOT penalize for:
- Being a student or recent graduate
- Limited work history
- Non-corporate or non-traditional background

DO penalize for:
- Headline with zero connection to the target role
- About section with no narrative — just a list of unconnected facts
- No keywords from the job posting anywhere in the profile

A profile with a targeted headline, a connected story, and good keyword presence should score 16-18/20.

Scoring per dimension: award points based on how well the content meets the criterion.
Overall tiers: 90–100 = Outstanding, 75–89 = Strong, 60–74 = Developing, below 60 = Needs Work.

Respond with ONLY a JSON object — no markdown, no explanation, just the raw JSON from {{ to }}:
{{
  "dimensions": [
    {{
      "name": "Headline Positioning",
      "score": <int 0–8>,
      "max_points": 8,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }},
    {{
      "name": "About Section",
      "score": <int 0–8>,
      "max_points": 8,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }},
    {{
      "name": "Keyword Optimization",
      "score": <int 0–4>,
      "max_points": 4,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }}
  ],
  "total_score": <int 0–20>,
  "tier": "<Outstanding | Strong | Developing | Needs Work — keep improving>",
  "plain_english_summary": "<3–4 sentences on overall LinkedIn quality for this role>",
  "top_3_improvements": ["<improvement 1>", "<improvement 2>", "<improvement 3>"],
  "strongest_element": "<what the student did best>",
  "improved_version": "<Rewrite the student's LinkedIn profile completely optimized for this specific job posting. Format as: HEADLINE: [headline text]\\n\\nABOUT: [about section text]. Rules: (1) Keep all real facts and credentials — never invent experience. (2) Craft a headline that uses the job posting's exact role title and key skills — make it immediately recognizable to recruiters searching for this role. (3) Rewrite the About section to open with a strong hook, use the job posting's language throughout, and close with a clear call to action. (4) Mirror the job posting's terminology for skills and competencies. (5) Make every sentence speak directly to what this employer needs. (6) Write in first person, professional but conversational tone. (7) This improved version should score 85+ if re-evaluated — make it substantially better, not just marginally tweaked. CRITICAL: The improved version you generate MUST score at least 80/100 if evaluated against this exact same rubric. This means: for resume — it must have explicit keywords from the job posting, quantified achievements, and clear role relevance; for linkedin — headline must directly target this role, about must tell a compelling story; for pitch written — must have clear hook, value prop tied to job posting, strong CTA; for pitch voice — must sound natural, have clear structure, be 60-90 seconds. Do not generate a version that you would score below 80. If the student's original content is limited, add reasonable professional context that elevates it — always keeping their real facts but framing them at their best possible light. You are the coach AND the evaluator — your improved version must pass your own test.>"
}}"""


def get_pitch_written_coach_prompt(
    pitch: str,
    job_posting: str,
    student_name: str,
    job_title: str,
    company: str,
) -> str:
    word_count = len(pitch.strip().split()) if pitch.strip() else 0
    word_flag = ""
    if word_count < 100:
        word_flag = f"NOTE: The pitch is only {word_count} words — flag this as too short (target 100–250 words)."
    elif word_count > 250:
        word_flag = f"NOTE: The pitch is {word_count} words — flag this as too long (target 100–250 words)."

    return f"""You are an expert career coach evaluating a student's written elevator pitch for a specific job.
Student: {student_name}
Target role: {job_title} at {company}
Word count: {word_count} words
{word_flag}

JOB POSTING:
{job_posting}

STUDENT WRITTEN PITCH:
{pitch}

Evaluate this written pitch on FIVE things ONLY:
1. Hook (5 pts): Does the opening create interest? (a question, bold statement, or surprising fact all count — penalize only if it opens with "Hi, my name is..." and nothing else)
2. Who You Are (5 pts): Does the student clearly state their identity and what they bring? (student, academic, career-changer are all valid if stated with confidence and direction)
3. Value Proposition (8 pts): Is there a specific value tied to this employer's needs? (transferable value counts — teaching, consulting, research, leadership all map to B2B sales competencies)
4. Call to Action (5 pts): Does it end with a specific ask or next step? (any clear, confident close counts)
5. Job Alignment (2 pts): Does it reference the company, role, or specific needs from the posting? (any direct reference counts for full credit)

CRITICAL: Do NOT penalize for:
- Academic or non-corporate background
- Less than 5 years of work experience
- Non-traditional career path

DO penalize for:
- No discernible opening hook — pitch just states name with no engagement
- Value proposition with zero specifics ("I'm a hard worker" alone)
- No CTA — pitch simply stops without a close
- Zero reference to the role or company anywhere

A pitch with clear structure, specific transferable value, and a real CTA should score 20-22/25.

Scoring per dimension: award points based on how well the content meets the criterion.
Overall tiers: 90–100 = Outstanding, 75–89 = Strong, 60–74 = Developing, below 60 = Needs Work.

Respond with ONLY a JSON object — no markdown, no explanation, just the raw JSON from {{ to }}:
{{
  "dimensions": [
    {{
      "name": "Hook",
      "score": <int 0–5>,
      "max_points": 5,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }},
    {{
      "name": "Who You Are",
      "score": <int 0–5>,
      "max_points": 5,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }},
    {{
      "name": "Value Proposition",
      "score": <int 0–8>,
      "max_points": 8,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }},
    {{
      "name": "Call to Action",
      "score": <int 0–5>,
      "max_points": 5,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }},
    {{
      "name": "Job Alignment",
      "score": <int 0–2>,
      "max_points": 2,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }}
  ],
  "total_score": <int 0–25>,
  "tier": "<Outstanding | Strong | Developing | Needs Work — keep improving>",
  "plain_english_summary": "<3–4 sentences on overall pitch quality>",
  "top_3_improvements": ["<improvement 1>", "<improvement 2>", "<improvement 3>"],
  "strongest_element": "<what the student did best>",
  "improved_version": "<Rewrite the student's elevator pitch completely optimized for this specific job posting. Rules: (1) Keep all real facts and credentials — never invent experience. (2) Open with a compelling hook that immediately signals fit for this role. (3) State who they are using the exact language the employer uses in the posting. (4) Articulate a specific value proposition tied directly to what this employer needs — not generic. (5) Close with a confident, specific call to action. (6) Mirror the job posting's terminology throughout. (7) Target 130–200 words (60–90 seconds spoken). (8) Write in first person, natural and confident tone — not stiff or corporate. (9) This improved version should score 85+ if re-evaluated — make it substantially better, not just marginally tweaked. CRITICAL: The improved version you generate MUST score at least 80/100 if evaluated against this exact same rubric. This means: for resume — it must have explicit keywords from the job posting, quantified achievements, and clear role relevance; for linkedin — headline must directly target this role, about must tell a compelling story; for pitch written — must have clear hook, value prop tied to job posting, strong CTA; for pitch voice — must sound natural, have clear structure, be 60-90 seconds. Do not generate a version that you would score below 80. If the student's original content is limited, add reasonable professional context that elevates it — always keeping their real facts but framing them at their best possible light. You are the coach AND the evaluator — your improved version must pass your own test.>"
}}"""


def get_pitch_voice_coach_prompt(
    transcript: str,
    job_posting: str,
    student_name: str,
    job_title: str,
    company: str,
    duration_seconds: float,
) -> str:
    duration_note = (
        f"{duration_seconds:.0f} seconds"
        if duration_seconds
        else "unknown duration"
    )
    if duration_seconds and 60 <= duration_seconds <= 90:
        timing_note = "Timing is within the ideal 60–90 second range."
    elif duration_seconds and (45 <= duration_seconds < 60 or 90 < duration_seconds <= 105):
        timing_note = "Timing is close but outside the ideal 60–90 second range — award partial points."
    elif duration_seconds:
        timing_note = "Timing is significantly outside the 60–90 second range — award 0 for Timing."
    else:
        timing_note = "Duration unknown — evaluate Timing based on transcript length and density."

    return f"""You are an expert career coach evaluating a student's spoken elevator pitch for a specific job.
Student: {student_name}
Target role: {job_title} at {company}
Recorded duration: {duration_note}
Timing guidance: {timing_note}

JOB POSTING:
{job_posting}

VOICE PITCH TRANSCRIPT:
{transcript}

Evaluate this voice pitch transcript on FIVE things ONLY:
1. Hook (7 pts): Does the opening create interest when heard out loud? (any engaging opening counts — penalize only if it opens with flat self-introduction and nothing more)
2. Fluency (7 pts): Does it sound conversational rather than read? (natural pauses, contractions, and slight imperfections are FINE and expected — penalize only if clearly monotone and word-for-word scripted with zero variation)
3. Value Proposition (10 pts): Is there a specific value tied to this employer's needs? (transferable value from any background counts — teaching, consulting, research, leadership all map to sales competencies)
4. Call to Action (7 pts): Does it end with a clear, confident ask? (any genuine close counts)
5. Timing (4 pts): 60–90 sec = full 4 pts; 45–60 or 90–105 sec = 2 pts; outside that range = 0 pts.

CRITICAL: Do NOT penalize for:
- Accent or non-native English patterns
- Nervousness, brief pauses, or filler words (um, uh) in moderation
- Academic or non-corporate background in the content

DO penalize for:
- Clearly reading word-for-word (monotone, no rhythm, no natural variation)
- No discernible value proposition — content is entirely vague
- No CTA — pitch stops mid-thought without a close

A pitch with clear structure, natural delivery, specific transferable value, and proper timing should score 28-32/35.

Scoring per dimension: award points based on how well the content meets the criterion.
Overall tiers: 90–100 = Outstanding, 75–89 = Strong, 60–74 = Developing, below 60 = Needs Work.

Respond with ONLY a JSON object — no markdown, no explanation, just the raw JSON from {{ to }}:
{{
  "dimensions": [
    {{
      "name": "Hook",
      "score": <int 0–7>,
      "max_points": 7,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }},
    {{
      "name": "Fluency",
      "score": <int 0–7>,
      "max_points": 7,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }},
    {{
      "name": "Value Proposition",
      "score": <int 0–10>,
      "max_points": 10,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }},
    {{
      "name": "Call to Action",
      "score": <int 0–7>,
      "max_points": 7,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }},
    {{
      "name": "Timing",
      "score": <int 0–4>,
      "max_points": 4,
      "rationale": "<1–2 sentences noting the actual duration>",
      "suggestion": "<one concrete improvement>"
    }}
  ],
  "total_score": <int 0–35>,
  "tier": "<Outstanding | Strong | Developing | Needs Work — keep improving>",
  "plain_english_summary": "<3–4 sentences on overall voice pitch quality>",
  "top_3_improvements": ["<improvement 1>", "<improvement 2>", "<improvement 3>"],
  "strongest_element": "<what the student did best>",
  "improved_version": "<Rewrite the student's elevator pitch as a polished script optimized for natural spoken delivery and this specific job posting. Rules: (1) Keep all real facts and credentials — never invent experience. (2) Open with a hook that sounds natural out loud — not like a written sentence being read. (3) State who they are in conversational language that still signals direct fit for this role. (4) Articulate a specific value proposition tied to what this employer needs — avoid generic phrases. (5) Close with a confident, natural-sounding call to action. (6) Mirror the job posting's terminology but keep the language flowing and unscripted. (7) Target 130–200 words (60–90 seconds at natural pace). (8) Write for the ear, not the eye — use short sentences, natural rhythm, and contractions where appropriate. (9) This improved version should score 85+ if re-evaluated — make it substantially better, not just marginally tweaked. CRITICAL: The improved version you generate MUST score at least 80/100 if evaluated against this exact same rubric. This means: for resume — it must have explicit keywords from the job posting, quantified achievements, and clear role relevance; for linkedin — headline must directly target this role, about must tell a compelling story; for pitch written — must have clear hook, value prop tied to job posting, strong CTA; for pitch voice — must sound natural, have clear structure, be 60-90 seconds. Do not generate a version that you would score below 80. If the student's original content is limited, add reasonable professional context that elevates it — always keeping their real facts but framing them at their best possible light. You are the coach AND the evaluator — your improved version must pass your own test.>"
}}"""


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def call_coach_api(prompt: str, section_name: str) -> dict:
    client = OpenAI(api_key=get_openai_api_key())
    response = client.chat.completions.create(
        model=MODEL_COACH,
        messages=[{"role": "user", "content": prompt}],
        temperature=TEMP_COACH,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"```\s*$", "", raw)
    raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "dimensions": [],
            "total_score": 0,
            "tier": "Needs Work — keep improving",
            "plain_english_summary": f"Could not parse {section_name} feedback. Please try again.",
            "top_3_improvements": ["Re-submit to get AI feedback."],
            "strongest_element": "N/A",
        }


def call_whisper_api(audio_bytes: bytes) -> tuple[str, float]:
    """Transcribe audio and return (transcript, duration_seconds)."""
    client = OpenAI(api_key=get_openai_api_key())
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "pitch.wav"
    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="verbose_json",
    )
    transcript = response.text.strip()
    duration = float(response.duration) if hasattr(response, "duration") and response.duration else 0.0
    return transcript, duration


# ---------------------------------------------------------------------------
# Screen 1 — Setup
# ---------------------------------------------------------------------------

def screen_setup() -> None:
    st.title("Chapter 11 — Personal Branding Lab")

    st.markdown(
        """
        <div style="background:#1B3A6B; border-radius:10px; padding:1.2rem 1.4rem;
             margin-bottom:1.25rem; color:#FAFAFA;">
          <div style="font-weight:700; font-size:1.05rem; margin-bottom:0.6rem;">
            🎯 What you will do:
          </div>
          <div style="margin-bottom:0.6rem;">
            Submit and refine <strong>4 elements of your personal brand</strong> —
            all evaluated against the real job posting you are targeting.
          </div>
          <div style="margin-bottom:0.25rem;">
            <strong>Step 1 — Resume:</strong>
            Does your experience align with what this employer needs?
          </div>
          <div style="margin-bottom:0.25rem;">
            <strong>Step 2 — LinkedIn:</strong>
            Does your profile speak the employer's language?
          </div>
          <div style="margin-bottom:0.25rem;">
            <strong>Step 3 — Elevator Pitch (Written):</strong>
            Can you articulate your value in 60–90 sec?
          </div>
          <div style="margin-bottom:0.75rem;">
            <strong>Step 4 — Elevator Pitch (Voice):</strong>
            Can you deliver it naturally and confidently?
          </div>
          <div style="color:#B8C8E0; font-size:0.9rem;">
            You can improve and re-evaluate each section as many times as you need.<br>
            Your scorecard appears when all 4 sections are locked —
            <strong>screenshot and submit to Canvas.</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📊 How you'll be scored (100 pts)", expanded=False):
        st.markdown(
            "**Resume — 20 pts**\n"
            "- Keyword Alignment: 8 pts\n"
            "- Impact & Metrics: 7 pts\n"
            "- Role Relevance: 5 pts\n\n"
            "**LinkedIn — 20 pts**\n"
            "- Headline Positioning: 8 pts\n"
            "- About Section: 8 pts\n"
            "- Keyword Optimization: 4 pts\n\n"
            "**Elevator Pitch Written — 25 pts**\n"
            "- Hook: 5 pts\n"
            "- Who You Are: 5 pts\n"
            "- Value Proposition: 8 pts\n"
            "- Call to Action: 5 pts\n"
            "- Job Alignment: 2 pts\n\n"
            "**Elevator Pitch Voice — 35 pts**\n"
            "- Hook: 7 pts\n"
            "- Fluency: 7 pts\n"
            "- Value Proposition: 10 pts\n"
            "- Call to Action: 7 pts\n"
            "- Timing 60–90 sec: 4 pts"
        )

    name = st.text_input("Your full name", key="ch11_input_name")
    job_title = st.text_input("Target job title", key="ch11_input_job_title")
    company = st.text_input("Target company", key="ch11_input_company")
    job_posting = st.text_area(
        "Paste the full job posting here",
        height=220,
        key="ch11_input_job_posting",
    )

    all_filled = bool(
        name.strip()
        and job_title.strip()
        and company.strip()
        and job_posting.strip()
    )

    if st.button(
        "Start Personal Branding Lab →",
        disabled=not all_filled,
        type="primary",
        use_container_width=True,
        key="ch11_btn_start",
    ):
        st.session_state["ch11_student_name"] = name.strip()
        st.session_state["ch11_job_title"] = job_title.strip()
        st.session_state["ch11_company"] = company.strip()
        st.session_state["ch11_job_posting"] = job_posting.strip()
        st.session_state["ch11_phase"] = "resume"
        st.rerun()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STEPS = [
    ("resume", "Resume"),
    ("linkedin", "LinkedIn"),
    ("pitch_written", "Pitch Written"),
    ("pitch_voice", "Voice"),
]

NEXT_PHASE = {
    "resume": "linkedin",
    "linkedin": "pitch_written",
    "pitch_written": "pitch_voice",
    "pitch_voice": "scorecard",
}

SECTION_MAX = {
    "resume": 20,
    "linkedin": 20,
    "pitch_written": 25,
    "pitch_voice": 35,
}

_TIER_COLOR = {
    "Outstanding": "#27AE60",
    "Strong": "#4A90D9",
    "Developing": "#F39C12",
    "Needs Work — keep improving": "#E74C3C",
}


# ---------------------------------------------------------------------------
# Shared UI helpers
# ---------------------------------------------------------------------------

def _working_phase() -> str:
    """Return the first unlocked section phase, or 'scorecard' if all locked."""
    locked = st.session_state["ch11_locked"]
    for key, _ in STEPS:
        if not locked[key]:
            return key
    return "scorecard"


def _render_progress_header() -> None:
    locked = st.session_state["ch11_locked"]
    phase = st.session_state["ch11_phase"]
    cols = st.columns(4)
    for i, (key, label) in enumerate(STEPS):
        with cols[i]:
            if locked[key]:
                if st.button(f"✅ {label}", key=f"ch11_nav_{key}", use_container_width=True):
                    st.session_state["ch11_phase"] = key
                    st.rerun()
            elif phase == key:
                st.button(f"🔄 {label}", key=f"ch11_nav_{key}", use_container_width=True, disabled=True)
            else:
                st.button(f"⬜ {label}", key=f"ch11_nav_{key}", use_container_width=True, disabled=True)
    st.markdown("---")


def _render_job_ref() -> None:
    posting = st.session_state["ch11_job_posting"]
    title = st.session_state["ch11_job_title"]
    company = st.session_state["ch11_company"]
    preview = posting[:300] + "..." if len(posting) > 300 else posting
    with st.expander(f"📋 Your target role: {title} at {company}", expanded=False):
        st.markdown(preview)


def _render_results(section_key: str, extra_note: str = "") -> None:
    data = st.session_state["ch11_feedback"].get(section_key)
    if not data:
        return
    score = data.get("total_score", 0)
    max_score = SECTION_MAX[section_key]
    tier = data.get("tier", _tier(score))
    color = _TIER_COLOR.get(tier, "#888")

    st.markdown(
        f"""
        <div style="background:{color}22; border:2px solid {color}; border-radius:10px;
             padding:1rem 1.2rem; margin:0.75rem 0; text-align:center;">
          <div style="font-size:2rem; font-weight:800; color:{color};">{score}/{max_score} pts</div>
          <div style="font-size:1rem; font-weight:700; color:{color}; margin-top:0.2rem;">{tier}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f"*{data.get('plain_english_summary', '')}*")

    st.markdown("#### Breakdown")
    for dim in data.get("dimensions", []):
        dim_score = dim.get("score", 0)
        dim_max = dim.get("max_points", 1)
        pct = dim_score / dim_max if dim_max > 0 else 0
        st.markdown(f"**{dim['name']}** — {dim_score}/{dim_max} pts")
        st.progress(pct)
        st.caption(dim.get("rationale", ""))
        if pct < 0.70:
            st.info(f"💡 {dim.get('suggestion', '')}")

    st.markdown("#### Top 3 Improvements")
    for item in data.get("top_3_improvements", []):
        st.markdown(f"- {item}")

    st.markdown(
        f"""
        <div style="background:#1B3A6B22; border:1px solid #2E5FA3; border-radius:8px;
             padding:0.75rem 1rem; margin-top:0.5rem;">
          <strong>⭐ Strongest element:</strong> {data.get('strongest_element', '')}
        </div>
        """,
        unsafe_allow_html=True,
    )

    improved = data.get("improved_version", "")
    if improved:
        st.markdown("---")
        st.markdown("#### ✨ Here's an improved version")
        iteration = st.session_state["ch11_iterations"].get(section_key, 0)
        st.text_area(
            "Copy this improved version, personalize it, then paste it above and re-evaluate.",
            value=improved,
            height=300,
            key=f"ch11_improved_{section_key}_{iteration}",
        )

    if extra_note:
        st.caption(extra_note)


def _action_buttons(section_key: str) -> str | None:
    """Returns 're_evaluate', 'lock', 'unlock', or None."""
    locked = st.session_state["ch11_locked"][section_key]
    score = st.session_state["ch11_scores"][section_key]
    max_score = SECTION_MAX[section_key]

    if locked:
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown(
                '<span style="background:#27AE60; color:white; border-radius:12px; '
                'padding:4px 14px; font-weight:700; display:inline-block;">✅ Locked</span>',
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("Edit this section", key=f"ch11_edit_{section_key}"):
                return "unlock"
        return None

    if score is None:
        return None

    if score < 75:
        st.markdown(
            f"""
            <div style="background:#F39C1222; border:1px solid #F39C12; border-radius:8px;
                 padding:0.75rem 1rem; margin-bottom:0.75rem; color:#FAFAFA;">
              ⚠️ Your score is <strong>{score}/{max_score}</strong>.
              Use the improved version above to help you get above 75.
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "🔄 Re-evaluate with my changes",
            key=f"ch11_reeval_{section_key}",
            type="primary",
            use_container_width=True,
        ):
            return "re_evaluate"
        if st.button(
            "Skip and continue anyway →",
            key=f"ch11_lock_{section_key}",
            use_container_width=True,
        ):
            return "lock"
    else:
        st.markdown(
            f"""
            <div style="background:#27AE6022; border:1px solid #27AE60; border-radius:8px;
                 padding:0.75rem 1rem; margin-bottom:0.75rem; color:#FAFAFA;">
              ✅ Great work! Score: <strong>{score}/{max_score}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "✅ Lock & continue →",
                key=f"ch11_lock_{section_key}",
                type="primary",
                use_container_width=True,
            ):
                return "lock"
        with col2:
            if st.button(
                "🔄 Re-evaluate with changes",
                key=f"ch11_reeval_{section_key}",
                use_container_width=True,
            ):
                return "re_evaluate"

    return None


def _maybe_back_button() -> None:
    """Show a back button when the student is reviewing a locked section out of order."""
    phase = st.session_state["ch11_phase"]
    working = _working_phase()
    if phase == working:
        return
    label_map = dict(STEPS)
    dest_label = "Scorecard" if working == "scorecard" else label_map.get(working, working.title())
    if st.button(f"← Back to {dest_label}", key="ch11_back_to_working"):
        st.session_state["ch11_phase"] = working
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 2 — Resume
# ---------------------------------------------------------------------------

def screen_resume() -> None:
    _render_progress_header()
    st.subheader("Step 1 — Resume")
    _render_job_ref()

    locked = st.session_state["ch11_locked"]["resume"]

    resume = st.text_area(
        "Paste your resume here",
        height=350,
        placeholder=(
            "Paste the full text of your resume. "
            "Include your summary, experience, education, and skills sections."
        ),
        disabled=locked,
        key="ch11_input_resume",
    )
    word_count = len(resume.strip().split()) if resume.strip() else 0
    st.caption(f"{word_count} words")

    def _evaluate_resume(text: str) -> None:
        with st.spinner("Evaluating your resume…"):
            prompt = get_resume_coach_prompt(
                text,
                st.session_state["ch11_job_posting"],
                st.session_state["ch11_student_name"],
                st.session_state["ch11_job_title"],
                st.session_state["ch11_company"],
            )
            data = call_coach_api(prompt, "resume")
        st.session_state["ch11_resume"] = text
        st.session_state["ch11_feedback"]["resume"] = data
        st.session_state["ch11_scores"]["resume"] = data.get("total_score", 0)
        st.session_state["ch11_iterations"]["resume"] += 1

    if not locked:
        if st.button(
            "Evaluate my resume →",
            disabled=(word_count < 100),
            type="primary",
            use_container_width=True,
            key="ch11_eval_resume",
        ):
            _evaluate_resume(resume)
            st.rerun()

    if st.session_state["ch11_scores"]["resume"] is not None:
        st.markdown("---")
        _render_results("resume")
        st.markdown("---")
        action = _action_buttons("resume")
        if action == "lock":
            st.session_state["ch11_locked"]["resume"] = True
            st.session_state["ch11_phase"] = "linkedin"
            st.rerun()
        elif action == "unlock":
            st.session_state["ch11_locked"]["resume"] = False
            st.rerun()
        elif action == "re_evaluate":
            _evaluate_resume(resume)
            st.rerun()

    _maybe_back_button()


# ---------------------------------------------------------------------------
# Screen 3 — LinkedIn
# ---------------------------------------------------------------------------

def screen_linkedin() -> None:
    _render_progress_header()
    st.subheader("Step 2 — LinkedIn")
    _render_job_ref()

    locked = st.session_state["ch11_locked"]["linkedin"]

    headline = st.text_area(
        "Your LinkedIn Headline",
        height=80,
        placeholder="e.g. Sales Development Representative | UCF Business Student | B2B Enthusiast",
        disabled=locked,
        key="ch11_input_linkedin_headline",
    )
    about = st.text_area(
        "Your LinkedIn About section",
        height=250,
        placeholder="Paste the full text of your LinkedIn About section.",
        disabled=locked,
        key="ch11_input_linkedin_about",
    )
    about_words = len(about.strip().split()) if about.strip() else 0
    st.caption(f"About section: {about_words} words")

    enough = bool(headline.strip()) and about_words >= 50

    def _evaluate_linkedin(h: str, a: str) -> None:
        combined = f"HEADLINE: {h.strip()}\n\nABOUT: {a.strip()}"
        with st.spinner("Evaluating your LinkedIn profile…"):
            prompt = get_linkedin_coach_prompt(
                combined,
                st.session_state["ch11_job_posting"],
                st.session_state["ch11_student_name"],
                st.session_state["ch11_job_title"],
                st.session_state["ch11_company"],
            )
            data = call_coach_api(prompt, "linkedin")
        st.session_state["ch11_linkedin"] = combined
        st.session_state["ch11_feedback"]["linkedin"] = data
        st.session_state["ch11_scores"]["linkedin"] = data.get("total_score", 0)
        st.session_state["ch11_iterations"]["linkedin"] += 1

    if not locked:
        if st.button(
            "Evaluate my LinkedIn →",
            disabled=not enough,
            type="primary",
            use_container_width=True,
            key="ch11_eval_linkedin",
        ):
            _evaluate_linkedin(headline, about)
            st.rerun()

    if st.session_state["ch11_scores"]["linkedin"] is not None:
        st.markdown("---")
        _render_results("linkedin")
        st.markdown("---")
        action = _action_buttons("linkedin")
        if action == "lock":
            st.session_state["ch11_locked"]["linkedin"] = True
            st.session_state["ch11_phase"] = "pitch_written"
            st.rerun()
        elif action == "unlock":
            st.session_state["ch11_locked"]["linkedin"] = False
            st.rerun()
        elif action == "re_evaluate":
            _evaluate_linkedin(headline, about)
            st.rerun()

    _maybe_back_button()


# ---------------------------------------------------------------------------
# Screen 4 — Elevator Pitch (Written)
# ---------------------------------------------------------------------------

def screen_pitch_written() -> None:
    _render_progress_header()
    st.subheader("Step 3 — Elevator Pitch (Written)")
    _render_job_ref()

    locked = st.session_state["ch11_locked"]["pitch_written"]

    pitch = st.text_area(
        "Write your elevator pitch here",
        height=250,
        placeholder=(
            "60–90 seconds when spoken aloud. ~130–200 words.\n"
            "Include: Hook → Who You Are → Value Proposition → Call to Action."
        ),
        disabled=locked,
        key="ch11_input_pitch_written",
    )
    word_count = len(pitch.strip().split()) if pitch.strip() else 0
    est_seconds = round(word_count / 2.3)
    st.caption(f"{word_count} words · (~{est_seconds} seconds when spoken at average pace)")

    def _evaluate_pitch_written(text: str) -> None:
        with st.spinner("Evaluating your written pitch…"):
            prompt = get_pitch_written_coach_prompt(
                text,
                st.session_state["ch11_job_posting"],
                st.session_state["ch11_student_name"],
                st.session_state["ch11_job_title"],
                st.session_state["ch11_company"],
            )
            data = call_coach_api(prompt, "pitch_written")
        st.session_state["ch11_pitch_written"] = text
        st.session_state["ch11_feedback"]["pitch_written"] = data
        st.session_state["ch11_scores"]["pitch_written"] = data.get("total_score", 0)
        st.session_state["ch11_iterations"]["pitch_written"] += 1

    if not locked:
        if st.button(
            "Evaluate my written pitch →",
            disabled=(word_count < 50),
            type="primary",
            use_container_width=True,
            key="ch11_eval_pitch_written",
        ):
            _evaluate_pitch_written(pitch)
            st.rerun()

    if st.session_state["ch11_scores"]["pitch_written"] is not None:
        st.markdown("---")
        _render_results("pitch_written")
        st.markdown("---")
        action = _action_buttons("pitch_written")
        if action == "lock":
            st.session_state["ch11_locked"]["pitch_written"] = True
            st.session_state["ch11_phase"] = "pitch_voice"
            st.rerun()
        elif action == "unlock":
            st.session_state["ch11_locked"]["pitch_written"] = False
            st.rerun()
        elif action == "re_evaluate":
            _evaluate_pitch_written(pitch)
            st.rerun()

    _maybe_back_button()


# ---------------------------------------------------------------------------
# Screen 5 — Elevator Pitch (Voice)
# ---------------------------------------------------------------------------

def screen_pitch_voice() -> None:
    _render_progress_header()
    st.subheader("Step 4 — Elevator Pitch (Voice)")
    _render_job_ref()

    written_pitch = st.session_state.get("ch11_pitch_written", "")
    if written_pitch:
        with st.expander("📝 Your written pitch (for reference)", expanded=False):
            st.markdown(written_pitch)

    locked = st.session_state["ch11_locked"]["pitch_voice"]
    transcript = st.session_state.get("ch11_pitch_voice_transcript", "")
    duration = st.session_state.get("ch11_voice_duration", 0.0)
    audio_bytes = st.session_state.get("ch11_voice_audio_bytes", None)

    if not locked:
        st.markdown(
            """
            <div style="background:#1B3A6B; border-radius:10px; padding:1rem 1.2rem;
                 margin-bottom:1rem; color:#FAFAFA;">
              <div style="font-weight:700; margin-bottom:0.4rem;">🎤 Record your elevator pitch</div>
              <div>
                Aim for <strong>60–90 seconds</strong>. Speak naturally —
                imagine you are at a networking event or job interview.
                Do not read from a script.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        playback_on = st.checkbox("🔊 Play back my recording", value=True, key="ch11_playback_toggle")

        audio = mic_recorder(
            start_prompt="🎤 Click to record",
            stop_prompt="⏹ Stop recording",
            key="ch11_voice_recorder",
        )

        if audio and audio.get("bytes"):
            new_id = str(audio.get("id", ""))
            if new_id != st.session_state.get("ch11_voice_recording_id", ""):
                st.session_state["ch11_voice_recording_id"] = new_id
                st.session_state["ch11_voice_audio_bytes"] = audio["bytes"]
                st.session_state["ch11_pitch_voice_transcript"] = ""
                st.session_state["ch11_voice_duration"] = 0.0
                audio_bytes = audio["bytes"]
                transcript = ""
                duration = 0.0

        if audio_bytes:
            if playback_on:
                st.audio(audio_bytes, format="audio/wav")

            if not transcript:
                if st.button("Transcribe recording →", key="ch11_transcribe", use_container_width=True):
                    with st.spinner("Transcribing your recording…"):
                        t, d = call_whisper_api(audio_bytes)
                    st.session_state["ch11_pitch_voice_transcript"] = t
                    st.session_state["ch11_voice_duration"] = d
                    st.rerun()
            else:
                st.markdown("**Here is what we heard:**")
                st.markdown(
                    f'<div style="background:#0E1117; border:1px solid #333; border-radius:8px; '
                    f'padding:0.75rem 1rem; color:#ccc; font-size:0.9rem;">{transcript}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(f"Recording length: {duration:.0f} seconds")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "Evaluate my voice pitch →",
                        type="primary",
                        use_container_width=True,
                        key="ch11_eval_pitch_voice",
                    ):
                        with st.spinner("Evaluating your voice pitch…"):
                            prompt = get_pitch_voice_coach_prompt(
                                transcript,
                                st.session_state["ch11_job_posting"],
                                st.session_state["ch11_student_name"],
                                st.session_state["ch11_job_title"],
                                st.session_state["ch11_company"],
                                duration,
                            )
                            data = call_coach_api(prompt, "pitch_voice")
                        st.session_state["ch11_feedback"]["pitch_voice"] = data
                        st.session_state["ch11_scores"]["pitch_voice"] = data.get("total_score", 0)
                        st.session_state["ch11_iterations"]["pitch_voice"] += 1
                        st.rerun()
                with col2:
                    if st.button("Record again", use_container_width=True, key="ch11_rerecord"):
                        st.session_state["ch11_pitch_voice_transcript"] = ""
                        st.session_state["ch11_voice_duration"] = 0.0
                        st.session_state["ch11_voice_audio_bytes"] = None
                        st.session_state["ch11_voice_recording_id"] = ""
                        st.rerun()
    else:
        if transcript:
            st.markdown("**Transcript:**")
            st.markdown(
                f'<div style="background:#0E1117; border:1px solid #333; border-radius:8px; '
                f'padding:0.75rem 1rem; color:#ccc; font-size:0.9rem;">{transcript}</div>',
                unsafe_allow_html=True,
            )
            if duration:
                st.caption(f"Recording length: {duration:.0f} seconds")

    if st.session_state["ch11_scores"]["pitch_voice"] is not None:
        st.markdown("---")
        _render_results(
            "pitch_voice",
            extra_note=(
                "The AI evaluates your transcript for natural language patterns. "
                "Filler words, incomplete sentences, and very short recordings affect the Fluency score."
            ),
        )
        st.markdown("---")
        action = _action_buttons("pitch_voice")
        if action == "lock":
            st.session_state["ch11_locked"]["pitch_voice"] = True
            st.session_state["ch11_phase"] = "scorecard"
            st.rerun()
        elif action == "unlock":
            st.session_state["ch11_locked"]["pitch_voice"] = False
            st.rerun()

    _maybe_back_button()


# ---------------------------------------------------------------------------
# Scorecard summary generator
# ---------------------------------------------------------------------------

def _generate_scorecard_summary() -> dict:
    feedback = st.session_state["ch11_feedback"]
    scores = st.session_state["ch11_scores"]
    name = st.session_state["ch11_student_name"]
    title = st.session_state["ch11_job_title"]
    company = st.session_state["ch11_company"]

    sections_text = ""
    all_improvements = []
    for key, label in [
        ("resume", "Resume"),
        ("linkedin", "LinkedIn"),
        ("pitch_written", "Pitch Written"),
        ("pitch_voice", "Voice Pitch"),
    ]:
        data = feedback.get(key, {})
        if data:
            sections_text += (
                f"\n{label} ({scores.get(key, 0)}/{SECTION_MAX[key]} pts):\n"
                f"  Summary: {data.get('plain_english_summary', '')}\n"
                f"  Strongest: {data.get('strongest_element', '')}\n"
            )
            for item in data.get("top_3_improvements", []):
                all_improvements.append(f"[{label}] {item}")

    prompt = f"""Student: {name}
Target role: {title} at {company}

Personal brand evaluations:
{sections_text}
All improvement suggestions:
{chr(10).join(all_improvements)}

Write a combined personal branding assessment. Respond ONLY with a JSON object from {{ to }}:
{{
  "summary": "<4 sentences combining insights from all 4 components into one coherent narrative specific to this student and role>",
  "top_priorities": ["<most impactful improvement across all sections>", "<second most impactful>", "<third most impactful>"]
}}"""

    client = OpenAI(api_key=get_openai_api_key())
    response = client.chat.completions.create(
        model=MODEL_COACH,
        messages=[{"role": "user", "content": prompt}],
        temperature=TEMP_COACH,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"```\s*$", "", raw)
    raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "summary": "Unable to generate summary. Review the section feedback above for details.",
            "top_priorities": ["Re-submit your work to regenerate the AI summary."],
        }


# ---------------------------------------------------------------------------
# Screen 6 — Scorecard
# ---------------------------------------------------------------------------

def screen_scorecard() -> None:
    scores = st.session_state["ch11_scores"]
    feedback = st.session_state["ch11_feedback"]
    name = st.session_state["ch11_student_name"]
    title = st.session_state["ch11_job_title"]
    company = st.session_state["ch11_company"]

    total = sum(scores.get(k, 0) or 0 for k in SECTION_MAX)

    if total >= 90:
        tier, color = "Outstanding", "#27AE60"
    elif total >= 75:
        tier, color = "Strong Candidate", "#4A90D9"
    elif total >= 60:
        tier, color = "Developing", "#F39C12"
    else:
        tier, color = "Keep Improving", "#E74C3C"

    st.info(
        "📸 Screenshot this page to submit to Canvas — "
        "your name and date must be visible in the screenshot."
    )

    st.title("Chapter 11 — Personal Branding Scorecard")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Student", name)
    with col2:
        st.metric("Target Role", f"{title} at {company}")
    with col3:
        st.metric("Date", str(date.today()))

    st.markdown("---")

    st.markdown(
        f"""
        <div style="background:{color}22; border:3px solid {color}; border-radius:12px;
             padding:1.5rem; margin:0.5rem 0 1rem 0; text-align:center;">
          <div style="font-size:0.85rem; color:{color}; font-weight:700; text-transform:uppercase;
               letter-spacing:0.08em; margin-bottom:0.4rem;">Overall Score</div>
          <div style="font-size:3.2rem; font-weight:900; color:{color}; line-height:1.1;">{total}/100</div>
          <div style="font-size:1.25rem; font-weight:700; color:{color}; margin-top:0.3rem;">{tier}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### Section Breakdown")

    SECTION_DISPLAY = [
        ("resume",       "📄 Resume",       20),
        ("linkedin",     "💼 LinkedIn",     20),
        ("pitch_written","✍️ Pitch Written", 25),
        ("pitch_voice",  "🎤 Pitch Voice",   35),
    ]

    for row in [SECTION_DISPLAY[:2], SECTION_DISPLAY[2:]]:
        cols = st.columns(2, gap="medium")
        for i, (key, label, max_pts) in enumerate(row):
            with cols[i]:
                sec_score = scores.get(key, 0) or 0
                strongest = feedback.get(key, {}).get("strongest_element", "—")
                pct = sec_score / max_pts if max_pts > 0 else 0
                st.markdown(
                    f"""
                    <div style="background:#1A2332; border:1px solid #2E5FA3;
                         border-radius:10px; padding:1rem; margin-bottom:0.3rem;">
                      <div style="color:#4A90D9; font-weight:700; font-size:0.88rem;
                           margin-bottom:0.25rem;">{label}</div>
                      <div style="font-size:1.7rem; font-weight:800; color:#FAFAFA;
                           line-height:1.1;">{sec_score}/{max_pts}</div>
                      <div style="color:#aaa; font-size:0.8rem; margin-top:0.35rem;">
                        ⭐ {strongest}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.progress(pct)

    st.markdown("---")

    if not st.session_state.get("ch11_scorecard_summary"):
        with st.spinner("Generating your personal branding summary…"):
            summary_data = _generate_scorecard_summary()
        st.session_state["ch11_scorecard_summary"] = summary_data
    else:
        summary_data = st.session_state["ch11_scorecard_summary"]

    st.markdown("### 📋 Your Personal Branding Summary")
    st.markdown(summary_data.get("summary", ""))

    st.markdown("### 🎯 Your Top 3 Priorities")
    for i, item in enumerate(summary_data.get("top_priorities", []), 1):
        st.markdown(f"**{i}.** {item}")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "🔄 Improve a section",
            type="primary",
            use_container_width=True,
            key="ch11_sc_improve",
        ):
            for k in st.session_state["ch11_locked"]:
                st.session_state["ch11_locked"][k] = False
            st.session_state["ch11_phase"] = "resume"
            st.session_state["ch11_scorecard_summary"] = None
            st.rerun()
    with col2:
        if st.button(
            "🆕 Start over",
            use_container_width=True,
            key="ch11_sc_reset",
        ):
            _reset_state()
            st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_chapter11() -> None:
    _init_state()
    phase = st.session_state["ch11_phase"]
    if phase == "setup":
        screen_setup()
    elif phase == "resume":
        screen_resume()
    elif phase == "linkedin":
        screen_linkedin()
    elif phase == "pitch_written":
        screen_pitch_written()
    elif phase == "pitch_voice":
        screen_pitch_voice()
    elif phase == "scorecard":
        screen_scorecard()
    else:
        screen_setup()
