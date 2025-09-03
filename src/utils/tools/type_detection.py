# 파일 형식 감지 함수


def type_detection(file_path):
    # 음성 파일
    if (
        file_path.endswith(".m4a")
        or file_path.endswith(".mp3")
        or file_path.endswith(".wav")
    ):
        return "audio"

    # PDF 파일
    elif file_path.endswith(".pdf"):
        return "pdf"

    # 이미지 파일
    elif (
        file_path.endswith(".jpg")
        or file_path.endswith(".jpeg")
        or file_path.endswith(".png")
    ):
        return "image"

    # 엑셀
    elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
        return "excel"

    # csv
    elif file_path.endswith(".csv"):
        return "csv"

    # 워드
    elif file_path.endswith(".docx") or file_path.endswith(".doc"):
        return "word"

    # 지원하지 않는 파일 형식
    else:
        return "exception"


if __name__ == "__main__":
    PATH = "https://rqzqyiswugdzsgswybga.supabase.co/storage/v1/object/public/portfolio-bucket//music.m4a"

    print(type_detection(PATH))
