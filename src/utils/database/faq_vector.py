import logging
import pandas as pd
from qdrant_client.models import PointStruct

from src.utils.database.connect_qdrant import init_qdrant, reset_collection
from src.utils.database.connect_mysql import init_mysql
from src.utils.tools.embedding import vectorize

QDRANT_COLLECTION = "faq-vectors"
qdrant_client = init_qdrant(QDRANT_COLLECTION)


# MySQL에서 FAQ 데이터 로드
def load_data():
    conn = init_mysql()
    try:
        sql = """
        SELECT faq.question, faq.answer, faq_category.name AS category
        FROM faq
        JOIN faq_category ON faq.category_id = faq_category.category_id
        """
        df = pd.read_sql(sql, conn)
        return df
    except Exception as e:
        logging.error(f"MySQL 데이터 로드 실패: {e}")
        return None
    finally:
        conn.close()


# FAQ 데이터 로드 및 벡터 변환 후 Qdrant에 저장
def upsert_faq():
    reset_collection(QDRANT_COLLECTION)
    faq_data = load_data()

    if faq_data is None:
        print("데이터 로드에 실패하여 작업을 중단합니다.")
        return

    points = []
    for idx, row in faq_data.iterrows():
        try:
            question = row["question"]
            print(f"  - {idx}번 질문 벡터화 중: {question[:30]}...")

            vector = vectorize(question)

            point = PointStruct(
                id=idx,
                vector=vector,
                payload={
                    "faq_id": idx,
                    "question": question,
                    "answer": row["answer"],
                    "category": row["category"],
                },
            )
            points.append(point)

        except Exception as e:
            logging.error(f"질문 {idx} 처리 중 오류: {e}")
            continue

    if points:
        qdrant_client.upsert(
            collection_name=QDRANT_COLLECTION, points=points, wait=True
        )
        logging.info(f"Qdrant에 {len(points)}개의 FAQ 벡터 저장을 완료했습니다.")
    else:
        logging.error("저장할 벡터가 없습니다.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    print("🚀 FAQ 벡터화 작업을 시작합니다...")

    # FAQ 벡터 저장
    print(load_data().info())
