# server.py
import os
import re
import csv
import streamlit as st
from openai import OpenAI

# ---------- CONFIG ----------
st.set_page_config(page_title="VisitWise — AI triage assistant", layout="wide")

# ---------- COLOR SCHEME ----------
COLORS = {
    "bg": "#e9f4ff",
    "card": "#ffffff",
    "accent": "#2b7cff",
    "muted": "#475569",
    "soft": "#eaf6ff",
    "savebox_dark": "#003a99",
    "savebox_light": "#4d8fff"
}

st.markdown(
    f"""
    <style>
    .stApp {{background-color: {COLORS['bg']}; color: #0f172a;}}
    .user-msg {{background: linear-gradient(90deg,#e6f4ff,#dbeeff); padding: 10px; border-radius: 12px; max-width: 80%; margin-left: auto; margin-bottom: 6px;}}
    .bot-msg {{background: linear-gradient(90deg,#fbfdff,#eef9ff); padding: 10px; border-radius: 12px; max-width: 80%; margin-right: auto; margin-bottom: 6px;}}
    .thinking {{font-style: italic; color: {COLORS['accent']};}}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- DATA ----------
DATA_FOLDER = "data"
CSV_PATH = os.path.join(DATA_FOLDER, "medicines.csv")

# Fix double-extension bug if it exists
if os.path.exists(os.path.join(DATA_FOLDER, "medicines.csv.csv")) and not os.path.exists(CSV_PATH):
    os.rename(os.path.join(DATA_FOLDER, "medicines.csv.csv"), CSV_PATH)

def load_medicines():
    items = []
    if not os.path.exists(CSV_PATH):
        print("WARNING: medicines.csv not found")
        return items
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append(row)
    return items

MEDICINES = load_medicines()

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thinking" not in st.session_state:
    st.session_state.thinking = False

if "profile" not in st.session_state:
    st.session_state.profile = {"age": "", "gender": "", "medical_history": ""}

# ---------- PROFILE SIDEBAR ----------
with st.sidebar:
    st.markdown("### Profile (optional)")
    st.session_state.profile["age"] = st.number_input("Age", min_value=0, max_value=120, value=0)
    st.session_state.profile["gender"] = st.selectbox("Gender", ["", "Female", "Male", "Non-binary", "Other"])
    st.session_state.profile["medical_history"] = st.text_area(
        "Medical history (optional)",
        value=st.session_state.profile["medical_history"],
        height=80
    )

# ---------- CHAT AREA ----------
st.markdown("## Chat with VisitWise")

with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_area("Describe your symptoms", height=60)
    send = st.form_submit_button("Send")

# ---------- EMERGENCY REGEX ----------
EMERGENCY_RE = re.compile(
    r"\bchest pain\b|\bdifficulty breathing\b|\bshortness of breath\b|\bunconscious\b|\bstroke\b",
    re.IGNORECASE
)

# ---------- OPENAI CLIENT ----------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are VisitWise, a triage assistant and symptom educator.

RULES:
- If message begins with "I have" always address the user, regardless of age, but if message begins with "my son/daughter/child etc." address what the user can do to aid that person.
- Give replies as if you are sending a friendly message to someone in one or two clear sentences.
- Give concise short advice that is easily readable
- Never name illnesses or conditions.
- Never diagnose.
- If question is nothing to do with Symptoms, please say "Please contain the conversation to medical advice" and do not respond further.
- You are only answering medical questions.
- Always mention to research recommended dose amount for over the counter medication or include recommended amount in medicine advice sentence.
- Advise the Over-the-counter medications if you see fit.
- Only give general guidance.
- Advise seeing a GP if you see fit but only if Over-the-counter medication or other at home recovery methods will not suffice for the presumed illness.
- Never name any illnesses.
- If symptoms sound severe, recommend urgent care.
- You may reference non‑prescription products in general terms.
"""

def safe_openai_response(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.2
    )
    return response.choices[0].message.content.strip()

# ---------- SEND MESSAGE ----------
if send and user_input.strip():
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.thinking = True

# ---------- PROCESS BOT RESPONSE ----------
if st.session_state.thinking and st.session_state.messages:
    last_user_msg = st.session_state.messages[-1]["content"]

    if EMERGENCY_RE.search(last_user_msg):
        reply = "⚠️ Your symptoms may be serious — please contact emergency services immediately."
    else:
        user_prompt = f"""
User message: {last_user_msg}
Age: {st.session_state.profile['age']}
Gender: {st.session_state.profile['gender']}
Medical history: {st.session_state.profile['medical_history']}

Non‑prescription items list:
{MEDICINES}

Respond with general safe advice only.
"""
        reply = safe_openai_response(user_prompt)

    st.session_state.messages.append({"role": "bot", "content": reply})
    st.session_state.thinking = False

# ---------- DISPLAY CHAT ----------
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-msg"><strong>You:</strong> {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bot-msg"><strong>VisitWise:</strong> {msg["content"]}</div>', unsafe_allow_html=True)

# ---------- SHOW THINKING ----------
if st.session_state.thinking:
    st.markdown('<div class="thinking">VisitWise is thinking...</div>', unsafe_allow_html=True)

# ---------- FOOTER ----------
st.markdown(f"<footer style='color:{COLORS['muted']}; margin-top:12px'>For emergencies call local services (999/112/911).</footer>", unsafe_allow_html=True)


