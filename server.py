import os
import re
import csv
import streamlit as st
from openai import OpenAI

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="VisitWise — AI triage assistant",
    page_icon="🩺",
    layout="wide"
)

# -----------------------------
# STYLING (matches your HTML)
# -----------------------------
st.markdown("""
<style>
:root {
  --bg:#e9f4ff;
  --card:#ffffff;
  --accent:#2b7cff;
  --muted:#475569;
}
body { background-color: var(--bg); }

.card {
  background: var(--card);
  padding: 14px;
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(20,30,60,0.06);
}

.chatbox {
  height: 480px;
  overflow-y: auto;
  padding: 12px;
  border-radius: 10px;
  background: linear-gradient(180deg,#fff,#fbfeff);
  border: 1px solid #e6f2ff;
}

.msg-user {
  background: linear-gradient(90deg,#e6f4ff,#dbeeff);
  padding: 10px;
  border-radius: 12px;
  margin: 8px 0 8px auto;
  max-width: 80%;
}

.msg-bot {
  background: linear-gradient(90deg,#fbfdff,#eef9ff);
  padding: 10px;
  border-radius: 12px;
  margin: 8px auto 8px 0;
  max-width: 80%;
}

footer {
  text-align: center;
  color: var(--muted);
  font-size: 13px;
  margin-top: 12px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# DATA / CONFIG
# -----------------------------
DATA_FOLDER = "data"
CSV_PATH = os.path.join(DATA_FOLDER, "medicines.csv")

EMERGENCY_RE = re.compile(
    r"\bchest pain\b|\bdifficulty breathing\b|\bshortness of breath\b|\bunconscious\b|\bstroke\b",
    re.IGNORECASE
)

SYSTEM_PROMPT = """
You are VisitWise, a triage assistant and symptom educator.
Never diagnose or name illnesses.
Give short, friendly, general advice only.
"""

# -----------------------------
# API KEY
# -----------------------------
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API key not found. Add it to Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=api_key)

# -----------------------------
# LOAD CSV
# -----------------------------
def load_medicines():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

MEDICINES = load_medicines()

# -----------------------------
# OPENAI CALL
# -----------------------------
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

# -----------------------------
# SESSION STATE
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "profile_saved" not in st.session_state:
    st.session_state.profile_saved = False

# -----------------------------
# HEADER
# -----------------------------
st.markdown("## **VisitWise**")
st.markdown("<span style='color:#475569'>AI-Powered triage assistant and symptom educator</span>", unsafe_allow_html=True)

# -----------------------------
# LAYOUT
# -----------------------------
left, right = st.columns([3, 1.3], gap="medium")

# -----------------------------
# CHAT COLUMN
# -----------------------------
with left:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='chatbox'>", unsafe_allow_html=True)

    for msg in st.session_state.messages:
        cls = "msg-user" if msg["role"] == "user" else "msg-bot"
        label = "You" if msg["role"] == "user" else "VisitWise"
        st.markdown(
            f"<div class='{cls}'><strong>{label}:</strong><br>{msg['content']}</div>",
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)

    user_input = st.text_area(
        "",
        placeholder="Describe your symptoms (no personal names)",
        height=80
    )

    col_send, col_clear = st.columns([1,1])
    send = col_send.button("Send")
    clear = col_clear.button("Clear")

    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# PROFILE COLUMN
# -----------------------------
with right:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Profile (optional)")

    age = st.number_input("Age", min_value=0, max_value=120, step=1)
    gender = st.selectbox("Gender", ["Prefer not to say", "Female", "Male", "Non-binary", "Other"])
    history = st.text_area("Medical history (optional)", height=80)

    if st.button("Enter"):
        if age or gender != "Prefer not to say" or history.strip():
            st.session_state.profile_saved = True
            st.success("Profile saved")
        else:
            st.error("Fill profile first")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**About this site**")
    st.markdown(
        "<span style='color:#475569;font-size:14px'>"
        "VisitWise is a triage assistant and does not diagnose or replace a GP."
        "</span>",
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# CHAT ACTIONS
# -----------------------------
if clear:
    st.session_state.messages = []
    st.experimental_rerun()

if send and user_input.strip():
    st.session_state.messages.append({"role": "user", "content": user_input})

    if EMERGENCY_RE.search(user_input):
        reply = "Your symptoms may be serious — please contact emergency services immediately."
    else:
        prompt = f"""
User message: {user_input}
Age: {age}
Gender: {gender}
Medical history: {history}

Non-prescription items list:
{MEDICINES}
"""
        with st.spinner("Thinking..."):
            reply = safe_openai_response(prompt)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.experimental_rerun()

# -----------------------------
# FOOTER
# -----------------------------
st.markdown(
    "<footer>For emergencies call local services (999 / 112 / 911).</footer>",
    unsafe_allow_html=True
)
