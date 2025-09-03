import redis
import json
import logging
import hashlib
import numpy as np

from src.utils.database.connect_redis import get_redis_client
from src.utils.tools.embedding import vectorize

# 상수 정의
EMBEDDING_DIMENSION = 768
DOC_ID_LENGTH = 12
DEFAULT_TTL_SECONDS = 3600
DEFAULT_MIN_SIMILARITY = 0.85
VECTOR_INDEX_NAME = "vec_idx"
REDIS_KEY_PREFIX = "vec:"
REDIS_MAX_MEMORY = "100mb"
DB_PORT = 0


# Redis 연결
redis_client = get_redis_client(DB_PORT)


# Redis 설정
def configure_redis() -> None:
    redis_client.config_set("maxmemory-policy", "allkeys-lru")
    redis_client.config_set("maxmemory", REDIS_MAX_MEMORY)

    try:
        redis_client.ft(VECTOR_INDEX_NAME).create_index(
            [
                redis.commands.search.field.TextField("id"),
                redis.commands.search.field.VectorField(
                    "vec",
                    "FLAT",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": EMBEDDING_DIMENSION,
                        "DISTANCE_METRIC": "COSINE",
                    },
                ),
            ],
            definition=redis.commands.search.index_definition.IndexDefinition(
                prefix=[REDIS_KEY_PREFIX]
            ),
        )
        logging.info("Vector index created successfully")
    except redis.exceptions.ResponseError as e:
        if "Index already exists" not in str(e):
            raise
        logging.info("Vector index already exists")


# 캐싱 추가
def add_cache(
    question: str, answer: str, url_data=None, ttl_sec: int = DEFAULT_TTL_SECONDS
):
    try:
        doc_id = hashlib.md5(question.encode("utf-8")).hexdigest()[:DOC_ID_LENGTH]

        vector = vectorize(question)

        if url_data is None:
            matched_template = ""
        else:
            matched_template = json.dumps(
                {"title": url_data.get("title", ""), "url": url_data.get("url", "")},
                ensure_ascii=False,
            )

        key = f"{REDIS_KEY_PREFIX}{doc_id}"
        pipe = redis_client.pipeline()
        mapping = {
            "id": doc_id,
            "vec": np.array(vector).astype(np.float32).tobytes(),
            "answer": answer,
            "question": question,
            "matched_template": matched_template,
        }

        pipe.hset(key, mapping=mapping)
        pipe.expire(key, ttl_sec)
        pipe.execute()

        return doc_id

    except Exception as e:
        logging.error(f"Error adding Cache {doc_id}: {e}")
        raise


# 답변 검색
def search_cache(question: str, min_similarity: float = DEFAULT_MIN_SIMILARITY):
    try:
        query_vector = vectorize(question)
        query_bytes = np.array(query_vector).astype(np.float32).tobytes()

        search_query = "*=>[KNN 1 @vec $vec_param AS score]"
        params = {"vec_param": query_bytes}
        results = redis_client.ft(VECTOR_INDEX_NAME).search(
            search_query, query_params=params
        )

        if not results.docs:
            return None, 0.0, None

        doc = results.docs[0]
        similarity = 1 - float(doc.score)

        if similarity < min_similarity:
            return None, similarity, None

        answer = redis_client.hget(doc.id, "answer")
        matched_template_json = redis_client.hget(doc.id, "matched_template")
        matched_template = None
        if matched_template_json:
            decoded = matched_template_json
            if decoded == "":
                matched_template = None
            else:
                try:
                    matched_template = json.loads(decoded)
                except Exception:
                    matched_template = None
        if answer:
            return answer, similarity, matched_template

        return None, similarity, None

    except Exception as e:
        logging.error(f"Error getting answer: {e}")
        return None, 0.0, None


# 테스트
if __name__ == "__main__":
    configure_redis()
    # 테스트 데이터
    datas = {
        "오늘 회의 일정이 어떻게 되나요?": "오늘 오후 2시에 회의실 A에서 팀 미팅이 있고, 4시에 프로젝트 리뷰 회의가 예정되어 있습니다.",
        "프로젝트 마감일이 언제인지 확인해주세요": "현재 진행중인 프로젝트의 마감일은 다음 주 금요일(8월 8일)입니다. 진행 상황을 확인해 드릴까요?",
        "점심시간에 회사 식당 메뉴가 뭐예요?": "오늘 점심 메뉴는 김치찌개, 불고기정식, 샐러드바가 준비되어 있습니다. 운영시간은 11:30~13:30입니다.",
        "IT 지원팀에 컴퓨터 문제 신고하고 싶어요": "IT 지원 요청은 내부 포털 > IT 지원 > 장애신고에서 접수 가능합니다. 긴급한 경우 내선 1004번으로 연락주세요.",
        "휴가 신청 방법을 알려주세요": "휴가 신청은 인사포털에서 가능합니다. 연차는 3일 전, 반차는 1일 전까지 신청해주시고 팀장 승인이 필요합니다.",
        "회사 복리후생 제도에 대해 설명해주세요": "주요 복리후생으로는 4대보험, 연차 15일, 경조휴가, 교육비 지원, 건강검진, 점심 지원 등이 있습니다.",
        "신입사원 온보딩 일정을 확인하고 싶습니다": "신입사원 온보딩은 입사 첫 주에 진행되며, 회사 소개, 시스템 교육, 멘토 배정 등의 프로그램이 포함됩니다.",
        "회의실 예약하는 방법을 알려주세요": "회의실 예약은 사내 포털 > 시설예약에서 가능합니다. 최대 2주 전부터 예약 가능하며, 사용 후 정리해주세요.",
    }

    # Q&A 데이터 저장
    for i, (question, answer) in enumerate(datas.items()):
        doc_id = add_cache(question, answer, None)
        print(f"캐시 저장 완료 [{i+1}/8]: {question[:25]}... (ID: {doc_id})")

    # 검색 테스트
    user_questions = [
        "회의 스케줄 알려주세요",
        "프로젝트 언제 끝나나요?",
        "오늘 점심 뭐 나와요?",
        "컴퓨터가 안 켜져요",
    ]

    for test_question in user_questions:
        print(f"사용자 질문: '{test_question}'")

        answer, similarity, matched_template = search_cache(test_question)

        if answer:
            print(f"유사도: {similarity:.2%} \n답변: {answer}\n\n")
        else:
            print(f"유사한 질문을 찾을 수 없습니다. (유사도: {similarity:.2%})\n\n")
