import logging

from src.utils.tools.embedding import vectorize
from src.utils.database.connect_qdrant import init_qdrant

QDRANT_COLLECTION = "faq-vectors"
SIMILARITY_THRESHOLD = 0.78

# 클라이언트 초기화
qdrant_client = init_qdrant(QDRANT_COLLECTION)


# 사용자 질문을 받아 벡터화 후 FAQ와 유사도 비교하여 적합한 답변 반환
def find_faq_answer(user_question: str, return_top_n: int = 3):
    try:
        # 사용자 질문 벡터화
        logging.info(f"검색 질문: {user_question}")
        query_vector = vectorize(user_question)

        if not query_vector:
            logging.error("텍스트를 벡터로 변환하는 데 실패했습니다.")
            return {"status": "error", "message": "질문 처리 중 오류가 발생했습니다."}

        # Qdrant 검색
        search_results = qdrant_client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=return_top_n,
            with_payload=True,
        )

        if not search_results:
            return {"status": "not_found", "message": "유사한 질문을 찾을 수 없습니다."}

        top_hit = search_results[0]
        score = top_hit.score

        if score >= SIMILARITY_THRESHOLD:
            logging.info(f"1차 검색 성공 (유사도: {score:.4f})")

            answer = top_hit.payload.get("answer")

            if answer:
                return {
                    "status": "success",
                    "answer": answer,
                    "score": score,
                    "matched_question": top_hit.payload.get("question", "N/A"),
                    "category": top_hit.payload.get("category", "N/A"),
                }
            else:
                logging.warning("답변을 찾지 못했습니다.")
                return {
                    "status": "source_error",
                    "message": "답변 데이터를 찾는 데 실패했습니다.",
                }
        else:
            # 나중에 선현이 형의 2차 RAG 로직과 합칠 때 리턴값 추가
            logging.info(
                f"1차 검색 실패 (유사도: {score:.4f} < 임계값: {SIMILARITY_THRESHOLD})"
            )
            return {
                "status": "fallback_to_rag",
                "message": "정확도 높은 답변을 찾지 못해 2차 검색이 필요합니다.",
                "best_score": score,
                "best_match": top_hit.payload.get("question", "N/A"),
            }

    except Exception as e:
        logging.error(f"FAQ 검색 중 예외 발생: {e}")
        return {"status": "error", "message": f"시스템 오류가 발생했습니다: {str(e)}"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("\n--- 1차 FAQ 검색 레이어 테스트 ---")

    test_questions = [
        # --- 1. 높은 유사도 + 성공해야 하는 질문들 ---
        "회사 와이파이 비번 알려줘",  # 원본: 사내 Wi-Fi 비밀번호가 궁금합니다.
        "컴퓨터가 고장났어",  # 원본: 노트북 고장 시 어떻게 해야 하나요?
        "휴가 쓰려면 어떻게 해?",  # 원본: 연차는 어떻게 신청하나요?
        "월급 언제 들어와요?",  # 원본: 급여일은 언제인가요?
        "출입증 잃어버렸는데 어떡하지?",  # 원본: 사내 출입증을 분실했는데 어떻게 해야 하나요?
        # --- 2. 중간 유사도 + 임계값 테스트용 경계선 질문들 ---
        "나 새로운 프로그램 설치하고 싶은데 방법 알려줘.",
        "재택근무 하면서 연차 쓸 수 있어?",  # 두 가지 키워드 결합
        "노트북 말고 데스크탑도 수리 지원 돼?",  # '노트북'의 범위를 테스트
        "경조사 휴가 일정이 궁금해",  # '경조사비'와 '경조 휴가'를 테스트
        "업무용 메신저 사용법 알려줘",  # '사내 메신저 사용 규정'과 유사하지만 다른 의도
        # --- 3. 낮은 유사도 + 실패해야 하는 질문들 (2차 RAG로 넘어가야 함) ---
        "오늘 점심 메뉴 추천해줘",  # 업무와 관련 없는 일상 질문
        "우리 회사 경쟁사는 어디야?",  # FAQ에 없는 비즈니스 질문
        "회식 언제쯤 할까요?",  # 사내 문화 관련 질문
        "새로운 프로젝트 아이디어가 있어요",  # FAQ 범위를 벗어나는 질문
        "사장님 성함이 어떻게 되시죠?",  # 인물 정보 질문
    ]

    for i, question in enumerate(test_questions):
        print(f"\n[{i+1}. 질문] {question}")
        result = find_faq_answer(question, return_top_n=3)

        if result["status"] == "success":
            print(f"[매칭된 질문] {result['matched_question']}")
            print(f"[카테고리] {result['category']}")
            print(f"[답변] {result['answer'][:100]}...")
        else:
            if "best_score" in result:
                print(f"[최고 유사도] {result['best_score']:.4f}")
                print(f"[최고 매칭] {result['best_match']}")
