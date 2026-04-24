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


# ---------------------------------------------------------------------------
# Screen 1 — Setup
# ---------------------------------------------------------------------------

def screen_setup() -> None:
    rec_key = st.session_state["ch1_recruiter_key"]
    rec = RECRUITERS[rec_key]

    st.title("Chapter 1 — The Selling Profession")

    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:8px; padding:0.9rem 1.1rem; margin-bottom:0.75rem;">
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.4rem;">
            &#128188; Your Interviewer
          </div>
          <div style="color:#FAFAFA; font-size:1.05rem; margin-bottom:0.15rem;">
            <strong>{_html.escape(rec['name'])}</strong>
            &mdash; {_html.escape(rec['company'])}
          </div>
          <div style="color:#aaa;">
            Role you are interviewing for:
            <strong>{_html.escape(rec['role'])}</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.75rem;">
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.5rem;">
            &#128188; What to expect
          </div>
          <div style="color:#FAFAFA; margin-bottom:0.5rem;">
            6 questions. Answer specifically &mdash; generic answers score poorly.
          </div>
          <div style="color:#FAFAFA; margin-bottom:0.2rem;">&#9989; Give real examples</div>
          <div style="color:#FAFAFA; margin-bottom:0.2rem;">&#9989; Show you understand B2B sales</div>
          <div style="color:#FAFAFA; margin-bottom:0.2rem;">&#9989; Sound like yourself, not a textbook</div>
          <div style="color:#FAFAFA;">&#9989; Demonstrate self-awareness</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**Your full name (appears on your scorecard):**")
    student_name = st.text_input(
        "Your full name",
        value=st.session_state["ch1_student_name"],
        placeholder="e.g. Ana García",
        key="ch1_name_input",
        label_visibility="collapsed",
    )

    ready = bool(student_name.strip())
    if not ready:
        st.caption("Enter your name above to enable the Start button.")

    if st.button(
        "Begin Interview →",
        disabled=not ready,
        type="primary",
        use_container_width=True,
    ):
        st.session_state["ch1_student_name"] = student_name.strip()
        st.session_state["ch1_phase"] = "interview"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 2 — Interview
# ---------------------------------------------------------------------------

def screen_interview() -> None:
    rec_key = st.session_state["ch1_recruiter_key"]
    rec = RECRUITERS[rec_key]
    messages = st.session_state["ch1_messages"]
    question_count = st.session_state["ch1_question_count"]

    # First render: generate recruiter's opening question
    if not messages:
        with st.spinner("Connecting to your interviewer…"):
            opening = call_recruiter_api([], rec_key)
        st.session_state["ch1_messages"] = [{"role": "assistant", "content": opening}]
        st.rerun()
        return

    st.title("Chapter 1 — The Selling Profession")

    progress_label = (
        f"Question {question_count + 1} of 6" if question_count < 6 else "Interview complete"
    )
    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:6px; padding:0.45rem 0.8rem; margin-bottom:0.65rem;
             font-size:0.92rem;">
          <span style="color:#4A90D9; font-weight:700;">&#127919; {progress_label}</span>
          <span style="color:#aaa; font-size:0.82rem;">
            &nbsp;&middot;&nbsp; {_html.escape(rec['name'])}
            &mdash; {_html.escape(rec['company'])}
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for msg in messages:
        if msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="👔"):
                st.write(msg["content"])
        else:
            with st.chat_message("user", avatar="🎓"):
                st.write(msg["content"])

    if question_count < 6:
        user_input = st.chat_input("Type your answer…")
        if user_input and user_input.strip():
            updated = list(messages)
            updated.append({"role": "user", "content": user_input.strip()})
            with st.spinner("Interviewer responding…"):
                reply = call_recruiter_api(updated, rec_key)
            updated.append({"role": "assistant", "content": reply})
            st.session_state["ch1_messages"] = updated
            st.session_state["ch1_question_count"] = question_count + 1
            st.rerun()
    else:
        st.markdown("---")
        if st.button(
            "Finish & Reflect →",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["ch1_phase"] = "reflection"
            st.rerun()


# ---------------------------------------------------------------------------
# Screen 3 — Self-reflection
# ---------------------------------------------------------------------------

def screen_reflection() -> None:
    st.title("Chapter 1 — The Selling Profession")

    st.markdown(
        """
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:8px; padding:1rem 1.2rem; margin-bottom:1rem;">
          <div style="font-weight:700; color:#4A90D9; font-size:1.05rem;
               margin-bottom:0.4rem;">
            Before you see your score &mdash; reflect:
          </div>
          <div style="color:#ddd;">
            Your self-assessment will appear alongside your AI evaluation score.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ref = st.session_state.get(
        "ch1_reflection", {"confidence": 3, "specificity": 3, "authentic": 3}
    )

    confidence = st.slider(
        "How confident did you feel?", 1, 5, ref["confidence"], key="ch1_ref_conf"
    )
    specificity = st.slider(
        "How specific were your answers?", 1, 5, ref["specificity"], key="ch1_ref_spec"
    )
    authentic = st.slider(
        "Did you sound like yourself?", 1, 5, ref["authentic"], key="ch1_ref_auth"
    )

    st.markdown("&nbsp;")
    if st.button("See My Score →", type="primary", use_container_width=True):
        st.session_state["ch1_reflection"] = {
            "confidence": confidence,
            "specificity": specificity,
            "authentic": authentic,
        }
        with st.spinner("Evaluating your interview — this may take 15–25 seconds…"):
            scorecard = call_coach_api(
                st.session_state["ch1_messages"],
                st.session_state["ch1_student_name"],
                st.session_state["ch1_recruiter_key"],
            )
        st.session_state["ch1_scorecard"] = scorecard
        st.session_state["ch1_phase"] = "scorecard"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 4 — Scorecard
# ---------------------------------------------------------------------------

def screen_scorecard() -> None:
    data = st.session_state.get("ch1_scorecard") or {}
    rec_key = st.session_state["ch1_recruiter_key"]
    rec = RECRUITERS[rec_key]
    student_name = st.session_state["ch1_student_name"]
    ref = st.session_state.get(
        "ch1_reflection", {"confidence": 3, "specificity": 3, "authentic": 3}
    )

    total = data.get("total_score", 0)
    tier = data.get("tier", "")

    _TIER_COLORS = {
        "Offer Extended":   "#27AE60",
        "Strong Candidate": "#2E5FA3",
        "Developing":       "#F39C12",
        "Not Ready Yet":    "#E74C3C",
    }
    tier_color = _TIER_COLORS.get(tier, "#888")

    st.title("Chapter 1 — Recruiter Scorecard")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Student", student_name)
    with c2:
        st.metric("Position", f"{rec['company']} · {rec['role']}")
    with c3:
        st.metric("Date", date.today().strftime("%b %d, %Y"))

    st.markdown("---")

    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #2E5FA3; border-radius:8px;
             padding:0.7rem 1rem; margin-bottom:0.8rem; font-size:0.9rem; color:#ddd;">
          <strong style="color:#4A90D9;">Your self-assessment:</strong>
          &nbsp; Confidence {ref['confidence']}/5
          &nbsp;&middot;&nbsp; Specificity {ref['specificity']}/5
          &nbsp;&middot;&nbsp; Authenticity {ref['authentic']}/5
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style="background:{tier_color}22; border:2px solid {tier_color};
             border-radius:10px; padding:1rem 1.2rem; margin-bottom:1rem; text-align:center;">
          <div style="font-size:2.2rem; font-weight:700; color:{tier_color};">{total} / 100</div>
          <div style="font-size:1.05rem; font-weight:600; color:{tier_color}; margin-top:0.2rem;">
            {_html.escape(tier)}
          </div>
          <div style="color:#ddd; font-size:0.9rem; margin-top:0.5rem;">
            {_html.escape(data.get('plain_english_summary', ''))}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Score Breakdown")
    for dim in data.get("dimensions", []):
        score = dim.get("score", 0)
        max_pts = dim.get("max_points", 0)
        pct = int(score / max_pts * 100) if max_pts else 0
        bar_color = "#27AE60" if pct >= 75 else ("#F39C12" if pct >= 50 else "#E74C3C")
        label = f"{dim.get('name', '')}  —  {score} / {max_pts}"
        with st.expander(label, expanded=(pct < 70)):
            st.markdown(
                f"""
                <div style="background:#0E1117; border-radius:4px; height:6px;
                     margin-bottom:0.6rem;">
                  <div style="background:{bar_color}; width:{pct}%; height:6px;
                       border-radius:4px;"></div>
                </div>
                <div style="color:#aaa; font-size:0.87rem; margin-bottom:0.4rem;">
                  <em>&#8220;{_html.escape(dim.get('evidence', ''))}&#8221;</em>
                </div>
                """,
                unsafe_allow_html=True,
            )
            coaching = dim.get("coaching_note", "")
            if pct < 70:
                st.info(coaching)
            else:
                st.caption(coaching)

    st.markdown("---")
    ka, kb = st.columns(2)
    with ka:
        st.markdown(
            f"""
            <div style="background:#1A2332; border-left:4px solid #27AE60;
                 border-radius:6px; padding:0.8rem 1rem;">
              <div style="color:#27AE60; font-weight:700; margin-bottom:0.3rem;">
                &#127942; Strongest Moment
              </div>
              <div style="color:#ddd;">
                {_html.escape(data.get('strongest_moment', ''))}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kb:
        st.markdown(
            f"""
            <div style="background:#1A2332; border-left:4px solid #E74C3C;
                 border-radius:6px; padding:0.8rem 1rem;">
              <div style="color:#E74C3C; font-weight:700; margin-bottom:0.3rem;">
                &#128270; Critical Gap
              </div>
              <div style="color:#ddd;">
                {_html.escape(data.get('critical_gap', ''))}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("&nbsp;")
    st.markdown(
        f"""
        <div style="background:#1A2332; border-left:4px solid #F39C12;
             border-radius:6px; padding:0.8rem 1rem; margin-top:0.5rem;">
          <div style="color:#F39C12; font-weight:700; margin-bottom:0.3rem;">
            &#128218; Practice Recommendation
          </div>
          <div style="color:#ddd;">
            {_html.escape(data.get('behavioral_recommendation', ''))}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    if st.button("Try Again →", use_container_width=True):
        _reset_state()
        st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_chapter1() -> None:
    _init_state()
    phase = st.session_state["ch1_phase"]
    if phase == "setup":
        screen_setup()
    elif phase == "interview":
        screen_interview()
    elif phase == "reflection":
        screen_reflection()
    else:
        screen_scorecard()
