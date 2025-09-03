from qdrant_client.models import PointStruct
import json
import os

from src.utils.tools.embedding import vectorize
import src.layers.LLM.bedrock_model as bedrock_model
from src.utils.tools.stt import get_caption
from src.utils.database.connect_qdrant import init_qdrant

# 환경 변수 설정
QDRANT_COLLECTION = "meeting_vectors"
BATCH_SIZE = 30
qdrant_client = init_qdrant(QDRANT_COLLECTION)


# 텍스트 요약 함수
def summarize_texts(texts):
    # Google Gemini API 클라이언트 생성
    client = bedrock_model.setup_bedrock()
    response = bedrock_model.call_model(
        client,
        f"Please summarize the following conversation in the language you entered. Do not summarize abstractly, and do not write the conversation verbatim. Write in paragraph form. target text : {texts}",
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    )

    return response


# 배치로 Qdrant에 데이터 저장
def save_data(batch_data, audio_path):
    points = []
    for _, (data, vector) in enumerate(batch_data):
        point_id = hash(f"{audio_path}_{data['start']}_{data['end']}") % (2**31)

        # 메타데이터 구성
        payload = {
            "description": data["description"],
            "file_name": os.path.basename(audio_path),
            "start": data["start"],
            "end": data["end"],
            "text": data["text"],
        }

        points.append(PointStruct(id=point_id, vector=vector, payload=payload))

    qdrant_client.upsert(collection_name=QDRANT_COLLECTION, points=points)


# 요약데이터 저장
def save_summarize(audio_path, description, summarize):
    vector = vectorize(description)
    point_id = hash(description) % (2**31)

    # 메타데이터 구성
    payload = {
        "summarize": summarize,
        "description": description,
        "audio_path": audio_path,
    }

    point = PointStruct(id=point_id, vector=vector, payload=payload)

    # Qdrant에 저장
    qdrant_client.upsert(collection_name=QDRANT_COLLECTION, points=[point])


# 파이프 라인 생성
def pipeline(file_description, audio_path):
    global qdrant_client
    if qdrant_client is None:
        qdrant_client = init_qdrant(QDRANT_COLLECTION)

    # 오디오 파일에서 텍스트 추출
    datas = get_caption(audio_path)
    datas = json.loads(datas)

    # 내용 요약
    summarize = summarize_texts(" ".join([data["text"] for data in datas]))
    save_summarize(audio_path, file_description, summarize)

    # 각 세그먼트에 예시 description 추가
    for data in datas:
        data["description"] = file_description

    # 배치 처리
    for i in range(0, len(datas), BATCH_SIZE):
        batch = datas[i : i + BATCH_SIZE]

        texts = []
        filtered_batch = []
        for data in batch:
            if data["text"].strip():  # 빈 문자열이 아니면
                texts.append(data["text"])
                filtered_batch.append(data)

        # 벡터화 (빈 리스트가 아닐 때만)
        if texts:
            vectors = vectorize(texts)
            batch_data = list(zip(filtered_batch, vectors))
            save_data(batch_data, audio_path)


if __name__ == "__main__":
    # 파일에 대한 설명 추가
    file_description = "2025년 7월 23일 상우형과의 대화"
    audio_path = "https://rqzqyiswugdzsgswybga.supabase.co/storage/v1/object/public/portfolio-bucket//music.m4a"

    pipeline(file_description, audio_path)
    print("Pipeline executed successfully.")
