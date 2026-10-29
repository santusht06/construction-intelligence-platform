import json
import os
import re
from datetime import datetime
from io import BytesIO
from urllib.parse import quote

import streamlit as st
from PIL import Image

APP_NAME = "Multimodal Construction Intelligence Platform"
DEFAULT_MODEL = "gemini-2.5-flash"

st.set_page_config(page_title=f"{APP_NAME} | Santusht Kotai", page_icon="🏗️", layout="wide")

# ----------------------------- Styling ---------------------------------------
st.markdown("""
<style>
:root { --ink:#172033; --muted:#65718a; --accent:#f59e0b; --panel:#ffffff; }
.block-container {padding-top:1.4rem; padding-bottom:2rem; max-width:1440px;}
.hero {padding:1.4rem 1.6rem; border-radius:18px; color:white;
       background:linear-gradient(120deg,#172033 0%,#253c59 62%,#8b5e19 100%); margin-bottom:1rem;}
.hero h1 {font-size:2rem; margin:0 0 .35rem 0; color:white;}
.hero p {margin:0; color:#e8edf5;}
.section-note {color:#65718a; font-size:.92rem;}
.metric-card {border:1px solid #e4e8ef; border-radius:14px; padding:1rem;
              background:linear-gradient(180deg,#fff,#f8fafc); min-height:112px;}
.metric-label {font-size:.82rem;color:#65718a;margin-bottom:.35rem;}
.metric-value {font-size:1.55rem;font-weight:750;color:#172033;}
.pill {display:inline-block;padding:.25rem .65rem;border-radius:99px;font-weight:700;font-size:.8rem;}
.pill-good {background:#dcfce7;color:#166534}.pill-warn {background:#fef3c7;color:#92400e}
.pill-bad {background:#fee2e2;color:#991b1b}.pill-neutral {background:#e2e8f0;color:#334155}
div[data-testid="stMetric"] {background:#fff;border:1px solid #e4e8ef;padding:14px;border-radius:14px;}
[data-testid="stSidebar"] {border-right:1px solid #e5e7eb;}
.small-muted {color:#65718a;font-size:.82rem;}
</style>
""", unsafe_allow_html=True)


# ----------------------------- Utilities -------------------------------------
def pill(label, tone="neutral"):
    tone = tone if tone in {"good", "warn", "bad", "neutral"} else "neutral"
    st.markdown(f'<span class="pill pill-{tone}">{label}</span>', unsafe_allow_html=True)

def json_download(data, filename):
    st.download_button("⬇️ Download JSON report", data=json.dumps(data, indent=2, ensure_ascii=False),
                       file_name=filename, mime="application/json", use_container_width=False)

def safe_json_from_text(text):
    """Extract a JSON object from model output, tolerating markdown fences."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.I)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise ValueError("The AI response did not contain valid JSON.")

def image_to_bytes(upload):
    image = Image.open(upload).convert("RGB")
    image.thumbnail((1600, 1600))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue(), image

def gemini_generate(api_key, prompt, image_bytes=None, mime_type="image/jpeg", history=None):
    """Call Gemini via official SDK or REST fallback."""
    model = st.session_state.get("model_name", DEFAULT_MODEL)
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        contents = []
        if history:
            contents.extend(history)
        if image_bytes:
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
        contents.append(prompt)
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        return response.text or ""
    except Exception as sdk_err:
        import base64
        import urllib.request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        parts = []
        if image_bytes:
            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({"inline_data": {"mime_type": mime_type, "data": b64_data}})
        parts.append({"text": prompt})
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.2}
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
                return ""
        except Exception as rest_err:
            raise RuntimeError(f"Gemini API error (SDK: {sdk_err}, REST: {rest_err})")

def call_or_demo(api_key, prompt, demo_data, image_bytes=None, mime_type="image/jpeg"):
    if api_key:
        try:
            raw = gemini_generate(api_key, prompt, image_bytes, mime_type)
            return safe_json_from_text(raw), "Gemini AI"
        except Exception as exc:
            st.error(f"Gemini request failed. Showing demo output instead. Details: {exc}")
    return demo_data, "Demonstration mode (illustrative; not image-derived)"

def inr(value):
    return f"₹{value:,.0f}"

def inr_compact(value):
    if value >= 1e7:
        return f"₹{value / 1e7:.2f} Cr"
    if value >= 1e5:
        return f"₹{value / 1e5:.2f} L"
    return inr(value)

def make_demo_safety():
    return {
        "safety_score": 78,
        "overall_status": "Needs Improvement",
        "ppe_detection": {
            "helmets": {"status": "Partially compliant", "observations": "Some workers may require helmet verification."},
            "high_visibility_vests": {"status": "Partially compliant", "observations": "Check all workers in active work zones."},
            "steel_toe_boots": {"status": "Not verifiable", "observations": "Footwear protection cannot be confirmed from this view."},
            "safety_harnesses": {"status": "Not verifiable", "observations": "Harness use depends on work-at-height exposure."}
        },
        "hazards": [
            {"hazard": "Unverified PPE coverage", "severity": "Medium", "location": "Active work area",
             "remedy": "Pause entry to the work zone until the competent supervisor verifies required PPE."},
            {"hazard": "Potential trip hazards", "severity": "Low", "location": "Ground-level access",
             "remedy": "Clear debris, route cables safely, and keep access paths unobstructed."}
        ],
        "limitations": "Illustrative demonstration data only; no image was analyzed."
    }

def make_demo_crack():
    return {
        "defect_type": "Hairline",
        "estimated_crack_width_mm": 0.3,
        "confidence": "Low (demonstration only)",
        "likely_root_causes": ["Drying shrinkage", "Thermal movement"],
        "recommended_repairs": [
            "Record crack width and length; install a dated monitoring gauge if appropriate.",
            "Have a qualified structural engineer inspect before selecting a repair method."
        ],
        "urgency": "Routine inspection",
        "red_flags": ["Rapid widening, water ingress, displacement, or diagonal cracks near supports require prompt professional assessment."],
        "limitations": "Illustrative demonstration data only; no image was analyzed."
    }

# ----------------------------- Sidebar ---------------------------------------
with st.sidebar:
    st.markdown("## 🏗️ Construction Intelligence")
    st.caption("Developed by **Santusht Kotai**")
    api_key = st.text_input("Google Gemini API key", type="password",
                            help="Used only for requests made in this session. Avoid sharing or committing keys.")
    st.session_state["model_name"] = st.text_input("Gemini model", value=DEFAULT_MODEL,
                                                   help="Change this if your API project uses a different supported model.")
    st.markdown("---")
    st.markdown("### Architecture")
    st.markdown("**Streamlit UI** → Gemini multimodal API → validated JSON → metrics and reports")
    st.caption("Local session state only. No external database.")
    st.markdown("---")
    st.markdown("### Modules")
    st.markdown("1. Site safety & PPE audit\n2. Crack diagnostics\n3. Planning & valuation\n4. Site assistant & weather")
    st.info("Without an API key, image-analysis tabs return clearly labelled demo data.")
    st.markdown("---")
    st.markdown("**Safety note:** AI outputs are decision support, not a certified inspection, structural diagnosis, valuation, or engineering approval.")

# ----------------------------- Header ----------------------------------------
st.markdown(f"""
<div class="hero">
  <h1>🏗️ {APP_NAME}</h1>
  <p>Multimodal site intelligence for safety audits, defect triage, project planning and weather-aware operations.</p>
  <p style="margin-top: 0.5rem; font-size: 0.95rem; opacity: 0.95;">Created & Maintained by <strong>Santusht Kotai</strong></p>
</div>
""", unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs([
    "🦺 Site Safety & PPE", "🧱 Crack Diagnostics",
    "📐 Planning & Valuation", "🌦️ Daily Site Assistant"
])

# ----------------------------- Tab 1 -----------------------------------------
with t1:
    st.subheader("Site Safety & PPE Audit")
    st.markdown('<p class="section-note">Upload a clear site photo. Results are visual screening support and must be verified by a competent safety professional.</p>', unsafe_allow_html=True)
    upload = st.file_uploader("Construction site photo", type=["jpg", "jpeg", "png"], key="safety_img")
    if upload:
        try:
            image_bytes, preview = image_to_bytes(upload)
            st.image(preview, caption="Uploaded site photo", use_container_width=True)
            if st.button("Run PPE & hazard audit", type="primary", key="run_safety"):
                prompt = """Act as a construction safety visual screening assistant. Inspect the supplied image only.
Return ONLY valid JSON with this schema:
{"safety_score": integer 0-100, "overall_status": string,
"ppe_detection":{"helmets":{"status":string,"observations":string},
"high_visibility_vests":{"status":string,"observations":string},
"steel_toe_boots":{"status":string,"observations":string},
"safety_harnesses":{"status":string,"observations":string}},
"hazards":[{"hazard":string,"severity":"Low|Medium|High|Critical","location":string,"remedy":string}],
"limitations":string}
Distinguish visible evidence from not-verifiable items; never claim boots or hidden PPE are confirmed from an image that cannot show them. Identify only observable hazards. Use OSHA concepts and applicable Indian site practice; do not claim that IS 456 is a PPE standard. Include uncertainty and recommend professional verification. No markdown."""
                with st.spinner("Reviewing image…"):
                    result, source = call_or_demo(api_key, prompt, make_demo_safety(), image_bytes, "image/jpeg")
                st.session_state["safety_result"] = result
                st.session_state["safety_source"] = source
        except Exception as exc:
            st.error(f"Could not read the uploaded image: {exc}")
    result = st.session_state.get("safety_result")
    if result:
        st.markdown("### Audit summary")
        c1, c2, c3 = st.columns(3)
        score = max(0, min(100, int(result.get("safety_score", 0))))
        c1.metric("Safety score", f"{score}/100")
        c2.metric("Overall status", str(result.get("overall_status", "Not specified")))
        c3.metric("Hazards identified", len(result.get("hazards", [])))
        st.caption(f"Source: {st.session_state.get('safety_source', 'Unknown')}")
        st.progress(score / 100)
        st.markdown("#### PPE checklist")
        ppe = result.get("ppe_detection", {})
        labels = [("helmets", "Helmets"), ("high_visibility_vests", "High-visibility vests"),
                  ("steel_toe_boots", "Steel-toe boots"), ("safety_harnesses", "Safety harnesses")]
        cols = st.columns(2)
        for idx, (key, label) in enumerate(labels):
            item = ppe.get(key, {})
            with cols[idx % 2]:
                st.markdown(f"**{label}**")
                st.write(item.get("status", "Not assessed") if isinstance(item, dict) else str(item))
                if isinstance(item, dict) and item.get("observations"):
                    st.caption(item["observations"])
        st.markdown("#### Hazards & corrective actions")
        hazards = result.get("hazards", [])
        if hazards:
            for h in hazards:
                severity = str(h.get("severity", "Unknown"))
                tone = "bad" if severity in ("Critical", "High") else "warn" if severity == "Medium" else "neutral"
                with st.container(border=True):
                    st.markdown(f"**{h.get('hazard', 'Hazard')}**")
                    pill(severity, tone)
                    st.caption(h.get("location", "Location not specified"))
                    st.write(h.get("remedy", "Obtain a competent-person review."))
        else:
            st.success("No hazards were returned. This does not prove the site is hazard-free.")
        if result.get("limitations"):
            st.warning(result["limitations"])
        json_download(result, f"site_safety_audit_{datetime.now():%Y%m%d_%H%M%S}.json")

# ----------------------------- Tab 2 -----------------------------------------
with t2:
    st.subheader("Crack Diagnostics & Structural Integrity")
    st.markdown('<p class="section-note">Visual triage only. Crack width estimates from a photo are unreliable without a scale reference; structural decisions require a qualified engineer.</p>', unsafe_allow_html=True)
    crack_upload = st.file_uploader("Concrete or wall surface photo", type=["jpg", "jpeg", "png"], key="crack_img")
    scale_known = st.checkbox("A measurement scale is visible beside the crack", value=False)
    if crack_upload:
        try:
            crack_bytes, crack_preview = image_to_bytes(crack_upload)
            st.image(crack_preview, caption="Uploaded surface photo", use_container_width=True)
            if st.button("Analyze visible defect", type="primary", key="run_crack"):
                prompt = f"""Inspect the supplied concrete/wall image for visible defects. Scale visible beside crack: {scale_known}.
Return ONLY valid JSON:
{{"defect_type":"Hairline|Settlement|Structural Shear|Thermal Expansion|Spalling|Uncertain",
"estimated_crack_width_mm": number or null, "confidence":"Low|Medium|High",
"likely_root_causes":[string], "recommended_repairs":[string],
"urgency":"Routine inspection|Schedule engineer review|Prompt engineer assessment|Immediate safety assessment",
"red_flags":[string], "limitations":string}}
Do not infer exact crack width without a visible scale; return null or a broad uncertain estimate. Do not prescribe epoxy injection or re-grouting unless appropriate and conditional on engineer assessment. Flag displacement, progressive cracks, exposed reinforcement, falling concrete, or load-bearing concerns. No markdown."""
                with st.spinner("Assessing visible defect…"):
                    result, source = call_or_demo(api_key, prompt, make_demo_crack(), crack_bytes, "image/jpeg")
                st.session_state["crack_result"] = result
                st.session_state["crack_source"] = source
        except Exception as exc:
            st.error(f"Could not read the uploaded image: {exc}")
    result = st.session_state.get("crack_result")
    if result:
        st.markdown("### Diagnostic summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Defect classification", result.get("defect_type", "Uncertain"))
        width = result.get("estimated_crack_width_mm")
        c2.metric("Estimated width", f"{width} mm" if width is not None else "Not estimable")
        c3.metric("Urgency", result.get("urgency", "Unspecified"))
        st.caption(f"Source: {st.session_state.get('crack_source', 'Unknown')} · Confidence: {result.get('confidence', 'Not specified')}")
        st.markdown("#### Likely root causes")
        for cause in result.get("likely_root_causes", []):
            st.markdown(f"- {cause}")
        st.markdown("#### Recommended next steps")
        for repair in result.get("recommended_repairs", []):
            st.markdown(f"- {repair}")
        if result.get("red_flags"):
            st.markdown("#### Red flags")
            for flag in result["red_flags"]:
                st.warning(flag)
        if result.get("limitations"):
            st.caption(result["limitations"])
        json_download(result, f"crack_diagnostics_{datetime.now():%Y%m%d_%H%M%S}.json")

# ----------------------------- Tab 3 -----------------------------------------
with t3:
    st.subheader("Project Planning & Real Estate Valuation")
    st.markdown('<p class="section-note">Planning figures are editable assumptions, not a quantity-surveyor estimate or formal property valuation. Calibrate unit rates to local quotations and current market data.</p>', unsafe_allow_html=True)
    left, right = st.columns([1.1, 0.9], gap="large")
    with left:
        structure = st.selectbox("Structure type", ["Residential apartment", "Independent house", "Commercial office", "Warehouse / industrial", "Institutional"])
        area = st.number_input("Built-up area (sq ft)", min_value=100, max_value=2_000_000, value=5000, step=100)
        tier = st.selectbox("Location tier", ["Tier 1", "Tier 2", "Tier 3"])
        completion = st.slider("Construction completion", 0, 100, 35, 5, format="%d%%")
        custom_rate = st.number_input("Build cost rate (₹/sq ft)", min_value=500, max_value=20000, value={"Tier 1": 2600, "Tier 2": 2100, "Tier 3": 1700}[tier], step=100)
        land_value = st.number_input("Estimated land / location value (₹)", min_value=0, value=2500000, step=100000)
        contingency_pct = st.slider("Contingency allowance", 0, 20, 10, 1, format="%d%%")
    multipliers = {"Residential apartment": 1.0, "Independent house": 0.95, "Commercial office": 1.25,
                   "Warehouse / industrial": 0.8, "Institutional": 1.15}
    base_cost = float(area) * float(custom_rate) * multipliers[structure]
    contingency = base_cost * contingency_pct / 100
    total_budget = base_cost + contingency
    incurred = base_cost * completion / 100
    # Early-stage illustrative planning assumptions; not a bill of quantities.
    steel_kg = area * 4.0 * multipliers[structure]
    cement_bags = area * 0.40 * multipliers[structure]
    market_multiplier = {"Tier 1": 1.35, "Tier 2": 1.18, "Tier 3": 1.05}[tier]
    market_value = land_value + base_cost * market_multiplier * (0.35 + 0.65 * completion / 100)
    with right:
        st.markdown("#### Estimated project dashboard")
        st.metric("Estimated construction budget", inr_compact(total_budget))
        st.metric("CapEx incurred to date", inr_compact(incurred), f"{completion}% completion assumption")
        st.metric("Indicative current asset value", inr_compact(market_value))
        st.metric("Estimated steel requirement", f"{steel_kg:,.0f} kg", f"{steel_kg/1000:.1f} tonnes")
        st.metric("Estimated cement requirement", f"{cement_bags:,.0f} bags (50 kg)")
        st.markdown("**Milestone progress**")
        st.progress(completion / 100)
        st.caption(f"{completion}% complete · Remaining budget baseline: {inr_compact(max(0, total_budget - incurred))}")
    st.markdown("---")
    st.markdown("#### Conceptual 3D architectural rendering")
    render_prompt = st.text_area("Describe the desired design", value=f"Photorealistic architectural visualization of a {structure.lower()}, {area:,} square feet, contemporary Indian climate-responsive design, realistic materials, daylight, professional architectural render, no text or watermark.", height=90)
    pollinations_url = "https://image.pollinations.ai/prompt/" + quote(render_prompt, safe="")
    st.link_button("Open conceptual render (Pollinations AI)", pollinations_url)
    st.caption("External image generation service. Avoid entering confidential project/site details. Output is conceptual, not a construction drawing.")
    plan_report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "structure_type": structure, "built_up_area_sqft": area, "location_tier": tier,
        "completion_percent": completion, "assumed_build_rate_inr_per_sqft": custom_rate,
        "contingency_percent": contingency_pct, "estimated_base_construction_cost_inr": round(base_cost),
        "contingency_inr": round(contingency), "estimated_total_budget_inr": round(total_budget),
        "estimated_capex_incurred_inr": round(incurred), "indicative_asset_value_inr": round(market_value),
        "illustrative_steel_requirement_kg": round(steel_kg), "illustrative_cement_bags_50kg": round(cement_bags),
        "assumptions": "Illustrative screening estimates only. Excludes verified BOQ, taxes, financing, approvals, and local market appraisal."
    }
    json_download(plan_report, "construction_planning_estimate.json")

# ----------------------------- Tab 4 -----------------------------------------
with t4:
    st.subheader("Daily Site Assistant & Weather-Aware Advisory")
    weather = st.selectbox("Current / forecast site condition", ["Normal", "High Wind", "Heavy Rain", "Extreme Heat"])
    weather_advice = {
        "Normal": ("Routine controls", "Run toolbox talk, verify PPE and access routes, inspect equipment, and follow approved method statements. Monitor changing forecasts."),
        "High Wind": ("Wind-related controls", "Suspend crane/lifting operations when wind exceeds the equipment or lift-plan limit. Secure loose materials and temporary works; restrict exposed-edge work. Follow manufacturer limits and the lift supervisor's decision."),
        "Heavy Rain": ("Rain / electrical controls", "Stop work in unsafe flooded or lightning-exposed areas. Isolate damaged electrical equipment, use RCD/GFCI protection, inspect excavations and access routes, and protect fresh concrete from washout. Resume only after competent-person checks."),
        "Extreme Heat": ("Heat-stress controls", "Provide shade, drinking water and planned rest breaks; acclimatize workers and use a buddy system. Adjust work-rest cycles to local heat-stress guidance. Protect and cure concrete according to the approved mix and specification.")
    }
    heading, advice = weather_advice[weather]
    tone = "bad" if weather in ("High Wind", "Heavy Rain", "Extreme Heat") else "good"
    with st.container(border=True):
        st.markdown(f"### {heading}")
        pill("Enhanced precautions" if tone == "bad" else "Routine precautions", tone)
        st.write(advice)
    st.markdown("#### Ask the construction assistant")
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [{"role": "assistant", "content": "Hello! I am Santusht Kotai's Construction Intelligence Assistant. I can help with construction planning, safe work procedures, material estimates, and site coordination. Share your structure, activity, and constraints. (Note: Decision support only; verify with licensed engineers and safety officers)."}]
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    user_prompt = st.chat_input("Ask about a site activity, materials, safety, or planning…")
    if user_prompt:
        st.session_state.chat_messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)
        if api_key:
            try:
                # Send a compact conversation context to avoid excessive payloads.
                history = "\n".join(f'{m["role"]}: {m["content"]}' for m in st.session_state.chat_messages[-8:])
                answer = gemini_generate(api_key,
                    "You are a cautious construction engineering assistant for Indian projects. Be practical and concise. "
                    "State assumptions, distinguish general guidance from code-specific requirements, and advise qualified review for structural, legal, electrical, lifting, or life-safety decisions. "
                    "Do not claim certification. Current weather condition selected: " + weather + ".\nConversation:\n" + history)
            except Exception as exc:
                answer = f"AI request failed ({exc}). Demonstration guidance: define the work scope, check the approved method statement and site risk assessment, confirm competent supervision, and stop work if conditions are unsafe."
        else:
            answer = ("Demonstration response: For this activity, review the approved drawings and method statement, perform a task-specific risk assessment, "
                      "confirm competent supervision and required PPE, and document inspections. For structural or life-safety decisions, consult the responsible qualified engineer. "
                      f"Selected weather condition: {weather}. Add a Gemini API key for context-aware AI responses.")
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
    if st.button("Clear chat history"):
        st.session_state.chat_messages = []
        st.rerun()

st.markdown("---")
st.markdown('<p class="small-muted">Developed by <strong>Santusht Kotai</strong> | Prototype decision-support software. Verify applicable Indian codes, local regulations, site conditions and professional advice before acting on results.</p>', unsafe_allow_html=True)
