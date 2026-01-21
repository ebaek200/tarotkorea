import random
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

# 임시 사용자 데이터베이스 (서버 재시작 시 초기화됨)
# 실서비스 시에는 PostgreSQL 등을 연결해야 데이터가 유지됩니다.
user_db = {}

# 랜덤 해설 문장 소스
sentences = [
    "현재 운세는 새로운 변화의 흐름 앞에 서 있습니다.",
    "과거의 낡은 습관을 버리고 새 길을 찾는 것이 길합니다.",
    "주변의 조력자와 화합하면 큰 성취를 이룰 수 있습니다.",
    "자신의 신념을 믿고 꾸준히 정진하는 태도가 중요합니다.",
    "조급함을 버리고 순리에 맡길 때 진정한 행복이 찾아옵니다.",
    "기대하지 않았던 곳에서 귀인이 나타나 도움을 줄 것입니다.",
    "지금은 내실을 다지며 때를 기다리는 것이 현명한 선택입니다.",
    "작은 것에 연연하지 말고 큰 목표를 향해 나아가세요.",
    "정직하고 성실한 자세가 결국 승리를 가져다줄 것입니다.",
    "마음의 평온을 유지하면 막혔던 일들이 술술 풀리게 됩니다."
]

class RegisterRequest(BaseModel):
    phone: str
    is_paid: bool

@app.get("/")
async def root():
    return {"message": "주역 타로 서버가 정상 작동 중입니다."}

@app.post("/register")
async def register(req: RegisterRequest):
    # 신규 등록이거나 유료 결제 체크 시 횟수 부여
    if req.is_paid:
        user_db[req.phone] = 10
    elif req.phone not in user_db:
        user_db[req.phone] = 1  # 무료 사용자는 기본 1회
    
    return {"remain": user_db.get(req.phone, 0)}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    # 횟수 확인 및 차감
    current_remain = user_db.get(phone, 0)
    
    if current_remain > 0:
        user_db[phone] -= 1
        current_remain = user_db[phone]
        
        # 5줄 랜덤 조합 생성
        selected = random.sample(sentences, 5)
        # 클라이언트 가독성을 위해 번호를 붙여서 전송
        advice = "\n".join([f"{i+1}. {s}" for i, s in enumerate(selected)])
    else:
        advice = "잔여 횟수가 부족합니다. 유료 회원 가입 후 이용해주세요."

    return {
        "combined_advice": advice,
        "remain": current_remain
    }

if __name__ == "__main__":
    # Render 배포 시에는 0.0.0.0으로 열어야 외부 접속이 가능합니다.
    uvicorn.run(app, host="0.0.0.0", port=8000)
