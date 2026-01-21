import uvicorn
import json
import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

DB_FILE = "users.json"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCkSUH094XbgbOQv7sxOVA5HM5FscVhq18")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash')

user_db = {} # load_db() 로직 포함 (생략)

@app.get("/interpret")
async def interpret(card1: int, card2: int, category: str, phone: str):
    # AI에게 각 카드에 대한 명칭과 상세 해설을 요청
    prompt = (
        f"주역 전문가로서 {category} 상담을 합니다. 카드 {card1}번과 {card2}번을 뽑았습니다.\n"
        f"1. {card1}번 괘의 이름과 한 줄 의미\n"
        f"2. {card2}번 괘의 이름과 한 줄 의미\n"
        f"3. 두 괘를 조합한 상세 운세 풀이를 5문장 내외로 작성하세요.\n"
        "가독성을 위해 섹션을 명확히 구분하세요."
    )
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        advice = response.text if response else "해설을 생성할 수 없습니다."
        return {"combined_advice": advice, "status": "success"}
    except Exception as e:
        return {"status": "fail", "msg": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
