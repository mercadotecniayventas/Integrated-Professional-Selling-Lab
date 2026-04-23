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
# Parts 2 and 3 appended below
# ---------------------------------------------------------------------------
