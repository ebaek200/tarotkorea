import uvicorn
import json
import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# --- 데이터 보존 및 API 설정 ---
DB_FILE = "users.json"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCkSUH094XbgbOQv7sxOVA5HM5FscVhq18")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash')

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_db(db):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=4)
    except: pass

user_db = load_db()

class RegisterRequest(BaseModel):
    phone: str
    is_paid: bool

@app.get("/")
async def root():
    return {"status": "online", "service": "Hwagyeong Iching AI"}

@app.post("/register")
async def register(req: RegisterRequest):
    phone = req.phone
    global user_db
    if phone not in user_db:
        user_db[phone] = {"remain": 10 if req.is_paid else 3, "used_free": not req.is_paid}
    else:
        if req.is_paid: user_db[phone]["remain"] = 10
    save_db(user_db)
    return {"status": "success", "remain": user_db[phone]["remain"], "msg": "인증 성공"}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    global user_db
    if phone in user_db and user_db[phone]["remain"] > 0:
        # 클라이언트에서 분리하기 쉽도록 특수 기호(##)로 구분하여 요청
        prompt = (
            f"주역 전문가로서 {category} 상담을 합니다. {card1}번과 {card2}번 괘를 뽑았습니다.\n"
            f"다음 형식을 엄격히 지켜 답변하세요.\n"
            f"카드1설명: {card1}번 괘의 이름과 핵심 의미(20자 이내)\n"
            f"##\n"
            f"카드2설명: {card2}번 괘의 이름과 핵심 의미(20자 이내)\n"
            f"##\n"
            f"종합해설: 두 괘를 결합한 {category} 운세 풀이를 따뜻한 말투로 5문장 내외 작성."
        )

        try:
            response = await asyncio.to_thread(model.generate_content, prompt)
            if response and response.text:
                advice = response.text
                user_db[phone]["remain"] -= 1
                save_db(user_db)
                return {"combined_advice": advice, "remain": user_db[phone]["remain"], "status": "success"}
    return {"status": "fail", "msg": "상담 횟수가 부족하거나 오류가 발생했습니다."}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
