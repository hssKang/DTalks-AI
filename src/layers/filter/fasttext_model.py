import fasttext
import logging
import os

from src.layers.filter.preprocessing import preprocess_text


# 모델 재학습
def model_retrain(input_path="./dataset/train.txt"):
    global model

    try:
        if not os.path.exists(input_path):
            return None

        # 모델 학습
        model = fasttext.train_supervised(
            input=input_path,
            epoch=50,
            wordNgrams=2,
            dim=100,
            lr=0.1,
            minCount=1,
            verbose=2,
        )

        model.save_model(model_path)
        logging.info(f"모델이 {model_path}에 저장되었습니다.")

        # 동적 import
        from src.layers.filter.feedback_modal import (
            calculate_centroids,
            save_centroids,
        )

        centroids = calculate_centroids(input_path, model)
        save_centroids(centroids, "./src/layers/filter/pretrained/centroids.npz")

        return model

    except Exception as e:
        logging.error(f"모델 훈련 중 오류: {e}")
        return None


# 모델 예측 함수
def model_predict(text, k=2):
    global model
    if model is None:
        model = model_retrain()

    processed_text = preprocess_text(text)
    result = model.predict(processed_text, k=k)
    return result


# 텍스트의 중심 벡터 얻기
def sentence_vector(text):
    global model
    if model is None:
        model = model_retrain()

    processed_text = preprocess_text(text)
    vector = model.get_sentence_vector(processed_text)
    return vector


# 원래 모델 불러오기
model_path = "./src/layers/filter/pretrained/model.bin"
model = None

try:
    model = fasttext.load_model(model_path)
except Exception as e:
    logging.warning(f"모델 로드 실패: {e}")
    model = None

if __name__ == "__main__":
    # 테스트 케이스
    test_cases = [
        ("오늘 너무 바빠요", "__label__smalltalk"),
        ("스케줄 확인해주세요", "__label__scheduling"),
        ("회의 언제예요", "__label__scheduling"),
        ("점심 뭐 먹을까", "__label__smalltalk"),
        ("급여일 언제죠", "__label__internal_info"),
        ("양식 필요해요", "__label__form_request"),
        ("팀장님 어디 계세요", "__label__internal_info"),
        ("프린터 고장났어요", "__label__internal_info"),
        ("집에 가고 싶어", "__label__smalltalk"),
    ]

    correct = 0
    total = len(test_cases)

    for test, expected in test_cases:
        result = model_predict(test)
        if result:
            predicted = result[0][0]
            confidence = result[1][0]

            if predicted == expected:
                correct += 1

            print(f"{test}")
            print(f"   예상: {expected}")
            print(f"   예측: {predicted} ({confidence:.3f})\n")

    accuracy = correct / total * 100
    print(f"테스트 정확도: {correct}/{total} = {accuracy:.1f}%")
