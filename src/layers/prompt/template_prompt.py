import logging

from src.utils.database.connect_qdrant import init_qdrant
from src.utils.tools.embedding import vectorize

# 환경설정 및 클라이언트 설정
QDRANT_COLLECTION = "template_vectors"
SIMILARITY_THRESHOLD = 0.65

# 클라이언트 초기화
qdrant_client = init_qdrant(QDRANT_COLLECTION)


# 템플릿 유사도 검색 함수
def find_similar_template(query: str):
    try:
        logging.info(f"검색 쿼리: {query}")
        query_vector = vectorize(query)

        search_results = qdrant_client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=1,
            with_payload=True,
        )

        if not search_results:
            return {
                "status": "not_found",
                "message": "유사한 템플릿을 찾을 수 없습니다.",
            }

        top_hit = search_results[0]
        score = top_hit.score

        if score >= SIMILARITY_THRESHOLD:
            return {
                "status": "success",
                "score": score,
                "matched_template": {
                    "title": top_hit.payload.get("title", "N/A"),
                    "description": top_hit.payload.get("description", "N/A"),
                    "url": top_hit.payload.get("url", "N/A"),
                },
            }
        else:
            return {
                "status": "fallback",
                "message": "1차 검색 임계값 미달",
                "score": score,
                "best_match": top_hit.payload.get("title", "N/A"),
            }

    except Exception as e:
        logging.error(f"템플릿 검색 중 오류 발생: {e}")
        return {"status": "error", "message": f"검색 실패: {str(e)}"}


# 템플릿 프롬프트 생성 함수
def make_prompt(query: str):
    # 템플릿 검색
    finded = find_similar_template(query)
    matched_template = (
        finded["matched_template"] if finded.get("status") == "success" else None
    )

    template = f"""You are the company's document management assistant.

Instructions:
- Do not mention accuracy scores in your answers.
- Provide as much information as possible.
- If there is no CONTEXT DATA, say so and provide a draft form.
- Match the language of the User question.
- Write your answer in an easy-to-read key-value pair format.
- Do not display the URL.

Context data: {finded}
User question: {query}

Please provide your answer based on the above context data."""

    return template, matched_template


if __name__ == "__main__":
    test_queries = [
        "개발 회의록 템플릿 추천해줘",
        "기획자용 보고서 형식 알려줘",
        "디자이너를 위한 작업일지 없을까?",
        "상반기 결산보고서 템플릿 알려줘",
        "직무 인터뷰 정리 양식 있어?",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i}] 질문: {query}")
        result = find_similar_template(query)

        if result["status"] == "success":
            payload = result["matched_template"]
            print(f"템플릿 제목: {payload['title']}")
            print(f"설명: {payload['description']}")
            print(f"링크: {payload['url']}")
        elif result["status"] == "fallback":
            print(f"유사도 부족 (score: {result['score']:.4f}) → fallback 필요")
            print(f"가장 가까운 템플릿: {result['best_match']}")
        else:
            print(f"오류: {result.get('message')}")

    print("\n\n\n\n\n\n")
    print(make_prompt("개발 회의록 템플릿 있어?"))
