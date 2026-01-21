import uvicorn
import json
import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

DB_FILE = "users.json"
GEMINI_API_KEY = "AIzaSyCCNjtYV0aE1BW9OHsQvhdycbXNCYeDX54"

# 1. API 설정 및 가용 모델 목록 출력 (디버깅 핵심)
genai.configure(api_key=GEMINI_API_KEY)

print("--- 사용 가능한 모델 목록 확인 시작 ---")
try:
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"사용 가능 모델 발견: {m.name}")
            available_models.append(m.name)
    
    # 목록 중 가장 적절한 모델 자동 선택 (fallback 로직)
    if 'models/gemini-1.5-flash' in available_models:
        target_model = 'models/gemini-1.5-flash'
    elif 'models/gemini-pro' in available_models:
        target_model = 'models/gemini-pro'
    else:
        target_model = available_models[0] if available_models else 'gemini-pro'
        
    model = genai.GenerativeModel(target_model)
    print(f"--- 최종 선택된 모델: {target_model} ---")
except Exception as e:
    print(f"!!! 모델 목록 로드 실패: {e}")
    model = genai.GenerativeModel('gemini-pro') # 기본값 유지

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
    return {"message": "Iching Server V2.7 (Auto Model Selector Active)"}

@app.post("/register")
async def register(req: RegisterRequest):
    phone = req.phone
    global user_db
    if phone not in user_db:
        if req.is_paid:
            user_db[phone] = {"remain": 10, "used_free": False}
            msg = f"{phone}님 유료 10회."
        else:
            user_db[phone] = {"remain": 3, "used_free": True}
            msg = "무료 3회."
        save_db(user_db)
        return {"status": "success", "remain": user_db[phone]["remain"], "msg": msg}
    else:
        user = user_db[phone]
        if req.is_paid:
            user["remain"] = 10
            save_db(user_db)
            return {"status": "success", "remain": 10, "msg": f"결제 완료. {user['remain']}회."}
        else:
            if user.get("used_free"):
                return {"status": "fail", "msg": "무료 체험 종료."}
            else:
                user["remain"] = 3
                user["used_free"] = True
                save_db(user_db)
                return {"status": "success", "remain": 3, "msg": "무료 체험."}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    global user_db
    if phone in user_db and user_db[phone]["remain"] > 0:
        prompt = f"주역 전문가로서 {category} 상담. {card1}번과 {card2}번 괘 조합. 5문장 한국어 답변."
        try:
            response = await asyncio.to_thread(model.generate_content, prompt)
            if response and response.text:
                advice = response.text
                user_db[phone]["remain"] -= 1
                save_db(user_db)
                return {"combined_advice": advice, "remain": user_db[phone]["remain"], "status": "success"}
            else:
                return {"combined_advice": "해설 생성 실패.", "remain": user_db[phone]["remain"], "status": "success"}
        except Exception as e:
            return {"combined_advice": f"오류: {str(e)[:40]}", "remain": user_db[phone]["remain"], "status": "success"}
    return {"status": "over", "msg": "횟수 초과"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
