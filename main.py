import uvicorn
import json
import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# 브라우저 접속 허용 설정 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 키 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
else:
    print("⚠️ GEMINI_API_KEY 환경변수가 없습니다.")

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
    return {"status": "online", "message": "Hwagyeong Iching Web Server is Live"}

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
    # 테스트 편의를 위해 DB에 번호가 없으면 자동 등록(3회) 해주는 로직 추가
    if phone not in user_db:
        user_db[phone] = {"remain": 3}
        save_db(user_db)
    
    if user_db[phone]["remain"] <= 0:
        return {"status": "fail", "msg": "상담 횟수가 모두 소진되었습니다."}
    
    prompt = (
        f"당신은 심오한 지혜를 가진 주역 대가입니다. [{category}]에 대해 상담합니다.\n"
        f"내담자가 뽑은 괘는 {card1}번과 {card2}번입니다.\n\n"
        f"형식:\n첫 번째 괘 해설\n##\n두 번째 괘 해설\n##\n종합적인 처세술과 조언"
    )

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        if response and response.text:
            user_db[phone]["remain"] -= 1
            save_db(user_db)
            return {
                "status": "success", 
                "combined_advice": response.text, 
                "remain": user_db[phone]["remain"]
            }
        return {"status": "fail", "msg": "AI 응답 생성 실패"}
    except Exception as e:
        return {"status": "fail", "msg": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
