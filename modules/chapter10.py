import random
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

DEALS_A = {
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
# Variant B — same companies, different situations & correct answers
# ---------------------------------------------------------------------------

DEALS_B = {
    "A": {
        "label": "Deal A — Nexbridge Logistics",
        "company": "Nexbridge Logistics",
        "value": 110_000,
        "stage": "Engage",
        "situation": (
            "After 3 weeks of silence, your contact replied and wants to schedule a demo. "
            "You haven't confirmed budget authority yet."
        ),
        "crm_status": "Stage shows Engage. No discovery notes. Budget field blank.",
        "strategy": {
            "question": "What do you do?",
            "options": [
                {"text": "A) Send a demo invite immediately — strike while it's hot",
                 "points": 0,
                 "consequence": "Jumping to demo without confirming budget authority risks wasting both parties' time if the contact can't approve a purchase.",
                 "privacy_violation": False},
                {"text": "B) Qualify budget and authority before scheduling the demo",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "C) Reply to thank them and wait for them to propose a time",
                 "points": 3,
                 "consequence": "Being responsive is good, but leaving scheduling to them risks another silence.",
                 "privacy_violation": False},
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {"text": "A) Log the reply and add a note about demo interest",
                 "points": 3,
                 "consequence": "Logging the reply is important, but without a stage update the pipeline still shows stale activity.",
                 "privacy_violation": False},
                {"text": "B) Update the stage to Qualify and set a next step",
                 "points": 3,
                 "consequence": "Stage update is needed, but without logging the reply context you lose deal history.",
                 "privacy_violation": False},
                {"text": "C) Both — log the reply AND update the stage with a next step",
                 "points": 5, "consequence": None, "privacy_violation": False},
            ],
            "best_index": 2,
        },
    },
    "B": {
        "label": "Deal B — CoreBridge Solutions",
        "company": "CoreBridge Solutions",
        "value": 195_000,
        "stage": "Qualify",
        "situation": (
            "Your champion Tom is supportive, but the VP of Operations is skeptical. "
            "You've only met Tom — no relationship with the VP."
        ),
        "crm_status": "One contact logged. No stakeholder map. VP not in CRM.",
        "strategy": {
            "question": "What do you do?",
            "options": [
                {"text": "A) Schedule a full buying team meeting immediately",
                 "points": 3,
                 "consequence": "Moving to a full team meeting without a plan for the VP's skepticism risks the meeting becoming adversarial.",
                 "privacy_violation": False},
                {"text": "B) Ask Tom to arrange a direct introduction to the VP",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "C) Send the VP a cold introduction email directly",
                 "points": 0,
                 "consequence": "Bypassing your champion to cold-contact the VP risks undermining Tom's credibility.",
                 "privacy_violation": False},
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {"text": "A) Log Tom's concern about VP skepticism",
                 "points": 3,
                 "consequence": "Logging the concern is valuable, but without a next step the deal has no forward momentum.",
                 "privacy_violation": False},
                {"text": "B) Add a next step: request VP introduction",
                 "points": 3,
                 "consequence": "A clear next step is essential, but without logging the VP concern you'll lack context when prepping.",
                 "privacy_violation": False},
                {"text": "C) Both — log the VP skepticism AND set next step for introduction",
                 "points": 5, "consequence": None, "privacy_violation": False},
            ],
            "best_index": 2,
        },
    },
    "C": {
        "label": "Deal C — MedVantex",
        "company": "MedVantex",
        "value": 52_000,
        "stage": "Target",
        "situation": (
            "You found the prospect on LinkedIn. Their public profile shows "
            "work history, company role, and recent industry posts."
        ),
        "crm_status": "No contact created yet. No research logged.",
        "strategy": {
            "question": "How do you approach outreach?",
            "options": [
                {"text": "A) Comment on one of their industry posts to start a conversation",
                 "points": 3,
                 "consequence": "Engaging with public industry content is acceptable, but commenting can feel transactional without a stronger value signal.",
                 "privacy_violation": False},
                {"text": "B) Research the company first, then craft a message based on business fit",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "C) Send a generic connection request without a personalized message",
                 "points": 0,
                 "consequence": "Generic outreach signals low effort. Personalization based on professional context dramatically improves response rates.",
                 "privacy_violation": False},
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {"text": "A) Create a contact with professional research — role, company, industry context",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "B) Log their recent post content and personal professional opinions",
                 "points": 0,
                 "consequence": "⚠️ DATA PRIVACY: Logging personal opinions and post content from social media crosses into personal data territory. CRM records should contain business-relevant professional information only.",
                 "privacy_violation": True},
                {"text": "C) Don't create a contact yet — wait until they respond",
                 "points": 3,
                 "consequence": "Waiting to log until they respond means losing the research context you already have.",
                 "privacy_violation": False},
            ],
            "best_index": 0,
        },
    },
    "D": {
        "label": "Deal D — Pinnacle Retail Group",
        "company": "Pinnacle Retail Group",
        "value": 165_000,
        "stage": "Qualify",
        "situation": (
            "The prospect asked for a proposal by Friday after a 20-minute discovery call. "
            "You still have major gaps in understanding their needs and decision process."
        ),
        "crm_status": "Discovery call logged. Key fields blank: budget, authority, timeline.",
        "strategy": {
            "question": "What do you do?",
            "options": [
                {"text": "A) Send the proposal by Friday as requested",
                 "points": 0,
                 "consequence": "Sending a proposal with major discovery gaps means guessing at their needs. A weak proposal is worse than a delayed one.",
                 "privacy_violation": False},
                {"text": "B) Ask for another discovery session before sending a quality proposal",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "C) Send a generic proposal with standard pricing as a starting point",
                 "points": 3,
                 "consequence": "A generic proposal shows responsiveness but signals you don't understand their specific situation.",
                 "privacy_violation": False},
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {"text": "A) Log the discovery gaps before sending any proposal",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "B) Log 'Proposal requested — Friday deadline'",
                 "points": 3,
                 "consequence": "Capturing the deadline is useful, but without noting the discovery gaps you'll lose track of what's unresolved.",
                 "privacy_violation": False},
                {"text": "C) Update the stage to Convert since they asked for a proposal",
                 "points": 0,
                 "consequence": "Advancing to Convert based on a proposal request — without confirmed budget or authority — overstates deal health.",
                 "privacy_violation": False},
            ],
            "best_index": 0,
        },
    },
    "E": {
        "label": "Deal E — Westlake University",
        "company": "Westlake University",
        "value": 38_000,
        "stage": "Convert",
        "situation": (
            "You sent the contract 2 weeks ago. No response. "
            "The AI deal score dropped from 82 to 61 overnight."
        ),
        "crm_status": "Contract sent. No follow-up logged. AI risk score: High.",
        "strategy": {
            "question": "What do you do?",
            "options": [
                {"text": "A) Resend the contract with a new signature deadline",
                 "points": 0,
                 "consequence": "Resending without understanding why they went quiet adds pressure without addressing the real issue.",
                 "privacy_violation": False},
                {"text": "B) Call to understand what has changed since they went quiet",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "C) Drop the price 10% to re-engage them",
                 "points": 3,
                 "consequence": "Discounting without knowing the reason for silence may not address the real issue and surrenders margin unnecessarily.",
                 "privacy_violation": False},
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {"text": "A) Log that the AI score dropped and add a risk flag",
                 "points": 3,
                 "consequence": "Flagging the risk is important, but without logging a specific outreach attempt the next step is unclear.",
                 "privacy_violation": False},
                {"text": "B) Log the outreach attempt and note that internal status is unknown",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "C) Update the stage to Stalled and deprioritize",
                 "points": 3,
                 "consequence": "Updating the stage may be accurate, but without logging your outreach attempt you lose key deal context.",
                 "privacy_violation": False},
            ],
            "best_index": 1,
        },
    },
}

# ---------------------------------------------------------------------------
# Variant C — same companies, different situations & correct answers
# ---------------------------------------------------------------------------

DEALS_C = {
    "A": {
        "label": "Deal A — Nexbridge Logistics",
        "company": "Nexbridge Logistics",
        "value": 88_000,
        "stage": "Convert",
        "situation": (
            "The deal is in legal review — 3 weeks now. "
            "Your manager wants it on the Q3 forecast at 80% probability."
        ),
        "crm_status": "Stage: Convert. Probability: blank. No legal contact logged.",
        "strategy": {
            "question": "What do you do?",
            "options": [
                {"text": "A) Tell your manager the deal is at 80% probability as requested",
                 "points": 0,
                 "consequence": "Reporting a probability with no supporting evidence distorts the forecast. Without talking to legal, 80% is a guess.",
                 "privacy_violation": False},
                {"text": "B) Call the legal contact to get a realistic timeline before forecasting",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "C) Set a follow-up reminder for next week and wait",
                 "points": 3,
                 "consequence": "3 weeks of legal silence may mean the deal stalled internally. A proactive call surfaces that risk earlier.",
                 "privacy_violation": False},
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {"text": "A) Log the legal review status and update the probability with evidence",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "B) Set the probability to 80% to keep it on the forecast",
                 "points": 0,
                 "consequence": "Entering a forecast probability without evidence distorts the pipeline. CRM data should reflect reality, not wishful thinking.",
                 "privacy_violation": False},
                {"text": "C) Log the legal status and note that probability should be updated once timeline is confirmed",
                 "points": 5, "consequence": None, "privacy_violation": False},
            ],
            "best_index": 0,
        },
    },
    "B": {
        "label": "Deal B — CoreBridge Solutions",
        "company": "CoreBridge Solutions",
        "value": 220_000,
        "stage": "Engage",
        "situation": (
            "You've sent 3 emails with no response. "
            "You found a personal cell phone number for the contact online."
        ),
        "crm_status": "3 email attempts logged. No phone number on file.",
        "strategy": {
            "question": "What do you do?",
            "options": [
                {"text": "A) Call the personal cell phone number",
                 "points": 0,
                 "consequence": "⚠️ DATA PRIVACY: Calling a personal cell found online — without the contact's consent — violates data privacy policy and is likely to create a hostile first impression.",
                 "privacy_violation": True},
                {"text": "B) Connect on LinkedIn with a professional, value-focused message",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "C) Ask your manager to reach out to the contact's manager",
                 "points": 3,
                 "consequence": "Escalating to the manager level can work but risks feeling aggressive before all direct channels are exhausted.",
                 "privacy_violation": False},
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {"text": "A) Log that you found a personal number but chose not to use it",
                 "points": 3,
                 "consequence": "Noting your decision is professional, but without logging the LinkedIn outreach the next step isn't captured.",
                 "privacy_violation": False},
                {"text": "B) Log the outreach attempts with no mention of the personal number",
                 "points": 3,
                 "consequence": "Logging the attempts is important, but omitting the privacy context means a future rep might find the number and not know your decision.",
                 "privacy_violation": False},
                {"text": "C) Both — log all outreach attempts AND note your decision on the personal cell number",
                 "points": 5, "consequence": None, "privacy_violation": False},
            ],
            "best_index": 2,
        },
    },
    "C": {
        "label": "Deal C — MedVantex",
        "company": "MedVantex",
        "value": 41_000,
        "stage": "Qualify",
        "situation": (
            "IT and Operations both attended the demo — and they want different things. "
            "IT wants API flexibility. Ops wants simplicity. The deal is stalling."
        ),
        "crm_status": "One contact logged. No stakeholder map. Competing priorities not noted.",
        "strategy": {
            "question": "What do you do?",
            "options": [
                {"text": "A) Focus all communication on the IT stakeholder — they'll likely own the decision",
                 "points": 0,
                 "consequence": "Choosing one stakeholder without a clear reason risks alienating Ops — who may have equal or greater influence on final approval.",
                 "privacy_violation": False},
                {"text": "B) Map both stakeholders and tailor your messaging to each",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "C) Defer to whoever responds first",
                 "points": 3,
                 "consequence": "Reactive selling loses deals at the multi-stakeholder stage. You need a deliberate engagement plan for both parties.",
                 "privacy_violation": False},
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {"text": "A) Log IT's priorities and technical objections",
                 "points": 3,
                 "consequence": "Logging IT's side is a good start, but without Ops' perspective you have an incomplete picture.",
                 "privacy_violation": False},
                {"text": "B) Log Ops' priorities and simplicity concerns",
                 "points": 3,
                 "consequence": "Logging Ops' concerns is valuable, but without IT's technical requirements you're missing half the buying picture.",
                 "privacy_violation": False},
                {"text": "C) Both — log both stakeholders' priorities AND begin a buying center map",
                 "points": 5, "consequence": None, "privacy_violation": False},
            ],
            "best_index": 2,
        },
    },
    "D": {
        "label": "Deal D — Pinnacle Retail Group",
        "company": "Pinnacle Retail Group",
        "value": 175_000,
        "stage": "Target",
        "situation": (
            "The CEO just posted on LinkedIn about supply chain modernization. "
            "You have no contact at Pinnacle and no account in your CRM."
        ),
        "crm_status": "No account in CRM. No contact. Opportunity not created.",
        "strategy": {
            "question": "What do you do?",
            "options": [
                {"text": "A) Comment on the CEO's LinkedIn post to get noticed",
                 "points": 3,
                 "consequence": "Engaging with public content is visible, but commenting on a CEO's post without a warm introduction rarely converts to a real conversation.",
                 "privacy_violation": False},
                {"text": "B) Research Pinnacle first and find the right contact before reaching out",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "C) Send the CEO a cold direct message on LinkedIn",
                 "points": 0,
                 "consequence": "Cold CEO outreach without research or a warm connection rarely works and risks being ignored or flagged as spam.",
                 "privacy_violation": False},
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {"text": "A) Create an account record only — no contact identified yet",
                 "points": 3,
                 "consequence": "Creating the account is a good first step, but without logging the LinkedIn signal and research notes you lose the context that triggered outreach.",
                 "privacy_violation": False},
                {"text": "B) Create account and contact records with research notes",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "C) Create account + contact + log the LinkedIn post as a trigger event",
                 "points": 5, "consequence": None, "privacy_violation": False},
            ],
            "best_index": 1,
        },
    },
    "E": {
        "label": "Deal E — Westlake University",
        "company": "Westlake University",
        "value": 55_000,
        "stage": "Qualify",
        "situation": (
            "The demo went great. The contact said, 'I need to run this by my team.' "
            "You don't know who else is involved or what they need to approve."
        ),
        "crm_status": "Demo logged. No stakeholder map. Decision process unknown.",
        "strategy": {
            "question": "What do you do?",
            "options": [
                {"text": "A) Send a follow-up email summarizing the demo and wait",
                 "points": 3,
                 "consequence": "Sending a recap is professional, but without knowing who else is involved you have no way to influence the team decision.",
                 "privacy_violation": False},
                {"text": "B) Ask directly who is on the team and what they'll need to approve",
                 "points": 5, "consequence": None, "privacy_violation": False},
                {"text": "C) Ask for a firm commitment before the team review happens",
                 "points": 0,
                 "consequence": "Asking for commitment before the contact has consulted their team creates pressure that typically backfires.",
                 "privacy_violation": False},
            ],
            "best_index": 1,
        },
        "crm": {
            "question": "What do you log in the CRM?",
            "options": [
                {"text": "A) Log the demo outcome as positive",
                 "points": 3,
                 "consequence": "Noting the demo went well is a start, but without logging a next step or stakeholder info you have no clear path forward.",
                 "privacy_violation": False},
                {"text": "B) Log next step: team review — stakeholders TBD",
                 "points": 3,
                 "consequence": "Logging the next step is good, but without capturing the demo outcome and stakeholder mapping you lose context for the follow-up.",
                 "privacy_violation": False},
                {"text": "C) Both — log the demo outcome AND begin a stakeholder map for the decision team",
                 "points": 5, "consequence": None, "privacy_violation": False},
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
        "ch10_decision_step": "strategy",
        "ch10_strategy_choice": None,
        "ch10_crm_choice": None,
        "ch10_answers": {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
    # Auto-assign variant on first play; never repeat the same one consecutively.
    if "ch10_variant" not in st.session_state:
        last = st.session_state.get("ch10_last_variant", None)
        options = [v for v in ["A", "B", "C"] if v != last]
        variant = random.choice(options)
        st.session_state["ch10_variant"] = variant
        st.session_state["ch10_last_variant"] = variant


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
          Each time you play, you'll face a different set of deals.
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
STAGE_DISCIPLINE_A = {
    "A": {0: 3, 1: 5, 2: 0},   # log activity=3, update Stalled=5, leave=0
    "B": {0: 3, 1: 5, 2: 5},   # notes only=3, next step=5, both=5
    "C": {0: 5, 1: 0, 2: 3},   # pro log=5, personal log=0, nothing=3
    "D": {0: 3, 1: 5, 2: 5},   # log discount=3, champion=5, both=5
    "E": {0: 5, 1: 3, 2: 5},   # stage update=5, notes only=3, both=5
}

STAGE_DISCIPLINE_B = {
    "A": {0: 3, 1: 5, 2: 5},   # log reply=3, update stage+next=5, both=5
    "B": {0: 3, 1: 5, 2: 5},   # log concern=3, next step=5, both=5
    "C": {0: 5, 1: 0, 2: 3},   # pro research=5, personal post (privacy)=0, nothing=3
    "D": {0: 5, 1: 0, 2: 3},   # log gaps=5, proposal note only=0, premature Convert=3
    "E": {0: 0, 1: 5, 2: 0},   # risk flag no outreach=0, log outreach+status=5, premature Stall=0
}

STAGE_DISCIPLINE_C = {
    "A": {0: 5, 1: 3, 2: 5},   # log legal+evidence=5, fictitious prob=3, log+note=5
    "B": {0: 3, 1: 3, 2: 5},   # log found number=3, log attempts only=3, both+privacy note=5
    "C": {0: 3, 1: 3, 2: 5},   # IT only=3, Ops only=3, both+buying center=5
    "D": {0: 3, 1: 5, 2: 5},   # account only=3, account+contact+research=5, +trigger event=5
    "E": {0: 3, 1: 3, 2: 5},   # log demo=3, next step only=3, both+stakeholder map=5
}

_DEALS_MAP = {"A": DEALS_A, "B": DEALS_B, "C": DEALS_C}
_STAGE_MAP  = {"A": STAGE_DISCIPLINE_A, "B": STAGE_DISCIPLINE_B, "C": STAGE_DISCIPLINE_C}


def _compute_scores(answers: dict, variant: str = "A") -> dict:
    deals = _DEALS_MAP[variant]
    stage_map = _STAGE_MAP[variant]
    strategy_pts = sum(
        deals[k]["strategy"]["options"][answers[k]["strategy"]]["points"]
        for k in answers
    )
    crm_pts = sum(
        deals[k]["crm"]["options"][answers[k]["crm"]]["points"]
        for k in answers
    )
    stage_pts = sum(
        stage_map[k][answers[k]["crm"]]
        for k in answers
    )
    # Data Privacy: 25 base, -10 per privacy_violation committed (floor 0)
    privacy_pts = 25
    for deal_key in answers:
        for dt in ("strategy", "crm"):
            idx = answers[deal_key][dt]
            if deals[deal_key][dt]["options"][idx].get("privacy_violation", False):
                privacy_pts = max(0, privacy_pts - 10)
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
    variant = st.session_state.get("ch10_variant", "A")
    deals = _DEALS_MAP[variant]
    deal_index = st.session_state["ch10_current_deal_index"]
    answers: dict = st.session_state["ch10_answers"]

    if deal_index >= len(DEAL_ORDER):
        st.session_state["ch10_phase"] = "scorecard"
        st.rerun()
        return

    current_key = DEAL_ORDER[deal_index]
    deal = deals[current_key]
    decision_step = st.session_state["ch10_decision_step"]

    col_left, col_center, col_right = st.columns([1.5, 4, 1.5])

    # ── LEFT — Pipeline sidebar ───────────────────────────────────────────────
    with col_left:
        st.markdown("**📊 Pipeline**")
        for i, key in enumerate(DEAL_ORDER):
            d = deals[key]
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
        st.markdown(
            f"""
            <div style="background:#1A2332; border:1px solid #2E5FA3;
                 border-radius:8px; padding:0.8rem 1rem; margin-bottom:0.65rem;">
              <div style="color:#4A90D9; font-weight:700; margin-bottom:0.3rem;">
                Situation
              </div>
              <div style="color:#FAFAFA; margin-bottom:0.5rem;">
                {deal['situation']}
              </div>
              <div style="color:#4A90D9; font-weight:700; margin-bottom:0.25rem;">
                CRM Status
              </div>
              <div style="color:#aaa; font-style:italic;">{deal['crm_status']}</div>
            </div>
            """,
            unsafe_allow_html=True,
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
            s_pts = deals[key]["strategy"]["options"][answers[key]["strategy"]]["points"]
            c_pts = deals[key]["crm"]["options"][answers[key]["crm"]]["points"]
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
                deals[k]["strategy"]["options"][answers[k]["strategy"]]["points"] +
                deals[k]["crm"]["options"][answers[k]["crm"]]["points"]
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
    variant = st.session_state.get("ch10_variant", "A")
    deals = _DEALS_MAP[variant]
    answers: dict = st.session_state["ch10_answers"]
    scores = _compute_scores(answers, variant)
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
        (1 if deals[k]["strategy"]["options"][answers[k]["strategy"]]["points"] == 5 else 0) +
        (1 if deals[k]["crm"]["options"][answers[k]["crm"]]["points"] == 5 else 0)
        for k in answers
    )

    st.title("Scorecard — Sales Technology Stack: CRM Game")
    st.markdown("---")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Student", student_name)
    with col_b:
        st.metric("Score", f"{total} / 100")
    with col_c:
        st.metric("Date", str(date.today()))

    st.markdown("")

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
        "privacy": "Any choice misusing personal data costs −10 pts (starting from 25).",
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
        k for k in DEAL_ORDER if k in answers and (
            deals[k]["strategy"]["options"][answers[k]["strategy"]].get("privacy_violation", False) or
            deals[k]["crm"]["options"][answers[k]["crm"]].get("privacy_violation", False)
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
            deals[k]["strategy"]["options"][answers[k]["strategy"]]["points"] +
            deals[k]["crm"]["options"][answers[k]["crm"]]["points"]
        )
        for k in answers
    }
    best_key = max(deal_totals, key=deal_totals.get)
    worst_key = min(deal_totals, key=deal_totals.get)

    col1, col2 = st.columns(2)
    with col1:
        b_s = deals[best_key]["strategy"]["options"][answers[best_key]["strategy"]]
        b_c = deals[best_key]["crm"]["options"][answers[best_key]["crm"]]
        st.success(
            f"**Strongest: {deals[best_key]['company']}**\n\n"
            f"Strategy: {b_s['text']}\n\n"
            f"CRM: {b_c['text']}"
        )
    with col2:
        w_s = deals[worst_key]["strategy"]["options"][answers[worst_key]["strategy"]]
        w_c = deals[worst_key]["crm"]["options"][answers[worst_key]["crm"]]
        w_note = w_s.get("consequence") or w_c.get("consequence") or "Review both decisions for this deal."
        st.error(
            f"**Needs Work: {deals[worst_key]['company']}**\n\n"
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

