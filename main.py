import random
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

user_db = {}

# 종합 해설 문장 소스
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

@app.post("/register")
async def register(req: RegisterRequest):
    if req.phone not in user_db:
        user_db[req.phone] = 10 if req.is_paid else 1
    else:
        if req.is_paid: user_db[req.phone] = 10
    return {"remain": user_db[req.phone]}

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    if phone in user_db and user_db[phone] > 0:
        user_db[phone] -= 1

    selected = random.sample(sentences, 5)
    advice = "\n".join(selected)

    return {
        "combined_advice": advice,
        "remain": user_db.get(phone, 0)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
