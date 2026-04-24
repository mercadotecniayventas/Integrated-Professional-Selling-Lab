import html as _html
import random
import streamlit as st
from datetime import date
from openai import OpenAI
from config import get_openai_api_key

# ---------------------------------------------------------------------------
# Buying center (same across all variants)
# ---------------------------------------------------------------------------

BUYING_CENTER = [
    {"icon": "👤", "name": "Tom Chen",     "title": "IT Manager",     "note": "your initial contact"},
    {"icon": "💰", "name": "Sarah Walsh",  "title": "CFO",            "note": "economic buyer, approves budget"},
    {"icon": "🏭", "name": "Linda Park",   "title": "VP Operations",  "note": "end user, skeptical"},
    {"icon": "📋", "name": "Marcus Webb",  "title": "Procurement",    "note": "contracts and vendor qualification"},
    {"icon": "🎯", "name": "James Ortiz",  "title": "CEO",            "note": "appears if deal progresses well"},
]

# ---------------------------------------------------------------------------
# Variant data
# ---------------------------------------------------------------------------

VARIANTS = {
    "A": {"decisions": [
        {
            "situation": "Tom Chen connected with you on LinkedIn and expressed interest. You have a meeting scheduled for tomorrow. Before the meeting, you research and discover Sarah Walsh (CFO) is the real decision maker.",
            "question": "What do you do before tomorrow's meeting?",
            "options": [
                {"text": "Meet Tom as planned — build the champion relationship first",                         "points": 10, "consequence": "Smart. Tom becomes your internal champion. He schedules a follow-up with Sarah."},
                {"text": "Cancel Tom and reach out directly to Sarah Walsh",                                    "points":  0, "consequence": "Tom feels bypassed. He becomes a blocker. Sarah ignores your cold outreach."},
                {"text": "Ask Tom to invite Sarah to tomorrow's meeting without explaining why",                "points":  5, "consequence": "Tom feels used. Sarah declines — she doesn't know why she's needed."},
            ],
        },
        {
            "situation": "Tom loved the intro meeting and wants to schedule a demo. He says 'I can get my team together — about 8 people from IT.' Sarah and Linda are not mentioned.",
            "question": "How do you respond to Tom's demo request?",
            "options": [
                {"text": "Schedule the demo with Tom's IT team — momentum is key",                             "points":  0, "consequence": "You give a great demo to 8 IT people who can't approve budget. The deal stalls."},
                {"text": "Thank Tom and ask if Sarah Walsh and Linda Park could join — frame it as making the demo more relevant", "points": 10, "consequence": "Tom agrees. Sarah and Linda attend. The demo becomes a real evaluation."},
                {"text": "Ask Tom to get budget approval before scheduling the demo",                           "points":  3, "consequence": "Tom feels put on the spot. He goes quiet for two weeks."},
            ],
        },
        {
            "situation": "After the demo, Linda Park emails Tom: 'I'm not convinced we need this. Our current process works fine.' Tom forwards it to you nervously.",
            "question": "What do you do about Linda's concern?",
            "options": [
                {"text": "Ask Tom to convince Linda — he knows her better than you do",                        "points":  0, "consequence": "Tom tries but fails. Linda digs in. She has more influence than you thought."},
                {"text": "Email Linda directly asking for a 15-minute call to understand her concerns",        "points": 10, "consequence": "Linda appreciates being heard. She reveals a failed implementation 2 years ago — the real reason for her skepticism."},
                {"text": "Send Linda a case study and ROI calculator",                                         "points":  3, "consequence": "Linda doesn't read it. Generic content doesn't address her real concern."},
            ],
        },
        {
            "situation": "Marcus Webb from Procurement enters the process. He emails: 'We need 3 vendor references and a 15% discount to proceed to contract review.'",
            "question": "How do you respond to Marcus?",
            "options": [
                {"text": "Agree to the discount immediately to keep the deal moving",                          "points":  0, "consequence": "Marcus asks for another 10%. If you dropped 15% that fast, he knows there's more margin."},
                {"text": "Provide references immediately and ask for a call to understand what's driving the discount request", "points": 10, "consequence": "Marcus reveals they have budget pressure this quarter. You find a creative solution — phased implementation."},
                {"text": "Tell Marcus the price is firm and escalate to your manager",                         "points":  3, "consequence": "Marcus feels dismissed. The process slows down significantly."},
            ],
        },
        {
            "situation": "Two weeks of silence. Tom stops responding. Your manager asks for a forecast update on this deal.",
            "question": "What do you do?",
            "options": [
                {"text": "Tell your manager it's 80% likely to close this quarter",                            "points":  0, "consequence": "You're forecasting based on hope. This is exactly what kills pipeline accuracy."},
                {"text": "Ask Tom directly: 'Has something changed internally? I want to make sure I'm not missing something.'", "points": 10, "consequence": "Tom reveals Sarah has put a budget freeze on all Q3 purchases. You update your forecast honestly and plan a Q4 approach."},
                {"text": "Send a 'checking in' email to the full buying center",                                "points":  3, "consequence": "Sarah replies asking who you are. Tom is embarrassed. Trust erodes."},
            ],
        },
    ]},
    "B": {"decisions": [
        {
            "situation": "You've been working this account for 3 weeks. Tom is your champion but has gone quiet. You just found out Linda Park was the one who killed the last vendor deal.",
            "question": "What's your next move?",
            "options": [
                {"text": "Call Tom and ask directly what happened",                                            "points": 10, "consequence": "Tom reveals Linda raised concerns in an internal meeting. You now know your real obstacle."},
                {"text": "Reach out to Linda directly and introduce yourself",                                 "points":  5, "consequence": "Linda is surprised but agrees to a call. You start to build the relationship."},
                {"text": "Escalate to Sarah Walsh over Tom's head",                                            "points":  0, "consequence": "Tom finds out and feels bypassed. He stops helping you internally."},
            ],
        },
        {
            "situation": "Linda agrees to a call. She says 'We tried something similar 2 years ago and it failed. My team lost 3 months of productivity during implementation.'",
            "question": "How do you respond to Linda?",
            "options": [
                {"text": "Immediately explain why your solution is different from what failed before",         "points":  3, "consequence": "Linda feels you're not listening. She becomes more guarded."},
                {"text": "Ask what specifically went wrong in the previous implementation",                    "points": 10, "consequence": "Linda opens up. The failure was a change management problem, not a technology problem. You can address this directly."},
                {"text": "Send her a case study of a successful implementation in her industry",               "points":  3, "consequence": "Linda reads it but says 'that's a different kind of company.' Still skeptical."},
            ],
        },
        {
            "situation": "Sarah Walsh asks for a business case document before she'll approve the budget. Tom says 'just send her your standard ROI calculator.'",
            "question": "What do you send Sarah?",
            "options": [
                {"text": "Send the standard ROI calculator as Tom suggested",                                  "points":  0, "consequence": "Sarah emails back: 'This is generic. I need numbers specific to our situation.'"},
                {"text": "Ask Sarah for a 20-minute call to build the business case together using her numbers", "points": 10, "consequence": "Sarah agrees. The business case you build together becomes her internal justification document."},
                {"text": "Build a custom business case using the numbers from your discovery and send it without a call", "points": 7, "consequence": "Sarah appreciates the effort. She has a few questions but is mostly satisfied."},
            ],
        },
        {
            "situation": "Marcus Webb in Procurement says he needs to run a formal RFP process with 3 competitors. This will take 60 days.",
            "question": "How do you respond?",
            "options": [
                {"text": "Accept the RFP process and submit your best proposal",                               "points":  3, "consequence": "You enter a 3-way competition with no advantage. It becomes a price war."},
                {"text": "Ask Marcus if there's a way to accelerate — you have a Q3 implementation slot available", "points": 7, "consequence": "Marcus checks with Sarah. She wants to move faster. RFP is shortened."},
                {"text": "Ask your champion Tom to push back on the RFP internally",                           "points": 10, "consequence": "Tom makes the case to Sarah that the RFP is unnecessary given the work already done. Process is waived."},
            ],
        },
        {
            "situation": "You win the deal. Sarah signs the contract. Marcus asks for your implementation timeline.",
            "question": "What do you do next?",
            "options": [
                {"text": "Hand off to your implementation team and move to your next prospect",                "points":  0, "consequence": "Implementation struggles. Linda's team resists. Tom calls you 3 months later frustrated. Renewal is at risk."},
                {"text": "Schedule a kickoff call with Tom, Linda, and your implementation lead before you disengage", "points": 10, "consequence": "Linda's concerns are addressed upfront. Implementation goes smoothly. Tom introduces you to two other division heads."},
                {"text": "Email the full buying center congratulating them on the decision",                    "points":  3, "consequence": "Nice gesture but James Ortiz replies asking who you are. You never built that relationship."},
            ],
        },
    ]},
    "C": {"decisions": [
        {
            "situation": "First meeting with Tom went well. He says 'I love it — let me champion this internally.' Two weeks later, nothing. You learn there was an internal meeting about vendor selection that you weren't told about.",
            "question": "What do you do?",
            "options": [
                {"text": "Wait for Tom to follow up — don't pressure your champion",                           "points":  0, "consequence": "Three more weeks pass. The internal committee moves forward without you."},
                {"text": "Ask Tom directly: 'I heard there was an internal discussion — can you help me understand where things stand?'", "points": 10, "consequence": "Tom appreciates your directness. He reveals there are 2 internal skeptics you haven't met yet."},
                {"text": "Reach out to Sarah Walsh to get an update",                                          "points":  3, "consequence": "Sarah tells you to work through Tom. Tom feels undermined."},
            ],
        },
        {
            "situation": "Tom tells you Linda Park and Marcus Webb are the two skeptics. Linda thinks the price is too high. Marcus thinks implementation risk is too high.",
            "question": "What's your priority?",
            "options": [
                {"text": "Address Linda first — price objections are easier to handle",                        "points":  5, "consequence": "You handle price well but Marcus raises implementation risk louder at the next meeting."},
                {"text": "Address Marcus first — implementation risk can kill deals faster than price",        "points":  7, "consequence": "Marcus is satisfied. Linda's price concern is still unresolved but less blocking."},
                {"text": "Schedule a joint meeting with both Linda and Marcus to address concerns together",   "points": 10, "consequence": "They hear each other's concerns. Linda realizes price is less important than risk. Both concerns are addressed more efficiently."},
            ],
        },
        {
            "situation": "Sarah Walsh asks: 'What happens if implementation fails? We can't afford another disruption.' This is the first time she's raised a concern directly with you.",
            "question": "How do you respond to Sarah?",
            "options": [
                {"text": "Explain your implementation methodology and success rate",                           "points":  5, "consequence": "Sarah nods but isn't fully reassured. She wants something more concrete."},
                {"text": "Ask Sarah what a failed implementation would mean for her specifically",             "points": 10, "consequence": "Sarah opens up about a previous failure that cost her politically. You now understand her real concern and can address it directly."},
                {"text": "Offer a money-back guarantee to eliminate her risk",                                 "points":  3, "consequence": "Sarah appreciates the gesture but says 'money back doesn't fix the disruption to my team.'"},
            ],
        },
        {
            "situation": "James Ortiz (CEO) unexpectedly joins a meeting. He says: 'I've heard good things. Tell me in 60 seconds why we should do this.'",
            "question": "What do you say to the CEO?",
            "options": [
                {"text": "Walk him through your full product demo",                                            "points":  0, "consequence": "James says 'I don't need the details — I just wanted the headline.' He leaves unimpressed."},
                {"text": "Deliver a crisp value statement: '$2.1M at risk, 3 manual check-ins daily, competitive differentiation none of your rivals offer.'", "points": 10, "consequence": "James says 'That's exactly what I needed to hear' and tells Sarah to move forward."},
                {"text": "Say 'Tom and Sarah can speak to the details — I'm here to support their decision.'","points":  3, "consequence": "James respects the humility but wanted to hear your conviction. A missed opportunity."},
            ],
        },
        {
            "situation": "The deal is approved. Before you move to the next prospect, Tom asks: 'Can you introduce me to other customers who've done this successfully?'",
            "question": "What do you do?",
            "options": [
                {"text": "Connect Tom with 2 reference customers immediately",                                 "points":  7, "consequence": "Tom is grateful. Implementation starts well."},
                {"text": "Connect Tom with references AND ask if he'd be willing to be a reference for you in the future", "points": 10, "consequence": "Tom agrees enthusiastically. You now have a new reference AND an internal advocate for expansion."},
                {"text": "Tell Tom references will be provided during onboarding",                             "points":  3, "consequence": "Tom feels the relationship cooled after the signature. Early warning sign for renewal."},
            ],
        },
    ]},
}

# ---------------------------------------------------------------------------
# Scoring dimensions
# ---------------------------------------------------------------------------

DIMENSIONS = [
    {
        "name": "Pipeline Stage Discipline",
        "max_pts": 25,
        "decision_indices": [0, 4],
        "raw_max": 20,
        "description": "Avoided forecasting on hope; maintained honest pipeline visibility.",
    },
    {
        "name": "Stakeholder Strategy",
        "max_pts": 30,
        "decision_indices": [0, 1, 2],
        "raw_max": 30,
        "description": "Navigated champion, blocker, and economic buyer correctly.",
    },
    {
        "name": "Deal Strategy",
        "max_pts": 25,
        "decision_indices": [2, 3],
        "raw_max": 20,
        "description": "Handled objections and negotiations with process discipline.",
    },
    {
        "name": "Relationship Quality",
        "max_pts": 20,
        "decision_indices": [1, 3, 4],
        "raw_max": 30,
        "description": "Invested in stakeholder relationships beyond the immediate transaction.",
    },
]


def compute_scores(choices: dict) -> tuple[int, int, list[dict]]:
    """Return (raw_total, scaled_total, dim_results)."""
    raw_total = sum(c["points"] for c in choices.values())

    dim_results = []
    for dim in DIMENSIONS:
        raw = sum(choices[i]["points"] for i in dim["decision_indices"] if i in choices)
        scaled = round((raw / dim["raw_max"]) * dim["max_pts"]) if dim["raw_max"] else 0
        dim_results.append({
            "name": dim["name"],
            "description": dim["description"],
            "scaled": scaled,
            "max_pts": dim["max_pts"],
            "raw": raw,
            "raw_max": dim["raw_max"],
        })

    scaled_total = sum(d["scaled"] for d in dim_results)
    return raw_total, scaled_total, dim_results


# ---------------------------------------------------------------------------
# API function
# ---------------------------------------------------------------------------

def call_coach_api(choices: dict, variant: str) -> str:
    decisions = VARIANTS[variant]["decisions"]
    lines = []
    for i, dec in enumerate(decisions):
        c = choices.get(i, {})
        opt = dec["options"][c.get("option_idx", 0)]
        lines.append(
            f"Decision {i + 1}: {dec['question']}\n"
            f"  Chose: {opt['text']} ({c.get('points', 0)} pts)\n"
            f"  Consequence: {opt['consequence']}"
        )
    transcript = "\n\n".join(lines)

    prompt = (
        "You are a B2B sales coach. A student just completed a stakeholder navigation simulation "
        "managing a $180K deal at a manufacturing company.\n\n"
        f"Their 5 decisions:\n\n{transcript}\n\n"
        "Write 2–3 sentences of specific coaching based on their ACTUAL choices. "
        "Reference specific decision numbers. Be direct and constructive. "
        "Focus on what the pattern of choices reveals about their understanding of B2B sales process discipline. "
        "Do not be generic."
    )
    try:
        client = OpenAI(api_key=get_openai_api_key())
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Complete all 5 decisions to receive your personalized process coaching."


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def _init_state() -> None:
    # Variant rotation — persists across resets, never consecutive repeats
    if "ch2_variant" not in st.session_state:
        last = st.session_state.get("ch2_last_variant", None)
        options = [v for v in ["A", "B", "C"] if v != last]
        chosen = random.choice(options)
        st.session_state["ch2_variant"] = chosen
        st.session_state["ch2_last_variant"] = chosen

    defaults = {
        "ch2_phase": "setup",
        "ch2_student_name": "",
        "ch2_current_decision": 0,   # 0-4
        "ch2_choices": {},            # {idx: {option_idx, points, text, consequence}}
        "ch2_confirmed": False,       # whether current decision has been confirmed
        "ch2_insight": "",            # plain-text coaching from call_coach_api
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset_state() -> None:
    last = st.session_state.get("ch2_last_variant", None)
    keys = [k for k in st.session_state if k.startswith("ch2_")]
    for k in keys:
        del st.session_state[k]
    if last is not None:
        st.session_state["ch2_last_variant"] = last
    _init_state()


# ---------------------------------------------------------------------------
# Screen 1 — Setup
# ---------------------------------------------------------------------------

def screen_setup() -> None:
    _init_state()
    st.title("Chapter 2 — The B2B Sales Process")

    st.markdown(
        """
        <div style="background:#1A2332; border:1px solid #2E5FA3; border-radius:10px;
             padding:1.1rem 1.3rem; margin-bottom:1.2rem; color:#FAFAFA;
             font-size:0.93rem; line-height:1.75;">
          <div style="font-size:1rem; font-weight:700; color:#4A90D9; margin-bottom:0.6rem;">
            🏢 Stakeholder Navigation Game
          </div>
          <div style="margin-bottom:0.6rem;">
            You are an SDR at <strong>DataFlow Solutions</strong> managing a
            <strong>$180K software deal</strong> at <strong>Meridian Manufacturing</strong>.
          </div>
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.35rem; font-size:0.88rem;
               text-transform:uppercase; letter-spacing:0.04em;">
            The Buying Center
          </div>
          <div style="margin-bottom:0.7rem;">
            👤 <strong>Tom Chen</strong> — IT Manager <span style="color:#aaa;">(your contact)</span><br>
            💰 <strong>Sarah Walsh</strong> — CFO <span style="color:#aaa;">(economic buyer)</span><br>
            🏭 <strong>Linda Park</strong> — VP Operations <span style="color:#aaa;">(end user, skeptical)</span><br>
            📋 <strong>Marcus Webb</strong> — Procurement <span style="color:#aaa;">(contracts &amp; vendor qualification)</span><br>
            🎯 <strong>James Ortiz</strong> — CEO <span style="color:#aaa;">(appears if deal progresses well)</span>
          </div>
          <div style="border-top:1px solid #2E5FA3; padding-top:0.7rem; color:#ddd; font-size:0.88rem;">
            You will make <strong style="color:#FAFAFA;">5 sequential decisions</strong>.
            Each decision affects the next. Think carefully —
            in real B2B sales, process discipline determines outcomes.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📊 How you'll be scored"):
        st.markdown(
            """
            <div style="color:#ddd; font-size:0.9rem; line-height:1.7;">
              <div style="font-weight:700; color:#4A90D9; margin-bottom:0.5rem;">100 pts total</div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Pipeline Stage Discipline</strong>
                <span style="color:#4A90D9;"> — 25 pts</span><br>
                Did you avoid forecasting based on hope?
              </div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Stakeholder Strategy</strong>
                <span style="color:#4A90D9;"> — 30 pts</span><br>
                Did you navigate champion, blocker, and economic buyer correctly?
              </div>
              <div style="margin-bottom:0.4rem;">
                <strong style="color:#FAFAFA;">Deal Strategy</strong>
                <span style="color:#4A90D9;"> — 25 pts</span><br>
                Did you handle objections and negotiations with process discipline?
              </div>
              <div>
                <strong style="color:#FAFAFA;">Relationship Quality</strong>
                <span style="color:#4A90D9;"> — 20 pts</span><br>
                Did you invest in relationships beyond the immediate transaction?
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("**Your full name (appears on your scorecard):**")
    student_name = st.text_input(
        "Your full name",
        value=st.session_state["ch2_student_name"],
        placeholder="e.g. Ana García",
        key="ch2_name_input",
        label_visibility="collapsed",
    )

    ready = bool(student_name.strip())
    if not ready:
        st.caption("Enter your name above to enable the Start button.")

    if st.button(
        "Start Simulation →",
        disabled=not ready,
        type="primary",
        use_container_width=True,
    ):
        st.session_state["ch2_student_name"] = student_name.strip()
        st.session_state["ch2_phase"] = "game"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 2 — Game
# ---------------------------------------------------------------------------

def screen_game() -> None:
    _init_state()
    variant = st.session_state["ch2_variant"]
    decisions = VARIANTS[variant]["decisions"]
    idx = st.session_state["ch2_current_decision"]
    confirmed = st.session_state["ch2_confirmed"]
    choices = st.session_state["ch2_choices"]
    dec = decisions[idx]

    # Deal header
    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center;
             background:#1A2332; border:1px solid #2E5FA3; border-radius:8px;
             padding:0.55rem 1rem; margin-bottom:0.8rem;">
          <span style="color:#4A90D9; font-weight:700; font-size:0.88rem;">
            Meridian Manufacturing
          </span>
          <span style="color:#FAFAFA; font-weight:700;">$180K</span>
          <span style="color:#aaa; font-size:0.85rem;">DataFlow Solutions</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Progress bar
    pct = int((idx / 5) * 100)
    bar_segs = "".join(
        f'<div style="flex:1; height:6px; border-radius:3px; margin-right:3px; '
        f'background:{"#4A90D9" if i <= idx else "#2E3A50"};"></div>'
        for i in range(5)
    )
    st.markdown(
        f'<div style="margin-bottom:0.25rem;">'
        f'<div style="font-size:0.82rem; color:#aaa; margin-bottom:4px;">'
        f'Decision {idx + 1} of 5</div>'
        f'<div style="display:flex; gap:3px;">{bar_segs}</div></div>',
        unsafe_allow_html=True,
    )

    # Situation card
    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #2E5FA3; border-radius:10px;
             padding:0.9rem 1.1rem; margin-bottom:0.9rem; color:#FAFAFA;
             font-size:0.92rem; line-height:1.65;">
          <div style="font-size:0.75rem; font-weight:700; color:#4A90D9;
               text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.4rem;">
            Situation
          </div>
          {_html.escape(dec['situation'])}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f"**{dec['question']}**")

    if not confirmed:
        option_texts = [f"{chr(65+i)}) {o['text']}" for i, o in enumerate(dec["options"])]
        selection = st.radio(
            "Your choice:",
            options=option_texts,
            index=None,
            key=f"ch2_radio_{idx}",
            label_visibility="collapsed",
        )
        can_confirm = selection is not None
        if not can_confirm:
            st.caption("Select an option above to confirm.")
        if st.button(
            "Confirm Decision →",
            disabled=not can_confirm,
            type="primary",
            use_container_width=True,
        ):
            opt_idx = option_texts.index(selection)
            opt = dec["options"][opt_idx]
            updated = dict(choices)
            updated[idx] = {
                "option_idx": opt_idx,
                "points": opt["points"],
                "text": opt["text"],
                "consequence": opt["consequence"],
            }
            st.session_state["ch2_choices"] = updated
            st.session_state["ch2_confirmed"] = True
            st.rerun()

    else:
        # Show selected choice
        chosen = choices[idx]
        opt_letter = chr(65 + chosen["option_idx"])
        st.markdown(
            f'<div style="color:#aaa; font-size:0.88rem; margin-bottom:0.6rem;">'
            f'You chose: <strong style="color:#FAFAFA;">{opt_letter}) {_html.escape(chosen["text"])}</strong></div>',
            unsafe_allow_html=True,
        )

        # Consequence box
        pts = chosen["points"]
        if pts >= 8:
            bg, border, label, label_color = "#0D1F14", "#27AE60", "✅ Best choice", "#27AE60"
        elif pts >= 4:
            bg, border, label, label_color = "#1A1A0D", "#F39C12", "⚠️ Acceptable choice", "#F39C12"
        else:
            bg, border, label, label_color = "#1A0F0F", "#E74C3C", "❌ Poor choice", "#E74C3C"

        st.markdown(
            f'<div style="background:{bg}; border:1px solid {border}; border-radius:8px;'
            f' padding:0.8rem 1rem; margin-bottom:1rem;">'
            f'<div style="font-weight:700; color:{label_color}; font-size:0.88rem;'
            f' margin-bottom:0.35rem;">{label} — {pts} pts</div>'
            f'<div style="color:#ddd; font-size:0.9rem;">{_html.escape(chosen["consequence"])}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if idx < 4:
            if st.button("Next Decision →", type="primary", use_container_width=True):
                st.session_state["ch2_current_decision"] = idx + 1
                st.session_state["ch2_confirmed"] = False
                st.rerun()
        else:
            if st.button("View Results →", type="primary", use_container_width=True):
                with st.spinner("Generating your process insight…"):
                    insight = call_coach_api(st.session_state["ch2_choices"], variant)
                st.session_state["ch2_insight"] = insight
                st.session_state["ch2_phase"] = "scorecard"
                st.rerun()
