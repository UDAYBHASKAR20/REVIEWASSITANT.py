import time
from openai import OpenAI
import gspread
import os
import json
import base64
from google.oauth2.service_account import Credentials

# ==========================
# ENV VARIABLES
# ==========================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
encoded = os.getenv("GOOGLE_CREDENTIALS")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found")

if not SPREADSHEET_ID:
    raise ValueError("SPREADSHEET_ID not found")

if not encoded:
    raise ValueError("GOOGLE_CREDENTIALS not found")

# ==========================
# INIT GROQ CLIENT
# ==========================

client_llm = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ==========================
# CONNECT TO GOOGLE SHEETS
# ==========================

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

decoded = base64.b64decode(encoded).decode("utf-8")
creds_dict = json.loads(decoded)

creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=scope
)

gc = gspread.authorize(creds)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

rows = sheet.get_all_records()

print("Connected to Google Sheet successfully.")

# ==========================
# PROCESS EACH ROW
# ==========================

for index, row in enumerate(rows, start=2):

    client_name = row.get("CLIENT NAME")
    google_location = row.get("GOOGLE LOCATION")
    processed = row.get("Processed")

    if processed == "DONE":
        continue

    if not client_name or not google_location:
        continue

    print(f"Generating reviews for: {client_name}")

    prompt = f"""
You are writing authentic Google reviews.

Business: {client_name}
Location: {google_location}

Generate:
1) A short Google review (15-25 words)
2) A detailed Google review (60-100 words)

Return strictly in format:

SHORT REVIEW:
<text>

DETAILED REVIEW:
<text>
"""

    response = client_llm.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You write authentic, natural Google reviews."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    result_text = response.choices[0].message.content.strip()

    if "DETAILED REVIEW:" in result_text:
        parts = result_text.split("DETAILED REVIEW:")
        short_review = parts[0].replace("SHORT REVIEW:", "").strip()
        detailed_review = parts[1].strip()
    else:
        short_review = result_text
        detailed_review = "Parsing error"

    sheet.update_cell(index, 8, short_review)
    sheet.update_cell(index, 9, detailed_review)
    sheet.update_cell(index, 10, "DONE")

    print(f"Updated: {client_name}")
    time.sleep(1)

print("All rows processed successfully.")
