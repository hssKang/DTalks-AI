import os
import uuid
import logging
import pandas as pd
from qdrant_client.models import PointStruct
from src.utils.database.connect_qdrant import init_qdrant
from src.utils.tools.embedding import vectorize

# 환경 변수 설정
QDRANT_COLLECTION = "template_vectors"
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768
CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "dataset", "template_dummy.csv"
)


qdrant_client = init_qdrant(QDRANT_COLLECTION)


# 템플릿 CSV 로드 함수
def load_templates(csv_path=CSV_PATH):
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    return df.to_dict(orient="records")


# 벡터 + 메타데이터 저장 함수
def upsert_templates_batch(templates):
    points = []
    # 빈 문자열 제거
    titles = [t for t in templates["title"] if t and t.strip()]
    descriptions = [d for d in templates["description"] if d and d.strip()]
    try:
        if titles:
            title_vectors = vectorize(titles)
            for t, v in zip(titles, title_vectors):
                title_payload = {**templates, "part": "title", "title": t}
                points.append(
                    PointStruct(id=str(uuid.uuid4()), vector=v, payload=title_payload)
                )
        if descriptions:
            desc_vectors = vectorize(descriptions)
            for d, v in zip(descriptions, desc_vectors):
                desc_payload = {**templates, "part": "description", "description": d}
                points.append(
                    PointStruct(id=str(uuid.uuid4()), vector=v, payload=desc_payload)
                )
        if points:
            qdrant_client.upsert(collection_name=QDRANT_COLLECTION, points=points)
            logging.info(f"총 {len(points)}개 벡터를 Qdrant에 저장 완료")
        else:
            logging.warning("업서트할 벡터가 없습니다.")
    except Exception as e:
        logging.error(f"템플릿 배치 업서트 실패: {e}")
        raise


# 실행
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logging.info("템플릿 벡터 저장 시작")
    templates = load_templates()
    logging.info(f"불러온 템플릿 개수: {len(templates)}")
    upsert_templates_batch(templates)
