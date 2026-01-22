import uvicorn
import json
import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# 브라우저 접속 허용 (CORS 설정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API 설정 (가장 안정적인 모델명 사용) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # 404 에러 방지를 위해 가장 표준적인 모델명 사용
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
    except: pass

user_db = load_db()

class RegisterRequest(BaseModel):
    phone: str
    is_paid: bool

@app.get("/")
async def root():
    return {"status": "online", "message": "Iching Web Server"}

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
    if phone not in user_db: user_db[phone] = {"remain": 3}
    
    if user_db[phone]["remain"] <= 0:
        return {"status": "fail", "msg": "상담 횟수 소진"}
    
    prompt = (
        f"당신은 주역 전문가입니다. [{category}] 상담입니다.\n"
        f"뽑은 괘: {card1}번, {card2}번.\n\n"
        f"형식:\n첫 번째 괘 의미\n##\n두 번째 괘 의미\n##\n종합 조언"
    )

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        if response and response.text:
            user_db[phone]["remain"] -= 1
            save_db(user_db)
            return {"status": "success", "combined_advice": response.text, "remain": user_db[phone]["remain"]}
        return {"status": "fail", "msg": "AI 응답 실패"}
    except Exception as e:
        return {"status": "fail", "msg": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
