import uvicorn
import json
import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# 데이터 저장 파일 및 API 키 설정
DB_FILE = "users.json"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCkSUH094XbgbOQv7sxOVA5HM5FscVhq18")

# Gemini AI 설정 (로그에서 확인된 최신 모델 사용)
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
        # 신규가입 시 무료 3회, 결제 시 10회
        user_db[phone] = {"remain": 10 if req.is_paid else 3, "used_free": not req.is_paid}
    else:
        if req.is_paid: user_db[phone]["remain"] = 10
    save_db(user_db)
    return {"status": "success", "remain": user_db[phone]["remain"], "msg": "인증되었습니다."}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    global user_db
    if phone in user_db and user_db[phone]["remain"] > 0:
        # 가독성을 고려한 구조적 프롬프트
        prompt = (
            f"당신은 주역(I Ching) 대가입니다. 아래 조건에 맞춰 {category} 상담을 진행하세요.\n\n"
            f"1. 첫 번째 카드({card1}번 괘)의 명칭과 핵심 의미를 간략히 설명하세요.\n"
            f"2. 두 번째 카드({card2}번 괘)의 명칭과 핵심 의미를 간략히 설명하세요.\n"
            f"3. 위 두 괘의 조합을 통해 {category}에 대한 종합 해석을 따뜻하고 희망적인 말투로 5문장 내외로 작성하세요.\n\n"
            "형식 예시:\n"
            "● 첫 번째 카드 [괘이름]: 의미 요약\n"
            "● 두 번째 카드 [괘이름]: 의미 요약\n\n"
            "■ 종합 해석: ...\n"
            "반드시 한국어로 작성하고 각 섹션 사이에 줄바꿈을 두어 가독성을 높이세요."
        )

        try:
            response = await asyncio.to_thread(model.generate_content, prompt)
            if response and response.text:
                advice = response.text
                user_db[phone]["remain"] -= 1
                save_db(user_db)
                return {"combined_advice": advice, "remain": user_db[phone]["remain"], "status": "success"}
            else:
                return {"combined_advice": "해설을 불러오지 못했습니다. 다시 시도해 주세요.", "status": "fail"}
        except Exception as e:
            return {"combined_advice": f"오류 발생: {str(e)[:50]}", "status": "fail"}
            
    return {"status": "over", "msg": "잔여 상담 횟수가 부족합니다."}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
