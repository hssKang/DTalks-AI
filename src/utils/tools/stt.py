from dotenv import load_dotenv
from groq import Groq
import json
import os

# 환경 변수 설정
env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path=os.path.abspath(env_path))

# Groq 클라이언트 생성
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)


# 옥디오데서 텍스트 추출 코드
def get_caption(audio_path: str):
    transcription = client.audio.transcriptions.create(
        url=audio_path,
        model="whisper-large-v3",
        response_format="verbose_json",
        timestamp_granularities=[
            "word",
            "segment",
        ],
    )

    # 원하는 정보만 추출
    result = []
    for segment in transcription.segments:
        start = segment["start"]
        end = segment["end"]
        text = segment["text"].strip()
        result.append({"start": round(start, 2), "end": round(end, 2), "text": text})

    # "start", "end", "text" 형식으로 변환
    return json.dumps(result, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    audio_path = "https://rqzqyiswugdzsgswybga.supabase.co/storage/v1/object/public/portfolio-bucket//music.m4a"
    print(get_caption(audio_path))
