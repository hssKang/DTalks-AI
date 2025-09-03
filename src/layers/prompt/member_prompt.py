from src.utils.database.member_vector import vectorize
from src.utils.database.connect_qdrant import init_qdrant

# 환경 변수 설정
QDRANT_COLLECTION = "member_vectors"
qdrant_client = None


# Qdrant에서 유저 검색
def search_vec(text):
    global qdrant_client
    # Qdrant에서 값 가져오기
    vec = vectorize(text)

    if qdrant_client is None:
        qdrant_client = init_qdrant(QDRANT_COLLECTION)

    search_result = qdrant_client.search(
        collection_name=QDRANT_COLLECTION, query_vector=vec, limit=5
    )

    # 결과 값에 대해서 정확도 필드 추가 및 confidence 0.5 이상만 필터링
    if search_result:
        results = []
        for result in search_result:
            confidence = round(result.score, 3)
            if confidence > 0.5:
                data = result.payload.copy()
                data["정확도"] = confidence
                results.append(data)
        return results if results else None
    else:
        return None


# 프롬프트 생성 함수
def make_prompt(prompt):
    search_result = search_vec(prompt)
    template = f"""You are a company HR representative.

INSTRUCTIONS:
- Do NOT mention accuracy scores and employee_number in your response
- Only answer if the user asks about work duties or location
- Match the language of the USER QUESTION.
- Format your response in clean Key-Value pairs for easy reading
- If additional information about duties or location is needed, please inform the user

CONTEXT DATA: {search_result}
USER QUESTION: {prompt}

Please provide your answer based on the context data above."""

    return template


if __name__ == "__main__":
    print(make_prompt("IT 개발팀의 조직도를 알려줘"))
