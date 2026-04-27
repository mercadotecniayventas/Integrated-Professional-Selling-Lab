import io
import json
import re
import streamlit as st
from datetime import date
from openai import OpenAI
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

Evaluate across 3 dimensions. Do NOT penalize spelling or grammar — evaluate strategic content only.

Dimensions and max points:
1. Keyword Alignment (8 pts): Does the resume use language, skills, and terminology from the job posting?
2. Impact & Metrics (7 pts): Are achievements quantified with numbers, percentages, or concrete outcomes?
3. Role Relevance (5 pts): Is the experience directly relevant to this specific role at this specific company?

Scoring tiers per dimension: award points based on how well the content meets the criterion.
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

Evaluate across 3 dimensions. Do NOT penalize spelling or grammar — evaluate strategic content only.

Dimensions and max points:
1. Headline Positioning (8 pts): Does the headline clearly communicate value and align with the target role?
2. About Section (8 pts): Does the About section tell a compelling story that speaks the employer's language?
3. Keyword Optimization (4 pts): Does the profile use keywords from the job posting that recruiters search for?

Scoring tiers per dimension: award points based on how well the content meets the criterion.
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

Evaluate across 5 dimensions. Do NOT penalize spelling or grammar — evaluate strategic content only.

Dimensions and max points:
1. Hook (5 pts): Does the opening grab attention and make the listener want to hear more?
2. Who You Are (5 pts): Does the student clearly state who they are and what they bring?
3. Value Proposition (8 pts): Does the student articulate a clear, specific value they offer this employer?
4. Call to Action (5 pts): Does the pitch end with a clear, confident ask or next step?
5. Job Alignment (2 pts): Does the pitch speak directly to this role and company, not generically?

Scoring tiers per dimension: award points based on how well the content meets the criterion.
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

Evaluate across 5 dimensions. Do NOT penalize spelling or grammar — evaluate strategic content and delivery only.

Dimensions and max points:
1. Hook (7 pts): Does the opening grab attention and make the listener want to hear more?
2. Fluency (7 pts): Does the delivery sound natural and conversational, or does it sound scripted and read aloud?
3. Value Proposition (10 pts): Does the student articulate a clear, specific value they offer this employer?
4. Call to Action (7 pts): Does the pitch end with a clear, confident ask or next step?
5. Timing (4 pts): 60–90 sec = full 4 pts; 45–60 or 90–105 sec = 2 pts; outside that range = 0 pts.

Scoring tiers per dimension: award points based on how well the content meets the criterion.
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
# Entry point (Part 1 placeholder — screens added in Part 2 & 3)
# ---------------------------------------------------------------------------

def run_chapter11() -> None:
    _init_state()
    phase = st.session_state["ch11_phase"]
    if phase == "setup":
        screen_setup()
    else:
        st.info("Screens for this phase are coming in Part 2.")
