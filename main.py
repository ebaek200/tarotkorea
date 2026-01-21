import uvicorn
import json
import os
import asyncio
import sys
from fastapi import FastAPI
from pydantiimport uvicorn
import json
import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

DB_FILE = "users.json"
GEMINI_API_KEY = "AIzaSyCCNjtYV0aE1BW9OHsQvhdycbXNCYeDX54"

# 최신 라이브러리 호환 설정
genai.configure(api_key=GEMINI_API_KEY)

# 안전 설정 (필요시 사용)
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# 모델명 앞에 'models/'를 붙여서 경로를 확실히 합니다.
model = genai.GenerativeModel(
    model_name='models/gemini-1.5-flash',
    safety_settings=safety_settings
)

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
    return {"message": "Hwagyeong Iching Server V2.4 (Model Path Fixed)"}

@app.post("/register")
async def register(req: RegisterRequest):
    phone = req.phone
    global user_db
    if phone not in user_db:
        if req.is_paid:
            user_db[phone] = {"remain": 10, "used_free": False}
            msg = f"{phone}님 유료회원 10회 부여."
        else:
            user_db[phone] = {"remain": 3, "used_free": True}
            msg = "3회 무료 체험 부여."
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
                return {"status": "fail", "msg": "무료체험 만료."}
            else:
                user["remain"] = 3
                user["used_free"] = True
                save_db(user_db)
                return {"status": "success", "remain": 3, "msg": "무료 체험 부여."}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    global user_db
    if phone in user_db and user_db[phone]["remain"] > 0:
        # 프롬프트 고도화
        prompt = f"주역 타로 전문가로서 {category} 상담을 진행합니다. 선택된 괘 번호는 {card1}번과 {card2}번입니다. 따뜻하고 전문적인 말투로 5문장 내외 한국어 답변을 작성하세요."

        try:
            print(f"Gemini API 호출 시도...")
            # 최신 라이브러리 방식의 호출
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            if response and response.text:
                advice = response.text
                user_db[phone]["remain"] -= 1
                save_db(user_db)
            else:
                advice = "AI가 해설을 생성했으나 내용을 출력할 수 없습니다."
        except Exception as e:
            print(f"!!! CRITICAL AI ERROR: {str(e)}")
            advice = f"해설 생성 중 오류가 발생했습니다. (사유: {str(e)[:40]}...)"
        
        return {"combined_advice": advice, "remain": user_db[phone]["remain"], "status": "success"}
    return {"status": "over", "msg": "남은 횟수가 없습니다."}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)c import BaseModel
import google.generativeai as genai

app = FastAPI()

DB_FILE = "users.json"
GEMINI_API_KEY = "AIzaSyCCNjtYV0aE1BW9OHsQvhdycbXNCYeDX54"

# Gemini AI 설정 최신화
try:
    genai.configure(api_key=GEMINI_API_KEY)
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    # 모델명을 gemini-1.5-flash로 변경 (응답 속도가 훨씬 빠릅니다)
    model = genai.GenerativeModel('gemini-1.5-flash', safety_settings=safety_settings)
    print("Gemini 1.5 Flash 모델 설정 완료")
except Exception as e:
    print(f"Gemini 설정 오류: {str(e)}")

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
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
    return {"message": "Hwagyeong Iching Server V2.3 (Gemini 1.5 Flash)"}

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
            return {"status": "success", "remain": 10, "msg": f"결제 확인. {user['remain']}회 남았습니다."}
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
        prompt = (
            f"주역 타로 전문가로서 {category} 운세 상담에 답변해줘. "
            f"선택된 주역 괘 번호는 {card1}번과 {card2}번이야. "
            f"따뜻하고 희망적인 조언을 한국어로 친절하게 5문장 내외로 작성해줘."
        )

        try:
            print(f"AI 호출 시작: {category}")
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            if response and response.text:
                advice = response.text
                user_db[phone]["remain"] -= 1
                save_db(user_db)
                print(f"AI 호출 성공: {phone}")
            else:
                advice = "AI가 답변을 생성했으나 안전 필터에 의해 차단되었습니다."

        except Exception as e:
            print(f"!!! AI API ERROR: {str(e)}")
            advice = f"해설 생성 중 오류가 발생했습니다. (사유: {str(e)[:50]})"
        
        return {"combined_advice": advice, "remain": user_db[phone]["remain"], "status": "success"}
    return {"status": "over", "msg": "남은 횟수가 없습니다."}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

