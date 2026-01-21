import random
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
# 알려주신 API Key를 적용했습니다.
GEMINI_API_KEY = "AIzaSyCCNjtYV0aE1BW9OHsQvhdycbXNCYeDX54"

# Gemini AI 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# 사용자 DB 로드/저장 함수
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

user_db = load_db()

class RegisterRequest(BaseModel):
    phone: str
    is_paid: bool

@app.get("/")
async def root():
    return {"message": "Hwagyeong Iching Server V2.0 (AI Powered)"}

@app.post("/register")
async def register(req: RegisterRequest):
    phone = req.phone
    global user_db
    
    # 1. 신규 접속 번호
    if phone not in user_db:
        if req.is_paid:
            user_db[phone] = {"remain": 10, "used_free": False}
            msg = f"{phone}님은 10회 사용이 가능하십니다. 기억에 남는 시간 되세요."
        else:
            user_db[phone] = {"remain": 3, "used_free": True}
            msg = "처음 사용하는 번호이시군요. 3회 무료 체험이 가능합니다."
        save_db(user_db)
        return {"status": "success", "remain": user_db[phone]["remain"], "msg": msg}
    
    # 2. 기존 접속 번호
    else:
        user = user_db[phone]
        if req.is_paid:
            user["remain"] = 10 
            save_db(user_db)
            return {"status": "success", "remain": 10, "msg": f"결제가 확인되었습니다. 현재 {user['remain']}회 남았습니다."}
        else:
            if user["used_free"]:
                return {"status": "fail", "msg": "이미 무료 체험을 사용한 번호입니다. 유료 결제 후 사용 가능합니다."}
            else:
                user["remain"] = 3
                user["used_free"] = True
                save_db(user_db)
                return {"status": "success", "remain": 3, "msg": "3회 무료 체험이 가능합니다."}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    global user_db
    if phone in user_db and user_db[phone]["remain"] > 0:
        user_db[phone]["remain"] -= 1
        save_db(user_db)
        
        # AI 프롬프트 구성
        prompt = (
            f"당신은 주역 타로 전문가입니다. "
            f"고객의 고민 카테고리: {category}. "
            f"선택한 주역 괘: {card1}번과 {card2}번. "
            f"이 두 괘의 상징적 의미를 결합하여 {category} 운세를 상세하고 따뜻하게 풀이해 주세요. "
            f"한국어로 친절하게 5문장 정도로 답변해 주세요."
        )

        try:
            # Gemini AI 호출
            response = await asyncio.to_thread(model.generate_content, prompt)
            advice = response.text
        except Exception as e:
            advice = "죄송합니다. AI 해설 생성 중 일시적인 오류가 발생했습니다."
            print(f"AI Error: {e}")
        
        return {
            "combined_advice": advice,
            "remain": user_db[phone]["remain"],
            "status": "success"
        }
    else:
        return {"status": "over", "msg": "남은 횟수가 없습니다. 유료로 사용하세요."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
