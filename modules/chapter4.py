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
            "about them, the goal, the tone, and the format."
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
            "actually said, not assumed answers. A good prompt acknowledges this limitation."
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
            "knowing WHY the buyer said it — which only comes from good discovery."
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
            "information produce confident but wrong outputs."
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

Dimensions and scoring:

1. Prompt Specificity (30 pts)
   30 = Highly specific to this exact situation
   20 = Mostly specific, some generic elements
   10 = Could apply to any sales situation
    0 = Completely generic

2. Context Provided (25 pts)
   25 = Gave AI all relevant context available
   18 = Gave some context, missed key elements
   10 = Minimal context — AI had to guess
    0 = No context provided

3. AI Limitations Awareness (25 pts)
   25 = Acknowledged what AI can/cannot do in this context
   18 = Showed some awareness
   10 = Treated AI as if it knows everything
    0 = No awareness of limitations shown

4. Output Quality (20 pts — evaluate based on the actual student output above)
   20 = Immediately usable in real B2B work
   14 = Useful with minor edits
    8 = Needs significant human improvement
    0 = Generic or unusable

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
