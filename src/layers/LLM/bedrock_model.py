import os
import boto3
import json
import logging
from dotenv import load_dotenv


# Bedrock 클라이언트 설정 및 인증 확인
def setup_bedrock():
    try:
        # 환경 변수 등록
        env_path = os.path.join(os.path.dirname(__file__), "..", "..","..", ".env")
        load_dotenv(dotenv_path=os.path.abspath(env_path))
        API_KEY = os.getenv("AWS_BEARER_TOKEN_BEDROCK")

        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = API_KEY
        REGION = "us-east-2"

        # Bedrock 클라이언트 생성
        client = boto3.client(service_name="bedrock-runtime", region_name=REGION)

        return client

    except Exception as e:
        logging.error(f"클라이언트 설정 오류: {e}")
        return None


# Amazon Bedrock 모델 호출 함수
def call_model(
    client, message_text, model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0"
):  # us.anthropic.claude-sonnet-4-20250514-v1:0, us.anthropic.claude-3-5-haiku-20241022-v1:0
    try:
        # 메시지 구성
        messages = [{"role": "user", "content": [{"text": message_text}]}]

        # API 호출
        response = client.converse(
            modelId=model_id,
            messages=messages,
            inferenceConfig={"temperature": 0.7},
        )

        # 응답 추출
        if "output" in response and "message" in response["output"]:
            content = response["output"]["message"]["content"]
            if content and len(content) > 0:
                return content[0]["text"]

        logging.error("LLM 연결이 끊겼습니다.")
        return "LLM 연결이 끊겼습니다."

    except Exception as e:
        logging.error(f"LLM 오류: {str(e)}")
        return "LLM 연결이 끊겼습니다."

# 이미지 OCR을 위한 Bedrock 호출 함수
def call_image_ocr(image_base64, media_type, model_id="us.anthropic.claude-sonnet-4-20250514-v1:0"):
    try:
        client = setup_bedrock()
        if client is None:
            raise RuntimeError("Bedrock 클라이언트 설정 실패")
        
        # LLM에게 보낼 메세지 구성
        message = {
            "role": "user",
            "content":[
                {
                    "type": "image",
                    "source":{
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_base64
                    }
                },
                {
                    "type": "text",
                    "text": "이 이미지에 포함된 모든 텍스트를 정확하게 추출해주세요. 모든 언어를 인식하여 텍스트를 추출하고, 가능한 한 정확하게 번역해주세요. 원본의 문단 구조와 줄바꿈을 최대한 유지하여 텍스트를 반환해주세요."
                }
            ]
        }

        # API 요청 바디 구성
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "messages": [message],
            "temperature": 0.1      # 낮은 온도로 정확성 향상
        }

        # Bedrock API 호출
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        # 응답 파싱
        response_body = json.loads(response['body'].read())
        extracted_text = response_body['content'][0]['text']
        
        logging.info(f"Claude OCR 텍스트 추출 완료: {len(extracted_text)} 문자")
        return extracted_text
        
    except Exception as e:
        logging.error(f"이미지 OCR 처리 중 오류 발생: {str(e)}")
        raise RuntimeError(f"이미지 OCR 처리 중 오류 발생: {str(e)}")


if __name__ == "__main__":
    # 클라이언트 설정
    client = setup_bedrock()

    # 모델 호출 테스트
    test_message = "안녕하세요! Amazon Bedrock에 대해 간단히 설명해주세요."

    print(f"질문: {test_message}")

    response = call_model(client, test_message)
    print(f"응답: {response}")
