import streamlit as st

# ---------------------------------------------------------------------------
# Stage color palette (mimics CRM pipeline view)
# ---------------------------------------------------------------------------

STAGE_COLORS = {
    "Target":  "#888888",
    "Engage":  "#4A90D9",
    "Qualify": "#F39C12",
    "Convert": "#27AE60",
    "Stalled": "#E74C3C",
}

DEAL_ORDER = ["A", "B", "C", "D", "E"]

# ---------------------------------------------------------------------------
# Game data — 5 pipeline deals
# Each decision has: text, points (0/3/5), consequence (str|None),
# privacy_violation (bool)
# ---------------------------------------------------------------------------

DEALS = {
    "A": {
        "label": "Deal A — Nexbridge Logistics",
        "company": "Nexbridge Logistics",
        "value": 95_000,
        "stage": "Qualify",
        "situation": (
            "Your contact Tom Chen hasn't responded in 2 weeks. "
            "Last activity was a demo call."
        ),
        "crm_status": "No follow-up logged. Stage not updated in 18 days.",
        "strategy": {
            "question": "What do you do?",
            "options": [
                {
                    "text": "A) Send follow-up #4 this week",
                    "points": 0,
                    "consequence": (
                        "A 4th unanswered follow-up without a new angle rarely moves deals. "
                        "Persistence without strategy signals desperation."
                    ),
                    "privacy_violation": False,
                },
                {
                    "text": "B) Find a second contact at Nexbridge and reach out",
                    "points": 5,
                    "consequence": None,
                    "privacy_violation": False,
                },
                {
                    "text": "C) Move to Stalled and deprioritize",
                    "points": 3,
                    "consequence": (
                        "Updating the stage is honest hygiene, but deprioritizing without "
                        "trying a new angle closes the door prematurely."
                    ),
                    "privacy_violation": False,
                },
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {
                    "text": "A) Log the follow-up attempt with full context notes",
                    "points": 5,
                    "consequence": None,
                    "privacy_violation": False,
                },
                {
                    "text": "B) Update the stage to Stalled with reason",
                    "points": 3,
                    "consequence": (
                        "Updating the stage is good hygiene, but without logging the "
                        "follow-up attempts you lose the deal history."
                    ),
                    "privacy_violation": False,
                },
                {
                    "text": "C) Leave it — nothing new to log yet",
                    "points": 0,
                    "consequence": (
                        "18 days of silence IS a signal worth logging. "
                        "Leaving the CRM untouched means losing track of deal health."
                    ),
                    "privacy_violation": False,
                },
            ],
            "best_index": 0,
        },
    },

    "B": {
        "label": "Deal B — CoreBridge Solutions",
        "company": "CoreBridge Solutions",
        "value": 210_000,
        "stage": "Convert",
        "situation": (
            "CFO Sarah Walsh requested contract changes. "
            "The meeting is logged but no notes were taken and the next step is blank."
        ),
        "crm_status": "Meeting logged, no notes. Next step field blank.",
        "strategy": {
            "question": "What do you do?",
            "options": [
                {
                    "text": "A) Accept the changes and send a revised contract",
                    "points": 0,
                    "consequence": (
                        "Accepting contract changes without understanding what specifically "
                        "needs to change risks giving away too much — or changing the wrong things."
                    ),
                    "privacy_violation": False,
                },
                {
                    "text": "B) Schedule a call to understand what specifically needs to change",
                    "points": 5,
                    "consequence": None,
                    "privacy_violation": False,
                },
                {
                    "text": "C) Add a discount to sweeten the deal",
                    "points": 0,
                    "consequence": (
                        "Discounting before understanding the real objection signals weakness "
                        "and may not address what the CFO actually wants."
                    ),
                    "privacy_violation": False,
                },
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {
                    "text": "A) Log the CFO conversation with specific change requests",
                    "points": 3,
                    "consequence": (
                        "Good start, but without a logged next step "
                        "the deal can stall again immediately."
                    ),
                    "privacy_violation": False,
                },
                {
                    "text": "B) Update the next step with call date and agenda",
                    "points": 3,
                    "consequence": (
                        "Useful, but without logging what was discussed "
                        "you'll lose context when you prep for that call."
                    ),
                    "privacy_violation": False,
                },
                {
                    "text": "C) Both — log the conversation notes AND update the next step",
                    "points": 5,
                    "consequence": None,
                    "privacy_violation": False,
                },
            ],
            "best_index": 2,
        },
    },

    "C": {
        "label": "Deal C — MedVantex",
        "company": "MedVantex",
        "value": 45_000,
        "stage": "Target",
        "situation": (
            "New inbound lead. You have their name, company email, AND personal "
            "LinkedIn data including home city, family info, and personal interests."
        ),
        "crm_status": "Contact created. No research logged.",
        "strategy": {
            "question": "What do you do?",
            "options": [
                {
                    "text": "A) Call immediately — lead is fresh",
                    "points": 3,
                    "consequence": (
                        "Moving fast is a good instinct, but 30 minutes of research "
                        "typically leads to a stronger first call and higher conversion."
                    ),
                    "privacy_violation": False,
                },
                {
                    "text": "B) Research the company for 30 minutes then reach out",
                    "points": 5,
                    "consequence": None,
                    "privacy_violation": False,
                },
                {
                    "text": "C) Use the personal LinkedIn data to write a hyper-personalized outreach",
                    "points": 0,
                    "consequence": (
                        "⚠️ DATA PRIVACY: In most companies, using personal data "
                        "(home city, family info, personal interests) in outreach violates "
                        "data privacy policy and could expose the company to legal risk. "
                        "Outreach should be grounded in professional and company context only."
                    ),
                    "privacy_violation": True,
                },
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {
                    "text": "A) Log only professional research — company, role, business context",
                    "points": 5,
                    "consequence": None,
                    "privacy_violation": False,
                },
                {
                    "text": "B) Log everything including personal details found online",
                    "points": 0,
                    "consequence": (
                        "⚠️ DATA PRIVACY: Logging personal data (family info, personal interests, "
                        "home city) in a CRM violates data privacy policy. "
                        "CRM records are for professional business data only."
                    ),
                    "privacy_violation": True,
                },
                {
                    "text": "C) Log nothing until the first conversation happens",
                    "points": 3,
                    "consequence": (
                        "Not logging pre-call research means losing useful context. "
                        "Professional company and role research should be logged before the call."
                    ),
                    "privacy_violation": False,
                },
            ],
            "best_index": 0,
        },
    },

    "D": {
        "label": "Deal D — Pinnacle Retail Group",
        "company": "Pinnacle Retail Group",
        "value": 180_000,
        "stage": "Convert",
        "situation": (
            "Procurement asked for a 15% discount to close. "
            "You have no champion identified and no stakeholder map in the CRM."
        ),
        "crm_status": "Proposal logged. No stakeholder map. Champion field blank.",
        "strategy": {
            "question": "What do you do?",
            "options": [
                {
                    "text": "A) Give the 15% discount to close this week",
                    "points": 0,
                    "consequence": (
                        "Discounting immediately — without understanding who is driving the "
                        "request or why — destroys margin and sets a bad precedent. "
                        "Procurement almost always has more room."
                    ),
                    "privacy_violation": False,
                },
                {
                    "text": "B) Ask what is driving the discount request before responding",
                    "points": 5,
                    "consequence": None,
                    "privacy_violation": False,
                },
                {
                    "text": "C) Escalate immediately to your manager",
                    "points": 3,
                    "consequence": (
                        "Escalating can be appropriate, but going straight to a manager "
                        "without first asking a clarifying question means you arrive without information."
                    ),
                    "privacy_violation": False,
                },
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {
                    "text": "A) Log the discount request and your response",
                    "points": 3,
                    "consequence": (
                        "Logging the discount conversation is important, but without a champion "
                        "identified you're flying blind on the internal buying dynamics."
                    ),
                    "privacy_violation": False,
                },
                {
                    "text": "B) Update the champion field — identify your internal ally at Pinnacle",
                    "points": 3,
                    "consequence": (
                        "Identifying a champion is critical, but without logging the "
                        "discount conversation you lose the deal history."
                    ),
                    "privacy_violation": False,
                },
                {
                    "text": "C) Both — log the discount request AND identify/update the champion",
                    "points": 5,
                    "consequence": None,
                    "privacy_violation": False,
                },
            ],
            "best_index": 2,
        },
    },

    "E": {
        "label": "Deal E — Westlake University",
        "company": "Westlake University",
        "value": 30_000,
        "stage": "Engage",
        "situation": (
            "First call is tomorrow. You found personal info about the contact "
            "on social media — vacation photos, personal interests, family details. "
            "The CRM stage is still set to Target."
        ),
        "crm_status": "Contact created. Stage not updated from Target.",
        "strategy": {
            "question": "How do you prepare for the call?",
            "options": [
                {
                    "text": "A) Use the personal social media info to build rapport in your opener",
                    "points": 0,
                    "consequence": (
                        "⚠️ DATA PRIVACY: Using personal social media data "
                        "(vacation photos, family details, personal interests) to build rapport "
                        "in a sales call violates data privacy policy and is likely to make "
                        "the contact feel surveilled rather than valued."
                    ),
                    "privacy_violation": True,
                },
                {
                    "text": "B) Use only professional and company information",
                    "points": 5,
                    "consequence": None,
                    "privacy_violation": False,
                },
                {
                    "text": "C) Mention you saw their personal profile to show you did your research",
                    "points": 0,
                    "consequence": (
                        "⚠️ DATA PRIVACY: Referencing someone's personal social media profile "
                        "in a sales context violates data privacy policy — and is likely to make "
                        "the contact uncomfortable regardless of intent."
                    ),
                    "privacy_violation": True,
                },
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {
                    "text": "A) Update stage from Target to Engage with tomorrow's call date",
                    "points": 3,
                    "consequence": (
                        "Stage update is correct, but without logging your pre-call "
                        "research notes you lose the preparation context."
                    ),
                    "privacy_violation": False,
                },
                {
                    "text": "B) Log pre-call research notes — professional information only",
                    "points": 3,
                    "consequence": (
                        "Good research logging, but the stage is still showing Target "
                        "when Engage is the accurate current stage."
                    ),
                    "privacy_violation": False,
                },
                {
                    "text": "C) Both — update the stage AND log professional research notes",
                    "points": 5,
                    "consequence": None,
                    "privacy_violation": False,
                },
            ],
            "best_index": 2,
        },
    },
}


# ---------------------------------------------------------------------------
# Session state initializer
# ---------------------------------------------------------------------------

def _init_state() -> None:
    defaults = {
        "ch10_phase": "setup",
        "ch10_student_name": "",
        "ch10_current_deal_index": 0,
        "ch10_decision_step": "strategy",   # "strategy" | "crm" | "result"
        "ch10_strategy_choice": None,        # index of chosen strategy option
        "ch10_crm_choice": None,             # index of chosen crm option
        "ch10_answers": {},                  # {"A": {"strategy": idx, "crm": idx}, ...}
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# Screen 1 — Setup
# ---------------------------------------------------------------------------

def screen_setup() -> None:
    st.title("Chapter 10 — Sales Technology Stack: CRM Game")
    st.markdown("### Simulation Setup")
    st.markdown("---")

    student_name = st.text_input(
        "Your full name",
        value=st.session_state["ch10_student_name"],
        placeholder="e.g. Ana García",
        key="ch10_name_input",
    )

    st.markdown(
        """
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.5rem;">
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.6rem;">&#128203; Your Situation</div>
          You are an SDR at <strong>DataFlow Solutions</strong>. You have
          <strong>5 active deals</strong> in your pipeline. For each deal, you will
          make two decisions — one on <strong>deal strategy</strong> and one on
          <strong>CRM hygiene</strong>. Both matter equally. Your decisions have
          real consequences, which are revealed after each deal.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="background:#1A2332; border:1px solid #4A90D9;
             border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.75rem;">
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.4rem;">&#128202; How you'll be scored</div>
          <span style="color:#ddd;">Pipeline Stage Discipline</span>
          <strong style="color:#FAFAFA;">(25)</strong> &nbsp;&middot;&nbsp;
          <span style="color:#ddd;">Deal Strategy</span>
          <strong style="color:#FAFAFA;">(25)</strong> &nbsp;&middot;&nbsp;
          <span style="color:#ddd;">CRM Hygiene</span>
          <strong style="color:#FAFAFA;">(25)</strong> &nbsp;&middot;&nbsp;
          <span style="color:#ddd;">Data Privacy</span>
          <strong style="color:#FAFAFA;">(25)</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ready = bool(student_name.strip())
    if not ready:
        st.caption("Enter your name above to enable the Start button.")
    else:
        st.caption("⚠️ Once you start, decisions are final. Consequences are revealed after each deal.")

    if st.button(
        "Start CRM Simulation →",
        disabled=not ready,
        type="primary",
        use_container_width=True,
    ):
        st.session_state["ch10_student_name"] = student_name.strip()
        st.session_state["ch10_phase"] = "game"
        st.rerun()


# ---------------------------------------------------------------------------
# Part 2 — Score helpers + game screen
# ---------------------------------------------------------------------------

from datetime import date

# Pipeline Stage Discipline: maps (deal, crm_choice_index) → pts
# Measures whether the CRM choice kept the stage accurate and current.
STAGE_DISCIPLINE_MAP = {
    "A": {0: 3, 1: 5, 2: 0},   # log activity=3, update Stalled=5, leave=0
    "B": {0: 3, 1: 5, 2: 5},   # notes only=3, next step=5, both=5
    "C": {0: 5, 1: 0, 2: 3},   # pro log=5, personal log=0, nothing=3
    "D": {0: 3, 1: 5, 2: 5},   # log discount=3, champion=5, both=5
    "E": {0: 5, 1: 3, 2: 5},   # stage update=5, notes only=3, both=5
}


def _compute_scores(answers: dict) -> dict:
    strategy_pts = sum(
        DEALS[k]["strategy"]["options"][answers[k]["strategy"]]["points"]
        for k in answers
    )
    crm_pts = sum(
        DEALS[k]["crm"]["options"][answers[k]["crm"]]["points"]
        for k in answers
    )
    stage_pts = sum(
        STAGE_DISCIPLINE_MAP[k][answers[k]["crm"]]
        for k in answers
    )
    # Data Privacy: 8 pts (C strategy) + 7 pts (C crm) + 10 pts (E strategy) = 25
    privacy_pts = 0
    if "C" in answers:
        if not DEALS["C"]["strategy"]["options"][answers["C"]["strategy"]]["privacy_violation"]:
            privacy_pts += 8
        if not DEALS["C"]["crm"]["options"][answers["C"]["crm"]]["privacy_violation"]:
            privacy_pts += 7
    if "E" in answers:
        if not DEALS["E"]["strategy"]["options"][answers["E"]["strategy"]]["privacy_violation"]:
            privacy_pts += 10
    return {
        "strategy": strategy_pts,
        "crm": crm_pts,
        "stage": stage_pts,
        "privacy": privacy_pts,
        "total": strategy_pts + crm_pts + stage_pts + privacy_pts,
    }


def _show_result_box(label, choice_text, points, consequence, privacy_violation):
    if points == 5:
        border, icon, tier = "#27AE60", "✅", "Optimal choice"
    elif points == 3:
        border, icon, tier = "#F39C12", "⚠️", "Acceptable choice"
    else:
        border, icon, tier = "#E74C3C", "❌", "Poor choice"

    consequence_html = ""
    if consequence:
        bg = "#3D0000" if privacy_violation else "#1A2332"
        lb = "#E74C3C" if privacy_violation else "#555"
        consequence_html = (
            f'<div style="background:{bg}; border-left:3px solid {lb};'
            f' padding:0.45rem 0.7rem; margin-top:0.4rem; border-radius:4px;'
            f' font-size:0.84rem; color:#ddd;">{consequence}</div>'
        )

    st.markdown(
        f"""
        <div style="border:1px solid {border}; border-radius:8px;
             padding:0.7rem 1rem; margin-bottom:0.65rem;">
          <div style="font-weight:700; color:#FAFAFA; margin-bottom:0.2rem;">{label}</div>
          <div style="font-size:0.88rem; color:#ddd; margin-bottom:0.25rem;">{choice_text}</div>
          <div style="font-size:0.84rem;">
            <span style="color:{border};">{icon} {tier}</span>
            &nbsp;&nbsp;<strong style="color:{border};">+{points} pts</strong>
          </div>
          {consequence_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Screen 2 — CRM Game Interface
# ---------------------------------------------------------------------------

def screen_game() -> None:
    deal_index = st.session_state["ch10_current_deal_index"]
    answers: dict = st.session_state["ch10_answers"]

    if deal_index >= len(DEAL_ORDER):
        st.session_state["ch10_phase"] = "scorecard"
        st.rerun()
        return

    current_key = DEAL_ORDER[deal_index]
    deal = DEALS[current_key]
    decision_step = st.session_state["ch10_decision_step"]

    col_left, col_center, col_right = st.columns([1.5, 4, 1.5])

    # ── LEFT — Pipeline sidebar ───────────────────────────────────────────────
    with col_left:
        st.markdown("**📊 Pipeline**")
        for i, key in enumerate(DEAL_ORDER):
            d = DEALS[key]
            is_current = (i == deal_index)
            is_done = key in answers
            sc = STAGE_COLORS.get(d["stage"], "#888")
            val_k = f"${d['value'] // 1_000}k"
            prefix = "✅ " if is_done else ("▶ " if is_current else "")
            bg = "#1B3A6B" if is_current else "#1A2332"
            bdr = "#4A90D9" if is_current else "#2E5FA3"
            wt = "700" if is_current else "400"
            st.markdown(
                f"""
                <div style="background:{bg}; border:1px solid {bdr};
                     border-radius:6px; padding:0.4rem 0.6rem; margin-bottom:0.3rem;">
                  <div style="font-weight:{wt}; font-size:0.8rem; color:#FAFAFA;">
                    {prefix}{d['company']}
                  </div>
                  <div style="font-size:0.74rem; color:#aaa;">{val_k}</div>
                  <span style="background:{sc}; color:white; border-radius:10px;
                       padding:1px 6px; font-size:0.67rem;">{d['stage']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── CENTER — Deal workspace ───────────────────────────────────────────────
    with col_center:
        sc = STAGE_COLORS.get(deal["stage"], "#888")
        val_k = f"${deal['value'] // 1_000}k"
        st.markdown(
            f"""
            <div style="margin-bottom:0.65rem;">
              <span style="font-size:1.1rem; font-weight:700;">{deal['company']}</span>
              &nbsp;<span style="color:#aaa;">{val_k}</span>&nbsp;
              <span style="background:{sc}; color:white; border-radius:10px;
                   padding:2px 8px; font-size:0.77rem;">{deal['stage']}</span>
              &nbsp;&nbsp;
              <span style="color:#888; font-size:0.83rem;">
                Deal {deal_index + 1} of {len(DEAL_ORDER)}
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info(
            f"**Situation:** {deal['situation']}\n\n"
            f"**CRM status:** *{deal['crm_status']}*"
        )
        st.markdown("---")

        # Step 1 — Strategy
        if decision_step == "strategy":
            st.markdown("#### 📋 Decision 1 — Deal Strategy")
            opts = [o["text"] for o in deal["strategy"]["options"]]
            st.radio(
                deal["strategy"]["question"],
                options=range(len(opts)),
                format_func=lambda i: opts[i],
                key=f"ch10_s_{current_key}",
                index=0,
            )
            if st.button("Confirm Decision", type="primary",
                         use_container_width=True, key="ch10_btn_s"):
                st.session_state["ch10_strategy_choice"] = (
                    st.session_state.get(f"ch10_s_{current_key}", 0)
                )
                st.session_state["ch10_decision_step"] = "crm"
                st.rerun()

        # Step 2 — CRM
        elif decision_step == "crm":
            s_idx = st.session_state["ch10_strategy_choice"]
            s_text = deal["strategy"]["options"][s_idx]["text"]
            st.markdown(
                f"""
                <div style="background:#112030; border:1px solid #2E5FA3;
                     border-radius:6px; padding:0.5rem 0.8rem; margin-bottom:0.65rem;
                     color:#aaa; font-size:0.87rem;">
                  <strong style="color:#FAFAFA;">
                    📋 Decision 1 — Deal Strategy (locked)
                  </strong><br>{s_text}
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("#### 💾 Decision 2 — CRM Hygiene")
            opts = [o["text"] for o in deal["crm"]["options"]]
            st.radio(
                deal["crm"]["question"],
                options=range(len(opts)),
                format_func=lambda i: opts[i],
                key=f"ch10_c_{current_key}",
                index=0,
            )
            if st.button("Confirm Decision", type="primary",
                         use_container_width=True, key="ch10_btn_c"):
                c_idx = st.session_state.get(f"ch10_c_{current_key}", 0)
                answers[current_key] = {
                    "strategy": st.session_state["ch10_strategy_choice"],
                    "crm": c_idx,
                }
                st.session_state["ch10_answers"] = answers
                st.session_state["ch10_decision_step"] = "result"
                st.rerun()

        # Step 3 — Result
        elif decision_step == "result":
            s_idx = answers[current_key]["strategy"]
            c_idx = answers[current_key]["crm"]
            s_opt = deal["strategy"]["options"][s_idx]
            c_opt = deal["crm"]["options"][c_idx]
            deal_pts = s_opt["points"] + c_opt["points"]

            _show_result_box(
                "📋 Decision 1 — Deal Strategy",
                s_opt["text"], s_opt["points"],
                s_opt["consequence"], s_opt["privacy_violation"],
            )
            _show_result_box(
                "💾 Decision 2 — CRM Hygiene",
                c_opt["text"], c_opt["points"],
                c_opt["consequence"], c_opt["privacy_violation"],
            )
            st.markdown(
                f"""
                <div style="text-align:center; padding:0.55rem; background:#112030;
                     border-radius:8px; margin:0.4rem 0 0.65rem 0;">
                  <span style="font-size:0.97rem; font-weight:700; color:#FAFAFA;">
                    Points this deal: <span style="color:#4A90D9;">{deal_pts}</span> / 10
                  </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            is_last = (deal_index == len(DEAL_ORDER) - 1)
            btn_label = "See Results →" if is_last else "Next Deal →"
            if st.button(btn_label, type="primary",
                         use_container_width=True, key="ch10_btn_next"):
                if is_last:
                    st.session_state["ch10_phase"] = "scorecard"
                else:
                    st.session_state["ch10_current_deal_index"] = deal_index + 1
                    st.session_state["ch10_decision_step"] = "strategy"
                    st.session_state["ch10_strategy_choice"] = None
                    st.session_state["ch10_crm_choice"] = None
                st.rerun()

    # ── RIGHT — Activity log ──────────────────────────────────────────────────
    with col_right:
        st.markdown("**📝 Activity Log**")
        if not answers:
            st.caption("Decisions appear here.")
        for key in DEAL_ORDER:
            if key not in answers:
                continue
            s_pts = DEALS[key]["strategy"]["options"][answers[key]["strategy"]]["points"]
            c_pts = DEALS[key]["crm"]["options"][answers[key]["crm"]]["points"]
            s_icon = "✅" if s_pts == 5 else ("⚠️" if s_pts == 3 else "❌")
            c_icon = "✅" if c_pts == 5 else ("⚠️" if c_pts == 3 else "❌")
            st.markdown(
                f"""
                <div style="font-size:0.78rem; padding:0.28rem 0;
                     border-bottom:1px solid #2E5FA3; color:#ddd;">
                  <strong>Deal {key}</strong><br>
                  Strategy {s_icon} &nbsp;|&nbsp; CRM {c_icon}
                </div>
                """,
                unsafe_allow_html=True,
            )
        if answers:
            running = sum(
                DEALS[k]["strategy"]["options"][answers[k]["strategy"]]["points"] +
                DEALS[k]["crm"]["options"][answers[k]["crm"]]["points"]
                for k in answers
            )
            st.markdown(
                f"""
                <div style="margin-top:0.55rem; text-align:center;
                     background:#1A2332; border-radius:6px; padding:0.35rem;">
                  <span style="font-size:0.8rem; color:#4A90D9; font-weight:700;">
                    {running} pts so far
                  </span>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Screen 3 — Scorecard
# ---------------------------------------------------------------------------

def screen_scorecard() -> None:
    answers: dict = st.session_state["ch10_answers"]
    scores = _compute_scores(answers)
    student_name = st.session_state["ch10_student_name"]
    total = scores["total"]

    if total >= 90:
        tier, tier_color = "Pipeline Pro", "#27AE60"
    elif total >= 75:
        tier, tier_color = "Developing Professional", "#4A90D9"
    elif total >= 60:
        tier, tier_color = "Needs Practice", "#F39C12"
    else:
        tier, tier_color = "Rerun Recommended", "#E74C3C"

    DIM_NAMES = {
        "strategy": "Deal Strategy",
        "crm": "CRM Hygiene",
        "stage": "Pipeline Stage Discipline",
        "privacy": "Data Privacy",
    }
    dim_scores = {k: scores[k] for k in DIM_NAMES}
    best_dim = max(dim_scores, key=dim_scores.get)
    worst_dim = min(dim_scores, key=dim_scores.get)

    optimal_count = sum(
        (1 if DEALS[k]["strategy"]["options"][answers[k]["strategy"]]["points"] == 5 else 0) +
        (1 if DEALS[k]["crm"]["options"][answers[k]["crm"]]["points"] == 5 else 0)
        for k in answers
    )

    st.title("Scorecard — Sales Technology Stack: CRM Game")
    st.caption(f"{student_name}  ·  {date.today().strftime('%B %d, %Y')}")

    st.info(
        f"You made **{optimal_count} optimal decisions** out of 10 total. "
        f"Your strongest area was **{DIM_NAMES[best_dim]}** and your main gap was "
        f"**{DIM_NAMES[worst_dim]}**."
    )

    st.markdown(
        f"""
        <div style="background:#1A2332; border:2px solid {tier_color};
             border-radius:12px; padding:1.5rem; text-align:center; margin:0.75rem 0 1rem 0;">
          <div style="font-size:2.4rem; font-weight:800; color:{tier_color};">{total} / 100</div>
          <div style="font-size:1.05rem; color:#FAFAFA; font-weight:600;">{tier}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### Dimension Breakdown")

    COACHING = {
        "strategy": (
            "Focus on asking a clarifying question before acting. "
            "The best sales moves almost always start with understanding, not response."
        ),
        "crm": (
            "CRM is your organizational memory. Every logged interaction is insurance "
            "against losing context when it matters most."
        ),
        "stage": (
            "Keeping pipeline stages current is how managers assess deal health — "
            "and how you catch risk before it becomes loss."
        ),
        "privacy": (
            "Data privacy is not just policy — it's trust. Using personal data without "
            "consent damages relationships and can expose the company to legal risk."
        ),
    }
    DIM_CONTRIB = {
        "strategy": "All 5 strategy decisions (5 pts each).",
        "crm": "All 5 CRM hygiene decisions (5 pts each).",
        "stage": "CRM choices evaluated for stage accuracy: were stages kept current?",
        "privacy": "Deal C and Deal E decisions involving personal data (8 + 7 + 10 pts).",
    }

    for key in ["strategy", "crm", "stage", "privacy"]:
        s = scores[key]
        pct = s / 25
        with st.expander(f"{DIM_NAMES[key]} — {s} / 25 pts", expanded=True):
            st.progress(pct)
            st.caption(DIM_CONTRIB[key])
            if pct < 0.70:
                st.warning(f"**Coaching note:** {COACHING[key]}")

    st.markdown("---")
    st.markdown("### 🔒 On Data Privacy")
    st.info(
        "**What the data says:** 77% of B2B professionals report avoiding AI or personal data "
        "when handling confidential information — yet data privacy consistently ranks last in "
        "university curriculum priorities. The decisions in this simulation mirror real situations "
        "SDRs face weekly. Now you know why it matters."
    )

    privacy_violated_deals = [
        k for k in ["C", "E"] if k in answers and (
            DEALS[k]["strategy"]["options"][answers[k]["strategy"]]["privacy_violation"] or
            DEALS[k]["crm"]["options"][answers[k]["crm"]]["privacy_violation"]
        )
    ]
    if privacy_violated_deals:
        refs = " and ".join(f"Deal {k}" for k in privacy_violated_deals)
        st.error(
            f"**You committed a data privacy violation in {refs}.** "
            "In a professional context, these choices could trigger an HR review, "
            "damage the company's reputation, or result in a formal complaint."
        )
    else:
        st.success(
            "**No data privacy violations.** "
            "You handled personal data professionally across all decisions."
        )

    st.markdown("---")
    deal_totals = {
        k: (
            DEALS[k]["strategy"]["options"][answers[k]["strategy"]]["points"] +
            DEALS[k]["crm"]["options"][answers[k]["crm"]]["points"]
        )
        for k in answers
    }
    best_key = max(deal_totals, key=deal_totals.get)
    worst_key = min(deal_totals, key=deal_totals.get)

    col1, col2 = st.columns(2)
    with col1:
        b_s = DEALS[best_key]["strategy"]["options"][answers[best_key]["strategy"]]
        b_c = DEALS[best_key]["crm"]["options"][answers[best_key]["crm"]]
        st.success(
            f"**Strongest: {DEALS[best_key]['company']}**\n\n"
            f"Strategy: {b_s['text']}\n\n"
            f"CRM: {b_c['text']}"
        )
    with col2:
        w_s = DEALS[worst_key]["strategy"]["options"][answers[worst_key]["strategy"]]
        w_c = DEALS[worst_key]["crm"]["options"][answers[worst_key]["crm"]]
        w_note = w_s.get("consequence") or w_c.get("consequence") or "Review both decisions for this deal."
        st.error(
            f"**Needs Work: {DEALS[worst_key]['company']}**\n\n"
            f"Strategy: {w_s['text']}\n\n"
            f"Coaching: {w_note}"
        )

    st.markdown("---")
    if st.button("🔄 Restart Simulation", use_container_width=True):
        for k in list(st.session_state.keys()):
            if k.startswith("ch10_"):
                del st.session_state[k]
        st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_chapter10() -> None:
    _init_state()
    phase = st.session_state["ch10_phase"]
    if phase == "setup":
        screen_setup()
    elif phase == "game":
        screen_game()
    else:
        screen_scorecard()

