import logging
import numpy as np
import os

from src.layers.filter.fasttext_model import sentence_vector
from src.layers.filter.preprocessing import preprocess_text


# 라벨별 중심 벡터 계산 함수
def calculate_centroids(train_file, model):
    label_texts = {}

    if model is None:
        logging.warning("모델이 로드되지 않았습니다.")
        return {}

    try:
        with open(train_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(" ", 1)
                if len(parts) == 2:
                    label, text = parts
                    if label not in label_texts:
                        label_texts[label] = []
                    label_texts[label].append(text)

        centroids = {}
        for label, texts in label_texts.items():
            if texts:
                vectors = []
                for text in texts:
                    processed_text = preprocess_text(text)
                    vector = sentence_vector(processed_text)
                    vectors.append(vector)

                centroids[label] = np.mean(vectors, axis=0)
            else:
                logging.warning(f"{label}에 해당하는 텍스트가 없습니다.")

        return centroids

    except Exception as e:
        logging.error(f"중심 벡터 계산 중 오류: {e}")
        return {}


# 중심 벡터 저장 함수
def save_centroids(
    centroids, centroids_path="./src/layers/filter/pretrained/centroids.npz"
):
    try:
        np.savez(centroids_path, **centroids)
        logging.info(f"중심 벡터가 {centroids_path}에 저장되었습니다.")
    except Exception as e:
        logging.error(f"중심 벡터 저장 중 오류: {e}")


# 저장된 중심 벡터 로드 함수
def load_centroids(centroids_path="./src/layers/filter/pretrained/centroids.npz"):
    try:
        if os.path.exists(centroids_path):
            data = np.load(centroids_path)
            centroids = {key: data[key] for key in data.files}
            return centroids
        else:
            logging.warning("저장된 중심 벡터 파일이 없습니다.")
            return {}
    except Exception as e:
        logging.error(f"중심 벡터 로드 중 오류: {e}")
        return {}


# 피드백을 통한 중심벡터 업데이트 함수
def update_feedback(text, predicted_label, is_correct, learning_rate=0.1):
    try:
        text_vector = sentence_vector(text)
        label_centroids = load_centroids()

        if is_correct:
            # 좋아요: 해당 라벨 중심벡터를 텍스트 쪽으로 이동
            if predicted_label in label_centroids:
                old_centroid = label_centroids[predicted_label]
                new_centroid = old_centroid + learning_rate * (
                    text_vector - old_centroid
                )
                label_centroids[predicted_label] = new_centroid
        else:
            # 싫어요: 해당 라벨 중심벡터를 텍스트에서 멀어지게 (가중치를 낮게)
            if predicted_label in label_centroids:
                old_centroid = label_centroids[predicted_label]
                new_centroid = old_centroid - learning_rate / 2 * (
                    text_vector - old_centroid
                )
                label_centroids[predicted_label] = new_centroid

        # 업데이트된 중심 벡터 저장
        save_centroids(label_centroids)

        return label_centroids

    except Exception as e:
        logging.error(f"중심 벡터 업데 이트 중 오류: {e}")
        return label_centroids


if __name__ == "__main__":
    test_text = "오늘 회의가 언제인지 알려주세요"
    print(f"테스트 텍스트: {test_text}")

    vector = sentence_vector(test_text)
    if vector is not None:
        print(f"벡터 차원: {vector.shape}")
        print(f"벡터 샘플: {vector[:5]}...")
    else:
        print("벡터 계산 실패")
