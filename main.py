import uvicorn
import json
import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# --- 환경 변수 로드 ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # 2.0 대신 안정적인 1.5 버전 사용 (무료 할당량 확보 용이)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("⚠️ GEMINI_API_KEY missing")

DB_FILE = "users.json"

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
    except Exception as e: print(f"DB Error: {e}")

user_db = load_db()

class RegisterRequest(BaseModel):
    phone: str
    is_paid: bool

@app.get("/")
async def root():
    return {"status": "online", "model": "gemini-1.5-flash"}

@app.post("/register")
async def register(req: RegisterRequest):
    phone = req.phone
    global user_db
    if phone not in user_db:
        user_db[phone] = {"remain": 10 if req.is_paid else 3}
    elif req.is_paid:
        user_db[phone]["remain"] = 10
    save_db(user_db)
    return {"status": "success", "remain": user_db[phone]["remain"]}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    global user_db
    if phone not in user_db or user_db[phone]["remain"] <= 0:
        return {"status": "fail", "msg": "상담 횟수가 부족합니다."}
    
    if not GEMINI_API_KEY:
        return {"status": "fail", "msg": "API Key not set"}

    prompt = (
        f"당신은 주역 대가입니다. [{category}] 상담입니다.\n"
        f"뽑은 괘: {card1}번, {card2}번.\n"
        f"형식: 카드1의미 / ## / 카드2의미 / ## / 전문가 종합 조언"
    )

    try:
        # 비동기로 AI 호출
        response = await asyncio.to_thread(model.generate_content, prompt)
        
        if response and response.text:
            user_db[phone]["remain"] -= 1
            save_db(user_db)
            return {
                "status": "success", 
                "combined_advice": response.text, 
                "remain": user_db[phone]["remain"]
            }
        return {"status": "fail", "msg": "AI 응답 없음"}
            
    except Exception as e:
        # 429 에러 발생 시 사용자에게 친절하게 안내
        if "429" in str(e):
            return {"status": "fail", "msg": "현재 접속자가 많아 잠시 후 다시 시도해주세요. (API 할당량 초과)"}
        return {"status": "fail", "msg": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
