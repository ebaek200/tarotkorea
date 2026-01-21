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
# 새로 발급받으신 키를 직접 입력했습니다.
GEMINI_API_KEY = "AIzaSyCkSUH094XbgbOQv7sxOVA5HM5FscVhq18"

# API 설정
genai.configure(api_key=GEMINI_API_KEY)

# 가용한 모델을 자동으로 찾아 설정하는 함수
def get_best_model():
    try:
        # 현재 API 키로 사용 가능한 모델 목록 확인
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        print(f"가용 모델 목록: {models}")
        
        # 선호도 순서대로 모델 선택
        for preferred in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']:
            if preferred in models:
                print(f"최종 선택 모델: {preferred}")
                return genai.GenerativeModel(preferred)
        
        # 목록은 있으나 선호 모델이 없을 경우 첫 번째 모델 사용
        if models:
            return genai.GenerativeModel(models[0])
    except Exception as e:
        print(f"모델 리스트 조회 실패: {e}")
    
    # 실패 시 가장 기본 이름으로 리턴
    return genai.GenerativeModel('gemini-1.5-flash')

model = get_best_model()

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
    return {"message": "Hwagyeong Iching Server V3.2 (Auto-Model Recovery)"}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    global user_db
    if phone in user_db and user_db[phone]["remain"] > 0:
        prompt = f"주역 전문가로서 {category} 상담. {card1}번과 {card2}번 괘 조합. 따뜻한 한국어로 5문장 답변."
        
        try:
            # AI 호출 시 timeout 추가
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            if response and hasattr(response, 'text') and response.text:
                advice = response.text
                user_db[phone]["remain"] -= 1
                save_db(user_db)
                return {"combined_advice": advice, "remain": user_db[phone]["remain"], "status": "success"}
            else:
                return {"combined_advice": "AI가 답변을 생성했으나 정책상 내용을 표시할 수 없습니다.", "remain": user_db[phone]["remain"], "status": "success"}
        except Exception as e:
            # 여기서 404가 나면 로그에 상세 내용을 찍습니다.
            print(f"!!! AI Error Detailed: {str(e)}")
            return {"combined_advice": f"해설 생성 중 오류 (사유: {str(e)[:40]}...)", "remain": user_db[phone]["remain"], "status": "success"}
    return {"status": "over", "msg": "남은 횟수가 없습니다."}

@app.post("/register")
async def register(req: RegisterRequest):
    # (기존 register 로직 동일)
    phone = req.phone
    global user_db
    if phone not in user_db:
        user_db[phone] = {"remain": 10 if req.is_paid else 3, "used_free": not req.is_paid}
        save_db(user_db)
        return {"status": "success", "remain": user_db[phone]["remain"], "msg": "인증 성공"}
    return {"status": "success", "remain": user_db[phone]["remain"], "msg": "기존 회원"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
