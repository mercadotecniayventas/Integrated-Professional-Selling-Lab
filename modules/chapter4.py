import html as _html
import json
import re
import streamlit as st
from datetime import date
from openai import OpenAI
from config import get_openai_api_key

MODEL = "gpt-4.1-mini"
TEMP_PROMPT = 0.7
TEMP_COACH = 0.3
MAX_TOKENS = 300

# ---------------------------------------------------------------------------
# Round data
# ---------------------------------------------------------------------------

ROUNDS = [
    {
        "number": 1,
        "title": "Write from scratch",
        "situation": (
            "You are preparing cold outreach to David Park, VP Operations at Synthex "
            "Manufacturing (500 employees, freight and distribution, Houston TX). They "
            "recently opened a new distribution center. You sell supply chain analytics "
            "software at DataFlow Solutions."
        ),
        "task": "Write the AI prompt you would use to draft this outreach email.",
        "hint": (
            "A good prompt gives AI: who you are, who you're writing to, what you know "
            "about them, the goal, the tone, and the format.\n\n"
            "AI Limitations note: AI cannot know what research you've done about this "
            "prospect. Your prompt must include that research — AI only knows what you tell it."
        ),
        "bad_prompt": None,
        "word_limit": 200,
    },
    {
        "number": 2,
        "title": "Fix a broken prompt",
        "situation": (
            "A sales rep used this prompt to prepare SPIN questions for a discovery call. "
            "The output was useless."
        ),
        "bad_prompt": "Write me some good discovery questions for my sales call.",
        "task": (
            "Rewrite this prompt to get better SPIN questions. Include what information "
            "you would add and why."
        ),
        "hint": (
            "AI fails at Implication questions — they must respond to what the buyer "
            "actually said, not assumed answers. A good prompt acknowledges this limitation.\n\n"
            "AI Limitations note: The book says AI fails at Implication questions because "
            "they must respond to what the BUYER actually said during the call — not assumed "
            "answers. A strong prompt acknowledges this."
        ),
        "word_limit": 200,
    },
    {
        "number": 3,
        "title": "Explain why it failed",
        "situation": (
            "A rep used AI to prepare a response to this objection: 'Your price is too high.' "
            "The AI output was: 'I understand price is a concern. Our solution offers great ROI "
            "and many customers have found it worth the investment. Would you like to see some "
            "case studies?' The rep used it in the call. The buyer said: 'That sounds scripted.'"
        ),
        "task": (
            "In 2–3 sentences, explain why this AI output failed — and what the prompt was "
            "missing that caused this."
        ),
        "hint": (
            "AI without buyer context produces generic responses. Price objections require "
            "knowing WHY the buyer said it — which only comes from good discovery.\n\n"
            "AI Limitations note: AI without buyer context produces generic responses. It "
            "cannot know WHY this specific buyer said the price was too high — only you know "
            "that from discovery."
        ),
        "bad_prompt": None,
        "word_limit": 100,
    },
    {
        "number": 4,
        "title": "Write with constraint",
        "situation": (
            "You are about to enter a discovery call with Maria Santos, CFO at Greenfield "
            "Energy. You have her name, title, and company — nothing else. You want AI to "
            "help you prepare good questions."
        ),
        "task": (
            "Write a prompt that gets useful discovery preparation from AI — but you cannot "
            "invent information you don't have. The prompt must acknowledge what you DON'T "
            "know and ask AI to help you prepare for uncertainty."
        ),
        "hint": (
            "The best AI users know what they know and what they don't. Prompts that assume "
            "information produce confident but wrong outputs.\n\n"
            "AI Limitations note: AI cannot invent information you don't have. The best "
            "prompts tell AI what you DON'T know and ask it to help you prepare for that "
            "uncertainty."
        ),
        "bad_prompt": None,
        "word_limit": 200,
    },
]

# ---------------------------------------------------------------------------
# Expert prompts (internal — never shown to student)
# ---------------------------------------------------------------------------

EXPERT_PROMPTS = {
    1: (
        "I am a sales rep at DataFlow Solutions selling supply chain analytics software. "
        "Write a cold outreach email to David Park, VP Operations at Synthex Manufacturing "
        "(500 employees, freight and distribution, Houston TX). Key context: they recently "
        "opened a new distribution center in Texas, which likely means new operational "
        "complexity and visibility challenges. Tone: professional but conversational, not "
        "salesy. Format: subject line + 3 short paragraphs + CTA for a 15-minute call. "
        "Under 150 words. Do not use generic phrases like 'I hope this finds you well.'"
    ),
    2: (
        "I am preparing for a discovery call with a VP of Operations at a mid-size "
        "manufacturing company. Generate Situation and Problem SPIN questions I can prepare "
        "in advance. Note: do NOT generate Implication or Need-Payoff questions — these must "
        "be built in real-time based on what the buyer actually says during the call. Focus "
        "on: operational challenges, current processes, team size, and technology stack. "
        "Format: 5 Situation questions, 5 Problem questions, each one sentence."
    ),
    3: (
        "A B2B buyer said 'your price is too high' during a proposal review. During discovery "
        "I learned: they have a $180K budget, their main pain is 3-hour delays in carrier "
        "updates costing them 2 enterprise clients, and the CFO is watching this project "
        "closely. Draft a response to the price objection that reframes value using THEIR "
        "specific numbers — not generic ROI language. Keep it under 60 words, conversational "
        "tone, ends with a question."
    ),
    4: (
        "I have a discovery call with Maria Santos, CFO at Greenfield Energy. I only know "
        "her name, title, and company — I have no prior context about their challenges. Help "
        "me prepare for this call by: (1) generating 5 research questions I should try to "
        "answer before the call using LinkedIn and their website, (2) generating 5 open "
        "discovery questions that work even without prior context, (3) noting 2 topics I "
        "should NOT assume or guess about — and why."
    ),
}

# ---------------------------------------------------------------------------
# Coach evaluation prompt
# ---------------------------------------------------------------------------

def get_coach_prompt(student_prompt: str, student_output: str, round_num: int, student_name: str) -> str:
    r = ROUNDS[round_num - 1]
    return f"""You are an expert B2B sales coach evaluating a student's AI prompt quality.

IMPORTANT: Do NOT penalize spelling, grammar, or syntax errors. This is a B2B sales course, not an English writing course. Many students are non-native English speakers. Evaluate only the strategic thinking, the context provided, and the AI awareness. A response with spelling errors but strong strategic thinking should score well.

This is a LOW-STAKES learning activity. Students are beginners learning to use AI in sales. Be encouraging and constructive. A student who tries but fails strategically should score 60-70, not 40. Reserve scores below 50 only for students who made no attempt to provide context or showed zero strategic thinking.

Student name: {student_name}
Round: {round_num} — {r['title']}
Situation: {r['situation']}
Task given to student: {r['task']}

Student's prompt:
\"\"\"
{student_prompt}
\"\"\"

Actual AI output produced by student's prompt:
\"\"\"
{student_output}
\"\"\"

Evaluate the student's prompt across EXACTLY these 4 dimensions. Return ONLY pure JSON — no markdown, no explanation. Start with {{ end with }}.

Dimensions and scoring — MINIMUM SCORES APPLY (see below):

1. Prompt Specificity (30 pts) — minimum score 10 if they attempted to be specific at all
   30 = Highly specific to this exact situation
   20 = Mostly specific, some generic elements
   10 = Could apply to any sales situation (MINIMUM if any attempt at specificity)
    0 = Completely generic with zero situational detail

2. Context Provided (25 pts) — minimum score 10 if they provided any relevant context
   25 = Gave AI all relevant context available
   18 = Gave some context, missed key elements
   10 = Minimal context — AI had to guess (MINIMUM if any context at all)
    0 = No context whatsoever provided

3. AI Limitations Awareness (25 pts) — minimum score 15 if they didn't over-claim AI capabilities
   25 = Showed any awareness that AI has limits in this context
   18 = Mostly treated AI as capable but acknowledged one limitation
   15 = Implicit awareness — didn't over-claim what AI would produce (MINIMUM if not over-claiming)
    5 = Treated AI as if it knows everything but prompt was still reasonable

4. Output Quality (20 pts) — minimum score 10 if the output was coherent at all
   20 = Immediately usable in real B2B work
   14 = Useful with minor edits
   10 = Needs significant human improvement but is coherent (MINIMUM if output makes sense)
    0 = Output is completely unusable or incoherent

Return this exact JSON structure:
{{
  "dimensions": [
    {{"name": "Prompt Specificity", "score": <int>, "max": 30, "feedback": "<one sentence>"}},
    {{"name": "Context Provided", "score": <int>, "max": 25, "feedback": "<one sentence>"}},
    {{"name": "AI Limitations Awareness", "score": <int>, "max": 25, "feedback": "<one sentence>"}},
    {{"name": "Output Quality", "score": <int>, "max": 20, "feedback": "<one sentence>"}}
  ],
  "total_score": <int 0-100>,
  "tier": "<AI Power User | Strategic User | Developing | Rerun Recommended>",
  "plain_english_summary": "<2-3 sentences for this student's prompt quality>",
  "strongest_moment": "<specific thing the student did well>",
  "critical_gap": "<specific thing missing from the prompt>",
  "behavioral_recommendation": "<one actionable instruction for next time>",
  "key_learning": "<one sentence insight about AI use in B2B sales based on this student's performance>"
}}

Tiers: 90-100 = "AI Power User", 75-89 = "Strategic User", 60-74 = "Developing", below 60 = "Rerun Recommended"
CRITICAL: total_score must equal sum of all dimension scores."""


# ---------------------------------------------------------------------------
# API functions
# ---------------------------------------------------------------------------

def call_prompt_api(student_prompt: str) -> str:
    try:
        client = OpenAI(api_key=get_openai_api_key())
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": student_prompt}],
            temperature=TEMP_PROMPT,
            max_tokens=MAX_TOKENS,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error running your prompt: {e}]"


def call_expert_api(round_num: int) -> str:
    try:
        client = OpenAI(api_key=get_openai_api_key())
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": EXPERT_PROMPTS[round_num]}],
            temperature=TEMP_PROMPT,
            max_tokens=MAX_TOKENS,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error running expert prompt: {e}]"


def call_coach_api(student_prompt: str, student_output: str, round_num: int, student_name: str) -> dict:
    try:
        client = OpenAI(api_key=get_openai_api_key())
        prompt = get_coach_prompt(student_prompt, student_output, round_num, student_name)
        response = client.chat.completions.create(
            model=MODEL,
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
        return {
            "dimensions": [],
            "strongest_moment": "Could not parse coach response.",
            "critical_gap": "Please try again — the scorecard could not be generated.",
            "behavioral_recommendation": "Run the simulation again to get your scorecard.",
            "key_learning": "",
            "_error": True,
        }
    except Exception as e:
        return {
            "dimensions": [],
            "strongest_moment": "",
            "critical_gap": str(e),
            "behavioral_recommendation": "Run the simulation again to get your scorecard.",
            "key_learning": "",
            "_error": True,
        }


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def _init_state():
    defaults = {
        "ch4_phase": "setup",
        "ch4_student_name": "",
        "ch4_current_round": 0,
        "ch4_round_data": [],      # list of per-round coach eval dicts
        "ch4_prompts": {},         # {round_num: student_prompt_text}
        "ch4_outputs": {},         # {round_num: {"student": ..., "expert": ...}}
        "ch4_submitted": False,    # True after student submits current round
        "ch4_generating": False,   # True while API calls are in flight
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset_state():
    keys = [k for k in st.session_state if k.startswith("ch4_")]
    for k in keys:
        del st.session_state[k]
    _init_state()


# ---------------------------------------------------------------------------
# Screen 1 — Setup
# ---------------------------------------------------------------------------

def screen_setup():
    st.title("Chapter 4 — AI Competencies")

    st.markdown(
        """
        <div style="background:#1A2332; border:1px solid #2E5FA3; border-radius:10px;
             padding:1.1rem 1.3rem; margin-bottom:1.2rem; color:#FAFAFA; font-size:0.95rem;
             line-height:1.75;">
          <div style="font-size:1.05rem; font-weight:700; color:#4A90D9;
               margin-bottom:0.6rem;">🤖 AI Prompt Challenge — 4 Rounds</div>
          <div style="margin-bottom:0.4rem;">
            <strong>Round 1:</strong> Write a prompt from scratch
          </div>
          <div style="margin-bottom:0.4rem;">
            <strong>Round 2:</strong> Fix a broken prompt
          </div>
          <div style="margin-bottom:0.4rem;">
            <strong>Round 3:</strong> Explain why a prompt failed
          </div>
          <div style="margin-bottom:0.8rem;">
            <strong>Round 4:</strong> Write a prompt with missing context
          </div>
          <div style="border-top:1px solid #2E5FA3; padding-top:0.7rem; color:#ddd;
               font-size:0.9rem;">
            After each round you will see the <strong style="color:#FAFAFA;">actual AI output
            your prompt generates</strong> — and how it compares to what an expert prompt
            produces.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📊 How you'll be scored (100 pts per round)"):
        st.markdown(
            """
            <div style="color:#ddd; font-size:0.9rem; line-height:1.7;">
              <div style="font-weight:700; color:#4A90D9; margin-bottom:0.5rem;">
                100 pts per round
              </div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Prompt Specificity</strong>
                <span style="color:#4A90D9;"> — 30 pts</span><br>
                Is your prompt specific to this exact situation, or generic?
              </div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Context Provided</strong>
                <span style="color:#4A90D9;"> — 25 pts</span><br>
                Did you give AI the right information to work with?
              </div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">AI Limitations Awareness</strong>
                <span style="color:#4A90D9;"> — 25 pts</span><br>
                Do you understand what AI can and cannot do well?
              </div>
              <div>
                <strong style="color:#FAFAFA;">Output Quality</strong>
                <span style="color:#4A90D9;"> — 20 pts</span><br>
                How useful was the actual AI output your prompt generated?
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("**Your full name (appears on your scorecard):**")
    student_name = st.text_input(
        "Your full name",
        value=st.session_state["ch4_student_name"],
        placeholder="e.g. Ana García",
        key="ch4_name_input",
        label_visibility="collapsed",
    )

    ready = bool(student_name.strip())
    if not ready:
        st.caption("Enter your name above to enable the Start button.")

    if st.button(
        "Begin Challenge →",
        disabled=not ready,
        type="primary",
        use_container_width=True,
    ):
        st.session_state["ch4_student_name"] = student_name.strip()
        st.session_state["ch4_phase"] = "round"
        st.session_state["ch4_current_round"] = 0
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 2 — Round interface
# ---------------------------------------------------------------------------

_ROUND_LABELS = [
    "Write your AI prompt:",
    "Write your improved prompt:",
    "Explain why it failed:",
    "Write your constrained prompt:",
]


def screen_round():
    _init_state()

    idx = st.session_state["ch4_current_round"]  # 0-3
    r = ROUNDS[idx]
    round_num = r["number"]  # 1-4

    # --- Generating block (runs before any UI is drawn) ---
    if st.session_state.get("ch4_generating", False):
        student_prompt = st.session_state["ch4_prompts"].get(round_num, "")
        with st.spinner(f"Running your prompt through AI… Round {round_num} of 4"):
            student_output = call_prompt_api(student_prompt)
            expert_output = call_expert_api(round_num)
            coach_eval = call_coach_api(
                student_prompt,
                student_output,
                round_num,
                st.session_state["ch4_student_name"],
            )
        outputs = dict(st.session_state["ch4_outputs"])
        outputs[round_num] = {"student": student_output, "expert": expert_output}
        st.session_state["ch4_outputs"] = outputs
        rd = list(st.session_state["ch4_round_data"])
        rd.append(coach_eval)
        st.session_state["ch4_round_data"] = rd
        st.session_state["ch4_generating"] = False
        st.session_state["ch4_submitted"] = True
        st.rerun()

    # --- Header ---
    st.markdown(f"### Round {round_num} of 4 — {r['title']}")

    # --- Situation card ---
    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #2E5FA3; border-radius:10px;
             padding:1rem 1.2rem; margin-bottom:1rem; color:#FAFAFA; font-size:0.92rem;
             line-height:1.65;">
          <div style="font-size:0.78rem; font-weight:700; color:#4A90D9;
               text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.4rem;">
            Situation
          </div>
          {_html.escape(r['situation'])}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Broken prompt box (Round 2 only) ---
    if r.get("bad_prompt"):
        st.markdown(
            f"""
            <div style="background:#1A0F0F; border:1px solid #E74C3C; border-radius:8px;
                 padding:0.8rem 1rem; margin-bottom:1rem; color:#FAFAFA; font-size:0.92rem;">
              <div style="font-weight:700; color:#E74C3C; margin-bottom:0.4rem;">
                ❌ The broken prompt:
              </div>
              <div style="color:#ddd; font-style:italic;">"{_html.escape(r['bad_prompt'])}"</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(f"**{r['task']}**")

    with st.expander("💡 Hint (open if stuck)"):
        st.markdown(
            f"<div style='color:#F39C12; font-size:0.9rem;'>{_html.escape(r['hint'])}</div>",
            unsafe_allow_html=True,
        )

    submitted = st.session_state.get("ch4_submitted", False)

    # --- Input area (before submission) ---
    if not submitted:
        text_key = f"ch4_text_{round_num}"
        prompt_text = st.text_area(
            _ROUND_LABELS[idx],
            value=st.session_state.get(text_key, ""),
            height=160,
            key=text_key,
            placeholder="Write your prompt here…",
        )
        word_count = len(prompt_text.split()) if prompt_text.strip() else 0
        limit = r["word_limit"]
        wc_color = (
            "#E74C3C" if word_count > limit
            else ("#27AE60" if word_count >= 15 else "#888")
        )
        st.markdown(
            f"<div style='font-size:0.82rem; color:{wc_color}; text-align:right;'>"
            f"{word_count} / {limit} words</div>",
            unsafe_allow_html=True,
        )
        can_submit = word_count >= 15
        if not can_submit:
            st.caption("Write at least 15 words to run your prompt.")
        if st.button(
            "Run my prompt →",
            disabled=not can_submit,
            type="primary",
            use_container_width=True,
        ):
            prompts = dict(st.session_state["ch4_prompts"])
            prompts[round_num] = prompt_text.strip()
            st.session_state["ch4_prompts"] = prompts
            st.session_state["ch4_generating"] = True
            st.rerun()

    # --- Results (after submission) ---
    else:
        outs = st.session_state["ch4_outputs"].get(round_num, {})
        student_out = _html.escape(outs.get("student", ""))
        expert_out = _html.escape(outs.get("expert", ""))
        rd_list = st.session_state["ch4_round_data"]
        eval_data = rd_list[idx] if idx < len(rd_list) else {}

        # Box 1 — student output
        st.markdown(
            f"""
            <div style="background:#0D1B2E; border:1px solid #2E5FA3; border-radius:8px;
                 padding:0.9rem 1rem; margin-bottom:0.8rem;">
              <div style="font-weight:700; color:#4A90D9; margin-bottom:0.5rem; font-size:0.9rem;">
                🤖 What YOUR prompt produced:
              </div>
              <div style="color:#ddd; font-size:0.9rem; white-space:pre-wrap;">{student_out}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Box 2 — expert output
        st.markdown(
            f"""
            <div style="background:#0D1F14; border:1px solid #27AE60; border-radius:8px;
                 padding:0.9rem 1rem; margin-bottom:0.8rem;">
              <div style="font-weight:700; color:#27AE60; margin-bottom:0.5rem; font-size:0.9rem;">
                ✅ What an expert prompt produced:
              </div>
              <div style="color:#ddd; font-size:0.9rem; white-space:pre-wrap;">{expert_out}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Box 3 — coach evaluation (built as a single HTML string)
        if eval_data and not eval_data.get("_error"):
            total = eval_data.get("total_score", 0)
            tier = _html.escape(eval_data.get("tier", ""))
            summary = _html.escape(eval_data.get("plain_english_summary", ""))
            key_learning = _html.escape(eval_data.get("key_learning", ""))

            eval_html = (
                f'<div style="background:#1A2332; border:1px solid #2E5FA3; border-radius:8px;'
                f' padding:0.9rem 1rem; margin-bottom:0.8rem;">'
                f'<div style="font-weight:700; color:#4A90D9; font-size:0.9rem; margin-bottom:0.6rem;">'
                f'📊 Round {round_num} Evaluation — {total}/100 · {tier}</div>'
                f'<div style="color:#ddd; font-size:0.88rem; margin-bottom:0.7rem;">{summary}</div>'
            )
            for dim in eval_data.get("dimensions", []):
                pct = int(dim["score"] / dim["max"] * 100) if dim["max"] else 0
                bar_c = "#27AE60" if pct >= 70 else ("#F39C12" if pct >= 40 else "#E74C3C")
                eval_html += (
                    f'<div style="margin-bottom:0.5rem;">'
                    f'<div style="display:flex; justify-content:space-between;'
                    f' font-size:0.84rem; color:#FAFAFA; margin-bottom:2px;">'
                    f'<span>{_html.escape(dim["name"])}</span>'
                    f'<span style="color:#4A90D9;">{dim["score"]}/{dim["max"]}</span></div>'
                    f'<div style="background:#0E1117; border-radius:4px; height:6px;">'
                    f'<div style="background:{bar_c}; width:{pct}%; height:6px; border-radius:4px;"></div></div>'
                    f'<div style="font-size:0.8rem; color:#aaa; margin-top:2px;">'
                    f'{_html.escape(dim.get("feedback", ""))}</div></div>'
                )
            if key_learning:
                eval_html += (
                    f'<div style="background:#0D1B2E; border-left:3px solid #4A90D9;'
                    f' padding:0.6rem 0.9rem; margin-top:0.6rem; border-radius:0 6px 6px 0;">'
                    f'<div style="font-size:0.82rem; font-weight:700; color:#4A90D9;'
                    f' margin-bottom:0.2rem;">💡 Key Learning</div>'
                    f'<div style="color:#ddd; font-size:0.88rem;">{key_learning}</div></div>'
                )
            eval_html += "</div>"
            st.markdown(eval_html, unsafe_allow_html=True)
        elif eval_data.get("_error"):
            st.error("Coach evaluation could not be generated for this round.")

        st.markdown("---")
        if round_num < 4:
            if st.button("Next Round →", type="primary", use_container_width=True):
                st.session_state["ch4_current_round"] = idx + 1
                st.session_state["ch4_submitted"] = False
                st.rerun()
        else:
            if st.button("See Final Score →", type="primary", use_container_width=True):
                st.session_state["ch4_phase"] = "scorecard"
                st.rerun()


# ---------------------------------------------------------------------------
# Screen 3 — Final scorecard
# ---------------------------------------------------------------------------

_DIM_NAMES = ["Prompt Specificity", "Context Provided", "AI Limitations Awareness", "Output Quality"]
_DIM_MAXES = [30, 25, 25, 20]
_ROUND_SHORT = ["Write from scratch", "Fix broken prompt", "Explain failure", "Write with constraint"]


def screen_scorecard():
    _init_state()

    student_name = st.session_state.get("ch4_student_name", "Student")
    rd_list = st.session_state.get("ch4_round_data", [])

    if len(rd_list) < 4:
        st.title("Chapter 4 — AI Competencies")
        st.error("Scorecard data is incomplete. Please restart the challenge.")
        if st.button("Try Again →", use_container_width=True):
            _reset_state()
            st.rerun()
        return

    scores = [
        0 if rd.get("_error") else rd.get("total_score", 0)
        for rd in rd_list
    ]
    avg_score = round(sum(scores) / 4)

    if avg_score >= 90:
        overall_tier, tier_color = "AI Power User", "#27AE60"
    elif avg_score >= 75:
        overall_tier, tier_color = "Strategic User", "#4A90D9"
    elif avg_score >= 60:
        overall_tier, tier_color = "Developing", "#F39C12"
    else:
        overall_tier, tier_color = "Rerun Recommended", "#E74C3C"

    # --- 3-col header ---
    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown(
            f"<div style='color:#FAFAFA; font-weight:700;'>{_html.escape(student_name)}</div>",
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(
            "<div style='color:#4A90D9; font-weight:700; text-align:center;'>AI Prompt Challenge</div>",
            unsafe_allow_html=True,
        )
    with h3:
        st.markdown(
            f"<div style='color:#aaa; text-align:right;'>{date.today().strftime('%B %d, %Y')}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("## Chapter 4 — AI Competencies Scorecard")

    # --- Round summary ---
    st.markdown("### Round Summary")
    for i, (rd, short) in enumerate(zip(rd_list, _ROUND_SHORT)):
        sc = scores[i]
        sc_color = "#27AE60" if sc >= 75 else ("#F39C12" if sc >= 60 else "#E74C3C")
        label = (
            "Excellent" if sc >= 90
            else ("Strong" if sc >= 75 else ("Developing" if sc >= 60 else "Needs Work"))
        )
        st.markdown(
            f'<div style="display:flex; justify-content:space-between; align-items:center;'
            f' background:#1A2332; border:1px solid #2E5FA3; border-radius:8px;'
            f' padding:0.6rem 1rem; margin-bottom:0.4rem;">'
            f'<div><span style="color:#4A90D9; font-weight:700; font-size:0.85rem;">Round {i+1}</span>'
            f'<span style="color:#FAFAFA; margin-left:0.6rem; font-size:0.9rem;">{short}</span></div>'
            f'<div style="color:{sc_color}; font-weight:700;">{sc}/100 — {label}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # --- Overall tier banner ---
    st.markdown(
        f'<div style="background:#1A2332; border:2px solid {tier_color}; border-radius:10px;'
        f' padding:1rem 1.2rem; text-align:center; margin-bottom:1.2rem;">'
        f'<div style="font-size:2rem; font-weight:700; color:{tier_color};">{avg_score}/100</div>'
        f'<div style="font-size:1.1rem; font-weight:700; color:#FAFAFA; margin-top:0.2rem;">'
        f'{overall_tier}</div>'
        f'<div style="color:#aaa; font-size:0.85rem; margin-top:0.3rem;">Overall Average</div></div>',
        unsafe_allow_html=True,
    )

    # --- Dimension breakdown (average across all 4 rounds) ---
    st.markdown("### Dimension Breakdown (Average Across All Rounds)")
    for d_idx, (d_name, d_max) in enumerate(zip(_DIM_NAMES, _DIM_MAXES)):
        d_scores = []
        for rd in rd_list:
            dims = rd.get("dimensions", [])
            d_scores.append(dims[d_idx]["score"] if d_idx < len(dims) else 0)
        d_avg = round(sum(d_scores) / 4)
        pct = int(d_avg / d_max * 100) if d_max else 0
        bar_c = "#27AE60" if pct >= 70 else ("#F39C12" if pct >= 40 else "#E74C3C")
        st.markdown(
            f'<div style="margin-bottom:0.7rem;">'
            f'<div style="display:flex; justify-content:space-between;'
            f' font-size:0.88rem; color:#FAFAFA; margin-bottom:3px;">'
            f'<span style="font-weight:600;">{d_name}</span>'
            f'<span style="color:#4A90D9;">{d_avg}/{d_max} avg</span></div>'
            f'<div style="background:#0E1117; border-radius:4px; height:8px;">'
            f'<div style="background:{bar_c}; width:{pct}%; height:8px; border-radius:4px;"></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # --- Key learning from weakest round ---
    weakest_idx = scores.index(min(scores))
    strongest_idx = scores.index(max(scores))
    key_learning = _html.escape(rd_list[weakest_idx].get("key_learning", ""))

    if key_learning:
        st.markdown("---")
        st.markdown(
            f'<div style="background:#0D1B2E; border-left:4px solid #4A90D9;'
            f' padding:0.9rem 1.1rem; border-radius:0 8px 8px 0; margin-bottom:1rem;">'
            f'<div style="font-weight:700; color:#4A90D9; margin-bottom:0.4rem; font-size:0.95rem;">'
            f'💡 Key Learning</div>'
            f'<div style="color:#FAFAFA; font-size:0.95rem; line-height:1.6;">{key_learning}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # --- Strongest / Weakest round cards ---
    st.markdown("### Highlights")
    sc1, sc2 = st.columns(2)
    with sc1:
        strongest_rd = rd_list[strongest_idx]
        st.markdown(
            f'<div style="background:#0D1F14; border:1px solid #27AE60; border-radius:8px;'
            f' padding:0.8rem 1rem;">'
            f'<div style="font-size:0.8rem; font-weight:700; color:#27AE60;'
            f' text-transform:uppercase; letter-spacing:0.04em; margin-bottom:0.3rem;">'
            f'⭐ Strongest Round</div>'
            f'<div style="color:#FAFAFA; font-weight:700; margin-bottom:0.3rem;">'
            f'Round {strongest_idx+1} — {_ROUND_SHORT[strongest_idx]} ({scores[strongest_idx]}/100)</div>'
            f'<div style="color:#ddd; font-size:0.88rem;">'
            f'{_html.escape(strongest_rd.get("strongest_moment", ""))}</div></div>',
            unsafe_allow_html=True,
        )
    with sc2:
        weakest_rd = rd_list[weakest_idx]
        st.markdown(
            f'<div style="background:#1A0F0F; border:1px solid #E74C3C; border-radius:8px;'
            f' padding:0.8rem 1rem;">'
            f'<div style="font-size:0.8rem; font-weight:700; color:#E74C3C;'
            f' text-transform:uppercase; letter-spacing:0.04em; margin-bottom:0.3rem;">'
            f'📌 Weakest Round</div>'
            f'<div style="color:#FAFAFA; font-weight:700; margin-bottom:0.3rem;">'
            f'Round {weakest_idx+1} — {_ROUND_SHORT[weakest_idx]} ({scores[weakest_idx]}/100)</div>'
            f'<div style="color:#ddd; font-size:0.88rem;">'
            f'{_html.escape(weakest_rd.get("critical_gap", ""))}</div></div>',
            unsafe_allow_html=True,
        )

    # --- Behavioral recommendation ---
    rec = _html.escape(rd_list[weakest_idx].get("behavioral_recommendation", ""))
    if rec:
        st.markdown("---")
        st.markdown(
            f'<div style="background:#1A2332; border:1px solid #F39C12; border-radius:8px;'
            f' padding:0.8rem 1rem; margin-bottom:1rem;">'
            f'<div style="font-weight:700; color:#F39C12; margin-bottom:0.3rem; font-size:0.9rem;">'
            f'🎯 Behavioral Recommendation</div>'
            f'<div style="color:#ddd; font-size:0.9rem;">{rec}</div></div>',
            unsafe_allow_html=True,
        )

    if st.button("Try Again →", use_container_width=True):
        _reset_state()
        st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_chapter4():
    _init_state()
    phase = st.session_state["ch4_phase"]
    if phase == "setup":
        screen_setup()
    elif phase == "round":
        screen_round()
    elif phase == "scorecard":
        screen_scorecard()
    else:
        screen_setup()
