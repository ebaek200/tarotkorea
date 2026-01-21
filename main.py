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
GEMINI_API_KEY = "AIzaSyCCNjtYV0aE1BW9OHsQvhdycbXNCYeDX54"

# Gemini AI 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
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
    return {"message": "Hwagyeong Iching Server V2.1 (Deploy Fixed)"}

@app.post("/register")
async def register(req: RegisterRequest):
    phone = req.phone
    global user_db
    if phone not in user_db:
        if req.is_paid:
            user_db[phone] = {"remain": 10, "used_free": False}
            msg = f"{phone}님은 10회 사용이 가능하십니다."
        else:
            user_db[phone] = {"remain": 3, "used_free": True}
            msg = "3회 무료 체험이 가능합니다."
        save_db(user_db)
        return {"status": "success", "remain": user_db[phone]["remain"], "msg": msg}
    else:
        user = user_db[phone]
        if req.is_paid:
            user["remain"] = 10 
            save_db(user_db)
            return {"status": "success", "remain": 10, "msg": f"결제 확인. 현재 {user['remain']}회 남았습니다."}
        else:
            if user.get("used_free"):
                return {"status": "fail", "msg": "이미 무료 체험을 사용한 번호입니다."}
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
        
        prompt = (
            f"주역 타로 전문가로서 {category}에 대해 답변해줘. "
            f"선택한 괘: {card1}번, {card2}번. "
            f"따뜻한 말투로 5문장 내외 한국어 답변."
        )

        try:
            # 비동기 호출 최적화
            response = await asyncio.to_thread(model.generate_content, prompt)
            advice = response.text
        except Exception as e:
            advice = "AI 해설 생성 중 오류가 발생했습니다."
            print(f"Gemini Error: {e}")
        
        return {"combined_advice": advice, "remain": user_db[phone]["remain"], "status": "success"}
    return {"status": "over", "msg": "횟수 초과"}

if __name__ == "__main__":
    # Render 등 클라우드 환경에서는 PORT 환경변수를 사용해야 함
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
