import uvicorn
import json
import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# --- 환경 변수 로드 ---
GEMINI_API_KEY = os.environ.get("models/gemini-3-flash-preview")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # 모델명을 'gemini-1.5-flash-latest'로 수정하여 호환성 확보
    model = genai.GenerativeModel('gemini-pro')
else:
    print("⚠️ GEMINI_API_KEY가 설정되지 않았습니다.")

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
    return {"status": "online", "model_info": "gemini-1.5-flash-latest"}

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
    
    # 주역 전문가 페르소나 강화 프롬프트
    prompt = (
        f"당신은 깊은 통찰력을 가진 주역 전문가입니다. 상담 주제는 [{category}]입니다.\n"
        f"뽑은 괘는 {card1}번과 {card2}번입니다.\n\n"
        f"반드시 다음 형식을 지켜주세요:\n"
        f"첫 번째 괘 의미: 해당 괘의 핵심 풀이 (3문장)\n"
        f"##\n"
        f"두 번째 괘 의미: 해당 괘의 핵심 풀이 (3문장)\n"
        f"##\n"
        f"전문가 종합 조언: 두 괘의 상호작용을 통한 최종 조언 (5문장 내외)"
    )

    try:
        # 비동기 호출
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
        error_str = str(e)
        if "429" in error_str:
            return {"status": "fail", "msg": "서버 과부하입니다. 1분만 기다려주세요."}
        if "404" in error_str:
            return {"status": "fail", "msg": "모델 설정 오류입니다. 관리자에게 문의하세요."}
        return {"status": "fail", "msg": f"시스템 오류: {error_str}"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)


