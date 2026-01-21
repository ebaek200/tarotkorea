import uvicorn
import json
import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# --- 설정 및 데이터베이스 ---
DB_FILE = "users.json"
# Render 환경변수에 GEMINI_API_KEY를 등록하세요. 
# 등록되지 않았을 경우를 대비한 기본키 (보안상 환경변수 등록 권장)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCkSUH094XbgbOQv7sxOVA5HM5FscVhq18")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

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
        print(f"DB Save Error: {e}")

user_db = load_db()

# --- 데이터 모델 ---
class RegisterRequest(BaseModel):
    phone: str
    is_paid: bool

# --- API 엔드포인트 ---

@app.get("/")
async def root():
    """서버 상태 확인용 루팅"""
    return {"status": "online", "message": "Hwagyeong Iching AI Server is running"}

@app.post("/register")
async def register(req: RegisterRequest):
    """사용자 등록 및 횟수 부여"""
    phone = req.phone
    global user_db
    
    # 신규 등록 또는 유료 결제 시 횟수 셋팅
    if phone not in user_db:
        user_db[phone] = {"remain": 10 if req.is_paid else 3}
    else:
        if req.is_paid:
            user_db[phone]["remain"] = 10
            
    save_db(user_db)
    return {"status": "success", "remain": user_db[phone]["remain"], "msg": "인증되었습니다."}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    """주역 괘 해석 및 AI 응답 생성"""
    global user_db
    
    # 1. 사용자 권한 체크
    if phone not in user_db:
        return {"status": "fail", "msg": "등록되지 않은 번호입니다."}
    
    if user_db[phone]["remain"] <= 0:
        return {"status": "fail", "msg": "상담 가능 횟수가 모두 소진되었습니다."}

    # 2. AI 프롬프트 구성 (전문적인 주역 전문가 페르소나 부여)
    prompt = (
        f"당신은 30년 경력의 주역 및 명리학 대가입니다. "
        f"상담 주제는 [{category}]이며, 내담자가 뽑은 괘는 {card1}번과 {card2}번입니다.\n\n"
        f"다음 지침에 따라 해설을 작성하세요:\n"
        f"1. 각 괘의 명칭과 본질적인 의미를 깊이 있게 설명할 것.\n"
        f"2. {category}라는 주제에 집중하여 현재 상황과 미래 흐름을 분석할 것.\n"
        f"3. 답변 형식은 반드시 아래의 구분자(##)를 포함할 것.\n\n"
        f"[해설 형식]\n"
        f"첫 번째 카드: {card1}번 괘의 상세 의미와 내담자의 현재 심리/상황 설명 (3~4문장)\n"
        f"##\n"
        f"두 번째 카드: {card2}번 괘의 상세 의미와 앞으로 다가올 변화 설명 (3~4문장)\n"
        f"##\n"
        f"전문가 종합 조언: 두 괘의 조합을 통한 [{category}]에 대한 최종 결론 및 실질적인 처세술 (5문장 이상)"
    )

    try:
        # 3. Gemini AI 호출 (비동기 처리)
        response = await asyncio.to_thread(model.generate_content, prompt)
        
        if response and response.text:
            # 상담 횟수 차감 및 DB 저장
            user_db[phone]["remain"] -= 1
            save_db(user_db)
            
            return {
                "status": "success",
                "combined_advice": response.text,
                "remain": user_db[phone]["remain"]
            }
        else:
            return {"status": "fail", "msg": "AI가 응답을 생성하지 못했습니다."}

    except Exception as e:
        print(f"AI Interpret Error: {str(e)}")
        return {"status": "fail", "msg": f"서버 오류가 발생했습니다: {str(e)}"}

if __name__ == "__main__":
    # Render 환경의 포트에 맞게 실행
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
