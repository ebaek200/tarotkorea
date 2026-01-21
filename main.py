import uvicorn
import json
import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# --- 설정 및 데이터 관리 ---
DB_FILE = "users.json"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCkSUH094XbgbOQv7sxOVA5HM5FscVhq18")

# API 설정
genai.configure(api_key=GEMINI_API_KEY)

# [수정] 로그에서 확인된 가장 최신 모델명으로 고정합니다.
# 'models/gemini-2.5-flash'를 사용합니다.
try:
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    print("Gemini 2.5 Flash Model Configured Successfully!")
except Exception as e:
    print(f"Model Load Error: {e}")

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
    return {"status": "online", "model": "gemini-2.5-flash"}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    global user_db
    if phone in user_db and user_db[phone]["remain"] > 0:
        prompt = (
            f"주역 타로 전문가로서 {category} 운세를 풀이해줘. "
            f"선택된 카드는 {card1}번과 {card2}번이야. "
            f"따뜻한 말투로 5문장 내외 한국어 답변을 작성해줘."
        )

        try:
            # AI 호출
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            if response and response.text:
                advice = response.text
                user_db[phone]["remain"] -= 1
                save_db(user_db)
                return {"combined_advice": advice, "remain": user_db[phone]["remain"], "status": "success"}
            else:
                return {"combined_advice": "해설을 생성했으나 차단되었습니다. 다른 카드를 뽑아보세요.", "remain": user_db[phone]["remain"], "status": "success"}
        except Exception as e:
            print(f"!!! AI Error: {str(e)}")
            return {"combined_advice": f"해설 생성 중 오류 (사유: {str(e)[:40]}...)", "remain": user_db[phone]["remain"], "status": "success"}
    return {"status": "over", "msg": "남은 횟수가 없습니다."}

@app.post("/register")
async def register(req: RegisterRequest):
    phone = req.phone
    global user_db
    if phone not in user_db:
        user_db[phone] = {"remain": 10 if req.is_paid else 3, "used_free": not req.is_paid}
    else:
        if req.is_paid: user_db[phone]["remain"] = 10
    save_db(user_db)
    return {"status": "success", "remain": user_db[phone]["remain"], "msg": "인증 완료"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
