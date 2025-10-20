# ping_gemini.py
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise SystemExit("❌ GOOGLE_API_KEY가 없습니다. .env 파일을 확인하세요.")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

try:
    response = model.generate_content("Reply with exactly one word: pong")
    print("✅ OK:", response.text)
except Exception as e:
    print("❌ Error:", str(e))
