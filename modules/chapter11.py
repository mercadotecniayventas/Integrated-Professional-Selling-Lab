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
        "ch11_voice_messages": [],
        "ch11_voice_enabled": True,
        "ch11_recruiter_name": "",
        "ch11_recruiter_voice": "alloy",
        "ch11_interview_complete": False,
        "ch11_tts_bytes": None,
        "ch11_last_audio_id": None,
        "ch11_generating": False,
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
  "strongest_element": "<what the student did best>"
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
  "strongest_element": "<what the student did best>"
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
  "strongest_element": "<what the student did best>"
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
  "strongest_element": "<what the student did best>"
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


def call_tts_api(text: str, voice: str = "alloy") -> bytes | None:
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


_SECTION_LABELS = {
    "resume": "resume",
    "linkedin": "LinkedIn profile",
    "pitch_written": "written elevator pitch",
    "pitch_voice": "voice elevator pitch script",
}

_SECTION_FIX_INSTRUCTIONS = {
    "resume": (
        "- If Keyword Alignment lost points: add the exact missing keywords from the job posting into relevant sections\n"
        "- If Impact & Metrics lost points: add specific numbers to every vague claim\n"
        "- If Role Relevance lost points: reframe every experience to directly connect to job duties"
    ),
    "linkedin": (
        "- If Headline Positioning lost points: rewrite the headline to directly target this role using the posting's exact keywords\n"
        "- If About Section lost points: open with a hook, tell a connected story, close with a CTA\n"
        "- If Keyword Optimization lost points: weave the missing keywords naturally into both headline and about\n"
        "Format the output as: HEADLINE: [headline text]\\n\\nABOUT: [about text]"
    ),
    "pitch_written": (
        "- If Hook lost points: rewrite the opening to immediately create interest\n"
        "- If Who You Are lost points: state identity and background more clearly and confidently\n"
        "- If Value Proposition lost points: add specifics tied to this employer's exact needs\n"
        "- If Call to Action lost points: add a confident, specific close\n"
        "- If Job Alignment lost points: add an explicit reference to the company and role\n"
        "Target 130–200 words."
    ),
    "pitch_voice": (
        "- If Hook lost points: rewrite the opening to sound natural and engaging when spoken aloud\n"
        "- If Structure & Clarity lost points: organize clearly into who you are → what you offer → why them\n"
        "- If Language Confidence lost points: use shorter sentences, contractions, natural rhythm — write for the ear\n"
        "- If Value Proposition lost points: make value specific and tied to this employer's needs\n"
        "- If Call to Action lost points: add a confident, natural-sounding close\n"
        "Target 130–200 words, written for spoken delivery."
    ),
}


def call_improve_api(
    section_key: str,
    evaluation: dict,
    original_content: str,
    job_posting: str,
    student_name: str,
    job_title: str,
    company: str,
) -> str:
    """Generate a targeted improved version that explicitly fixes every identified weakness."""
    dimensions = evaluation.get("dimensions", [])
    total_score = evaluation.get("total_score", 0)
    max_score = SECTION_MAX[section_key]
    section_label = _SECTION_LABELS.get(section_key, section_key)
    fix_instructions = _SECTION_FIX_INSTRUCTIONS.get(section_key, "")

    dim_lines = ""
    for dim in dimensions:
        pts_lost = dim.get("max_points", 0) - dim.get("score", 0)
        dim_lines += (
            f"\n{dim['name']}: {dim['score']}/{dim['max_points']} pts"
            f" ({pts_lost} pts lost)\n"
            f"  What was weak: {dim.get('rationale', '')}\n"
            f"  Fix required: {dim.get('suggestion', '')}\n"
        )

    prompt = f"""You just evaluated a student's {section_label} and gave these scores:
{dim_lines}
Total: {total_score}/{max_score}

Student: {student_name}
Target role: {job_title} at {company}

JOB POSTING:
{job_posting}

ORIGINAL {section_label.upper()}:
{original_content}

Now rewrite this {section_label} to fix EVERY weakness you identified above:
{fix_instructions}

Rules:
- Do NOT add fictional facts — use only what the student actually wrote
- Use their real content but frame it to maximize every rubric dimension
- The rewritten version must earn full or near-full points on every dimension
- You know exactly what the rubric checks — write to pass it perfectly

Respond with ONLY the rewritten {section_label} — no explanation, no preamble, just the content."""

    client = OpenAI(api_key=get_openai_api_key())
    response = client.chat.completions.create(
        model=MODEL_COACH,
        messages=[{"role": "user", "content": prompt}],
        temperature=TEMP_COACH,
    )
    return response.choices[0].message.content.strip()


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
            "- Structure & Clarity: 7 pts\n"
            "- Language Confidence: 7 pts\n"
            "- Value Proposition: 10 pts\n"
            "- Call to Action: 4 pts"
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
        with st.spinner("Generating targeted improvement…"):
            data["improved_version"] = call_improve_api(
                "resume", data, text,
                st.session_state["ch11_job_posting"],
                st.session_state["ch11_student_name"],
                st.session_state["ch11_job_title"],
                st.session_state["ch11_company"],
            )
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
        with st.spinner("Generating targeted improvement…"):
            data["improved_version"] = call_improve_api(
                "linkedin", data, combined,
                st.session_state["ch11_job_posting"],
                st.session_state["ch11_student_name"],
                st.session_state["ch11_job_title"],
                st.session_state["ch11_company"],
            )
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
        with st.spinner("Generating targeted improvement…"):
            data["improved_version"] = call_improve_api(
                "pitch_written", data, text,
                st.session_state["ch11_job_posting"],
                st.session_state["ch11_student_name"],
                st.session_state["ch11_job_title"],
                st.session_state["ch11_company"],
            )
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
# Voice pitch — recruiter roleplay helpers
# ---------------------------------------------------------------------------

_CH11_RECRUITERS = [
    ("Jordan Ellis", "alloy"),
    ("Taylor Morgan", "nova"),
    ("Casey Rivera", "shimmer"),
    ("Alex Chen", "echo"),
    ("Sam Patel", "fable"),
]


def _generate_recruiter_info(company: str) -> tuple[str, str]:
    idx = sum(ord(c) for c in company) % len(_CH11_RECRUITERS)
    return _CH11_RECRUITERS[idx]


def get_pitch_recruiter_system_prompt(
    recruiter_name: str,
    job_title: str,
    company: str,
    job_posting: str,
) -> str:
    return f"""You are {recruiter_name}, a recruiter at {company} interviewing a candidate for the role of {job_title}.

You have a few minutes between sessions at a networking event. You will ask the candidate to deliver their elevator pitch, listen carefully, then ask exactly two follow-up questions.

YOUR STYLE: Professional, direct, genuinely curious. React briefly and naturally — not robotically.

SEQUENCE — follow this exactly:
1. Greet the candidate briefly and ask them to give you their elevator pitch (or tell you about themselves).
2. After they pitch, react in 1–2 sentences then ask ONE specific follow-up question about something they actually said.
3. After they answer, react briefly then ask ONE final follow-up question.
4. After they answer that final question, thank them genuinely and close the conversation.

RULES:
- Ask only ONE thing per turn. Never combine two questions in one message.
- Always respond in English only.
- Keep your responses short — 2–4 sentences max.
- After the student answers your final follow-up question, close with something like "Great talking with you — I'll be in touch." and append [INTERVIEW_COMPLETE] at the very end of your message on a new line.
- Never break character. Never mention you are an AI.

JOB POSTING (for context — do not quote directly):
{job_posting}"""


def call_pitch_recruiter_api(
    messages: list,
    recruiter_name: str,
    job_title: str,
    company: str,
    job_posting: str,
) -> str:
    client = OpenAI(api_key=get_openai_api_key())
    system = get_pitch_recruiter_system_prompt(recruiter_name, job_title, company, job_posting)
    payload = [{"role": "system", "content": system}] + messages
    response = client.chat.completions.create(
        model=MODEL_COACH,
        messages=payload,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def call_pitch_voice_coach_api(
    transcript: str,
    job_posting: str,
    student_name: str,
    job_title: str,
    company: str,
) -> dict:
    prompt = f"""You are an expert career coach evaluating a student's elevator pitch delivered during a recruiter roleplay.
Student: {student_name}
Target role: {job_title} at {company}

JOB POSTING:
{job_posting}

STUDENT'S PITCH (extracted from the roleplay — these are all the student's spoken turns):
{transcript}

Evaluate this pitch on FIVE dimensions ONLY:
1. Hook (7 pts): Did the opening create immediate interest? (any engaging opener counts — penalize only if it opens flat with zero hook)
2. Structure & Clarity (7 pts): Is the pitch well-organized? (who I am → what I offer → why them — any clear progression counts)
3. Language Confidence (7 pts): Did it sound natural and conversational? (contractions, rhythm, genuine delivery — penalize only if clearly robotic or memorized word-for-word)
4. Value Proposition (10 pts): Is there a specific value tied to this employer's needs? (transferable value from any background counts)
5. Call to Action (4 pts): Did it end with a clear, confident ask or close? (any genuine closing counts)

CRITICAL: Do NOT penalize for:
- Accent or non-native English patterns
- Brief filler words (um, uh) in moderation
- Academic or non-corporate background
- Short answers to the recruiter's follow-up questions — evaluate the main pitch delivery primarily

DO penalize for:
- No discernible hook — opening is entirely flat
- No clear value proposition — content is purely biographical with zero employer relevance
- No CTA — pitch stops without any close

A pitch with clear structure, natural delivery, specific transferable value, and a proper close should score 28–32/35.

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
      "name": "Structure & Clarity",
      "score": <int 0–7>,
      "max_points": 7,
      "rationale": "<2–3 sentences>",
      "suggestion": "<one concrete improvement>"
    }},
    {{
      "name": "Language Confidence",
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
      "score": <int 0–4>,
      "max_points": 4,
      "rationale": "<1–2 sentences>",
      "suggestion": "<one concrete improvement>"
    }}
  ],
  "total_score": <int 0–35>,
  "tier": "<Outstanding | Strong | Developing | Needs Work — keep improving>",
  "plain_english_summary": "<3–4 sentences on overall voice pitch quality>",
  "top_3_improvements": ["<improvement 1>", "<improvement 2>", "<improvement 3>"],
  "strongest_element": "<what the student did best>"
}}"""

    return call_coach_api(prompt, "pitch_voice")


# ---------------------------------------------------------------------------
# Screen 5 — Elevator Pitch (Voice)
# ---------------------------------------------------------------------------

def screen_pitch_voice() -> None:
    _render_progress_header()
    st.subheader("Step 4 — Elevator Pitch (Voice)")
    _render_job_ref()

    job_posting = st.session_state["ch11_job_posting"]
    job_title = st.session_state["ch11_job_title"]
    company = st.session_state["ch11_company"]
    student_name = st.session_state["ch11_student_name"]

    # Determine recruiter once per session
    if not st.session_state.get("ch11_recruiter_name"):
        name, voice = _generate_recruiter_info(company)
        st.session_state["ch11_recruiter_name"] = name
        st.session_state["ch11_recruiter_voice"] = voice
    recruiter_name = st.session_state["ch11_recruiter_name"]
    recruiter_voice = st.session_state.get("ch11_recruiter_voice", "alloy")

    written_pitch = st.session_state.get("ch11_pitch_written", "")
    if written_pitch:
        with st.expander("📝 Your written pitch (for reference)", expanded=False):
            st.markdown(written_pitch)

    locked = st.session_state["ch11_locked"]["pitch_voice"]
    messages = st.session_state.get("ch11_voice_messages", [])
    interview_complete = st.session_state.get("ch11_interview_complete", False)

    # --- Locked view ---
    if locked:
        if st.session_state["ch11_scores"]["pitch_voice"] is not None:
            _render_results("pitch_voice")
            st.markdown("---")
            action = _action_buttons("pitch_voice")
            if action == "unlock":
                st.session_state["ch11_locked"]["pitch_voice"] = False
                st.rerun()
        _maybe_back_button()
        return

    # --- No interview started yet ---
    if not messages:
        st.markdown(
            f"""
            <div style="background:#1B3A6B; border-radius:10px; padding:1rem 1.2rem;
                 margin-bottom:1rem; color:#FAFAFA;">
              <div style="font-weight:700; margin-bottom:0.4rem;">🎤 Recruiter Roleplay — Elevator Pitch</div>
              <div style="margin-bottom:0.5rem;">
                You will practice your elevator pitch with <strong>{recruiter_name}</strong>,
                a recruiter at {company}.
              </div>
              <div style="margin-bottom:0.25rem;">✅ Deliver your pitch naturally — no reading from a script</div>
              <div style="margin-bottom:0.25rem;">✅ Answer 2 follow-up questions</div>
              <div style="margin-bottom:0.25rem;">✅ Aim for 60–90 seconds on your main pitch</div>
              <div style="color:#B8C8E0; font-size:0.88rem; margin-top:0.5rem;">
                You can speak using the mic or type. Your pitch is scored on hook, structure,
                language confidence, value proposition, and call to action.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _hcol, _vcol = st.columns([5, 1])
        with _vcol:
            voice_on = st.toggle(
                "🔊 Voice",
                value=st.session_state.get("ch11_voice_enabled", True),
                key="ch11_voice_toggle",
            )
            st.session_state["ch11_voice_enabled"] = voice_on

        if st.button(
            "Begin Interview →",
            type="primary",
            use_container_width=True,
            key="ch11_begin_voice",
        ):
            with st.spinner("Connecting to your recruiter…"):
                try:
                    opening = call_pitch_recruiter_api(
                        [], recruiter_name, job_title, company, job_posting
                    )
                except Exception as exc:
                    st.error(f"Could not reach the recruiter ({exc}). Please try again.")
                    st.stop()
            clean_opening = opening.replace("[INTERVIEW_COMPLETE]", "").strip()
            st.session_state["ch11_voice_messages"] = [{"role": "assistant", "content": clean_opening}]
            if st.session_state.get("ch11_voice_enabled", True):
                with st.spinner("Generating voice…"):
                    tts = call_tts_api(clean_opening, voice=recruiter_voice)
                if tts:
                    st.session_state["ch11_tts_bytes"] = tts
            st.rerun()

        _maybe_back_button()
        return

    # --- Interview in progress or complete ---
    _hcol, _vcol = st.columns([5, 1])
    with _hcol:
        status = "Interview complete" if interview_complete else "Interview in progress"
        st.markdown(
            f"""
            <div style="background:#1A2332; border:1px solid #2E5FA3;
                 border-radius:6px; padding:0.45rem 0.8rem; margin-bottom:0.65rem;
                 font-size:0.92rem;">
              <span style="color:#4A90D9; font-weight:700;">🎤 {status}</span>
              <span style="color:#aaa; font-size:0.82rem;">
                &nbsp;·&nbsp; {recruiter_name} — {company}
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with _vcol:
        voice_on = st.toggle(
            "🔊 Voice",
            value=st.session_state.get("ch11_voice_enabled", True),
            key="ch11_voice_toggle",
        )
        st.session_state["ch11_voice_enabled"] = voice_on

    # Render chat history
    for msg in messages:
        if msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="👔"):
                st.write(msg["content"])
        else:
            with st.chat_message("user", avatar="🎓"):
                st.write(msg["content"])

    # Play pending TTS — cleared immediately so it only fires once
    tts_bytes = st.session_state.get("ch11_tts_bytes")
    if tts_bytes:
        st.audio(tts_bytes, format="audio/mp3", autoplay=True)
        st.session_state["ch11_tts_bytes"] = None

    if not interview_complete:
        # Mic input
        audio = mic_recorder(
            start_prompt="🎤 Click to speak",
            stop_prompt="⏹ Recording… click to stop",
            key="ch11_voice_mic",
        )
        if audio and audio.get("bytes"):
            if audio.get("id") != st.session_state.get("ch11_last_audio_id"):
                st.session_state["ch11_last_audio_id"] = audio["id"]
                with st.spinner("Transcribing…"):
                    t, _ = call_whisper_api(audio["bytes"])
                if t:
                    updated = list(st.session_state["ch11_voice_messages"])
                    updated.append({"role": "user", "content": t})
                    st.session_state["ch11_voice_messages"] = updated
                    st.session_state["ch11_generating"] = True
                    st.rerun()
                else:
                    st.warning("Could not transcribe — please try again or type below.")

        # Text fallback
        user_input = st.chat_input(
            "Type your answer…",
            disabled=st.session_state.get("ch11_generating", False),
        )
        if user_input and user_input.strip():
            updated = list(st.session_state["ch11_voice_messages"])
            updated.append({"role": "user", "content": user_input.strip()})
            st.session_state["ch11_voice_messages"] = updated
            st.session_state["ch11_generating"] = True
            st.rerun()

        # Generate recruiter response
        if st.session_state.get("ch11_generating", False):
            current_msgs = st.session_state["ch11_voice_messages"]
            try:
                with st.spinner("Recruiter responding…"):
                    reply = call_pitch_recruiter_api(
                        current_msgs, recruiter_name, job_title, company, job_posting
                    )
            except Exception as exc:
                st.error(f"The recruiter couldn't respond ({exc}). Please try again.")
                st.session_state["ch11_generating"] = False
                st.stop()

            complete = "[INTERVIEW_COMPLETE]" in reply
            clean_reply = reply.replace("[INTERVIEW_COMPLETE]", "").strip()

            updated = list(current_msgs)
            updated.append({"role": "assistant", "content": clean_reply})
            st.session_state["ch11_voice_messages"] = updated
            st.session_state["ch11_generating"] = False

            if complete:
                st.session_state["ch11_interview_complete"] = True

            if st.session_state.get("ch11_voice_enabled", True):
                with st.spinner("Generating voice…"):
                    tts = call_tts_api(clean_reply, voice=recruiter_voice)
                if tts:
                    st.session_state["ch11_tts_bytes"] = tts

            st.rerun()
    else:
        # Interview complete — show evaluate button if not yet scored
        st.markdown("---")
        if st.session_state["ch11_scores"]["pitch_voice"] is None:
            if st.button(
                "📊 Evaluate My Pitch →",
                type="primary",
                use_container_width=True,
                key="ch11_eval_voice_pitch",
            ):
                student_turns = [
                    m["content"]
                    for m in st.session_state["ch11_voice_messages"]
                    if m["role"] == "user"
                ]
                transcript = "\n\n".join(student_turns)
                st.session_state["ch11_pitch_voice_transcript"] = transcript

                with st.spinner("Evaluating your pitch…"):
                    data = call_pitch_voice_coach_api(
                        transcript, job_posting, student_name, job_title, company
                    )
                with st.spinner("Generating targeted improvement…"):
                    data["improved_version"] = call_improve_api(
                        "pitch_voice", data, transcript,
                        job_posting, student_name, job_title, company,
                    )
                st.session_state["ch11_feedback"]["pitch_voice"] = data
                st.session_state["ch11_scores"]["pitch_voice"] = data.get("total_score", 0)
                st.session_state["ch11_iterations"]["pitch_voice"] += 1
                st.rerun()

    # Show results if scored
    if st.session_state["ch11_scores"]["pitch_voice"] is not None:
        st.markdown("---")
        _render_results(
            "pitch_voice",
            extra_note=(
                "Your pitch is evaluated on hook, structure, language confidence, value, and CTA. "
                "Follow-up answers are not scored — only your main pitch delivery."
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
        elif action == "re_evaluate":
            st.session_state["ch11_interview_complete"] = False
            st.session_state["ch11_voice_messages"] = []
            st.session_state["ch11_scores"]["pitch_voice"] = None
            st.session_state["ch11_feedback"].pop("pitch_voice", None)
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
