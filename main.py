import os
import uvicorn
import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 임시 사용자 데이터베이스 (서버 재시작 시 초기화됨)
user_db = {}

# 타로 해설 문구
sentences = [
    "현재 운세는 새로운 변화의 흐름 앞에 서 있습니다.",
    "과거의 낡은 습관을 버리고 새 길을 찾는 것이 길합니다.",
    "주변의 조력자와 화합하면 큰 성취를 이룰 수 있습니다.",
    "자신의 신념을 믿고 꾸준히 정진하는 태도가 중요합니다.",
    "조급함을 버리고 순리에 맡길 때 진정한 행복이 찾아옵니다."
]

class RegisterRequest(BaseModel):
    phone: str
    is_paid: bool

@app.get("/")
def home():
    return {"status": "online", "message": "tarotkorea real server is running!"}

@app.post("/register")
async def register(req: RegisterRequest):
    # 등록 로직
    if req.phone not in user_db:
        user_db[req.phone] = 10 if req.is_paid else 1
    return {"remain": user_db[req.phone]}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    # 상담 횟수 차감 및 결과 반환
    if phone in user_db and user_db[phone] > 0:
        user_db[phone] -= 1
    
    selected = random.sample(sentences, 3)
    advice = " ".join(selected)
    
    return {
        "combined_advice": advice, 
        "remain": user_db.get(phone, 0)
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
