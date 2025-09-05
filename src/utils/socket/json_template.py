import src.utils.database.faq_reader as faq_reader


def feedback_template():
    return {
        "text": "챗봇을 평가해주세요!",
        "blocks": [
            {
                "type": "header",
                "text": "챗봇을 평가해주세요!",
                "style": "white",
            },
            {
                "type": "text",
                "text": "좋아요",
                "inlines": [
                    {
                        "type": "styled",
                        "text": "👍 : ",
                        "bold": False,
                        "color": "default",
                    },
                    {
                        "type": "styled",
                        "text": '"@좋아요"',
                        "bold": True,
                        "color": "red",
                    },
                    {
                        "type": "styled",
                        "text": "를 입력해주세요.",
                        "bold": False,
                        "color": "default",
                    },
                ],
            },
            {
                "type": "text",
                "text": "아쉬워요",
                "inlines": [
                    {
                        "type": "styled",
                        "text": "👎 : ",
                        "bold": False,
                        "color": "default",
                    },
                    {
                        "type": "styled",
                        "text": '"@싫어요"',
                        "bold": True,
                        "color": "blue",
                    },
                    {
                        "type": "styled",
                        "text": "를 입력해주세요.",
                        "bold": False,
                        "color": "default",
                    },
                ],
            },
        ],
    }


def url_template(data):
    return {
        "text": "요청하신 양식입니다.",
        "blocks": [
            {
                "type": "context",
                "content": {
                    "type": "text",
                    "text": "요청하신 양식입니다.",
                    "inlines": [
                        {
                            "type": "link",
                            "text": data["title"],
                            "url": data["url"],
                        }
                    ],
                },
            }
        ],
    }


def faq_category_template():
    df = faq_reader.load_category()
    blocks = [{"type": "header", "text": "FAQ 카테고리", "style": "white"}]
    # df의 각 행마다 description 블록 추가
    for _, row in df.iterrows():
        blocks.append(
            {
                "type": "description",
                "term": str(row["category_id"]),
                "content": {"type": "text", "text": row["name"]},
                "accent": True,
            }
        )
    # 마지막 안내 블록 추가
    blocks.append(
        {
            "type": "text",
            "text": "description",
            "inlines": [
                {"type": "styled", "text": "번호", "bold": True, "color": "red"},
                {
                    "type": "styled",
                    "text": "를 입력하면 해당 카테고리의 질문을 볼 수 있습니다!",
                    "bold": False,
                    "color": "default",
                },
            ],
        }
    )
    return {
        "text": "FAQ 메시지입니다.",
        "blocks": blocks,
    }


def faq_question_template(id):
    df = faq_reader.load_question(id)
    blocks = [{"type": "header", "text": "FAQ 질문", "style": "white"}]
    # df의 각 행마다 description 블록 추가
    for _, row in df.iterrows():
        blocks.append(
            {
                "type": "description",
                "term": str(row["faq_id"]),
                "content": {"type": "text", "text": row["question"]},
                "accent": True,
            }
        )
    # 마지막 안내 블록 추가
    blocks.append(
        {
            "type": "text",
            "text": "description",
            "inlines": [
                {"type": "styled", "text": "번호", "bold": True, "color": "red"},
                {
                    "type": "styled",
                    "text": "를 입력하면 해당 질문에 대한 답변을 볼 수 있습니다!",
                    "bold": False,
                    "color": "default",
                },
            ],
        }
    )
    return {
        "text": "FAQ 메시지입니다.",
        "blocks": blocks,
    }


def faq_answer_template(id):
    df = faq_reader.load_answer(id)
    return {
        "text": "FAQ 메시지입니다.",
        "blocks": [
            {"type": "header", "text": "FAQ", "style": "white"},
            {
                "type": "text",
                "text": "question",
                "inlines": [
                    {"type": "styled", "text": "Q. ", "bold": True, "color": "red"},
                    {
                        "type": "styled",
                        "text": df["question"].iloc[0],
                        "bold": False,
                        "color": "default",
                    },
                ],
            },
            {
                "type": "text",
                "text": "answer",
                "inlines": [
                    {"type": "styled", "text": "  A. ", "bold": True, "color": "blue"},
                    {
                        "type": "styled",
                        "text": df["answer"].iloc[0],
                        "bold": False,
                        "color": "default",
                    },
                ],
            },
        ],
    }

