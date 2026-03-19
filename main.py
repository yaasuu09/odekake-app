from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import services
import os

app = FastAPI(title="AI お出かけナビ API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NavigateRequest(BaseModel):
    mode: str
    origin: str
    destination: str

class SuggestRequest(BaseModel):
    mode: str
    schedule: str
    origin: str

@app.get("/")
def read_root():
    # トップページ (/) にアクセスした際は public/index.html が優先されるためここは無効化されます
    return {"message": "AI お出かけナビのバックエンドサーバーが正常に起動しています！"}

@app.post("/api/suggest")
def get_suggestion(req: SuggestRequest):
    """ユーザーの「移動手段」「予定日時」「出発地」に応じてAIでおすすめの行き先を複数提案する"""
    return services.suggest_destination(req.mode, req.schedule, req.origin)

@app.post("/api/navigate")
def get_navigation_info(req: NavigateRequest):
    # 1. ルートと駐車場情報の取得（Google Maps）
    route_info = services.get_route_and_parking(req.origin, req.destination, req.mode)
    # 2. 天気と自転車アラートの取得（OpenWeatherMap）
    weather_info = services.get_weather_info("Yokohama")
    # 3. 目的地の口コミをAIに分析させる（Gemini）
    ai_analysis = services.analyze_place(req.destination)
    
    return {
        "route": route_info,
        "weather": weather_info,
        "analysis": ai_analysis
    }

# デプロイ用に、フロントエンドのファイル（publicフォルダ）を配信する設定
app.mount("/", StaticFiles(directory="public", html=True), name="public")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
