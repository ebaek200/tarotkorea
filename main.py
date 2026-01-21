import uvicorn
import json
import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# --- 보안 설정: 환경 변수에서 API 키 로드 ---
# Render 대시보드 Environment 탭에 GEMINI_API_KEY가 반드시 등록되어 있어야 합니다.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
else:
    print("⚠️ 경고: GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

DB_FILE = "users.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db(db):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"DB 저장 오류: {e}")

user_db = load_db()

class RegisterRequest(BaseModel):
    phone: str
    is_paid: bool

# --- API 경로 정의 ---

@app.get("/")
async def root():
    """서버 생존 확인용 (404 방지)"""
    return {"status": "running", "api_configured": GEMINI_API_KEY is not None}

@app.post("/register")
async def register(req: RegisterRequest):
    """사용자 인증 및 상담 횟수 부여"""
    phone = req.phone
    global user_db
    if phone not in user_db:
        user_db[phone] = {"remain": 10 if req.is_paid else 3}
    elif req.is_paid:
        user_db[phone]["remain"] = 10
    
    save_db(user_db)
    return {"status": "success", "remain": user_db[phone]["remain"], "msg": "인증 완료"}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    """주역 전문가 AI 해설 생성"""
    global user_db
    
    # 1. 예외 처리 (등록 여부 및 횟수)
    if phone not in user_db or user_db[phone]["remain"] <= 0:
        return {"status": "fail", "msg": "상담 횟수가 부족합니다."}
    
    if not GEMINI_API_KEY:
        return {"status": "fail", "msg": "서버 API 키 설정이 누락되었습니다."}

    # 2. AI 프롬프트 (Eugene님의 요청에 맞춘 전문가 해설 모드)
    prompt = (
        f"당신은 심오한 지혜를 가진 주역 대가입니다. [{category}]에 대해 상담합니다.\n"
        f"내담자가 뽑은 괘는 {card1}번과 {card2}번입니다.\n\n"
        f"다음 형식을 엄격히 지켜 답변하세요:\n"
        f"첫 번째 카드 의미: {card1}번 괘의 특징과 현재 상황 해설 (3문장)\n"
        f"##\n"
        f"두 번째 카드 의미: {card2}번 괘의 특징과 다가올 운의 흐름 (3문장)\n"
        f"##\n"
        f"주역 전문가 종합 조언: 두 괘의 조화를 통해 [{category}]에 대한 최종 결론과 행동 지침 (5문장 내외)"
    )

    try:
        # 3. 비동기 방식으로 AI 호출
        response = await asyncio.to_thread(model.generate_content, prompt)
        
        if response and response.text:
            user_db[phone]["remain"] -= 1
            save_db(user_db)
            return {
                "status": "success", 
                "combined_advice": response.text, 
                "remain": user_db[phone]["remain"]
            }
        else:
            return {"status": "fail", "msg": "AI 응답 생성에 실패했습니다."}
            
    except Exception as e:
        # API 키 유출(403) 등의 에러를 여기서 포착
        error_msg = str(e)
        if "403" in error_msg:
            return {"status": "fail", "msg": "API 키 차단됨. 새로운 키를 등록하세요."}
        return {"status": "fail", "msg": f"오류 발생: {error_msg}"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
