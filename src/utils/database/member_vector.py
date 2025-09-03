import uuid
import logging
import pandas as pd
from qdrant_client.models import PointStruct

from src.utils.database.connect_qdrant import init_qdrant, reset_collection
from src.utils.database.connect_mysql import init_mysql
from src.utils.tools.embedding import vectorize


QDRANT_COLLECTION = "member_vectors"


qdrant_client = init_qdrant(QDRANT_COLLECTION)


# MySQL에서 FAQ 데이터 로드
def load_data():
    conn = init_mysql()
    try:
        sql = """
        SELECT users.employee_number, users.email, users.name, users.nickname, department.name as department 
        FROM users JOIN department 
        ON users.department_id = department.department_id
        """
        df = pd.read_sql(sql, conn)
        return df
    except Exception as e:
        logging.error(f"MySQL 데이터 로드 실패: {e}")
        return None
    finally:
        conn.close()


# File to dict (각 줄 별로 나눔)
def chunker():
    df = load_data()
    result = df.to_dict(orient="records")
    return result


# 배치로 Qdrant에 데이터 저장
def save_data():
    reset_collection(QDRANT_COLLECTION)
    datas = chunker()
    batch_size = 30
    points = []

    for i in range(0, len(datas), batch_size):
        batch = datas[i : i + batch_size]

        # 배치 내 모든 텍스트 준비
        texts = []
        filtered_batch = []
        for data in batch:
            text = ", ".join(
                [
                    f"{key}-{value}"
                    for key, value in data.items()
                    if key != "employee_number"
                ]
            )
            if text.strip():  # 빈 문자열이 아니면
                texts.append(text)
                filtered_batch.append(data)

        # 벡터화 및 저장
        if texts:
            vectors = vectorize(texts)
            batch_data = list(zip(filtered_batch, vectors))

            points = []
            for data, vector in batch_data:
                employee_number = data["employee_number"]
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, employee_number))
                points.append(PointStruct(id=point_id, vector=vector, payload=data))

            qdrant_client.upsert(collection_name=QDRANT_COLLECTION, points=points)


if __name__ == "__main__":
    save_data()
