from qdrant_client.models import VectorParams, Distance
from qdrant_client import QdrantClient
from dotenv import load_dotenv
import logging
import os


env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
load_dotenv(dotenv_path=os.path.abspath(env_path))

QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = int(os.getenv("QDRANT_PORT"))

qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


# Qdrant 컬렉션 초기화
def init_qdrant(collection_name):
    # Qdrant 클라이언트 생성
    collections = qdrant_client.get_collections().collections
    collections = [c.name for c in collections]

    if collection_name not in collections:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
        logging.info(f"'{collection_name}' 컬렉션을 생성했습니다.")
    else:
        logging.info(f"'{collection_name}' 컬렉션이 이미 존재합니다.")

    return qdrant_client


# Qdrant 컬렉션 리셋
def reset_collection(collection_name):
    try:
        qdrant_client.delete_collection(collection_name=collection_name)
        logging.info(f"Qdrant 컬렉션 '{collection_name}' 삭제 완료")
    except Exception as e:
        logging.warning(f"컬렉션 삭제 중 오류: {e}")

    # 컬렉션 재생성
    init_qdrant(collection_name)
    logging.info(f"Qdrant 컬렉션 '{collection_name}' 재생성 완료")
