"""Multimodal Construction Intelligence Platform — Skill Wallet Capstone Project 1.

AI outputs are decision-support only. Never use this demo to certify site safety or
make structural decisions without qualified professional inspection.
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import streamlit as st
from PIL import Image, UnidentifiedImageError

try:
    from google import genai
    from google.genai import types
except ImportError:  # Graceful demo-mode fallback when optional SDK is unavailable.
    genai = None
    types = None

APP_NAME = "Multimodal Construction Intelligence Platform"
APP_SUBTITLE = "Skill Wallet · Capstone Project 1"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_IMAGE_BYTES = 12 * 1024 * 1024

st.set_page_config(page_title=APP_NAME, page_icon="🏗️", layout="wide", initial_sidebar_state="expanded")

# ------------------------------- Styling ------------------------------------
st.markdown(
    """
    <style>
    .block-container {max-width: 1450px; padding-top: 1.25rem; padding-bottom: 2.5rem;}
    .hero {padding: 1.45rem 1.65rem; border-radius: 18px; color: #fff; margin-bottom: 1.1rem;
      background: linear-gradient(118deg,#102a43 0%,#145da0 57%,#16817d 100%);}
    .hero h1 {font-size: clamp(1.65rem,3vw,2.45rem); line-height:1.15; margin:.2rem 0 .45rem 0;}
    .hero p {font-size:1rem; margin:0; opacity:.92;}
    .eyebrow {font-size:.75rem; letter-spacing:.15em; text-transform:uppercase; font-weight:800; opacity:.8;}
    .section-title {font-size:1.3rem; font-weight:800; color:#14283e; margin:.1rem 0 .7rem 0;}
    .muted {color:#65758b; font-size:.88rem;}
    .metric-card {border:1px solid #e2e9f0; border-radius:14px; background:#fff; padding:1rem 1.1rem; min-height:112px;}
    .metric-label {color:#607187; font-size:.82rem; margin-bottom:.4rem;}
    .metric-value {color:#14283e; font-size:1.65rem; font-weight:800; line-height:1.2;}
    .metric-note {color:#607187; font-size:.77rem; margin-top:.4rem;}
    .pill {display:inline-block; border-radius:999px; padding:.28rem .68rem; font-size:.81rem; font-weight:800;}
    .pill-green {background:#d9f7e7;color:#11643a;} .pill-amber {background:#fff0c2;color:#805400;}
    .pill-red {background:#ffe0df;color:#9d2424;} .pill-blue {background:#dceeff;color:#124f82;}
    div[data-testid="stMetric"] {border:1px solid #e2e9f0; padding:.9rem 1rem; border-radius:13px; background:white;}
    .stTabs [data-baseweb="tab-list"] {gap:.4rem;}
    .stTabs [data-baseweb="tab"] {padding:10px 13px; border-radius:9px 9px 0 0;}
    div.stButton > button, div.stDownloadButton > button {border-radius:10px; font-weight:700;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------- Utilities ----------------------------------
def money_inr(value: float) -> str:
    """Format INR in lakhs/crores for dashboard display."""
    value = max(0.0, float(value))
    if value >= 10_000_000:
        return f"₹{value / 10_000_000:,.2f} Cr"
    if value >= 100_000:
        return f"₹{value / 100_000:,.2f} L"
    return f"₹{value:,.0f}"


def metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def status_pill(label: str) -> None:
    value = label.lower()
    if any(token in value for token in ("safe", "compliant", "normal", "low", "stable", "good")):
        style = "pill-green"
    elif any(token in value for token in ("critical", "unsafe", "high", "urgent", "structural shear")):
        style = "pill-red"
    elif any(token in value for token in ("insufficient", "review", "medium", "improvement", "unknown")):
        style = "pill-amber"
    else:
        style = "pill-blue"
    st.markdown(f'<span class="pill {style}">{html.escape(label)}</span>', unsafe_allow_html=True)


def download_json(label: str, data: Dict[str, Any], filename: str) -> None:
    st.download_button(label, data=json.dumps(data, indent=2, ensure_ascii=False), file_name=filename,
                       mime="application/json", use_container_width=False)


def get_secret_key() -> str:
    key = ""
    try:
        key = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        pass
    return key or os.getenv("GEMINI_API_KEY", "").strip()


def build_client(api_key: str):
    if not api_key or genai is None:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as exc:
        st.sidebar.warning(f"Gemini client setup failed; demo mode remains available. ({exc})")
        return None


def parse_json_response(text: str) -> Dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        if cleaned[:4].lower() == "json":
            cleaned = cleaned[4:].strip()
    left, right = cleaned.find("{"), cleaned.rfind("}")
    if left < 0 or right <= left:
        raise ValueError("The model did not return a JSON object. Please retry.")
    data = json.loads(cleaned[left:right + 1])
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object from the model.")
    return data


def analyze_image(client, prompt: str, image: Image.Image) -> Dict[str, Any]:
    if client is None or types is None:
        raise RuntimeError("Gemini is not configured.")
    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=[prompt, image],
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2),
    )
    return parse_json_response(response.text or "")


def analyze_text(client, prompt: str) -> str:
    if client is None:
        raise RuntimeError("Gemini is not configured.")
    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.35, max_output_tokens=900),
    )
    return (response.text or "No response was returned.").strip()


def safe_image(uploaded_file) -> Optional[Image.Image]:
    if uploaded_file is None:
        return None
    if uploaded_file.size > MAX_IMAGE_BYTES:
        st.error("Image is larger than 12 MB. Please resize it and upload again.")
        return None
    try:
        img = Image.open(uploaded_file)
        img.verify()
        uploaded_file.seek(0)
        return Image.open(uploaded_file).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        st.error(f"Could not read image: {exc}")
        return None


def make_report_metadata(report: Dict[str, Any], mode: str) -> Dict[str, Any]:
    report.setdefault("report_generated_at_utc", datetime.now(timezone.utc).isoformat())
    report.setdefault("analysis_mode", mode)
    report.setdefault("disclaimer", "Advisory only. Requires competent on-site verification; not a compliance certificate or structural diagnosis.")
    return report


def safety_demo() -> Dict[str, Any]:
    return {
        "safety_score": 76,
        "overall_status": "Needs Improvement",
        "ppe_detection": {
            "helmet": {"status": "Detected on some workers", "confidence": 0.78},
            "high_visibility_vest": {"status": "Partially detected", "confidence": 0.81},
            "steel_toe_boots": {"status": "Not verifiable from image", "confidence": 0.34},
            "safety_harness": {"status": "Not verifiable from image", "confidence": 0.29},
        },
        "hazards": [
            {"hazard": "Possible unprotected edge / fall exposure", "severity": "High",
             "corrective_remedy": "Have a competent person inspect the edge; install suitable guardrails or approved fall-protection controls before access."},
            {"hazard": "PPE cannot be fully verified from a photograph", "severity": "Medium",
             "corrective_remedy": "Check footwear and task-specific fall protection during an on-site walk-through."},
        ],
        "limitations": "DEMO SIMULATION — these findings were not derived from the uploaded photo.",
    }


def crack_demo() -> Dict[str, Any]:
    return {
        "defect_type": "Hairline", "estimated_crack_width_mm": 0.4, "confidence": 0.61,
        "likely_root_causes": ["Drying shrinkage", "Curing or surface-restraint variation"],
        "recommended_repairs": ["Record width and location; monitor for progression with a crack gauge.",
                                 "Have an engineer determine whether sealing is appropriate before selecting a repair system."],
        "urgency": "Medium", "requires_engineer_inspection": True,
        "limitations": "DEMO SIMULATION — this is not a diagnosis of the uploaded image.",
    }


def validate_safety(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data["safety_score"] = max(0, min(100, int(float(data.get("safety_score", 0)))))
    except (TypeError, ValueError):
        data["safety_score"] = 0
    data.setdefault("overall_status", "Review Required")
    data.setdefault("ppe_detection", {})
    data.setdefault("hazards", [])
    if not isinstance(data["ppe_detection"], dict):
        data["ppe_detection"] = {}
    if not isinstance(data["hazards"], list):
        data["hazards"] = []
    return data


def validate_crack(data: Dict[str, Any]) -> Dict[str, Any]:
    data.setdefault("defect_type", "Unclassified")
    data.setdefault("estimated_crack_width_mm", None)
    data.setdefault("confidence", None)
    data.setdefault("likely_root_causes", [])
    data.setdefault("recommended_repairs", [])
    data.setdefault("urgency", "Engineer Review Required")
    data.setdefault("requires_engineer_inspection", True)
    return data

# ------------------------------- Sidebar ------------------------------------
with st.sidebar:
    st.markdown("## 🏗️ MCIP")
    st.caption(APP_SUBTITLE)
    stored_key = get_secret_key()
    entered_key = st.text_input("Google Gemini API key", type="password",
                                placeholder="Enter key to enable live AI", help="Used only for this active session; not stored by this app.")
    api_key = entered_key.strip() or stored_key
    if api_key:
        st.success("Live AI configured" if genai else "Gemini SDK unavailable — demo mode")
    else:
        st.info("Demo mode · no API key required")
    client = build_client(api_key) if api_key else None
    st.divider()
    st.markdown("### Architecture overview")
    st.markdown("**UI:** Streamlit  ·  **AI:** Gemini multimodal  \n**Inputs:** Site photos and project assumptions  \n**Outputs:** JSON reports, estimates, advisory  \n**Persistence:** Session state only  \n**Deploy:** Streamlit Community Cloud")
    st.divider()
    st.markdown("### Feature navigation")
    st.markdown("1. Site Safety & PPE Audit  \n2. Crack Diagnostics  \n3. Planning & Valuation  \n4. Daily Site Assistant")
    st.caption(f"Model: `{DEFAULT_MODEL}`")

# -------------------------------- Header ------------------------------------
st.markdown(f'<div class="hero"><div class="eyebrow">{APP_SUBTITLE}</div><h1>{APP_NAME}</h1><p>AI-assisted site safety, defect triage, project economics and daily construction guidance.</p></div>', unsafe_allow_html=True)
st.warning("Engineering disclaimer: AI-generated findings and illustrative estimates are preliminary decision support only. They are not legal/code certification, quantity-surveyor estimates, or structural diagnoses.")

# ================================= Tabs =====================================
tab_safety, tab_crack, tab_planning, tab_assistant = st.tabs([
    "🦺 Site Safety & PPE Audit", "🧱 Crack Diagnostics", "📐 Planning & Valuation", "🌦️ Daily Site Assistant"
])

# -------------------------- Tab 1: Safety -----------------------------------
with tab_safety:
    st.markdown('<div class="section-title">Site Safety & PPE Audit</div>', unsafe_allow_html=True)
    st.write("Upload a JPG or PNG site photo to review visible PPE indicators and possible hazards.")
    safety_upload = st.file_uploader("Construction site photo", type=["jpg", "jpeg", "png"], key="safety_upload")
    safety_img = safe_image(safety_upload)
    if safety_img:
        st.image(safety_img, caption="Uploaded construction-site photo", use_container_width=True)
    if st.button("Run PPE & hazard audit", type="primary", key="run_safety", use_container_width=True):
        if safety_img is None:
            st.error("Please upload a valid JPG/PNG image first.")
        elif client is None:
            st.session_state.safety_report = make_report_metadata(safety_demo(), "demo")
            st.info("Demo report generated. It is simulated and does not describe your uploaded image.")
        else:
            safety_prompt = """
Act as a cautious construction safety assistant. Analyze only visible evidence in this photo. Return a JSON object with:
- safety_score: integer 0-100; overall_status: one of Compliant, Needs Improvement, Unsafe, Insufficient Visual Evidence.
- ppe_detection: keys helmet, high_visibility_vest, steel_toe_boots, safety_harness; each value has status (string) and confidence (number 0-1).
- hazards: array of {hazard, severity (Low|Medium|High|Critical), corrective_remedy}.
- limitations: string.
Consider worker helmets, high-visibility vests, steel-toe boots, and safety harnesses. Do not claim hidden footwear or other obscured equipment is present. Identify only evidence-supported hazards; if visibility is poor, say so. Offer practical remedies. Contextualize relevant OSHA construction safety concepts but do not certify legal compliance from an image. IS 456 is a concrete design code, not a PPE checklist; do not misrepresent it. Never invent details. Output JSON only.
"""
            try:
                with st.spinner("Analyzing photo with Gemini…"):
                    report = validate_safety(analyze_image(client, safety_prompt, safety_img))
                    st.session_state.safety_report = make_report_metadata(report, "gemini_live")
            except Exception as exc:
                st.error(f"Live analysis failed: {exc}")
                st.info("A labelled demonstration report is shown instead; it is not based on your image.")
                demo = safety_demo()
                demo["limitations"] += f" Live analysis error: {type(exc).__name__}."
                st.session_state.safety_report = make_report_metadata(demo, "demo_fallback")

    safety_report = st.session_state.get("safety_report")
    if safety_report:
        st.divider()
        if safety_report.get("analysis_mode", "").startswith("demo"):
            st.info("DEMONSTRATION DATA — do not use this report to assess the uploaded site.")
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Safety score", f"{safety_report.get('safety_score', 0)}/100")
        with c2:
            st.markdown("**Overall status**")
            status_pill(str(safety_report.get("overall_status", "Review Required")))
        with c3: st.metric("Hazards listed", len(safety_report.get("hazards", [])))
        st.progress(safety_report.get("safety_score", 0) / 100)
        st.markdown("#### PPE detection checklist")
        ppe = safety_report.get("ppe_detection", {})
        ppe_labels = [("helmet", "Helmet"), ("high_visibility_vest", "High-visibility vest"),
                      ("steel_toe_boots", "Steel-toe boots"), ("safety_harness", "Safety harness")]
        pcols = st.columns(4)
        for idx, (key, label) in enumerate(ppe_labels):
            item = ppe.get(key, {})
            if isinstance(item, dict):
                status = str(item.get("status", "Not assessed"))
                conf = item.get("confidence")
            else:
                status, conf = str(item), None
            with pcols[idx]:
                st.markdown(f"**{label}**")
                status_pill(status)
                if isinstance(conf, (int, float)):
                    st.caption(f"Model confidence: {max(0, min(1, conf)):.0%} · not a guarantee")
        st.markdown("#### Identified hazards & corrective remedies")
        hazards = safety_report.get("hazards", [])
        if not hazards:
            st.success("No hazards listed in this output. This does not prove the site is hazard-free.")
        for item in hazards:
            if not isinstance(item, dict):
                st.write(str(item)); continue
            with st.expander(f"{item.get('hazard', 'Hazard')} · {item.get('severity', 'Unrated')}", expanded=True):
                st.markdown("**Corrective remedy**")
                st.write(item.get("corrective_remedy", "No remedy provided."))
        if safety_report.get("limitations"):
            st.caption(f"Limitations: {safety_report['limitations']}")
        download_json("⬇️ Download safety JSON", safety_report, "site_safety_audit.json")

# -------------------------- Tab 2: Cracks -----------------------------------
with tab_crack:
    st.markdown('<div class="section-title">Crack Diagnostics & Structural Integrity</div>', unsafe_allow_html=True)
    st.write("Upload a concrete or wall-surface photo for preliminary visual triage.")
    crack_upload = st.file_uploader("Concrete / wall surface photo", type=["jpg", "jpeg", "png"], key="crack_upload")
    crack_img = safe_image(crack_upload)
    if crack_img:
        st.image(crack_img, caption="Uploaded surface photo", use_container_width=True)
    if st.button("Analyze visible defect", type="primary", key="run_crack", use_container_width=True):
        if crack_img is None:
            st.error("Please upload a valid JPG/PNG image first.")
        elif client is None:
            st.session_state.crack_report = make_report_metadata(crack_demo(), "demo")
            st.info("Demo diagnosis generated. It is simulated and not based on your uploaded image.")
        else:
            crack_prompt = """
You are a cautious visual construction-defect triage assistant. Examine the supplied photo and return JSON only.
Schema: defect_type (one of Hairline, Settlement, Structural Shear, Thermal Expansion, Spalling, Uncertain);
estimated_crack_width_mm (number or null; state that scale is unavailable if no reference is visible);
confidence (0-1); likely_root_causes (array of strings); recommended_repairs (array of strings);
urgency (Low, Medium, High, Critical, Engineer Review Required); requires_engineer_inspection (boolean); limitations (string).
Potential repairs may mention epoxy injection or structural re-grouting only conditionally, when an engineer confirms suitability. Never prescribe a repair solely from a photo. Explain that width estimates are uncertain without a scale, distinguish symptoms from causes, and flag potentially progressive, diagonal/shear-like, wide, displaced, or spalling defects for prompt qualified inspection. No false certainty. Output JSON only.
"""
            try:
                with st.spinner("Reviewing surface image with Gemini…"):
                    report = validate_crack(analyze_image(client, crack_prompt, crack_img))
                    st.session_state.crack_report = make_report_metadata(report, "gemini_live")
            except Exception as exc:
                st.error(f"Live analysis failed: {exc}")
                st.info("A labelled demonstration report is shown instead; it is not based on your image.")
                demo = crack_demo(); demo["limitations"] += f" Live analysis error: {type(exc).__name__}."
                st.session_state.crack_report = make_report_metadata(demo, "demo_fallback")

    crack_report = st.session_state.get("crack_report")
    if crack_report:
        st.divider()
        if crack_report.get("analysis_mode", "").startswith("demo"):
            st.info("DEMONSTRATION DATA — do not use this as a diagnosis of the uploaded surface.")
        a, b, c = st.columns(3)
        with a:
            st.markdown("**Defect classification**")
            status_pill(str(crack_report.get("defect_type", "Uncertain")))
        with b:
            width = crack_report.get("estimated_crack_width_mm")
            st.metric("Estimated width", f"{width} mm" if isinstance(width, (int, float)) else "Not estimable")
        with c:
            st.markdown("**Urgency**")
            status_pill(str(crack_report.get("urgency", "Engineer Review Required")))
        conf = crack_report.get("confidence")
        if isinstance(conf, (int, float)):
            st.caption(f"Model confidence: {max(0, min(1, conf)):.0%} · not a probability of structural safety")
        st.markdown("#### Possible root causes")
        roots = crack_report.get("likely_root_causes", [])
        if roots:
            for cause in roots: st.markdown(f"- {cause}")
        else: st.write("No root causes returned; qualified inspection is required.")
        st.markdown("#### Recommended next steps / repairs")
        repairs = crack_report.get("recommended_repairs", [])
        if repairs:
            for repair in repairs: st.markdown(f"- {repair}")
        else: st.write("No repair recommendation returned.")
        if crack_report.get("requires_engineer_inspection", True):
            st.warning("Qualified engineer inspection is required before selecting a structural repair.")
        if crack_report.get("limitations"):
            st.caption(f"Limitations: {crack_report['limitations']}")
        download_json("⬇️ Download crack report JSON", crack_report, "crack_diagnostics.json")

# -------------------------- Tab 3: Planning ---------------------------------
with tab_planning:
    st.markdown('<div class="section-title">Planning & Real Estate Valuation</div>', unsafe_allow_html=True)
    st.caption("Illustrative feasibility model. Edit assumptions with a local QS/engineer/valuer before relying on estimates.")
    left, right = st.columns([1.05, 1])
    with left:
        structure = st.selectbox("Structure type", ["Residential", "Commercial", "Warehouse / Industrial", "Institutional"])
        area = st.number_input("Built-up area (sq ft)", min_value=250, max_value=2_000_000, value=2_000, step=250)
        city_tier = st.selectbox("Location tier", ["Tier 1", "Tier 2", "Tier 3"], index=1,
                                 help="Choose based on your project market; city classification is an assumption.")
        completion = st.slider("Construction completion (%)", min_value=0, max_value=100, value=35, step=5)
    with right:
        st.markdown("#### Assumptions (editable)")
        cost_defaults = {
            "Residential": {"Tier 1": 2700, "Tier 2": 2100, "Tier 3": 1700},
            "Commercial": {"Tier 1": 3600, "Tier 2": 2800, "Tier 3": 2300},
            "Warehouse / Industrial": {"Tier 1": 1900, "Tier 2": 1550, "Tier 3": 1300},
            "Institutional": {"Tier 1": 3200, "Tier 2": 2500, "Tier 3": 2100},
        }
        market_defaults = {
            "Residential": {"Tier 1": 9000, "Tier 2": 5800, "Tier 3": 3900},
            "Commercial": {"Tier 1": 12500, "Tier 2": 8000, "Tier 3": 5200},
            "Warehouse / Industrial": {"Tier 1": 4200, "Tier 2": 3000, "Tier 3": 2200},
            "Institutional": {"Tier 1": 7000, "Tier 2": 4800, "Tier 3": 3300},
        }
        cost_rate = st.number_input("Construction budget rate (₹ / sq ft)", min_value=500, max_value=25000,
                                    value=cost_defaults[structure][city_tier], step=100, key=f"cost_rate_{structure}_{city_tier}")
        market_rate = st.number_input("Market valuation rate (₹ / sq ft)", min_value=500, max_value=100000,
                                      value=market_defaults[structure][city_tier], step=100, key=f"market_rate_{structure}_{city_tier}")
        contingency_pct = st.slider("Contingency allowance (%)", 0, 25, 10, 1)

    base_cost = area * cost_rate
    contingency = base_cost * contingency_pct / 100
    total_budget = base_cost + contingency
    capex_incurred = total_budget * completion / 100
    remaining = max(0.0, total_budget - capex_incurred)
    asset_value = area * market_rate
    # Order-of-magnitude planning thumb rules only; design and structural system change quantities materially.
    steel_kg_sqft = {"Residential": 3.8, "Commercial": 4.8, "Warehouse / Industrial": 2.6, "Institutional": 4.5}[structure]
    cement_bags_sqft = {"Residential": 0.40, "Commercial": 0.48, "Warehouse / Industrial": 0.28, "Institutional": 0.45}[structure]
    steel_tonnes = area * steel_kg_sqft / 1000
    cement_bags = area * cement_bags_sqft

    st.divider()
    k1, k2, k3, k4 = st.columns(4)
    with k1: metric_card("Estimated total budget", money_inr(total_budget), f"Base {money_inr(base_cost)} + contingency")
    with k2: metric_card("Capital expenditure incurred", money_inr(capex_incurred), f"{completion}% completion assumption")
    with k3: metric_card("Remaining budget", money_inr(remaining), "Simple pro-rata estimate")
    with k4: metric_card("Current market asset value", money_inr(asset_value), "Area × assumed market rate")
    p1, p2 = st.columns([1, 1])
    with p1:
        st.markdown("#### Milestone progress")
        st.progress(completion / 100)
        st.write(f"**{completion}%** estimated complete")
        steps = [("Planning", 10), ("Foundation", 25), ("Structure", 60), ("Finishes", 85), ("Handover", 100)]
        reached = [name for name, threshold in steps if completion >= threshold]
        st.write("Reached milestones: " + (", ".join(reached) if reached else "Planning not yet complete"))
    with p2:
        st.markdown("#### Indicative material requirements")
        st.metric("Steel", f"{steel_tonnes:,.1f} tonnes", f"Rule of thumb: {steel_kg_sqft:g} kg/sq ft")
        st.metric("Cement", f"{cement_bags:,.0f} bags", f"Rule of thumb: {cement_bags_sqft:g} bags/sq ft")
    planning_report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "structure_type": structure,
        "built_up_area_sqft": area, "location_tier_assumption": city_tier, "completion_percent": completion,
        "construction_rate_inr_per_sqft": cost_rate, "market_rate_inr_per_sqft": market_rate,
        "contingency_percent": contingency_pct, "estimated_base_cost_inr": round(base_cost, 2),
        "contingency_inr": round(contingency, 2), "estimated_total_project_budget_inr": round(total_budget, 2),
        "estimated_capex_incurred_inr": round(capex_incurred, 2), "estimated_remaining_budget_inr": round(remaining, 2),
        "estimated_current_market_asset_value_inr": round(asset_value, 2), "indicative_steel_tonnes": round(steel_tonnes, 2),
        "indicative_cement_bags": round(cement_bags, 0),
        "methodology_note": "Illustrative assumptions only. Verify local rates, design BOQ, wastage, taxes, financing, land costs, and market comparables.",
    }
    download_json("⬇️ Download planning estimate JSON", planning_report, "planning_valuation_estimate.json")

    st.divider()
    st.markdown("#### Conceptual 3D architectural rendering prompt")
    style = st.selectbox("Rendering style", ["Photorealistic modern", "Sustainable tropical", "Contemporary Indian", "Industrial minimal", "Brutalist concrete"])
    extras = st.text_input("Site / design notes", placeholder="e.g., 3 floors, courtyard, solar roof, landscaped entry")
    render_prompt = (f"Architectural concept visualization of a {structure.lower()} building, {area:,} square feet built-up, "
                     f"for an Indian {city_tier.lower()} city, {style.lower()} style, construction progress concept at {completion} percent. "
                     f"Design notes: {extras or 'clean massing, realistic materials, professional architectural presentation'}. "
                     "Wide composition, 3D architectural rendering, daylight, realistic scale, no text, no labels, concept art only.")
    st.text_area("Generated prompt", value=render_prompt, height=100, key="render_prompt_display")
    pollinations_url = "https://gen.pollinations.ai/image/" + quote(render_prompt, safe="") + "?model=black-forest-labs/flux.1-schnell"
    st.link_button("Open concept render with Pollinations AI", pollinations_url, help="Opens the image-generation endpoint in a new tab. Service availability and access requirements may vary.")
    st.caption("Rendering is conceptual, not a stamped architectural design or construction drawing.")

# -------------------------- Tab 4: Assistant -------------------------------
WEATHER_ADVISORIES = {
    "High Wind": ("High-wind precautions", "Pause crane/lifting operations when the manufacturer's or site lift-plan wind limits are reached. Secure loose materials, inspect scaffolds and temporary works, and follow the lift supervisor's stop-work criteria."),
    "Heavy Rain": ("Rain and electrical safety", "Stop work in flooded or unstable areas. Protect temporary electrical systems with suitable RCD/GFCI protection, keep connections elevated and dry, inspect excavations for water ingress, and check formwork, access routes and slopes before restarting."),
    "Extreme Heat": ("Heat stress and concrete curing", "Schedule strenuous work in cooler periods, provide shade, drinking water and rest breaks, and use a buddy/heat-illness response plan. Protect fresh concrete from rapid moisture loss and follow the approved curing method and mix/design specification."),
    "Normal": ("Routine site controls", "Continue toolbox talks, housekeeping, access control, PPE checks, lifting-plan compliance and inspection of temporary works. Confirm the day's permits, weather forecast and emergency arrangements."),
}

with tab_assistant:
    st.markdown('<div class="section-title">Daily Site Assistant & Weather-Aware Advisory</div>', unsafe_allow_html=True)
    wx = st.selectbox("Current / expected condition", list(WEATHER_ADVISORIES.keys()))
    title, advisory = WEATHER_ADVISORIES[wx]
    if wx == "Normal":
        st.success(f"**{title}**\n\n{advisory}")
    elif wx == "Extreme Heat":
        st.warning(f"**{title}**\n\n{advisory}")
    else:
        st.error(f"**{title}**\n\n{advisory}")
    st.caption("Use site-specific weather thresholds, approved method statements and the appointed competent person's stop-work authority.")
    st.divider()
    st.markdown("#### Construction engineering assistant")
    st.caption("Ask about sequencing, materials, planning, QA/QC, method statements or toolbox talks. Do not use this chatbot for emergency decisions or final structural design.")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    user_question = st.chat_input("Ask a construction question…")
    if user_question:
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)
        with st.chat_message("assistant"):
            if client:
                history = st.session_state.chat_history[-12:]
                transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)
                assistant_prompt = (
                    "You are a careful construction engineering support assistant. Answer in clear, practical language. "
                    "Ask clarifying questions where important project details are missing. Do not certify compliance, "
                    "invent local code clauses, or prescribe final structural design. For high-risk or structural concerns, "
                    "direct the user to a licensed engineer/site safety professional. Account for selected weather condition: "
                    f"{wx}. Current alert: {advisory}\n\nConversation:\n{transcript}\n\nAssistant response:"
                )
                try:
                    with st.spinner("Thinking…"):
                        answer = analyze_text(client, assistant_prompt)
                except Exception as exc:
                    answer = f"I couldn't reach Gemini right now ({type(exc).__name__}). Please retry, or continue in demo mode with general guidance only."
            else:
                q = user_question.lower()
                if any(word in q for word in ["crack", "column", "beam", "foundation", "structural"]):
                    answer = ("For a structural concern, document the location, pattern, approximate width, and whether it is changing; "
                              "restrict access if there are signs of movement, falling concrete, or instability, and arrange prompt inspection by a licensed structural engineer. "
                              "Do not choose epoxy injection or re-grouting from a photo alone. [DEMO MODE]")
                elif any(word in q for word in ["concrete", "curing", "cement", "pour"]):
                    answer = (f"For concrete work, follow the approved mix design, placement plan, temperature limits and curing specification. Current weather note: {advisory} "
                              "Confirm the method with the site engineer before changing water addition, admixtures or curing procedure. [DEMO MODE]")
                elif any(word in q for word in ["crane", "wind", "rain", "heat", "weather", "lift"]):
                    answer = f"Weather advisory for {wx}: {advisory} Follow the approved lift plan and site stop-work thresholds. [DEMO MODE]"
                else:
                    answer = ("I am in demonstration mode because no Gemini API key is configured. For a real site, first identify the work activity, "
                              "hazards, applicable approved method statement, and responsible competent person. Follow the project safety plan and consult the engineer for design decisions. [DEMO MODE]")
            st.markdown(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Clear chat", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()

# -------------------------------- Footer ------------------------------------
st.divider()
st.caption("MCIP · Skill Wallet Capstone Project 1 · Stateless by design (session state only) · Validate all AI outputs before field use.")
