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

# 1. API 설정
genai.configure(api_key=GEMINI_API_KEY)

# 2. 모델 설정 (경로 호출 방식 최적화)
# 404 에러 방지를 위해 가장 범용적인 'gemini-1.5-flash-latest' 사용
try:
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    print("Gemini 1.5 Flash 모델 로드 시도 완료")
except Exception as e:
    print(f"모델 초기화 에러: {e}")

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
    return {"message": "Hwagyeong Iching Server V2.6 (Model Path Optimized)"}

@app.post("/register")
async def register(req: RegisterRequest):
    phone = req.phone
    global user_db
    if phone not in user_db:
        if req.is_paid:
            user_db[phone] = {"remain": 10, "used_free": False}
            msg = f"{phone}님 유료 10회 부여."
        else:
            user_db[phone] = {"remain": 3, "used_free": True}
            msg = "무료 3회 부여."
        save_db(user_db)
        return {"status": "success", "remain": user_db[phone]["remain"], "msg": msg}
    else:
        user = user_db[phone]
        if req.is_paid:
            user["remain"] = 10
            save_db(user_db)
            return {"status": "success", "remain": 10, "msg": f"결제 완료. {user['remain']}회 남음."}
        else:
            if user.get("used_free"):
                return {"status": "fail", "msg": "이미 무료 체험을 하셨습니다."}
            else:
                user["remain"] = 3
                user["used_free"] = True
                save_db(user_db)
                return {"status": "success", "remain": 3, "msg": "무료 체험 부여."}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    global user_db
    if phone in user_db and user_db[phone]["remain"] > 0:
        prompt = (
            f"주역 전문가로서 {category} 상담을 합니다. "
            f"주역 {card1}번 괘와 {card2}번 괘를 조합하여 "
            f"따뜻한 한국어로 5문장 내외로 답변하세요."
        )

        try:
            # 안전 설정 없이 기본 호출 시도 (404 회피용)
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            if response and response.text:
                advice = response.text
                user_db[phone]["remain"] -= 1
                save_db(user_db)
            else:
                advice = "AI 답변 생성에 실패했습니다."
        except Exception as e:
            # [핵심] 여기서 에러가 나면 모델 리스트를 출력하여 실제 사용 가능한 모델명을 로그로 확인
            print(f"!!! AI ERROR: {str(e)}")
            advice = f"해설 생성 중 오류 (사유: {str(e)[:40]}...)"
        
        return {"combined_advice": advice, "remain": user_db[phone]["remain"], "status": "success"}
    return {"status": "over", "msg": "횟수 초과"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
