# fastText 모델과 feedback 모델의 파이프라인 코드
import numpy as np
import logging

from src.layers.filter.fasttext_model import model_predict, sentence_vector
from src.layers.filter.feedback_modal import load_centroids, update_feedback
from src.layers.filter.preprocessing import preprocess_text


# 메뉴얼적인 분류
def fallback_label_from_text(text: str) -> str:
    lowered = text.lower()
    ko = text
    try:
        if any(k in ko for k in ["조직도", "부서", "인원", "팀원", "소속", "구성원"]):
            return "__label__org_chart"
        if any(k in ko for k in ["양식", "폼", "서식", "신청서", "템플릿"]):
            return "__label__form_request"
        if any(
            k in ko
            for k in [
                "내부",
                "사내",
                "규정",
                "정책",
                "FAQ",
                "문의",
                "재택",
                "재택근무",
                "근태",
                "연차",
                "휴가",
                "복지",
                "급여",
                "경조",
            ]
        ):
            return "__label__internal_info"
        if any(k in lowered for k in ["org", "member", "people", "headcount"]):
            return "__label__org_chart"
        if any(k in lowered for k in ["form", "template", "request form"]):
            return "__label__form_request"
        if any(k in lowered for k in ["policy", "internal", "faq"]):
            return "__label__internal_info"
    except Exception:
        pass
    return None


# FastText + 중심벡터 예측 함수
def hybrid_predict(text, k=2):
    # 메뉴얼하게 찾기
    manual_fallback = fallback_label_from_text(text)
    if manual_fallback:
        return ([manual_fallback], [1.0])

    try:
        centroids = load_centroids()

        # 중심벡터가 없으면 FastText만 사용
        if not centroids:
            processed_text = preprocess_text(text)
            return model_predict(processed_text, k=1)

        # FastText로 Top-k 후보 선별
        processed_text = preprocess_text(text)
        fasttext_result = model_predict(processed_text, k=k)

        if not fasttext_result or len(fasttext_result[0]) == 0:
            return None

        top_labels = fasttext_result[0][:k]
        top_confidences = fasttext_result[1][:k]

        # 중심벡터 거리 계산
        text_vector = sentence_vector(processed_text)
        distances = {}

        for label in top_labels:
            if label in centroids:
                dist = np.linalg.norm(text_vector - centroids[label])
                distances[label] = dist

        if not distances:
            return fasttext_result

        # 가장 가까운 중심벡터의 라벨 선택
        best_label = min(distances, key=distances.get)
        best_distance = distances[best_label]

        # FastText 신뢰도 가져오기
        original_confidence = top_confidences[list(top_labels).index(best_label)]

        # 거리 기반 신뢰도 조정
        distance_threshold = 1.0
        distance_factor = max(
            0, (distance_threshold - best_distance) / distance_threshold
        )

        # 조정된 신뢰도 계산
        adjusted_confidence = original_confidence * (0.7 + 0.3 * distance_factor)
        adjusted_confidence = min(1.0, max(0.0, adjusted_confidence))

        return ([best_label], [adjusted_confidence])

    except Exception as e:
        logging.error(f"하이브리드 예측 중 오류: {e}")
        processed_text = preprocess_text(text)
        return model_predict(processed_text, k=1)


if __name__ == "__main__":
    # 피드백 테스트 예시
    feedback_test = "오늘 날씨가 좋아요"
    correct = True
    print(
        f"피드백 테스트 문장: {feedback_test} (피드백 {'좋아요' if correct else '싫어요'})"
    )

    # 첫 번째 예측
    initial_result = hybrid_predict(feedback_test, k=2)
    if initial_result:
        initial_label = initial_result[0][0]
        initial_confidence = initial_result[1][0]
        print(f"초기 예측: {initial_label} (신뢰도: {initial_confidence:.3f})")

        # 피드백 적용 후 재예측
        centroids = load_centroids()
        updated_centroids = update_feedback(
            feedback_test,
            initial_label,
            is_correct=correct,
            learning_rate=0.1,
        )

        updated_result = hybrid_predict(feedback_test, k=2)
        if updated_result:
            updated_label = updated_result[0][0]
            updated_confidence = updated_result[1][0]
            print(f"피드백 후 예측: {updated_label} (신뢰도: {updated_confidence:.3f})")
