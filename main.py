import uvicorn
import json
import os
import asyncio
import sys
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# --- 설정 및 데이터 관리 ---
DB_FILE = "users.json"
# Eugene님의 API Key를 직접 입력했습니다.
GEMINI_API_KEY = "AIzaSyCCNjtYV0aE1BW9OHsQvhdycbXNCYeDX54"

# Gemini AI 설정
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # 안전 설정: 해설이 차단되는 것을 방지하기 위해 필터링을 최소화합니다.
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    model = genai.GenerativeModel('gemini-pro', safety_settings=safety_settings)
    print("Gemini 모델 설정 완료")
except Exception as e:
    print(f"Gemini 설정 오류: {str(e)}")

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"DB 로드 오류: {e}")
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

@app.get("/")
async def root():
    return {"message": "Hwagyeong Iching Server V2.2 (Error Tracking Enabled)"}

@app.post("/register")
async def register(req: RegisterRequest):
    phone = req.phone
    global user_db
    
    if phone not in user_db:
        if req.is_paid:
            user_db[phone] = {"remain": 10, "used_free": False}
            msg = f"{phone}님은 10회 사용이 가능하십니다. 환영합니다."
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
            return {"status": "success", "remain": 10, "msg": f"결제 확인. {user['remain']}회 남았습니다."}
        else:
            if user.get("used_free"):
                return {"status": "fail", "msg": "이미 무료 체험을 사용한 번호입니다. 유료 결제가 필요합니다."}
            else:
                user["remain"] = 3
                user["used_free"] = True
                save_db(user_db)
                return {"status": "success", "remain": 3, "msg": "3회 무료 체험이 가능합니다."}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    global user_db
    if phone in user_db and user_db[phone]["remain"] > 0:
        # 먼저 횟수를 차감하기 전 성공 여부를 확인하기 위해 복사본 사용
        current_remain = user_db[phone]["remain"]
        
        prompt = (
            f"주역 타로 전문가로서 {category} 운세 상담에 답변해줘. "
            f"선택된 주역 괘 번호는 {card1}번과 {card2}번이야. "
            f"이 두 괘의 상징적 의미를 조합해서 고객의 고민인 '{category}'에 대해 따뜻하고 희망적인 조언을 해줘. "
            f"한국어로 친절하게 5문장 내외로 작성해줘."
        )

        try:
            # AI 호출 및 로그 기록
            print(f"AI 호출 시작: {category} (카드: {card1}, {card2})")
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            if response and response.text:
                advice = response.text
                # 성공했을 때만 횟수 차감
                user_db[phone]["remain"] -= 1
                save_db(user_db)
                print(f"AI 호출 성공: {phone} 잔여 {user_db[phone]['remain']}회")
            else:
                advice = "AI가 해설을 생성했으나 안전 정책으로 인해 내용이 차단되었습니다. 다른 카드를 뽑아주세요."
                print("AI Warning: Response blocked or empty.")

        except Exception as e:
            # 상세 에러 로그 출력 (Render의 Logs 탭에서 확인 가능)
            error_msg = str(e)
            print(f"!!! AI API ERROR: {error_msg}")
            advice = f"해설 생성 중 오류가 발생했습니다. (사유: {error_msg[:50]}...)"
        
        return {
            "combined_advice": advice,
            "remain": user_db[phone]["remain"],
            "status": "success"
        }
    else:
        return {"status": "over", "msg": "남은 횟수가 없습니다. 유료 결제 후 이용 가능합니다."}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
