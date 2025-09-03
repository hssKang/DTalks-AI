from src.layers.monitoring.metrics import metrics
from dotenv import load_dotenv
import time
import os
import requests
import logging
import json

load_dotenv()

PROMETHEUS_CONFIG = {
    "base_url": os.getenv("PROMETHEUS_BASE_URL"),
    "query_url": f"{os.getenv('PROMETHEUS_QUERY_URL')}",
    "timeout": int(os.getenv("PROMETHEUS_TIMEOUT")),
}

METRICS_DUMP_FILE = "metrics_dump.json"
RESPONSE_TIME_STATS_FILE = "./prometheus/response_time_stats.json"

# 응답 시간 집계용 변수
response_time_stats = {
    "total_sum": 0.0,
    "total_count": 0,
    "zone_counts": [0, 0, 0, 0, 0],  # 5, 10, 15, 20, +Inf
}

######################## 메트릭 함수 추가 ########################
def save_metrics():
    """메트릭 값을 파일로 저장"""
    def tuple_key_to_jsonstr_counter(d):
        return {json.dumps(k): {"_value": v._value.get()} for k, v in d.items()}

    def tuple_key_to_jsonstr_gauge(d):
        return {json.dumps(k): {"_value": v._value.get()} for k, v in d.items()}

    data = {
    "daily_conversations": tuple_key_to_jsonstr_counter(metrics.daily_conversations._metrics.copy()),
    "response_success": tuple_key_to_jsonstr_counter(metrics.response_success._metrics.copy()),
    "response_failure": tuple_key_to_jsonstr_counter(metrics.response_failure._metrics.copy()),
    "user_feedback": tuple_key_to_jsonstr_counter(metrics.user_feedback._metrics.copy()),
    "prompt_template_usage": tuple_key_to_jsonstr_counter(metrics.prompt_template_usage._metrics.copy()),
    "weekly_responses": tuple_key_to_jsonstr_counter(metrics.weekly_responses._metrics.copy()),
    "average_response_time": tuple_key_to_jsonstr_gauge(metrics.average_response_time._metrics.copy()),
    }
    with open(METRICS_DUMP_FILE, "w") as f:
        json.dump(data, f, default=str)
    with open(RESPONSE_TIME_STATS_FILE, "w") as f:
        json.dump(response_time_stats, f)

def load_metrics():
    """메트릭 값을 파일에서 복원"""
    if os.path.exists(METRICS_DUMP_FILE):
        with open(METRICS_DUMP_FILE, "r") as f:
            data = json.load(f)
        # Counter
        for k, v in data.get("daily_conversations", {}).items():
            metrics.daily_conversations.labels(*json.loads(k))._value.set(v["_value"])
        for k, v in data.get("response_success", {}).items():
            metrics.response_success.labels(*json.loads(k))._value.set(v["_value"])
        for k, v in data.get("response_failure", {}).items():
            metrics.response_failure.labels(*json.loads(k))._value.set(v["_value"])
        for k, v in data.get("user_feedback", {}).items():
            metrics.user_feedback.labels(*json.loads(k))._value.set(v["_value"])
        for k, v in data.get("prompt_template_usage", {}).items():
            metrics.prompt_template_usage.labels(*json.loads(k))._value.set(v["_value"])
        for k, v in data.get("weekly_responses", {}).items():
            metrics.weekly_responses.labels(*json.loads(k))._value.set(v["_value"])
        # Gauge
        for k, v in data.get("average_response_time", {}).items():
            metrics.average_response_time.labels(*json.loads(k))._value.set(v["_value"])
    # 응답 시간 집계값 복원
    if os.path.exists(RESPONSE_TIME_STATS_FILE):
        with open(RESPONSE_TIME_STATS_FILE, "r") as f:
            stats = json.load(f)
            response_time_stats["total_sum"] = stats.get("total_sum", 0.0)
            response_time_stats["total_count"] = stats.get("total_count", 0)
            response_time_stats["zone_counts"] = stats.get("zone_counts", [0, 0, 0, 0, 0])

######################################################################################

# 일일 대화 수 기록 함수
def record_conversation(language, date=None):
    """일일 대화 수 기록"""
    if date is None:
        date = time.strftime("%Y-%m-%d")
    metrics.daily_conversations.labels(date=date, language=language).inc()


# 성공 기록
def record_success(label_type, confidence_score):
    """성공적인 응답 기록"""
    confidence_level = (
        "high"
        if confidence_score > 0.8
        else "medium" if confidence_score > 0.6 else "low"
    )
    metrics.response_success.labels(
        label_type=label_type, confidence_level=confidence_level
    ).inc()


# 실패 기록
def record_failure(error_type, label_type="production"):
    """실패한 응답 기록"""
    metrics.response_failure.labels(label_type=label_type, error_type=error_type).inc()


# 프롬프트 템플릿 사용 기록
def record_prompt_usage(template_type, label_type):
    """프롬프트 템플릿 사용 기록"""
    metrics.prompt_template_usage.labels(
        template_type=template_type, label_type=label_type
    ).inc()


# 사용자 만족도 관련 함수들 ###
def record_user_feedback(feedback_type, label_type="production"):
    """사용자 피드백 기록"""
    metrics.user_feedback.labels(
        label_type=label_type, feedback_type=feedback_type
    ).inc()


# 전체 응답 시간 기록 함수
def record_total_response_time(label_type, duration, success=True):
    """전체 응답 시간 기록 + 직접 집계"""
    # 기존 메트릭 기록 (Prometheus용)
    success_status = "success" if success else "failure"
    # metrics.total_response_time.labels(label_type=label_type, success_status=success_status).observe(duration)
    # 직접 집계값 업데이트
    response_time_stats["total_sum"] += duration
    response_time_stats["total_count"] += 1
    # zone 구간: 5, 10, 15, 20, +Inf
    zones = [5, 10, 15, 20, float('inf')]
    for i, z in enumerate(zones):
        if duration <= z:
            response_time_stats["zone_counts"][i] += 1
            break

# 주간 응답 횟수 기록 함수
def record_weekly_response(label_type, success=True):
    """주간 응답 횟수 기록"""
    week = time.strftime("%Y-W%U")
    day_of_week = time.strftime("%A")
    metrics.weekly_responses.labels(
        week=week, label_type=label_type, day_of_week=day_of_week
    ).inc()


### 프로메테우스 쿼리 함수 ###
def query_prometheus(query):
    """프로메테우스 API를 통한 쿼리 실행"""
    try:
        logging.info(f"프로메테우스 쿼리 실행: {query}")
        # 프로메테우스 API 요청
        response = requests.get(
            PROMETHEUS_CONFIG["query_url"],
            params={"query": query},
            timeout=PROMETHEUS_CONFIG["timeout"],
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                logging.info(
                    f"✅ 프로메테우스 쿼리 성공: {len(data['data']['result'])}개의 결과"
                )
                return data["data"]["result"]
            else:
                logging.error(
                    f"❌ 프로메테우스 쿼리 실패: {data.get('error', '알 수 없는 오류')}"
                )
                return []
        else:
            logging.error(f"❌ 프로메테우스 API 요청 실패: HTTP {response.status_code}")
            return []
    except requests.RequestException as e:
        logging.error(f"❌ 프로메테우스 API 요청 중 오류 발생: {e}")
        return None
    except Exception as e:
        logging.error(f"❌ 예상치 못한 오류: {e}")
        return None


### API용 데이터 조회 함수들###
def get_daily_conversations():
    """일일 대화 수 조회(프로메테우스 쿼리)"""
    try:
        today = time.strftime("%Y-%m-%d")
        yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))

        # 오늘과 어제의 대화 수 조회
        today_query = f'sum(chatbot_daily_conversations_total{{date="{today}"}})'
        yesterday_query = (
            f'sum(chatbot_daily_conversations_total{{date="{yesterday}"}})'
        )

        today_result = query_prometheus(today_query)
        yesterday_result = query_prometheus(yesterday_query)

        today_count = float(today_result[0]["value"][1]) if today_result else 0
        yesterday_count = (
            float(yesterday_result[0]["value"][1]) if yesterday_result else 0
        )
        # 증가율 계산
        if yesterday_count > 0:
            increase_rate = ((today_count - yesterday_count) / yesterday_count) * 100
        else:
            increase_rate = 100 if today_count > 0 else 0
        return {"count": int(today_count), "increase": round(increase_rate, 2)}
    except Exception as e:
        print(f"일일 대화 수 조회 오류: {e}")
        return {"count": 0, "increase": 0}

# 답변 성공률 조회
def get_success_rate():
    """답변 성공률 조회"""
    try:
        # 이번 주 성공/실패 계산
        current_success_query = "sum(chatbot_response_success_total)"
        current_failure_query = "sum(chatbot_response_failure_total)"
        current_success_result = query_prometheus(current_success_query)
        current_failure_result = query_prometheus(current_failure_query)
        current_success = (
            float(current_success_result[0]["value"][1])
            if current_success_result
            else 0
        )
        current_failure = (
            float(current_failure_result[0]["value"][1])
            if current_failure_result
            else 0
        )

        # 저번 주 성공률 계산 (7일 전 시점의 누적값과 현재 누적값의 차이)
        seven_days_ago = int(time.time() - 7 * 86400)
        past_success_query = f"sum(chatbot_response_success_total @ {seven_days_ago})"
        past_failure_query = f"sum(chatbot_response_failure_total @ {seven_days_ago})"
        past_success_result = query_prometheus(past_success_query)
        past_failure_result = query_prometheus(past_failure_query)
        past_success = (
            float(past_success_result[0]["value"][1]) if past_success_result else 0
        )
        past_failure = (
            float(past_failure_result[0]["value"][1]) if past_failure_result else 0
        )

        # 성공률 계산
        current_total = current_success + current_failure
        current_rate = (
            (current_success / current_total) * 100 if current_total > 0 else 0
        )
        past_total = past_success + past_failure
        past_rate = (past_success / past_total) * 100 if past_total > 0 else 0
        # 증가율 계산
        if past_rate > 0:
            increase_rate = ((current_rate - past_rate) / past_rate) * 100
        else:
            increase_rate = 0
        return {"percent": round(current_rate, 2), "increase": round(increase_rate, 2)}
    except Exception as e:
        logging.error(f"답변 성공률 조회 오류: {e}")
        return {"percentage": 0, "increase": 0}


# 사용자 만족도 조회
def get_user_satisfaction():
    """사용자 만족도 조회"""
    try:
        # 현재 like/dislike 수
        current_likes_query = 'sum(chatbot_user_feedback_total{feedback_type="like"})'
        current_dislikes_query = (
            'sum(chatbot_user_feedback_total{feedback_type="dislike"})'
        )
        current_likes_result = query_prometheus(current_likes_query)
        current_dislikes_result = query_prometheus(current_dislikes_query)
        current_likes = (
            float(current_likes_result[0]["value"][1]) if current_likes_result else 0
        )
        current_dislikes = (
            float(current_dislikes_result[0]["value"][1])
            if current_dislikes_result
            else 0
        )

        # 7일 전 시점 데이터
        seven_days_ago = int(time.time() - 7 * 86400)
        past_likes_query = f'sum(chatbot_user_feedback_total{{feedback_type="like"}} @ {seven_days_ago})'
        past_dislikes_query = f'sum(chatbot_user_feedback_total{{feedback_type="dislike"}} @ {seven_days_ago})'
        past_likes_result = query_prometheus(past_likes_query)
        past_dislikes_result = query_prometheus(past_dislikes_query)
        past_likes = float(past_likes_result[0]["value"][1]) if past_likes_result else 0
        past_dislikes = (
            float(past_dislikes_result[0]["value"][1]) if past_dislikes_result else 0
        )

        # 만족도 계산
        current_total = current_likes + current_dislikes
        current_rate = (current_likes / current_total) * 100 if current_total > 0 else 0
        
        past_total = past_likes + past_dislikes
        past_rate = (past_likes / past_total) * 100 if past_total > 0 else 0

        # 증가율 계산
        if past_rate > 0:
            increase_rate = ((current_rate - past_rate) / past_rate) * 100
        else:
            increase_rate = 0

        return {"percent": round(current_rate, 2), "increase": round(increase_rate, 2)}
    except Exception as e:
        logging.error(f"사용자 만족도 조회 오류: {e}")
        return {"percent": 0, "increase": 0}


# 응답 시간 조회
def get_response_time_analysis():
    """응답 시간 분석"""
    try:
        # 저장된 값 불러오기
        save_sum = response_time_stats["total_sum"]
        save_count = response_time_stats["total_count"]
        save_zones = response_time_stats["zone_counts"]

        # 현재 서버 평균 응답 시간 계산
        sum_query = "sum(chatbot_total_response_time_seconds_sum)"
        count_query = "sum(chatbot_total_response_time_seconds_count)"

        sum_result = query_prometheus(sum_query)
        count_result = query_prometheus(count_query)
        current_sum = float(sum_result[0]["value"][1]) if sum_result else 0
        current_count = float(count_result[0]["value"][1]) if count_result else 0

        buckets = ["5.0", "10.0", "15.0", "20.0", "+Inf"]
        current_bucket_counts = []
        for bucket in buckets:
            bucket_query = (
                f'sum(chatbot_total_response_time_seconds_bucket{{le="{bucket}"}})'
            )
            bucket_result = query_prometheus(bucket_query)
            count = int(float(bucket_result[0]["value"][1])) if bucket_result else 0
            current_bucket_counts.append(count)

        current_zones = []
        for i in range(len(current_bucket_counts)):
            if i == 0:
                # 첫 번째 구간 (0-1초)
                current_zones.append(max(0, current_bucket_counts[i]))
            else:
                # 이후 구간 (현재 누적값 - 이전 누적값
                diff = current_bucket_counts[i] - current_bucket_counts[i - 1]
                current_zones.append(max(0, diff))
        # 마지막 +Inf 구간 제외하고 처음 5개 구간만 반환
        current_zones = current_zones[:5]

        # 저장된 값과 현재 값을 합산
        total_sum = save_sum + current_sum
        total_count = save_count + current_count
        total_zones = [save_zones[i] + current_zones[i] for i in range(5)]

        # 평균 계산
        avg_time = (total_sum / total_count) if total_count > 0 else 0

        return {"avg": round(avg_time, 2), "zones": total_zones}
    except Exception as e:
        logging.error(f"응답 시간 분석 오류: {e}")
        return {"avg": 0, "zones": [0, 0, 0, 0, 0]}


# 템플릿 사용 통계 조회
def get_template_usage():
    """프롬프트 템플릿 사용 통계"""
    try:
        templates = ["smalltalk", "org_chart", "form_request", "internal_rag", "faq"]
        counts = []

        for template in templates:
            query = f'sum(chatbot_prompt_template_usage_total{{template_type="{template}"}})'
            result = query_prometheus(query)
            count = int(float(result[0]["value"][1])) if result else 0
            counts.append(count)

        smalltalk_count = counts[0]
        org_chart_count = counts[1]
        form_request_count = counts[2]
        qna_count = counts[3] + counts[4]

        final_counts = [smalltalk_count, org_chart_count, form_request_count, qna_count]
        template_names = ["일상 대화", "조직도 조회", "양식 요청", "QnA"]

        # 전체 사용량 계산
        total_usage = sum(final_counts)

        # 퍼센트 계산
        percentages = []
        for count in final_counts:
            if total_usage > 0:
                percentage = round((count / total_usage) * 100, 1)
            else:
                percentage = 0.0
            percentages.append(percentage)

        return {
            "templates": template_names,
            "counts": final_counts,
            "percentages": percentages,
        }
    except Exception as e:
        logging.error(f"템플릿 사용 통계 오류: {e}")
        return {"templates": [], "counts": [], "percentages": []}


# 일주일간 응답 횟수
def get_week_response():
    """일주일간 응답 횟수"""
    try:
        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        values = []
        current_week = time.strftime("%Y-W%U")

        for day in days:
            query = f'sum(chatbot_weekly_responses_total{{week="{current_week}",day_of_week="{day}"}})'
            result = query_prometheus(query)
            value = int(float(result[0]["value"][1])) if result else 0
            values.append(value)

        return {"values": values}
    except Exception as e:
        logging.error(f"주간 응답 통계 오류: {e}")
        return {"values": [0] * 7}
