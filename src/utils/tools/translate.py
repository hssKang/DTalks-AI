import os
import deepl
from dotenv import load_dotenv


# 환경 변수 설정
env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path=os.path.abspath(env_path))


# DeepL 클라이언트 생성
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
deepl_client = deepl.DeepLClient(DEEPL_API_KEY)


# 번역 함수 정의
# lang을 기준으로 (유저가 입력한 언어) -> 영어 -> LLM -> 영어 -> (유저가 입력한 언어)로 번역 예정
def translater(text, lang="EN-GB"):
    # \n을 */로 치환
    text_with_placeholder = text.replace("\n", "*/")

    # DeepL API 호출
    result = deepl_client.translate_text(
        text_with_placeholder, target_lang=lang, model_type="prefer_quality_optimized"
    )

    # */를 다시 \n으로 복원
    translated_text = result.text.replace("*/", "\n")

    return (translated_text, result.detected_source_lang)
