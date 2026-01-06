# server.py
import os
import re
import csv
import streamlit as st
from openai import OpenAI

# ---------- CONFIG ----------
st.set_page_config(
    page_title="VisitWise — AI triage assistant",
    layout="wide"
)

# ---------- COLORS ----------
COLORS = {
    "bg": "#f8fafc",
    "card": "#ffffff",
    "accent": "#2b7cff",
    "muted": "#64748b"
}

# ---------- GLOBAL STYLES ----------
st.markdown(f"""
<style>

/* Page background */
.stApp {{
    background-color: {COLORS['bg']};
    color: #0f172a;
}}

/* Center main content */
.block-container {{
    max-width: 900px;
    padding-top: 2rem;
}}

/* Sidebar */
section[data-testid="stSidebar"] {{
    background-color: #f1f5f9;
    padding-top: 1.5rem;
}}

/* Banner */
.visitwise-banner {{
    background: linear-gradient(90deg, #eef6ff, #e6f0ff);
    padding: 26px 32px;
    border-radius: 18px;
    margin-bottom: 22px;
}}

.visitwise-title {{
    font-size: 30px;
    font-weight: 800;
    color: #2b7cff;
}}

.visitwise-subtitle {{
    font-size: 15px;
    color: #475569;
}}

/* Chat card */
.chat-card {{
    background: #ffffff;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 4px 14px rgba(15,23,42,0.05);
    margin-bottom: 16px;
}}

/* Button */
div.stButton > button {{
    background-color: #2b7cff;
    color: white;
    border-radius: 10px;
    padding: 6px 16px;
    font-weight: 600;
    border: none;
}}

div.stButton > button:hover {{
    background-color: #1f66e5;
    color: white;
}}

</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown("""
<div class="visitwise-banner">
    <div class="visitwise-title">VisitWise</div>
    <div class="visitwise-subtitle">
        AI-Powered triage assistant and symptom educator
    </div>
</div>
""", unsafe_allow_html=True)

# ---------- DATA ----------
DATA_FOLDER = "data"
CSV_PATH = os.path.join(DATA_FOLDER, "medicines.csv")

if os.path.exists(os.path.join(DATA_FOLDER, "medicines.csv.csv")) and not os.path.exists(CSV_PATH):
    os.rename(os.path.join(DATA_FOLDER, "medicines.csv.csv"), CSV_PATH)

def load_medicines():
    items = []
    if not os.path.exists(CSV_PATH):
        return items
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        items.extend(reader)
    return items

MEDICINES = load_medicines()

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thinking" not in st.session_state:
    st.session_state.thinking = False

if "profile" not in st.session_state:
    st.session_state.profile = {
        "age": 0,
        "gender": "",
        "medical_history": ""
    }

# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown("### Profile (optional)")
    st.session_state.profile["age"] = st.number_input(
        "Age", min_value=0, max_value=120, value=0
    )
    st.session_state.profile["gender"] = st.selectbox(
        "Gender", ["", "Female", "Male", "Non-binary", "Other"]
    )
    st.session_state.profile["medical_history"] = st.text_area(
        "Medical history (optional)", height=80
    )

# ---------- SECTION TITLE ----------
st.markdown("""
<h3 style="color:#475569; font-weight:600; margin-bottom:10px;">
Chat with VisitWise
</h3>
""", unsafe_allow_html=True)

# ---------- DISPLAY LAST RESPONSE ----------
if st.session_state.messages:
    last_bot = next(
        (m["content"] for m in reversed(st.session_state.messages) if m["role"] == "bot"),
        None
    )
    if last_bot:
        st.markdown(f"""
        <div class="chat-card">
            <strong>VisitWise</strong><br>
            {last_bot}
        </div>
        """, unsafe_allow_html=True)

# ---------- INPUT ----------
st.markdown('<div class="chat-card">', unsafe_allow_html=True)

with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_area(
        "Describe your symptoms",
        height=120,
        placeholder="e.g. Headache and nausea for two days"
    )
    send = st.form_submit_button("Send")

st.markdown('</div>', unsafe_allow_html=True)

# ---------- EMERGENCY DETECTION ----------
EMERGENCY_RE = re.compile(
    r"\bchest pain\b|\bdifficulty breathing\b|\bshortness of breath\b|\bunconscious\b|\bstroke\b",
    re.IGNORECASE
)

# ---------- OPENAI ----------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are VisitWise, a triage assistant and symptom educator.

RULES:
- Give friendly, short guidance in 1–2 sentences
- Never diagnose or name conditions
- Never name illnesses
- Only general advice
- Suggest OTC medication cautiously with dose reminder
- Recommend GP if appropriate
- Urgent symptoms → urgent care
"""

def safe_openai_response(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=300
    )
    return response.choices[0].message.content.strip()

# ---------- SEND ----------
if send and user_input.strip():
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )
    st.session_state.thinking = True

# ---------- RESPONSE ----------
if st.session_state.thinking:
    last_msg = st.session_state.messages[-1]["content"]

    if EMERGENCY_RE.search(last_msg):
        reply = "⚠️ These symptoms may be serious — please seek urgent medical care immediately."
    else:
        reply = safe_openai_response(f"""
User message: {last_msg}
Age: {st.session_state.profile['age']}
Gender: {st.session_state.profile['gender']}
Medical history: {st.session_state.profile['medical_history']}
Non-prescription items: {MEDICINES}
""")

    st.session_state.messages.append(
        {"role": "bot", "content": reply}
    )
    st.session_state.thinking = False
    st.rerun()

# ---------- FOOTER ----------
st.markdown("""
<p style="text-align:center; color:#64748b; font-size:14px; margin-top:32px;">
For emergencies call local services (999 / 112 / 911).
</p>
""", unsafe_allow_html=True)
