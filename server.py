import os
import re
import csv
import streamlit as st
from openai import OpenAI
import time

# -----------------------------
# App Config & Colors
# -----------------------------
st.set_page_config(page_title="VisitWise — AI triage assistant", page_icon="💊", layout="wide")

# Inject CSS for colors and UI
st.markdown("""
<style>
:root {
  --bg:#e9f4ff;
  --card:#ffffff;
  --accent:#2b7cff;
  --muted:#475569;
  --soft:#eaf6ff;
  --savebox-dark:#003a99;
  --savebox-light:#4d8fff;
}

/* Page background */
body, .stApp {
  background-color: var(--bg);
  color: #0f172a;
}

/* Card styling */
.card {
  background: var(--card);
  padding: 14px;
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(20,30,60,0.06);
  margin-bottom: 12px;
}

/* Buttons */
.stButton>button {
  background-color: var(--accent);
  color: white;
  border-radius: 10px;
  padding: 8px 12px;
}

/* Secondary text */
span, p {
  color: var(--muted);
}

/* Chat bubbles */
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
  word-wrap: break-word;
}

/* Profile saved box */
.save-box {
  padding: 10px;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  text-align: center;
  display: none;
}

.save-box.saved {
  background-color: var(--savebox-light);
  display: block;
}

.save-box.error {
  background-color: red;
  display: block;
}

/* Chat container */
#chat-container {
height: 480px;
overflow-y: auto;
padding: 12px;
border-radius: 10px;
background: linear-gradient(180deg,#fff,#fbfeff);
border: 1px solid #e6f2ff;
}

/* Footer */
footer {
  text-align: center;
  color: var(--muted);
  font-size: 13px;
  margin-top: 12px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Load Medicines CSV
# -----------------------------
DATA_FOLDER = "data"
CSV_PATH = os.path.join(DATA_FOLDER, "medicines.csv")

# Fix double-extension bug if it exists
if os.path.exists(os.path.join(DATA_FOLDER, "medicines.csv.csv")) and not os.path.exists(CSV_PATH):
    os.rename(os.path.join(DATA_FOLDER, "medicines.csv.csv"), CSV_PATH)

def load_medicines():
    items = []
    if not os.path.exists(CSV_PATH):
        st.warning("medicines.csv not found")
        return items
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append(row)
    return items

MEDICINES = load_medicines()

# -----------------------------
# OpenAI Client
# -----------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are VisitWise, a triage assistant and symptom educator.

RULES:
- Give replies in 1-2 clear sentences
- Do not diagnose or name illnesses
- Advise general guidance and OTC meds when appropriate
- Mention GP visit if needed
- Use simple language for kids (<8) and minimal wording for elderly (>70)
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

# -----------------------------
# Emergency Check
# -----------------------------
EMERGENCY_RE = re.compile(
    r"\bchest pain\b|\bdifficulty breathing\b|\bshortness of breath\b|\bunconscious\b|\bstroke\b",
    re.IGNORECASE
)

# -----------------------------
# Session State
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "profile" not in st.session_state:
    st.session_state.profile = {"age": "", "gender": "", "medical_history": ""}

if "thinking" not in st.session_state:
    st.session_state.thinking = False
  
# -----------------------------
# Layout
# -----------------------------
col1, col2 = st.columns([2, 1])

# Left: Chat
with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3>VisitWise Chat</h3>', unsafe_allow_html=True)
    
    # Display chat messages
    for m in st.session_state.messages:
        cls = "msg-user" if m["role"] == "user" else "msg-bot"
        st.markdown(f'<div class="{cls}"><strong>{m["role"].capitalize()}:</strong><br>{m["content"]}</div>', unsafe_allow_html=True)

    user_input = st.text_area("Describe your symptoms (no personal names)", key="user_input", height=80)

    col_send, col_clear = st.columns([1,1])
    with col_send:
        send = st.button("Send")
    with col_clear:
        clear = st.button("Clear")

    st.markdown('</div>', unsafe_allow_html=True)

# Right: Profile
with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h3>Profile (optional)</h3>", unsafe_allow_html=True)
    age = st.number_input("Age", min_value=0, max_value=120, value=int(st.session_state.profile["age"] or 0))
    gender = st.selectbox("Gender", ["Prefer not to say","Female","Male","Non-binary","Other"], index=0 if st.session_state.profile["gender"]=="" else ["Prefer not to say","Female","Male","Non-binary","Other"].index(st.session_state.profile["gender"]))
    history = st.text_area("Medical history", value=st.session_state.profile["medical_history"], height=80)
    
    save_profile = st.button("Enter Profile")
    save_box_html = '<div class="save-box saved">Profile saved</div>'
    
    if save_profile:
        if not age and not gender and not history.strip():
            st.markdown('<div class="save-box error">Fill profile first</div>', unsafe_allow_html=True)
        else:
            st.session_state.profile = {"age": age, "gender": gender, "medical_history": history}
            st.markdown(save_box_html, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    # About card
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<strong>About this site</strong>", unsafe_allow_html=True)
    st.markdown("""
    <p style="margin:8px 0;color:var(--muted);font-size:14px">
    VisitWise is a triage assistant and does not diagnose or replace a GP. Filling in the profile helps curate the experience.
    </p>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown('<footer>For emergencies call local services (999/112/911).</footer>', unsafe_allow_html=True)

# -----------------------------
# Chat Logic
# -----------------------------
if send and user_input.strip():
  st.session_state.messages.append({"role":"user", "content":user_input})
  st.session_state.user_input = ""
  st.session_state.thinking = True
  display_chat()
  st.experimental_rerun()

elif st.session_state.thinking:
  last_user_msg = st.session_state.messages[-1]["content"]
  
    # Emergency check
    if EMERGENCY_RE.search(user_input):
        reply = "Your symptoms may be serious — please contact emergency services immediately."
    else:
        user_prompt = f"""
User message: {user_input}
Age: {st.session_state.profile['age']}
Gender: {st.session_state.profile['gender']}
Medical history: {st.session_state.profile['medical_history']}

Non‑prescription items list:
{MEDICINES}

Respond with general safe advice only.
"""
        reply = safe_openai_response(user_prompt)
    
    # Update session messages
    st.session_state.messages.append({"role":"user", "content":user_input})
    st.session_state.thinking = False
    st.experimental_rerun()

if clear:
    st.session_state.messages = []
    st.experimental_rerun()


