import os
import logging
from google import genai
from dotenv import load_dotenv
from google.genai import types

# 환경 변수 설정
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
load_dotenv(dotenv_path=os.path.abspath(env_path))

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Google Gemini 클라이언트 초기화
client = genai.Client(api_key=GEMINI_API_KEY)


# 텍스트를 벡터화
def vectorize(texts) -> list:
    # texts가 str이면 리스트로 변환
    if isinstance(texts, str):
        texts = [texts]
        is_one = True
    else:
        is_one = len(texts) == 1

    try:
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
        )
        if is_one:
            return response.embeddings[0].values
        else:
            return [embedding.values for embedding in response.embeddings]

    except Exception as e:
        logging.error(f"벡터화 중 오류 발생: {e}")
        raise
