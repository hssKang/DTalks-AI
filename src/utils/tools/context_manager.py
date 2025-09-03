import re
import json
import logging
from typing import List, Dict
from datetime import datetime

import src.layers.LLM.bedrock_model as bedrock_model
import src.utils.database.connect_redis as connect_redis

# 환경 변수 설정과 설정값 조정
MAX_CONTEXT_LENGTH = 5
REDIS_TTL = 32400  # 9시간
SUMMARY_THRESHOLD = 200
DB_PORT = 1

redis_client = connect_redis.get_redis_client(DB_PORT)
bedrock_client = bedrock_model.setup_bedrock()


# 대화 기록에 추가
def add_to_history(
    user_id: str = "default_user", query: str = "", response: str = ""
) -> bool:
    try:
        key = f"chat_context:{user_id}"

        # 응답 요약 (200자 이상일 때만)
        summarized_response = response
        if len(response) > SUMMARY_THRESHOLD:
            try:
                summary_prompt = f"""Summarize the following response in 2-3 sentences, keeping only the key information:
                Response: {response}
                Summary:"""

                summarized_response = bedrock_model.call_model(
                    bedrock_client, summary_prompt
                )
                logging.info(
                    f"응답 요약됨: {len(response)}자 → {len(summarized_response)}자"
                )

            except Exception as e:
                logging.warning(f"요약 실패, 원본 사용: {e}")
                summarized_response = response

        record = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": summarized_response,
        }

        record_json = json.dumps(record, ensure_ascii=False)

        # Redis에 저장
        pipe = redis_client.pipeline()
        pipe.lpush(key, record_json)
        pipe.ltrim(key, 0, MAX_CONTEXT_LENGTH - 1)
        pipe.expire(key, REDIS_TTL)
        pipe.execute()

        current_length = redis_client.llen(key)
        logging.info(f"대화 기록 저장됨: {user_id}, 현재 {current_length}개")
        return True

    except Exception as e:
        logging.error(f"대화 기록 추가 중 오류 발생: {e}")
        return False


# 현재 질문과 관련된 이전 대화 찾기
def find_related_context(
    user_query: str, user_id: str = "default_user", client=None
) -> List[Dict]:
    try:
        key = f"chat_context:{user_id}"
        items = redis_client.lrange(key, 0, MAX_CONTEXT_LENGTH - 1)
        history = [json.loads(item) for item in items]

        if not history:
            logging.info("이전 대화 기록이 없습니다.")
            return []

        # 관련성 판단을 위한 프롬프트
        context_prompt = f"""
        Analyze the relationship between the current question and previous conversations.

        Current question: "{user_query}"

        Previous conversations:
        {json.dumps(history, ensure_ascii=False, indent=2)}

        Task: Identify which previous conversations are contextually related to the current question.
        Output: Return ONLY a JSON array of indices for related conversations.
        - Format: [0, 2, 4]
        - If no conversations are related: []
        - Do not include any explanation or additional text.
        """

        logging.info(f"맥락 검색 중: {user_query[:50]}...")
        response_text = bedrock_model.call_model(client, context_prompt)

        # JSON 파싱 시도
        match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", response_text, re.DOTALL)
        if match:
            response_text = match.group(1).strip()

        if response_text.startswith("[") and response_text.endswith("]"):
            related_indices = json.loads(response_text)
        else:
            logging.warning(f"JSON 파싱 실패: {response_text}")
            return []

        """""" """"""
        # 유효한 인덱스만 필터링
        valid_indices = [
            i for i in related_indices if isinstance(i, int) and 0 <= i < len(history)
        ]

        # 관련된 대화 추출
        related_context = [history[i] for i in valid_indices]

        if related_context:
            logging.info(f"{len(related_context)}개의 관련 대화를 찾았습니다.")

        else:
            logging.info("관련된 대화를 찾지 못했습니다.")

        return related_context

    except Exception as e:
        logging.error(f"맥락 파악 중 오류 발생: {e}")
        return []


# 관련 맥락을 포함한 프롬프트 생성
def build_context_prompt(user_query: str, related_context: List[Dict]) -> str:
    prompt_parts = []

    if related_context:
        prompt_parts.append("=== Related Previous Conversations (For Reference) ===")
        prompt_parts.append(
            "The following are summaries of previous conversations. Use them only to extract key context or information.\n"
        )

        for idx, conv in enumerate(related_context, 1):
            prompt_parts.extend(
                [
                    f"\n[Previous Conversation {idx}]",
                    f"User asked: {conv['query']}",
                    f"Assistant's response: {conv['response']}",
                    "",
                ]
            )

        prompt_parts.append(
            "Use the above conversations as a reference to answer the following question.\n"
        )

    prompt_parts.append(f"Current question: {user_query}")

    return "\n".join(prompt_parts)
