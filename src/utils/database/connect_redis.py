import os
import redis
import logging
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
load_dotenv(dotenv_path=os.path.abspath(env_path))

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")


# Redis 클라이언트 초기화 및 설정
def get_redis_client(db_port):
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=db_port,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    try:
        redis_client.ping()
        logging.info("Redis 연결 성공")
    except redis.ConnectionError as e:
        logging.error(f"Redis 연결 실패: {e}")
        raise
    return redis_client
