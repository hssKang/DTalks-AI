import re


# 전처리 함수
def preprocess_text(input_text):
    text = re.sub(r"[^\w\s가-힣?!]", " ", input_text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text
