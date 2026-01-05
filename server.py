import os

key = os.getenv("OPENAI_API_KEY")

if key:
    print("API key found! It starts with:", key[:6] + "...")
else:
    print("API key NOT found.")
import os
import re
import csv
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

print("Running from:", os.getcwd())

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
print("Loaded", len(MEDICINES), "medicines")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = Flask(__name__, template_folder="Templates")

EMERGENCY_RE = re.compile(
    r"\bchest pain\b|\bdifficulty breathing\b|\bshortness of breath\b|\bunconscious\b|\bstroke\b",
    re.IGNORECASE
)

SYSTEM_PROMPT = """
You are VisitWise, a triage assistant and symptom educator.

RULES:
- If message begins with "I have" always address the user, regardless of age, but if message begins with "my son/daughter/child etc." address what the user can do to aid that person.
- Give replies as if you are sending a friendly message to someone in one or two clear sentences.
- Give consice short advice that is easily readable
- Never name illnesses or conditions.
- Never diagnose.
- If question is nothing to do with Symptoms, please say "Please contain the conversation to medical advice" and do not respond further.
- You are only answering medical questions.
- Always mention to research reccommended dose amount for over the counter medication or include reccommended amount in medicine advise sentence.
- Advise the Over-the-counter medications if you see fit.
- Only give general guidance.
- Advise seeing a GP if you see fit but only if Over-the-counter medication or other at home recovery methods will not suffice for the presumed illness.
- Never name any illnesses or 
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

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    age = (data.get("age") or "").strip()
    gender = (data.get("gender") or "").strip()
    history = (data.get("medical_history") or "").strip()

    if not message:
        return jsonify({"error": "Empty message"})

    if EMERGENCY_RE.search(message):
        return jsonify({"reply": "Your symptoms may be serious — please contact emergency services immediately."})

    user_prompt = f"""
User message: {message}
Age: {age}
Gender: {gender}
Medical history: {history}

Non‑prescription items list:
{MEDICINES}

Rules:
-Do not diagnose users
-If users age is less than 8 please use simplified language as talking to a child.
-If users age is more than 70 please user minimal wording.
-Refer to medicine.csv file and advise certain over-the-counter medicines if considered necessary.
-Advise GP visit if considered necessary.
-Please take Age, Gender and Medical history into account to curate answers.

Respond with general safe advice only.
"""

    reply = safe_openai_response(user_prompt)
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(debug=True)
