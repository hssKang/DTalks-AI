import logging
import pandas as pd

from src.utils.database.connect_mysql import init_mysql


# MySQL에서 FAQ 카테고리 로드
def load_category():
    conn = init_mysql()
    try:
        sql = """SELECT category_id, name, description FROM faq_category WHERE is_active =True"""
        df = pd.read_sql(sql, conn)
        return df
    except Exception as e:
        logging.error(f"MySQL 데이터 로드 실패: {e}")
        return None
    finally:
        conn.close()


# MySQL에서 FAQ 질문 로드
def load_question(id):
    conn = init_mysql()
    try:
        sql = f"""SELECT faq_id, question FROM faq WHERE is_active=True and category_id={id}"""
        df = pd.read_sql(sql, conn)
        return df
    except Exception as e:
        logging.error(f"MySQL 데이터 로드 실패: {e}")
        return None
    finally:
        conn.close()


# MySQL에서 FAQ 답변 로드
def load_answer(id):
    conn = init_mysql()
    try:
        sql = (
            f"""SELECT question, answer FROM faq WHERE is_active=True and faq_id={id}"""
        )
        df = pd.read_sql(sql, conn)
        return df
    except Exception as e:
        logging.error(f"MySQL 데이터 로드 실패: {e}")
        return None
    finally:
        conn.close()
