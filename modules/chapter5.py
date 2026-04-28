import json
import re
import random
import streamlit as st
from datetime import date
from openai import OpenAI
from config import get_openai_api_key

MODEL_COACH = "gpt-4.1-mini"
TEMP_COACH = 0.3

# ---------------------------------------------------------------------------
# Company data
# ---------------------------------------------------------------------------

COMPANIES = {
    "dataflow": {
        "name": "DataFlow Solutions",
        "product": "Supply chain analytics software",
        "industry": "Logistics & freight brokerage",
        "target_customer": "Mid-size freight brokers",
        "geo_hint": "US Southeast",
        "price_min": 45_000,
        "price_max": 95_000,
        "context": (
            "DataFlow helps freight brokers get real-time carrier visibility. "
            "Your job: estimate how big this market is."
        ),
        "market_brief": [
            "There are approximately 17,000 licensed freight brokers in the US (FMCSA data).",
            "About 40% operate primarily in the Southeast region.",
            "Mid-size brokers (our target) represent roughly 25% of the total.",
            "Enterprise software adoption in logistics: ~35% of mid-size firms have invested in visibility tools.",
        ],
    },
    "talentiq": {
        "name": "TalentIQ",
        "product": "HR analytics and workforce planning software",
        "industry": "HR technology",
        "target_customer": "Mid-size companies scaling rapidly (200–500 employees)",
        "geo_hint": "US major metros",
        "price_min": 25_000,
        "price_max": 65_000,
        "context": (
            "TalentIQ helps fast-growing companies make data-driven HR decisions. "
            "Your job: estimate how big this market is."
        ),
        "market_brief": [
            "There are approximately 200,000 companies in the US with 200–500 employees (US Census data).",
            "Fast-growth companies (>20% headcount growth/year) represent roughly 15% of that segment.",
            "Major metro areas (NYC, SF, Austin, Chicago, Seattle) concentrate about 45% of high-growth firms.",
            "HR tech adoption in mid-size companies: ~40% use dedicated workforce analytics tools.",
        ],
    },
    "qualitypro": {
        "name": "QualityPro",
        "product": "Quality management and compliance software",
        "industry": "Medical device manufacturing",
        "target_customer": "FDA-regulated manufacturers (100–500 employees)",
        "geo_hint": "US nationwide",
        "price_min": 60_000,
        "price_max": 120_000,
        "context": (
            "QualityPro helps medical device manufacturers prepare for FDA audits. "
            "Your job: estimate how big this market is."
        ),
        "market_brief": [
            "Approximately 6,500 medical device manufacturers are registered with the FDA in the US.",
            "Firms with 100–500 employees represent about 30% of registered manufacturers.",
            "FDA 21 CFR Part 820 (Quality System Regulation) applies to virtually all device manufacturers.",
            "Digital QMS (quality management software) adoption: ~45% of mid-size device makers use dedicated tools.",
        ],
    },
}

# ---------------------------------------------------------------------------
# Scoring dimensions (used in coach prompt and scorecard)
# ---------------------------------------------------------------------------

DIMENSIONS = [
    {
        "name": "Assumption Quality",
        "max_points": 30,
        "description": "Are your assumptions reasonable for this specific industry?",
        "rubric": (
            "30 pts: Numbers are well-grounded with clear industry logic; geography and segment make sense.\n"
            "22–29 pts: Reasonable with some justification; minor gaps.\n"
            "12–21 pts: Plausible but thin — assumptions not connected to the industry.\n"
            "0–11 pts: Arbitrary numbers, no justification, or nonsensical geography/segment choice."
        ),
    },
    {
        "name": "TAM→SAM→SOM Logic",
        "max_points": 30,
        "description": "Does each level narrow correctly? Is SOM realistic for Year 1?",
        "rubric": (
            "30 pts: Each step narrows correctly; SOM ≤ 10% of SAM (realistic for early stage).\n"
            "22–29 pts: Narrowing logic mostly sound; minor gap in one step.\n"
            "12–21 pts: Narrowing present but SOM > 10% of SAM, or one step doesn't narrow.\n"
            "0–11 pts: SOM ≥ SAM, or SAM ≥ TAM, or fundamental misunderstanding of the framework."
        ),
    },
    {
        "name": "Price × Volume Consistency",
        "max_points": 25,
        "description": "Do your numbers make mathematical sense?",
        "rubric": (
            "25 pts: Price within assigned range; volume numbers internally consistent; math checks out.\n"
            "18–24 pts: Price close to range or minor inconsistency.\n"
            "10–17 pts: Price outside range OR volume numbers don't add up.\n"
            "0–9 pts: Price significantly outside range AND/OR clear math errors."
        ),
    },
    {
        "name": "Strategic Thinking",
        "max_points": 15,
        "description": "Do your notes show you understand WHY market sizing matters for B2B sales?",
        "rubric": (
            "15 pts: Notes explicitly connect sizing to sales strategy (reps needed, prospecting volume, etc.).\n"
            "11–14 pts: Awareness of what the numbers mean, even if not fully developed.\n"
            "6–10 pts: Notes focus on numbers but don't connect to sales implications.\n"
            "0–5 pts: Minimal notes or bare restatement of inputs without reasoning."
        ),
    },
]

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def _init_state() -> None:
    if "ch5_company_key" not in st.session_state:
        last = st.session_state.get("ch5_last_company")
        opts = (
            [k for k in COMPANIES if k != last]
            if (last and len(COMPANIES) > 1)
            else list(COMPANIES.keys())
        )
        st.session_state["ch5_company_key"] = random.choice(opts)

    defaults = {
        "ch5_phase": "setup",
        "ch5_student_name": "",
        "ch5_results": {},
        "ch5_scorecard": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset_state() -> None:
    last = st.session_state.get("ch5_last_company")
    keys = [k for k in st.session_state if k.startswith("ch5_")]
    for k in keys:
        del st.session_state[k]
    if last is not None:
        st.session_state["ch5_last_company"] = last
    _init_state()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(n: int | float) -> str:
    v = float(n)
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.2f} billion"
    if v >= 1_000_000:
        return f"${v / 1_000_000:.2f} million"
    if v >= 1_000:
        return f"${v / 1_000:.2f}K"
    return f"${int(v):,}"


def _word_count(text: str) -> int:
    return len(text.strip().split()) if text.strip() else 0


# ---------------------------------------------------------------------------
# Screen 1 — Setup
# ---------------------------------------------------------------------------

def screen_setup() -> None:
    company_key = st.session_state["ch5_company_key"]
    c = COMPANIES[company_key]

    st.title("Chapter 5 — Know Your Market")
    st.markdown("### TAM / SAM / SOM Calculator")
    st.markdown("---")

    # Company card
    st.markdown(
        f"""
        <div style="background:#1A2332; border:1px solid #2E5FA3;
             border-radius:10px; padding:1.2rem 1.4rem; margin-bottom:0.75rem;">
          <div style="font-size:0.75rem; color:#4A90D9; font-weight:700;
               text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.6rem;">
            🏢 Your Assigned Company
          </div>
          <div style="font-size:1.25rem; font-weight:700; color:#FAFAFA; margin-bottom:0.6rem;">
            {c['name']}
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem 1.4rem;
               margin-bottom:0.75rem;">
            <div>
              <div style="color:#888; font-size:0.8rem;">Product</div>
              <div style="color:#FAFAFA; font-size:0.9rem;">{c['product']}</div>
            </div>
            <div>
              <div style="color:#888; font-size:0.8rem;">Industry</div>
              <div style="color:#FAFAFA; font-size:0.9rem;">{c['industry']}</div>
            </div>
            <div>
              <div style="color:#888; font-size:0.8rem;">Target customer</div>
              <div style="color:#FAFAFA; font-size:0.9rem;">{c['target_customer']}</div>
            </div>
            <div>
              <div style="color:#888; font-size:0.8rem;">Price range</div>
              <div style="color:#FAFAFA; font-size:0.9rem;">${c['price_min']:,}–${c['price_max']:,}/year</div>
            </div>
          </div>
          <div style="border-top:1px solid #2E5FA3; padding-top:0.65rem;
               color:#ddd; font-size:0.9rem; font-style:italic;">
            {c['context']}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Instruction box
    st.markdown(
        """
        <div style="background:#0E1117; border:1px solid #4A90D9;
             border-radius:8px; padding:1.1rem 1.3rem; margin-bottom:0.75rem;">
          <div style="font-weight:700; color:#4A90D9; margin-bottom:0.6rem;">📊 Your Task</div>
          <div style="color:#FAFAFA; font-size:0.92rem; line-height:1.65;">
            Estimate the <strong>TAM, SAM, and SOM</strong> for your assigned company.<br><br>
            <strong>TAM — Total Addressable Market</strong><br>
            Every company that could ever buy this product in your geography.<br><br>
            <strong>SAM — Serviceable Addressable Market</strong><br>
            The portion of TAM you can realistically reach with your sales model.<br><br>
            <strong>SOM — Serviceable Obtainable Market</strong><br>
            What you can realistically capture in Year 1 given your resources.<br><br>
            <strong>Use the top-down method:</strong><br>
            Start with total market size → narrow by segment → narrow by capacity.<br><br>
            Show your assumptions clearly — the AI evaluates your
            <strong>REASONING</strong>, not just your numbers.<br><br>
            🤖 You may use AI to research market size estimates. The evaluation
            focuses on whether your logic is sound, not whether your numbers are perfect.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Scoring rubric expander
    with st.expander("📊 How you'll be scored (100 pts)", expanded=False):
        st.markdown(
            "| Dimension | Points |\n"
            "|-----------|--------|\n"
            "| Assumption Quality | 30 |\n"
            "| TAM→SAM→SOM Logic | 30 |\n"
            "| Price × Volume Consistency | 25 |\n"
            "| Strategic Thinking | 15 |"
        )
        st.markdown("")
        for dim in DIMENSIONS:
            st.markdown(f"**{dim['name']}** — {dim['description']}")
            st.caption(dim["rubric"])

    student_name = st.text_input(
        "Your full name",
        value=st.session_state.get("ch5_student_name", ""),
        placeholder="e.g. Ana García",
        key="ch5_name_input",
    )

    ready = bool(student_name.strip())
    if not ready:
        st.caption("Enter your name above to enable the Start button.")

    if st.button(
        "Start Calculator →",
        disabled=not ready,
        type="primary",
        use_container_width=True,
    ):
        st.session_state["ch5_student_name"] = student_name.strip()
        st.session_state["ch5_last_company"] = company_key
        st.session_state["ch5_phase"] = "calculator"
        st.rerun()


# ---------------------------------------------------------------------------
# Coach prompt
# ---------------------------------------------------------------------------

def get_coach_prompt(
    student_name: str,
    company_key: str,
    tam: int,
    sam: int,
    som: int,
    price: int,
    total_companies: int,
    prospect_pct: int,
    reachable_pct: int,
    closeable_pct: int,
    assumptions: str,
) -> str:
    c = COMPANIES[company_key]
    dim_rubrics = "\n\n".join(
        f"{i + 1}. {d['name'].upper()} ({d['max_points']} pts)\n{d['rubric']}"
        for i, d in enumerate(DIMENSIONS)
    )
    som_pct_of_sam = f"{som / sam * 100:.1f}%" if sam > 0 else "N/A (SAM is 0)"
    price_status = (
        "within assigned range"
        if c["price_min"] <= price <= c["price_max"]
        else f"OUTSIDE assigned range (${c['price_min']:,}–${c['price_max']:,})"
    )

    return f"""You are an expert B2B sales coach evaluating a TAM/SAM/SOM market sizing exercise.

STUDENT NAME: {student_name}
ASSIGNED COMPANY: {c['name']}
PRODUCT: {c['product']}
INDUSTRY: {c['industry']}
TARGET CUSTOMER: {c['target_customer']}
ASSIGNED PRICE RANGE: ${c['price_min']:,}–${c['price_max']:,}/year
GEOGRAPHY HINT: {c['geo_hint']}

STUDENT'S INPUTS:
  Total companies in target segment: {total_companies:,}
  % realistic prospects (TAM→SAM): {prospect_pct}%
  % reachable with sales model (SAM→SOM step 1): {reachable_pct}%
  % closeable Year 1 (SAM→SOM step 2): {closeable_pct}%
  Average annual contract value: ${price:,} — {price_status}

CALCULATED RESULTS:
  TAM: ${tam:,}
  SAM: ${sam:,}
  SOM: ${som:,}
  SOM as % of SAM: {som_pct_of_sam}

STUDENT'S ASSUMPTIONS AND NOTES:
{assumptions}

=== EVALUATION INSTRUCTIONS ===

Do NOT penalize spelling or grammar. Evaluate strategic reasoning only.

Critical checks:
- Does TAM→SAM→SOM narrow at each step? Flag if SOM > SAM or SAM > TAM.
- Is SOM > 10% of SAM? Flag as unrealistic for an early-stage company.
- Is the price within ${c['price_min']:,}–${c['price_max']:,}? Flag if not.
- Are assumptions clearly explained, or are they bare numbers with no justification?

Return ONLY a valid JSON object. No markdown, no backticks, no text before or after.
CRITICAL: Start your response with {{ and end with }}.

{{
  "dimensions": [
    {{
      "name": "Assumption Quality",
      "max_points": 30,
      "score": <integer 0-30>,
      "rationale": "<2-3 sentences>",
      "evidence": "<verbatim quote from student notes, or 'No specific assumption stated'>",
      "coaching_note": <null if score >= 21, otherwise "<2-3 sentences of specific coaching>">
    }},
    {{
      "name": "TAM→SAM→SOM Logic",
      "max_points": 30,
      "score": <integer 0-30>,
      "rationale": "<2-3 sentences evaluating narrowing logic and SOM realism>",
      "evidence": "<describe the narrowing pattern, e.g. SAM is X% of TAM, SOM is Y% of SAM>",
      "coaching_note": <null if score >= 21, otherwise "<2-3 sentences>">
    }},
    {{
      "name": "Price × Volume Consistency",
      "max_points": 25,
      "score": <integer 0-25>,
      "rationale": "<2-3 sentences on price range fit and math consistency>",
      "evidence": "<note whether price is in/out of range and whether the volume math holds>",
      "coaching_note": <null if score >= 18, otherwise "<2-3 sentences>">
    }},
    {{
      "name": "Strategic Thinking",
      "max_points": 15,
      "score": <integer 0-15>,
      "rationale": "<2-3 sentences on whether notes connect sizing to sales strategy>",
      "evidence": "<verbatim quote from notes showing strategic thinking, or 'No strategic reasoning expressed'>",
      "coaching_note": <null if score >= 11, otherwise "<2-3 sentences>">
    }}
  ],
  "total_score": <sum of all dimension scores>,
  "tier": "<one of: Market Ready | Strong Analysis | Developing | Rerun Recommended>",
  "plain_english_summary": "<2 sentences: what the student did well and where they fell short>",
  "one_thing_to_improve": "<1-2 sentences: the single most important change to improve this analysis>",
  "market_insight": "<1 sentence: what this market size means for sales strategy — niche vs. broad, prospecting volume, etc.>"
}}

=== SCORING RUBRIC ===

{dim_rubrics}

Tier assignment:
- 90–100: Market Ready
- 75–89: Strong Analysis
- 60–74: Developing
- Below 60: Rerun Recommended

Score strictly against what the student submitted. Award points only for demonstrated reasoning.
CRITICAL: Return ONLY the JSON object. Start with {{ and end with }}."""


# ---------------------------------------------------------------------------
# API helper
# ---------------------------------------------------------------------------

def call_coach_api(
    student_name: str,
    company_key: str,
    tam: int,
    sam: int,
    som: int,
    price: int,
    total_companies: int,
    prospect_pct: int,
    reachable_pct: int,
    closeable_pct: int,
    assumptions: str,
) -> dict:
    client = OpenAI(api_key=get_openai_api_key())
    prompt = get_coach_prompt(
        student_name, company_key,
        tam, sam, som, price,
        total_companies, prospect_pct, reachable_pct, closeable_pct,
        assumptions,
    )
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
            "tier": "Unknown",
            "plain_english_summary": "Could not parse coach response. Please try again.",
            "one_thing_to_improve": "Re-run the evaluation to receive your scorecard.",
            "market_insight": "",
            "_error": True,
        }


# ---------------------------------------------------------------------------
# Screen 2 — Calculator
# ---------------------------------------------------------------------------

def screen_calculator() -> None:
    st.markdown("<script>window.scrollTo(0, 0);</script>", unsafe_allow_html=True)
    company_key = st.session_state["ch5_company_key"]
    c = COMPANIES[company_key]

    st.title("Chapter 5 — Know Your Market")

    with st.expander(f"🏢 {c['name']} — company context", expanded=False):
        st.markdown(
            f"**Product:** {c['product']}  \n"
            f"**Industry:** {c['industry']}  \n"
            f"**Target customer:** {c['target_customer']}  \n"
            f"**Price range:** ${c['price_min']:,}–${c['price_max']:,}/year  \n"
            f"**Geography hint:** {c['geo_hint']}  \n\n"
            f"*{c['context']}*"
        )

    with st.expander(f"📋 {c['name']} — Market Brief", expanded=True):
        st.markdown(
            "Use these facts — or research your own. "
            "Your job: decide what % applies to this company and justify your reasoning."
        )
        for fact in c["market_brief"]:
            st.markdown(f"- {fact}")

    st.markdown("---")
    st.markdown("#### Geography")

    country = st.text_input(
        "Country",
        value="United States",
        placeholder="e.g. United States",
        key="ch5_input_country",
    )
    region = st.text_input(
        "State / Region (optional)",
        value="",
        placeholder=f"e.g. {c['geo_hint']}",
        key="ch5_input_region",
    )

    st.markdown("#### Market Sizing")

    total_companies = st.number_input(
        "Total companies in target segment in your geography",
        min_value=1,
        max_value=1_000_000,
        value=1_000,
        step=100,
        key="ch5_input_total_companies",
    )
    prospect_pct = st.slider(
        "% that are realistic prospects  (TAM → SAM)",
        min_value=0,
        max_value=100,
        value=30,
        step=1,
        key="ch5_input_prospect_pct",
    )
    reachable_pct = st.slider(
        "% you can reach with your sales model  (SAM → SOM, step 1)",
        min_value=0,
        max_value=100,
        value=20,
        step=1,
        key="ch5_input_reachable_pct",
    )
    closeable_pct = st.slider(
        "% realistic to close in Year 1  (SAM → SOM, step 2)",
        min_value=0,
        max_value=100,
        value=5,
        step=1,
        key="ch5_input_closeable_pct",
    )

    st.markdown("#### Pricing")

    price_default = (c["price_min"] + c["price_max"]) // 2
    avg_contract = st.number_input(
        "Average annual contract value ($)",
        min_value=1_000,
        max_value=10_000_000,
        value=price_default,
        step=1_000,
        key="ch5_input_avg_contract",
    )
    st.caption(
        f"This company's assigned range: ${c['price_min']:,}–${c['price_max']:,}/year"
    )

    # Live calculation
    tam = int(total_companies * avg_contract)
    sam = int(tam * prospect_pct / 100)
    som = int(sam * reachable_pct / 100 * closeable_pct / 100)

    st.markdown("---")
    st.markdown("#### Calculated Results")

    st.markdown(
        f"""
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.75rem;
             margin-bottom:0.75rem;">
          <div style="background:#0E1117; border:1px solid #4A90D9; border-radius:8px;
               padding:1rem; text-align:center;">
            <div style="color:#888; font-size:0.75rem; text-transform:uppercase;
                 letter-spacing:0.06em; margin-bottom:0.3rem;">TAM</div>
            <div style="font-size:1.35rem; font-weight:800; color:#4A90D9;">{_fmt(tam)}</div>
            <div style="color:#aaa; font-size:0.75rem; margin-top:0.2rem;">
              {total_companies:,} cos × {_fmt(avg_contract)}
            </div>
          </div>
          <div style="background:#0E1117; border:1px solid #F39C12; border-radius:8px;
               padding:1rem; text-align:center;">
            <div style="color:#888; font-size:0.75rem; text-transform:uppercase;
                 letter-spacing:0.06em; margin-bottom:0.3rem;">SAM</div>
            <div style="font-size:1.35rem; font-weight:800; color:#F39C12;">{_fmt(sam)}</div>
            <div style="color:#aaa; font-size:0.75rem; margin-top:0.2rem;">
              TAM × {prospect_pct}%
            </div>
          </div>
          <div style="background:#0E1117; border:1px solid #27AE60; border-radius:8px;
               padding:1rem; text-align:center;">
            <div style="color:#888; font-size:0.75rem; text-transform:uppercase;
                 letter-spacing:0.06em; margin-bottom:0.3rem;">SOM</div>
            <div style="font-size:1.35rem; font-weight:800; color:#27AE60;">{_fmt(som)}</div>
            <div style="color:#aaa; font-size:0.75rem; margin-top:0.2rem;">
              SAM × {reachable_pct}% × {closeable_pct}%
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Ratio sanity line
    sam_pct_of_tam = f"{sam / tam * 100:.1f}%" if tam > 0 else "—"
    som_pct_of_sam = f"{som / sam * 100:.1f}%" if sam > 0 else "—"
    st.caption(f"SAM is {sam_pct_of_tam} of TAM — SOM is {som_pct_of_sam} of SAM")

    # Sanity warnings
    if sam > 0 and som > sam:
        st.warning("⚠️ SOM is larger than SAM — check your percentages.")
    elif sam > 0 and som / sam > 0.10:
        st.warning(
            f"⚠️ SOM is {som / sam * 100:.0f}% of SAM. "
            "For an early-stage company, Year 1 capture above 10% of SAM is typically unrealistic."
        )
    if avg_contract < c["price_min"] or avg_contract > c["price_max"]:
        st.warning(
            f"⚠️ Your contract value ({_fmt(avg_contract)}) is outside the assigned range "
            f"(${c['price_min']:,}–${c['price_max']:,})."
        )

    st.markdown("---")
    st.markdown("#### Assumptions & Notes")

    assumptions = st.text_area(
        "Explain your key assumptions. Where did your numbers come from? "
        "Why did you choose these percentages?",
        value="",
        height=180,
        key="ch5_input_assumptions",
        placeholder=(
            "Example: I estimated roughly 2,400 freight brokers in the US Southeast "
            "based on FMCSA registration data. Of those, about 30% have the scale and "
            "pain points to buy analytics software at this price. My sales team can "
            "realistically reach 20% through targeted outbound over the year. In Year 1 "
            "we can close around 5% given typical enterprise sales cycles of 3-6 months..."
        ),
    )

    wc = _word_count(assumptions)
    wc_color = "#27AE60" if wc >= 50 else "#E74C3C"
    st.markdown(
        f"<span style='font-size:0.82rem; color:{wc_color};'>"
        f"{wc} / 50 words minimum</span>",
        unsafe_allow_html=True,
    )

    notes_ok = wc >= 50
    if not notes_ok:
        st.caption(f"Write at least 50 words in your assumptions to unlock AI evaluation ({wc} so far).")

    if st.button(
        "Get AI Evaluation →",
        disabled=not notes_ok,
        type="primary",
        use_container_width=True,
    ):
        results = {
            "country": country,
            "region": region,
            "total_companies": int(total_companies),
            "prospect_pct": int(prospect_pct),
            "reachable_pct": int(reachable_pct),
            "closeable_pct": int(closeable_pct),
            "avg_contract": int(avg_contract),
            "tam": tam,
            "sam": sam,
            "som": som,
            "assumptions": assumptions,
        }
        st.session_state["ch5_results"] = results

        with st.spinner("Evaluating your market analysis — this may take 20–30 seconds…"):
            data = call_coach_api(
                student_name=st.session_state["ch5_student_name"],
                company_key=company_key,
                tam=tam,
                sam=sam,
                som=som,
                price=int(avg_contract),
                total_companies=int(total_companies),
                prospect_pct=int(prospect_pct),
                reachable_pct=int(reachable_pct),
                closeable_pct=int(closeable_pct),
                assumptions=assumptions,
            )
        st.session_state["ch5_scorecard"] = data
        st.session_state["ch5_phase"] = "scorecard"
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 3 — Scorecard
# ---------------------------------------------------------------------------

def screen_scorecard() -> None:
    data: dict = st.session_state["ch5_scorecard"]
    company_key: str = st.session_state["ch5_company_key"]
    student_name: str = st.session_state["ch5_student_name"]
    results: dict = st.session_state.get("ch5_results", {})
    c = COMPANIES[company_key]

    dimensions: list = data.get("dimensions", [])
    total = data.get("total_score") or sum(d.get("score", 0) for d in dimensions)
    max_total = sum(d.get("max_points", 0) for d in dimensions) or 100

    _TIER_COLORS = {
        "Market Ready":      "#27AE60",
        "Strong Analysis":   "#2E86AB",
        "Developing":        "#F39C12",
        "Rerun Recommended": "#E74C3C",
    }
    tier = data.get("tier", "Developing")
    tier_color = _TIER_COLORS.get(tier, "#F39C12")

    st.title("Scorecard — TAM / SAM / SOM")
    st.markdown("---")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Student", student_name)
    with col_b:
        st.metric("Company", c["name"])
    with col_c:
        st.metric("Date", str(date.today()))

    st.markdown("")

    # TAM / SAM / SOM summary
    tam = results.get("tam", 0)
    sam = results.get("sam", 0)
    som = results.get("som", 0)

    st.markdown(
        f"""
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.75rem;
             margin-bottom:1rem;">
          <div style="background:#0E1117; border:1px solid #4A90D9; border-radius:8px;
               padding:1rem; text-align:center;">
            <div style="color:#888; font-size:0.75rem; text-transform:uppercase;
                 letter-spacing:0.06em; margin-bottom:0.3rem;">TAM</div>
            <div style="font-size:1.5rem; font-weight:800; color:#4A90D9;">{_fmt(tam)}</div>
          </div>
          <div style="background:#0E1117; border:1px solid #F39C12; border-radius:8px;
               padding:1rem; text-align:center;">
            <div style="color:#888; font-size:0.75rem; text-transform:uppercase;
                 letter-spacing:0.06em; margin-bottom:0.3rem;">SAM</div>
            <div style="font-size:1.5rem; font-weight:800; color:#F39C12;">{_fmt(sam)}</div>
          </div>
          <div style="background:#0E1117; border:1px solid #27AE60; border-radius:8px;
               padding:1rem; text-align:center;">
            <div style="color:#888; font-size:0.75rem; text-transform:uppercase;
                 letter-spacing:0.06em; margin-bottom:0.3rem;">SOM</div>
            <div style="font-size:1.5rem; font-weight:800; color:#27AE60;">{_fmt(som)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if data.get("plain_english_summary"):
        st.info(data["plain_english_summary"])

    # Score banner
    st.markdown(
        f"""
        <div style="background:{tier_color}22; border:2px solid {tier_color};
             border-radius:12px; padding:1.5rem; text-align:center; margin-bottom:1.5rem;">
          <div style="font-size:3rem; font-weight:800; color:{tier_color};">
            {total} / {max_total}
          </div>
          <div style="font-size:1.4rem; font-weight:700; color:{tier_color}; margin-top:0.25rem;">
            {tier}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Performance tier guide", expanded=False):
        st.markdown(
            "| Score | Tier |\n"
            "|-------|------|\n"
            "| 90–100 | Market Ready |\n"
            "| 75–89 | Strong Analysis |\n"
            "| 60–74 | Developing |\n"
            "| Below 60 | Rerun Recommended |"
        )

    st.markdown("### Dimension Breakdown")

    for dim in dimensions:
        score = dim.get("score", 0)
        max_pts = dim.get("max_points", 0)
        pct = score / max_pts if max_pts else 0
        with st.expander(
            f"**{dim['name']}** — {score} / {max_pts} pts",
            expanded=True,
        ):
            st.progress(pct)
            st.markdown(dim.get("rationale", ""))
            evidence = dim.get("evidence", "")
            no_evidence = (
                not evidence
                or evidence.startswith("No specific")
                or evidence.startswith("No strategic")
            )
            if not no_evidence:
                st.markdown(
                    f'<div style="background:#1A2332; border-left:3px solid #4A90D9; '
                    f'padding:0.6rem 1rem; border-radius:4px; font-style:italic; '
                    f'margin-top:0.5rem; font-size:0.92rem;">'
                    f'Evidence: &#8220;{evidence}&#8221;</div>',
                    unsafe_allow_html=True,
                )
            elif evidence:
                st.caption(f"Note: {evidence}")

            coaching = dim.get("coaching_note")
            if coaching and coaching != "null" and pct < 0.7:
                st.warning(f"**Coaching note:** {coaching}")

    st.markdown("---")

    # Market insight (blue, prominent)
    if data.get("market_insight"):
        st.markdown(
            f"""
            <div style="background:#112030; border:2px solid #4A90D9;
                 border-radius:8px; padding:1rem 1.2rem; margin-bottom:1rem;">
              <div style="font-size:0.78rem; color:#4A90D9; font-weight:700;
                   text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.4rem;">
                📈 Market Insight
              </div>
              <div style="color:#FAFAFA; font-size:0.95rem;">{data['market_insight']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # One thing to improve
    if data.get("one_thing_to_improve"):
        st.markdown(
            f"""
            <div style="background:#1A2332; border:2px solid #F39C12;
                 border-radius:8px; padding:1rem 1.2rem; margin-bottom:1.5rem;">
              <div style="font-size:0.88rem; font-weight:700; color:#F39C12; margin-bottom:0.3rem;">
                💡 One Thing to Improve
              </div>
              <div style="color:#ddd; font-size:0.95rem;">{data['one_thing_to_improve']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button("↩ Try Again with a new company", use_container_width=True):
        _reset_state()
        st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_chapter5() -> None:
    _init_state()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("Chapter 5.png", use_column_width=True)
    phase = st.session_state["ch5_phase"]
    if phase == "setup":
        screen_setup()
    elif phase == "calculator":
        screen_calculator()
    elif phase == "scorecard":
        screen_scorecard()
