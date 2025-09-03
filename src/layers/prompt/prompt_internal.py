from src.utils.tools.embedding import vectorize
from src.utils.database.connect_qdrant import init_qdrant
from src.utils.database.connect_mysql import init_mysql
import pandas as pd
import logging
import os


qdrant_client = init_qdrant("internal_documents")
qdrant_client = init_qdrant("meeting_vectors")


def search_authority(user_id):
    conn = init_mysql()
    try:
        sql = f"""SELECT latest_version_url FROM file WHERE file_status = 'ACTIVE' AND department_id = (SELECT department_id FROM users WHERE user_id = {user_id});"""
        df = pd.read_sql(sql, conn)
        blocks = df["latest_version_url"].astype(str).tolist()
        file_names = [os.path.basename(file_url) for file_url in blocks]

        return file_names
    except Exception as e:
        logging.error(f"MySQL 데이터 로드 실패: {e}")
        return None
    finally:
        conn.close()


def search_internal_documents(question, user_id, auth):
    # 질문 임베딩 생성
    question_vector = vectorize(question)
    collections = ["internal_documents", "meeting_vectors"]  # mp3 형태도 포함

    file_name = search_authority(user_id)
    filter_param = (
        {
            "must": [
                {
                    "key": "file_name",
                    "match": {"any": file_name},
                }
            ]
        }
        if auth and file_name
        else None
    )

    result = []
    # Qdrant에서 유사한 청크 검색
    for collection in collections:
        search_result = qdrant_client.search(
            collection_name=collection,
            query_vector=question_vector,
            limit=4,
            query_filter=filter_param,
            with_payload=True,
        )
    # 결과 값에 대해서 정확도 필드 추가 및 confidence 0.5 이상만 필터링
    filter = [hit.payload for hit in search_result if hit.score >= 0.5]
    result.extend(filter)
    if not result:
        logging.error("검색 결과가 없거나 정확도가 0.5 이상인 결과가 없습니다.")
        return None
    return result


# 프롬프트 생성 함수
def build_prompt(question, user_id, auth=True):
    # 질문과 유사도가 높은 문서
    result = search_internal_documents(question, user_id, auth)
    if not result:
        logging.error("관련 문서를 찾을 수 없습니다.")
        return "**No related data available. Please inform the user politely.**"

    document = result[0]
    prompt = f""" You are the one who provides the internal company documents.

    INSTRUCTIONS:
    - Do not mention accuracy scores in your answers.
    - If there is no internal documentation, answer “There is no internal documentation that corresponds to the question.”
    - Provide the CONTEXT DATA (text, file name) of the internal document corresponding to the question.
    - Match the language of the USER QUESTION.

    CONTEXT DATA: {document}
    USER QUESTION: {question}

    Please provide your answer based on the context data above."""

    return prompt


if __name__ == "__main__":
    print(build_prompt("2025년 7월 23일 상우형과의 대화", None, None))
