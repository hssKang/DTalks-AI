from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from apscheduler.schedulers.background import BackgroundScheduler
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import threading
import logging
import uvicorn
import atexit
import os


from src.layers.filter.fasttext_model import model_retrain
from src.utils.tools.type_detection import type_detection
from src.utils.database.connect_qdrant import init_qdrant
from src.utils.database import document_vector
from src.utils.database import template_vector
from src.utils.database import voice_vector
import src.layers.monitoring.monitoring as monitoring
from src.utils.socket import web_socket
import src.utils.database.member_vector as member_vector
import src.utils.database.faq_vector as faq_vector


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


app = FastAPI(title="Dtalks")
instrumentator = Instrumentator().instrument(app).expose(app)
monitoring.load_metrics()

atexit.register(monitoring.save_metrics)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 파일 타입 정의
class FilePayload(BaseModel):
    originalFileName: str
    description: str
    fileType: str
    fileUrl: str


# 헬스 체크
@app.get("/api/chatbot/health-check")
async def health_check():
    return Response(content="ok", media_type="text/plain")


# 모델 학습
@app.get("/api/chatbot/model-train")
async def model_train():
    model_retrain()
    return Response(content="ok", media_type="text/plain")


@app.get("/api/chatbot/chat-per-day")
async def chat_per_day():
    """일일 대화 수 조회"""
    try:
        result = monitoring.get_daily_conversations()
        return result
    except Exception as e:
        print(f"일일 대화 수 API 오류: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"일일 대화 수 조회 중 오류가 발생했습니다: {str(e)}",
        )


@app.get("/api/chatbot/success-rate")
async def success_rate():
    """답변 성공률 조회"""
    try:
        result = monitoring.get_success_rate()
        return result
    except Exception as e:
        print(f"답변 성공률 API 오류: {e}")
        raise HTTPException(
            status_code=400, detail=f"답변 성공률 조회 중 오류가 발생했습니다: {str(e)}"
        )


@app.get("/api/chatbot/satisfy")
async def user_satisfy():
    """사용자 만족도 조회"""
    try:
        result = monitoring.get_user_satisfaction()
        return result
    except Exception as e:
        print(f"사용자 만족도 API 오류: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"사용자 만족도 조회 중 오류가 발생했습니다: {str(e)}",
        )


@app.get("/api/chatbot/response-time")
async def response_time_analysis():
    """응답 시간 분석"""
    try:
        result = monitoring.get_response_time_analysis()
        return result
    except Exception as e:
        print(f"응답 시간 분석 API 오류: {e}")
        raise HTTPException(
            status_code=400, detail=f"응답 시간 분석 중 오류가 발생했습니다: {str(e)}"
        )


@app.get("/api/chatbot/template-count")
async def template_usage_count():
    """프롬프트 템플릿 사용 통계"""
    try:
        result = monitoring.get_template_usage()
        return result
    except Exception as e:
        print(f"템플릿 사용 통계 API 오류: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"프롬프트 템플릿 사용 통계 조회 중 오류가 발생했습니다: {str(e)}",
        )


@app.get("/api/chatbot/week-response")
async def week_response_statistics():
    """일주일간 응답 횟수 통계"""
    try:
        result = monitoring.get_week_response()
        return result
    except Exception as e:
        print(f"주간 응답 통계 API 오류: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"일주일간 응답 횟수 통계 조회 중 오류가 발생했습니다: {str(e)}",
        )


# 임베딩을 위한 파일 URL 수집 API
@app.post("/api/chatbot/file")
async def file_collect(payload: FilePayload):
    try:
        # 파일 타입 감지
        types = type_detection(payload.fileUrl)

        # 타입 오류
        if types == "exception":
            raise HTTPException(status_code=400)

        # 오디오 파일 처리
        elif types == "audio":
            voice_vector.pipeline(payload.description, payload.fileUrl)
            return Response(content="200", media_type="text/plain")

        else:
            # 사내 문서 처리
            if payload.fileType == "DICT" or payload.fileType == "ETC":
                init_qdrant("internal_documents")
                document_vector.process_and_store(
                    {"fileUrl": payload.fileUrl, "description": payload.description}
                )
                return Response(content="200", media_type="text/plain")

            # 템플릿 파일 처리
            elif payload.fileType == "TEMP":
                template_vector.upsert_templates_batch(
                    {
                        "title": payload.originalFileName,
                        "description": payload.description,
                        "url": payload.fileUrl,
                    }
                )
                return Response(content="200", media_type="text/plain")

    except Exception:
        raise HTTPException(status_code=400)


if __name__ == "__main__":
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
    load_dotenv(dotenv_path=os.path.abspath(env_path))

    ws_url = os.getenv("ws_url")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    webhook_url = os.getenv("webhook_url")

    client = web_socket.WebSocketClient(ws_url, BOT_TOKEN, webhook_url)
    threading.Thread(target=client.connect_with_retry, daemon=True).start()

    # BackgroundScheduler로 매일 4시 함수 실행
    scheduler = BackgroundScheduler()
    scheduler.add_job(member_vector.save_data, "cron", hour=4, minute=0)
    scheduler.add_job(faq_vector.upsert_faq, "cron", hour=4, minute=0)
    scheduler.start()

    uvicorn.run(app, host="0.0.0.0", port=8001)

