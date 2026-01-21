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

# [보안 팁] 환경 변수에 키가 없으면 직접 입력한 키를 사용하도록 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCkSUH094XbgbOQv7sxOVA5HM5FscVhq18")

# API 설정 및 모델 로드
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Gemini 1.5 Flash Model Configured Successfully.")
except Exception as e:
    print(f"Model Init Error: {e}")

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
    return {"message": "Hwagyeong Iching Server V3.1 (Security Enhanced)"}

@app.post("/register")
async def register(req: RegisterRequest):
    phone = req.phone
    global user_db
    if phone not in user_db:
        if req.is_paid:
            user_db[phone] = {"remain": 10, "used_free": False}
        else:
            user_db[phone] = {"remain": 3, "used_free": True}
        save_db(user_db)
        return {"status": "success", "remain": user_db[phone]["remain"], "msg": "인증에 성공하였습니다."}
    else:
        user = user_db[phone]
        if req.is_paid: user["remain"] = 10
        save_db(user_db)
        return {"status": "success", "remain": user["remain"], "msg": f"반갑습니다. {user['remain']}회 이용 가능합니다."}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    global user_db
    if phone in user_db and user_db[phone]["remain"] > 0:
        prompt = (
            f"주역 전문가로서 {category} 상담을 진행합니다. "
            f"선택된 주역 괘 번호는 {card1}번과 {card2}번입니다. "
            f"이 두 괘의 상징적 의미를 결합하여 {category} 운세를 친절하게 풀이해 주세요. "
            f"한국어로 따뜻하게 5문장 내외로 답변하세요."
        )

        try:
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            if response and hasattr(response, 'text') and response.text:
                advice = response.text
                user_db[phone]["remain"] -= 1
                save_db(user_db)
                return {"combined_advice": advice, "remain": user_db[phone]["remain"], "status": "success"}
            else:
                return {"combined_advice": "AI가 해설을 생성했으나 내용을 표시할 수 없습니다.", 
                        "remain": user_db[phone]["remain"], "status": "success"}
        except Exception as e:
            print(f"!!! AI Error: {str(e)}")
            return {"combined_advice": f"해설 생성 중 오류 발생 (사유: {str(e)[:30]})", 
                    "remain": user_db[phone]["remain"], "status": "success"}
            
    return {"status": "over", "msg": "남은 횟수가 없습니다. 유료 결제 후 이용해 주세요."}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
