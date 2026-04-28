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
        {
            "situation": "Deal is closed. During implementation Tom mentions two other divisions could benefit from the solution.",
            "question": "What do you do?",
            "options": [
                {"text": "Ask Tom to introduce you to the other division heads immediately",                    "points":  7, "consequence": "Tom makes introductions. You have 2 new conversations started."},
                {"text": "Wait until implementation is successful before pursuing expansion",                   "points": 10, "consequence": "Smart. You let results speak first. Three months later Tom becomes your biggest internal advocate and opens two expansion doors."},
                {"text": "Go directly to Sarah Walsh to discuss enterprise expansion",                          "points":  3, "consequence": "Sarah says 'let's see how this one goes first.' Too early for that conversation."},
            ],
        },
        {
            "situation": "A prospect in your pipeline asks for a customer reference in manufacturing. Tom Chen is your best option.",
            "question": "How do you approach Tom?",
            "options": [
                {"text": "Ask Tom directly to be a reference",                                                 "points":  7, "consequence": "Tom agrees but seems slightly put on the spot. He does it, but with less enthusiasm than you'd hoped."},
                {"text": "Check in on Tom's satisfaction first, then ask for the reference",                   "points": 10, "consequence": "Tom appreciates you asked about him first. He volunteers to be a reference before you even ask — and writes a testimonial unprompted."},
                {"text": "Use Tom's name without asking him first",                                            "points":  0, "consequence": "Tom finds out. Trust is severely damaged. He stops advocating for you internally."},
            ],
        },
        {
            "situation": "Contract renews in 90 days. Linda Park — the former skeptic — now runs a larger team and is the primary day-to-day user of your solution.",
            "question": "Who leads the renewal conversation?",
            "options": [
                {"text": "Go through Tom — he's your champion and knows the relationship",                     "points":  5, "consequence": "Tom is supportive but Linda now makes the real recommendation. She feels overlooked."},
                {"text": "Schedule separate conversations with Tom AND Linda before renewal",                   "points": 10, "consequence": "Linda becomes a co-champion. Renewal is approved quickly and includes an upsell."},
                {"text": "Send renewal paperwork directly to Marcus in Procurement",                           "points":  0, "consequence": "Marcus routes it to Sarah without context from Tom or Linda. Renewal almost falls through."},
            ],
        },
        {
            "situation": "Marcus Webb tells you a competitor offered the same functionality at 20% lower price for renewal.",
            "question": "How do you respond?",
            "options": [
                {"text": "Match the competitor's price immediately to keep the deal",                          "points":  0, "consequence": "Marcus asks for another 10%. You've shown there's room to move and set a bad precedent."},
                {"text": "Ask Marcus what specifically appeals about the competitor's offer",                   "points": 10, "consequence": "Marcus reveals it's purely price pressure from the CFO. Linda and Tom both want to stay with you. You address the CFO concern directly and renew at original price."},
                {"text": "Ask for a meeting with Sarah Walsh to defend your value directly",                   "points":  7, "consequence": "Sarah appreciates the directness. Renewal happens at original price, but it took more effort than necessary."},
            ],
        },
        {
            "situation": "Sarah Walsh invites you to present at their quarterly business review. You have 10 minutes with the full executive team.",
            "question": "What do you present?",
            "options": [
                {"text": "A product update highlighting your new features and roadmap",                        "points":  0, "consequence": "Sarah says 'we didn't need a sales pitch.' The relationship cools noticeably."},
                {"text": "ROI achieved using their numbers — delays eliminated, escalations resolved, competitive advantage gained", "points": 10, "consequence": "Sarah shares the presentation with James Ortiz. You're now positioned as a trusted advisor, not a vendor."},
                {"text": "A case study from another company in their industry",                                "points":  3, "consequence": "Interesting but not specific enough to Meridian's situation. A missed opportunity to demonstrate your value."},
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
        {
            "situation": "The contract is signed. Tom is proud of the decision but Linda Park — the former skeptic — is now the primary day-to-day user of your platform.",
            "question": "How do you approach the first month post-close?",
            "options": [
                {"text": "Let your implementation team handle onboarding and move on to your next prospect",   "points":  0, "consequence": "Three months later, Linda's team is frustrated. Implementation issues were foreseeable and you weren't there to catch them."},
                {"text": "Check in with Tom weekly and address any issues he flags",                           "points":  5, "consequence": "Tom appreciates the support but Linda's concerns go unaddressed at the source. A missed relationship opportunity."},
                {"text": "Schedule a direct touchpoint with Linda in week 2 to understand how her team is experiencing the transition", "points": 10, "consequence": "Linda is pleasantly surprised you reached out to her directly. She becomes a co-champion and refers you to a sister division."},
            ],
        },
        {
            "situation": "Tom tells you he's been promoted internally and will be moving to a different business unit. He won't oversee your account anymore.",
            "question": "What do you do?",
            "options": [
                {"text": "Congratulate Tom and ask him to introduce you to whoever replaces him",              "points":  7, "consequence": "Tom makes the intro. The new contact is friendly but cautious and needs time to get up to speed."},
                {"text": "Ask Tom to document your relationship and successes internally before transitioning, then make the intro", "points": 10, "consequence": "Tom writes an internal handoff note that becomes your reference document. His successor starts with a strong picture of the value you've delivered."},
                {"text": "Reach out to Linda to establish her as your new primary champion",                   "points":  3, "consequence": "Linda is receptive but doesn't have Tom's budget influence. The account feels less supported going into renewal."},
            ],
        },
        {
            "situation": "Renewal is in 90 days. Sarah Walsh's team has expanded — she now oversees two additional departments that could benefit from your solution.",
            "question": "How do you prepare for renewal?",
            "options": [
                {"text": "Send the standard renewal paperwork through Procurement",                            "points":  0, "consequence": "Marcus processes it at flat rate. The expansion opportunity is never raised."},
                {"text": "Ask Tom's replacement to lead the renewal conversation",                             "points":  3, "consequence": "Renewal happens but the expansion discussion never comes up — the new contact doesn't know to raise it."},
                {"text": "Request a business review with Sarah to present results before discussing renewal",  "points": 10, "consequence": "Sarah brings the heads of the two new departments. Renewal becomes an expansion conversation."},
            ],
        },
        {
            "situation": "Linda Park tells you she received a vendor pitch offering 'the same solution at lower cost.' She emails you: 'We should probably talk.'",
            "question": "How do you respond to Linda?",
            "options": [
                {"text": "Send Linda a feature comparison document showing your advantages",                   "points":  3, "consequence": "Linda reads it but says the price difference is hard to ignore without more context."},
                {"text": "Match the competitor's pricing immediately to keep Linda's loyalty",                 "points":  0, "consequence": "Linda appreciates it but wonders if she was overcharged before. Trust is subtly damaged."},
                {"text": "Call Linda and ask what specifically is appealing about the competitor's offer",     "points": 10, "consequence": "Linda reveals the pitch was mostly a colleague's talking point. She prefers your solution but needs cover to justify it internally. You help her build that case."},
            ],
        },
        {
            "situation": "James Ortiz (CEO) asks Tom's replacement to arrange a brief meeting with you. He wants to understand your company's long-term strategic direction.",
            "question": "How do you prepare for the CEO meeting?",
            "options": [
                {"text": "Prepare a detailed product roadmap presentation with upcoming features",             "points":  0, "consequence": "James says 'I didn't ask for a feature list — I wanted to understand your strategic direction.' The meeting falls flat."},
                {"text": "Ask Tom's replacement what James cares most about strategically, then tailor your content", "points": 10, "consequence": "You learn James is focused on competitive differentiation. The conversation lands perfectly. He tells Sarah to proceed with renewal and expansion."},
                {"text": "Bring your VP of Sales to signal seniority and partnership",                         "points":  5, "consequence": "James appreciates the seniority signal but the conversation stays surface-level. A missed listening opportunity."},
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
        {
            "situation": "Three months post-close, Tom asks if you can speak at an internal team meeting about how other companies have used the solution.",
            "question": "How do you respond?",
            "options": [
                {"text": "Decline — presenting to a customer's internal team isn't part of your role",        "points":  0, "consequence": "Tom stops advocating for you. Without internal momentum, expansion stalls and renewal confidence drops."},
                {"text": "Accept and prepare a standard industry overview",                                    "points":  5, "consequence": "The session goes fine. Tom introduces you to two colleagues afterward."},
                {"text": "Accept and tailor the content around Meridian's specific results so far",            "points": 10, "consequence": "The session is a hit. James Ortiz hears about it and calls it 'exactly the kind of partnership we want.' An expansion budget conversation begins."},
            ],
        },
        {
            "situation": "Tom refers you to a contact at a partner company. He made the intro informally — you haven't met the contact yet.",
            "question": "What do you do before reaching out to the referral?",
            "options": [
                {"text": "Reach out to the referred contact immediately while the intro is fresh",             "points":  3, "consequence": "The call goes well, but Tom doesn't hear back that you followed up. He feels slightly used."},
                {"text": "Thank Tom and let him know you'll keep him posted as the relationship develops",      "points": 10, "consequence": "Tom appreciates being kept in the loop. He refers you to two more contacts the following month."},
                {"text": "Ask Tom to join the first call with the referred contact",                           "points":  7, "consequence": "Tom joins and the call is productive, but you've asked more of him than necessary."},
            ],
        },
        {
            "situation": "90 days before renewal, Marcus Webb tells you Procurement has a new policy: all vendor contracts must go through a formal RFP — even renewals.",
            "question": "How do you respond?",
            "options": [
                {"text": "Submit the RFP response immediately without engaging Tom or Linda first",            "points":  0, "consequence": "Your response is generic. Tom and Linda can't advocate for you because they weren't part of the process."},
                {"text": "Tell Marcus the policy shouldn't apply to vendors already in good standing",         "points":  3, "consequence": "Marcus holds his ground. You've created friction without resolving anything."},
                {"text": "Contact Tom and Linda to understand the situation and ask if they can advocate for an expedited process", "points": 10, "consequence": "Tom and Linda both advocate internally. The RFP is shortened to a fast-track review. Renewal proceeds within two weeks."},
            ],
        },
        {
            "situation": "A competitor approaches James Ortiz directly with an 'enterprise platform' pitch that includes capabilities beyond your current solution.",
            "question": "How do you respond to this competitive threat?",
            "options": [
                {"text": "Send James a competitive comparison document highlighting your advantages",          "points":  3, "consequence": "James reviews it but asks 'what about the capabilities the other vendor mentioned?' You're now on the defensive."},
                {"text": "Request an urgent meeting with James before they evaluate the competitor",           "points": 10, "consequence": "You discover the competitor's 'extra capabilities' address problems Meridian doesn't actually have. James refocuses on what's working. The threat is neutralized."},
                {"text": "Ask Tom to brief James on the switching costs and disruption risk",                  "points":  7, "consequence": "Tom delivers a compelling message. James decides to hold off — but still wants to see both options evaluated."},
            ],
        },
        {
            "situation": "Sarah Walsh invites you to join a 2-day executive offsite as a 'strategic partner.' You have no formal agenda slot — just access.",
            "question": "How do you approach the two days?",
            "options": [
                {"text": "Use the informal access to introduce your expanded product suite to executives",     "points":  0, "consequence": "Executives feel the offsite became a vendor pitch. Sarah reconsiders the 'strategic partner' framing."},
                {"text": "Listen actively, offer insights on industry trends when asked, and avoid pitching anything", "points": 10, "consequence": "Sarah tells Tom afterward: 'That's the kind of partner we want long-term.' Expansion budget is formally allocated."},
                {"text": "Attend Day 1 but leave early on Day 2 to handle other priorities",                  "points":  5, "consequence": "You miss the strategic planning session on Day 2 where expansion budgets were discussed."},
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
        "decision_indices": [0, 4, 7],
        "raw_max": 30,
        "description": "Avoided forecasting on hope; maintained honest pipeline visibility.",
    },
    {
        "name": "Stakeholder Strategy",
        "max_pts": 30,
        "decision_indices": [0, 1, 2, 7, 9],
        "raw_max": 50,
        "description": "Navigated champion, blocker, and economic buyer correctly.",
    },
    {
        "name": "Deal Strategy",
        "max_pts": 25,
        "decision_indices": [2, 3, 8],
        "raw_max": 30,
        "description": "Handled objections and negotiations with process discipline.",
    },
    {
        "name": "Relationship Quality",
        "max_pts": 20,
        "decision_indices": [1, 3, 4, 5, 6, 9],
        "raw_max": 60,
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
        f"Their 10 decisions:\n\n{transcript}\n\n"
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
        return "Complete all 10 decisions to receive your personalized process coaching."


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
            You will make <strong style="color:#FAFAFA;">10 sequential decisions</strong>.
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
    pct = int((idx / 10) * 100)
    bar_segs = "".join(
        f'<div style="flex:1; height:6px; border-radius:3px; margin-right:3px; '
        f'background:{"#4A90D9" if i <= idx else "#2E3A50"};"></div>'
        for i in range(10)
    )
    st.markdown(
        f'<div style="margin-bottom:0.25rem;">'
        f'<div style="font-size:0.82rem; color:#aaa; margin-bottom:4px;">'
        f'Decision {idx + 1} of 10</div>'
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

        if idx < 9:
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


# ---------------------------------------------------------------------------
# Screen 3 — Scorecard
# ---------------------------------------------------------------------------

def screen_scorecard() -> None:
    _init_state()
    student_name = st.session_state.get("ch2_student_name", "Student")
    variant = st.session_state["ch2_variant"]
    choices = st.session_state["ch2_choices"]
    insight = st.session_state.get("ch2_insight", "")
    decisions = VARIANTS[variant]["decisions"]

    raw_total, scaled_total, dim_results = compute_scores(choices)

    # Deal outcome (raw out of 100 with 10 decisions)
    if raw_total >= 80:
        outcome, outcome_color = "Deal Closed ✅", "#27AE60"
    elif raw_total >= 50:
        outcome, outcome_color = "Deal Stalled ⚠️", "#F39C12"
    else:
        outcome, outcome_color = "Deal Lost ❌", "#E74C3C"

    # Tier
    if scaled_total >= 90:
        tier, tier_color = "Deal Architect", "#27AE60"
    elif scaled_total >= 75:
        tier, tier_color = "Strong Process", "#4A90D9"
    elif scaled_total >= 60:
        tier, tier_color = "Developing", "#F39C12"
    else:
        tier, tier_color = "Rerun Recommended", "#E74C3C"

    # --- Header ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Student", student_name)
    with col2:
        st.metric("Scenario", "Meridian Deal")
    with col3:
        st.metric("Date", date.today().strftime("%B %d, %Y"))

    st.markdown("---")
    st.markdown("## Chapter 2 — Stakeholder Navigation Scorecard")

    # Deal outcome banner
    st.markdown(
        f'<div style="background:#1A2332; border:2px solid {outcome_color}; border-radius:10px;'
        f' padding:0.8rem 1.2rem; margin-bottom:1rem; display:flex; justify-content:space-between;'
        f' align-items:center;">'
        f'<div style="font-size:1.1rem; font-weight:700; color:{outcome_color};">{outcome}</div>'
        f'<div style="color:#aaa; font-size:0.88rem;">Raw score: {raw_total}/100</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Score + tier banner
    st.markdown(
        f'<div style="background:#1A2332; border:2px solid {tier_color}; border-radius:10px;'
        f' padding:1rem 1.2rem; text-align:center; margin-bottom:1.2rem;">'
        f'<div style="font-size:2rem; font-weight:700; color:{tier_color};">{scaled_total}/100</div>'
        f'<div style="font-size:1.1rem; font-weight:700; color:#FAFAFA; margin-top:0.2rem;">{tier}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # --- Dimension breakdown ---
    st.markdown("### Dimension Breakdown")
    for dim in dim_results:
        pct = int(dim["scaled"] / dim["max_pts"] * 100) if dim["max_pts"] else 0
        bar_c = "#27AE60" if pct >= 70 else ("#F39C12" if pct >= 40 else "#E74C3C")
        st.markdown(
            f'<div style="margin-bottom:0.7rem;">'
            f'<div style="display:flex; justify-content:space-between; font-size:0.88rem;'
            f' color:#FAFAFA; margin-bottom:3px;">'
            f'<span style="font-weight:600;">{dim["name"]}</span>'
            f'<span style="color:#4A90D9;">{dim["scaled"]}/{dim["max_pts"]}</span></div>'
            f'<div style="background:#0E1117; border-radius:4px; height:8px;">'
            f'<div style="background:{bar_c}; width:{pct}%; height:8px; border-radius:4px;"></div>'
            f'</div>'
            f'<div style="font-size:0.8rem; color:#aaa; margin-top:2px;">{dim["description"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # --- Decision review ---
    st.markdown("---")
    st.markdown("### Decision Review")
    all_pts = [choices.get(i, {}).get("points", 0) for i in range(10)]
    best_idx = all_pts.index(max(all_pts))
    worst_idx = all_pts.index(min(all_pts))

    for i, dec in enumerate(decisions):
        c = choices.get(i, {})
        pts = c.get("points", 0)
        opt_letter = chr(65 + c.get("option_idx", 0))
        if pts >= 8:
            pt_color, badge = "#27AE60", "✅"
        elif pts >= 4:
            pt_color, badge = "#F39C12", "⚠️"
        else:
            pt_color, badge = "#E74C3C", "❌"
        highlight = " border:1px solid #4A90D9;" if i in (best_idx, worst_idx) else ""
        st.markdown(
            f'<div style="background:#1A2332;{highlight} border-radius:8px;'
            f' padding:0.55rem 0.9rem; margin-bottom:0.4rem; display:flex;'
            f' justify-content:space-between; align-items:flex-start;">'
            f'<div style="flex:1;">'
            f'<span style="color:#4A90D9; font-weight:700; font-size:0.82rem;">Decision {i+1}</span>'
            f'<span style="color:#FAFAFA; font-size:0.88rem; margin-left:0.5rem;">'
            f'{badge} {opt_letter}) {_html.escape(c.get("text", ""))}</span>'
            f'</div>'
            f'<div style="color:{pt_color}; font-weight:700; font-size:0.88rem;'
            f' white-space:nowrap; margin-left:0.5rem;">{pts} pts</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Best / worst callouts
    st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)
    bc1, bc2 = st.columns(2)
    with bc1:
        best_c = choices.get(best_idx, {})
        st.markdown(
            f'<div style="background:#0D1F14; border:1px solid #27AE60; border-radius:8px;'
            f' padding:0.7rem 0.9rem;">'
            f'<div style="font-size:0.78rem; font-weight:700; color:#27AE60;'
            f' text-transform:uppercase; margin-bottom:0.25rem;">⭐ Best Decision</div>'
            f'<div style="color:#FAFAFA; font-size:0.87rem; font-weight:600;">Decision {best_idx+1} — {best_c.get("points",0)} pts</div>'
            f'<div style="color:#ddd; font-size:0.83rem; margin-top:0.2rem;">'
            f'{_html.escape(best_c.get("consequence",""))}</div></div>',
            unsafe_allow_html=True,
        )
    with bc2:
        worst_c = choices.get(worst_idx, {})
        st.markdown(
            f'<div style="background:#1A0F0F; border:1px solid #E74C3C; border-radius:8px;'
            f' padding:0.7rem 0.9rem;">'
            f'<div style="font-size:0.78rem; font-weight:700; color:#E74C3C;'
            f' text-transform:uppercase; margin-bottom:0.25rem;">📌 Weakest Decision</div>'
            f'<div style="color:#FAFAFA; font-size:0.87rem; font-weight:600;">Decision {worst_idx+1} — {worst_c.get("points",0)} pts</div>'
            f'<div style="color:#ddd; font-size:0.83rem; margin-top:0.2rem;">'
            f'{_html.escape(worst_c.get("consequence",""))}</div></div>',
            unsafe_allow_html=True,
        )

    # --- Process insight ---
    if insight:
        st.markdown("---")
        st.markdown(
            f'<div style="background:#0D1B2E; border-left:4px solid #4A90D9;'
            f' padding:0.9rem 1.1rem; border-radius:0 8px 8px 0;">'
            f'<div style="font-weight:700; color:#4A90D9; margin-bottom:0.4rem; font-size:0.95rem;">'
            f'💡 What your decisions reveal about your B2B process understanding</div>'
            f'<div style="color:#ddd; font-size:0.92rem; line-height:1.65;">'
            f'{_html.escape(insight)}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    if st.button("Try Again →", use_container_width=True):
        _reset_state()
        st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_chapter2() -> None:
    _init_state()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("Chapter 2.png", use_column_width=True)
    phase = st.session_state["ch2_phase"]
    if phase == "setup":
        screen_setup()
    elif phase == "game":
        screen_game()
    elif phase == "scorecard":
        screen_scorecard()
    else:
        screen_setup()
