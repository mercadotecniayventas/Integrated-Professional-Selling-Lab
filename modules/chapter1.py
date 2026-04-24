import json
import random
import re
import html as _html
import streamlit as st
from datetime import date
from openai import OpenAI
from config import get_openai_api_key

MODEL = "gpt-4.1-mini"
TEMP_RECRUITER = 0.7
TEMP_EVAL = 0.2

# ---------------------------------------------------------------------------
# Recruiter data
# ---------------------------------------------------------------------------

RECRUITERS = {
    "alex_rivera": {
        "name": "Alex Rivera",
        "company": "CloudPulse Solutions",
        "industry": "Tech SaaS",
        "role": "Sales Development Representative (SDR)",
        "style": (
            "Direct, fast-paced, conversational. Values adaptability and AI literacy. "
            "Skeptical of candidates who give rehearsed or memorized answers."
        ),
        "questions": [
            (
                "Hey, thanks for coming in. I'll be straight — we move fast here. "
                "Tell me something about yourself that's NOT on your resume."
            ),
            "Why sales? And I mean really — not the rehearsed answer.",
            (
                "Our reps use AI tools daily. How do you think AI changes what it "
                "means to be good at sales?"
            ),
            (
                "Tell me about a time you kept going after repeated rejection. "
                "What kept you going?"
            ),
            "What's the most important thing a rep does in a discovery call — and why?",
            (
                "Last one: if your numbers were low in month 3, what would you do?"
            ),
        ],
    },
    "patricia_moore": {
        "name": "Patricia Moore",
        "company": "Vantex Industrial Solutions",
        "industry": "Manufacturing",
        "role": "Sales Representative",
        "style": (
            "Formal, process-oriented, traditional. Values reliability and ethics. "
            "Pushes back directly if answers are vague or generic."
        ),
        "questions": [
            (
                "Good morning. We've been in industrial sales 40 years and take hiring "
                "seriously. Why do you want to work in B2B sales?"
            ),
            (
                "Many think sales is about persuasion. We disagree. How would YOU "
                "define what a sales professional actually does?"
            ),
            (
                "Our cycles run 6–12 months. How do you stay organized and motivated "
                "when results take a long time?"
            ),
            "Describe a situation where you had to earn trust from someone initially skeptical of you.",
            (
                "One of our core values is ethics. Have you ever chosen the right "
                "thing over the easy thing?"
            ),
            "Where do you see yourself in this profession in 5 years?",
        ],
    },
    "david_chen": {
        "name": "David Chen",
        "company": "Meridian Capital Advisors",
        "industry": "Financial Services",
        "role": "Business Development Representative (BDR)",
        "style": (
            "Very formal, detail-oriented. Values professionalism, trust, and precision. "
            "Will push back clearly when answers are generic or vague."
        ),
        "questions": [
            (
                "Good afternoon. Our clients trust us with their most important financial "
                "decisions. What makes you someone who can earn that kind of trust?"
            ),
            (
                "B2B financial services is relationship-driven, not transactional. "
                "What does that mean to you in practice?"
            ),
            (
                "If a client raises concerns about your fees vs a competitor, "
                "how do you respond without discounting?"
            ),
            (
                "What do you know about how B2B buying decisions are made — and "
                "how does that change your approach?"
            ),
            "Tell me about an experience where you demonstrated genuine business acumen.",
            "Final question: why Meridian specifically, and why now?",
        ],
    },
}

_RECRUITER_KEYS = list(RECRUITERS.keys())


def get_system_prompt(recruiter_key: str) -> str:
    rec = RECRUITERS[recruiter_key]
    questions_block = "\n".join(
        f"  Q{i + 1}: {q}" for i, q in enumerate(rec["questions"])
    )
    return f"""You are {rec['name']}, a recruiter at {rec['company']} interviewing a candidate for the role of {rec['role']}.

INDUSTRY: {rec['industry']}
YOUR STYLE: {rec['style']}

YOUR 6 INTERVIEW QUESTIONS (ask them in this exact order):
{questions_block}

RULES — follow these exactly:
1. Ask ONE question per turn. Never ask two questions in the same message.
2. Ask the questions in order. Do not skip any question.
3. After the student answers a question, respond briefly (1–3 sentences) then ask the next question.
4. If the student gives a generic or rehearsed answer, say: "That's a common answer. Give me something more specific — a real example or your actual opinion." Then still ask the next question.
5. If the student gives a strong, specific answer, acknowledge it briefly ("Good." / "That's useful." / "Appreciate the honesty.") then move to the next question.
6. If the student naturally references B2B concepts (discovery, pipeline, multi-stakeholder decisions, relationship-building, long sales cycles) without naming them as textbook terms, show genuine brief interest before moving on.
7. After the student has answered Q6 (the final question), respond with: "Thank you for your time. We'll be in touch." Then stop — do not ask any further questions.
8. Never break character. Always respond in English. Never mention you are an AI."""


# ---------------------------------------------------------------------------
# Coach evaluation prompt
# ---------------------------------------------------------------------------

def get_coach_prompt(conversation_history: list, student_name: str, recruiter_key: str) -> str:
    rec = RECRUITERS[recruiter_key]
    lines = []
    for msg in conversation_history:
        speaker = rec["name"] if msg["role"] == "assistant" else student_name
        lines.append(f"{speaker}: {msg['content']}")
    transcript = "\n\n".join(lines)

    return f"""You are evaluating a mock job interview for a B2B sales position.

RECRUITER: {rec['name']} at {rec['company']}
ROLE: {rec['role']}
STUDENT: {student_name}

INTERVIEW TRANSCRIPT:
{transcript}

Evaluate the student on exactly 5 dimensions. Return ONLY valid JSON — start with {{ and end with }}.

{{
  "dimensions": [
    {{
      "name": "Professional Identity",
      "score": <0|10|18|25>,
      "max_points": 25,
      "evidence": "<exact quote from student or 'Not demonstrated'>",
      "coaching_note": "<specific actionable feedback>"
    }},
    {{
      "name": "Knowledge of the Profession",
      "score": <0|10|18|25>,
      "max_points": 25,
      "evidence": "<exact quote or 'Not demonstrated'>",
      "coaching_note": "<specific feedback>"
    }},
    {{
      "name": "Self-Awareness",
      "score": <0|8|14|20>,
      "max_points": 20,
      "evidence": "<exact quote or 'Not demonstrated'>",
      "coaching_note": "<specific feedback>"
    }},
    {{
      "name": "Authentic Communication",
      "score": <0|8|14|20>,
      "max_points": 20,
      "evidence": "<exact quote or 'Not demonstrated'>",
      "coaching_note": "<specific feedback>"
    }},
    {{
      "name": "Career Readiness",
      "score": <0|3|7|10>,
      "max_points": 10,
      "evidence": "<exact quote or 'Not demonstrated'>",
      "coaching_note": "<specific feedback>"
    }}
  ],
  "total_score": <sum of all scores, 0-100>,
  "tier": "<Offer Extended|Strong Candidate|Developing|Not Ready Yet>",
  "plain_english_summary": "<exactly 2 sentences summarizing overall performance>",
  "strongest_moment": "<the single strongest thing the student said, with brief context>",
  "critical_gap": "<the most important thing missing from their answers>",
  "behavioral_recommendation": "<one specific practice to improve before the next interview>"
}}

SCORING RUBRIC:

Professional Identity (25 pts):
  25 = Consistently framed sales as diagnosing problems and building trust
  18 = Mostly correct framing, one slip into transactional language
  10 = Mixed — some good moments, some stereotypical sales language
   0 = Defined sales as persuasion, closing, or convincing people to buy

Knowledge of the Profession (25 pts):
  25 = Referenced specific B2B concepts naturally (discovery, multi-stakeholder decisions, pipeline, relationship over transaction)
  18 = General understanding but surface level
  10 = Generic business knowledge, nothing B2B-specific
   0 = No evidence of understanding B2B complexity

Self-Awareness (20 pts):
  20 = Specific personal examples that clearly connect to sales competencies
  14 = Some self-awareness but examples were vague
   8 = Talked about themselves without connecting to the profession
   0 = Only abstract claims, no personal examples

Authentic Communication (20 pts):
  20 = Answers felt personal, specific, honest
  14 = Mostly genuine with one or two generic moments
   8 = Sounded scripted or memorized throughout
   0 = Completely generic — could apply to anyone

Career Readiness (10 pts):
  10 = Articulated a genuine, specific motivation for sales
   7 = Motivation present but vague
   3 = Generic "I like people" type answer
   0 = No clear motivation expressed

Tier thresholds: 90-100 = "Offer Extended", 75-89 = "Strong Candidate", 60-74 = "Developing", below 60 = "Not Ready Yet"

Return ONLY the JSON object. No markdown fences, no explanation."""


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def call_recruiter_api(messages: list, recruiter_key: str) -> str:
    client = OpenAI(api_key=get_openai_api_key())
    payload = [{"role": "system", "content": get_system_prompt(recruiter_key)}] + messages
    response = client.chat.completions.create(
        model=MODEL,
        messages=payload,
        temperature=TEMP_RECRUITER,
    )
    return response.choices[0].message.content.strip()


def _parse_json(raw: str) -> dict:
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
            "tier": "Error",
            "plain_english_summary": "Could not parse the evaluation. Please try again.",
            "strongest_moment": "",
            "critical_gap": "",
            "behavioral_recommendation": "",
            "_error": True,
        }


def call_coach_api(conversation_history: list, student_name: str, recruiter_key: str) -> dict:
    client = OpenAI(api_key=get_openai_api_key())
    prompt = get_coach_prompt(conversation_history, student_name, recruiter_key)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=TEMP_EVAL,
    )
    return _parse_json(response.choices[0].message.content.strip())


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def _init_state() -> None:
    # Persistent rotation tracker — survives resets
    if "ch1_last_recruiter" not in st.session_state:
        st.session_state["ch1_last_recruiter"] = None

    if "ch1_recruiter_key" not in st.session_state:
        last = st.session_state["ch1_last_recruiter"]
        available = [k for k in _RECRUITER_KEYS if k != last]
        if not available:
            available = _RECRUITER_KEYS[:]
        chosen = random.choice(available)
        st.session_state["ch1_recruiter_key"] = chosen
        st.session_state["ch1_last_recruiter"] = chosen

    defaults = {
        "ch1_phase": "setup",
        "ch1_student_name": "",
        "ch1_messages": [],
        "ch1_question_count": 0,
        "ch1_reflection": {"confidence": 3, "specificity": 3, "authentic": 3},
        "ch1_scorecard": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _reset_state() -> None:
    last = st.session_state.get("ch1_last_recruiter")
    for k in [
        "ch1_phase", "ch1_student_name", "ch1_recruiter_key",
        "ch1_messages", "ch1_question_count",
        "ch1_reflection", "ch1_scorecard",
    ]:
        st.session_state.pop(k, None)
    st.session_state["ch1_last_recruiter"] = last
    _init_state()
