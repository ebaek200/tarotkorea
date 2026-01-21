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
# 보안을 위해 환경변수 사용 권장하나, 현재 코드 그대로 유지
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCkSUH094XbgbOQv7sxOVA5HM5FscVhq18")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash') # 모델명 최신화

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

# [중요] 404 오류 방지를 위한 루트 경로
@app.get("/")
async def root():
    return {"status": "online", "message": "Hwagyeong Iching Server is running"}

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
    # 1. 사용자 체크
    if phone not in user_db or user_db[phone]["remain"] <= 0:
        return {"status": "fail", "msg": "상담 횟수가 부족합니다."}

    # 2. AI 해석 요청
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
        else:
            return {"status": "fail", "msg": "AI 응답 생성 실패"}
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "fail", "msg": "서버 내부 오류가 발생했습니다."}

if __name__ == "__main__":
    # Render는 PORT 환경변수를 사용하므로 10000 혹은 환경변수 포트를 따름
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
