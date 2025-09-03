from prometheus_client import Counter, Histogram, Gauge

### 매트릭 정의 ###
# 일일 대화 수 
daily_conversations = Counter(
    'chatbot_daily_conversations_total',
    'Total number of daily conversations',
    ['date','language']
)

# 답변 성공률
response_success = Counter(
    'chatbot_response_success_total',
    'Total number of successful responses',
    ['label_type','confidence_level']
)

# 답변 실패율
response_failure = Counter(
    'chatbot_response_failure_total',
    'Total number of failed responses',
    ['label_type', 'error_type']
)

# 사용자 만족도
user_feedback= Counter(
    'chatbot_user_feedback_total',
    'Total number of user feedback ratings',
    ['label_type', 'feedback_type']
)

# 응답 시간 분석 - 각 처리 단계별 응답 시간
response_time = Histogram(
    'chatbot_response_time_seconds',
    'Response time in seconds for each processing stage',
    ['label_type', 'processing_stage'],
    buckets=[0.1,0.25,0.5,0.75,1,2,3,5,10,15,20,30]
)

# 전체 응답 시간
total_response_time = Histogram(
    'chatbot_total_response_time_seconds',
    'Total response time in seconds',
    ['label_type', 'success_status'],
    buckets=[0.5, 1.0, 2.0,5.0,10.0,15.0,30.0,60.0]
)

# 평균 응답 시간
average_response_time = Gauge(
    'chatbot_average_response_time_seconds',
    'Average response time in seconds',
    ['label_type', 'time_window']
)


# 프롬프트 템플릿 사용 통계
prompt_template_usage = Counter(
    'chatbot_prompt_template_usage_total',
    'Usage count of prompt templates',
    ['template_type', 'label_type']
)

# 일주일간 응답 횟수 통계
weekly_responses = Counter(
    'chatbot_weekly_responses_total',
    'Total number of responses per week',
    ['week','label_type','day_of_week']
)

# metrics 객체 생성 (이 부분을 추가!)
class ChatbotMetrics:
    def __init__(self):
        self.daily_conversations = daily_conversations
        self.response_success = response_success
        self.response_failure = response_failure
        self.user_feedback = user_feedback
        self.response_time = response_time
        self.total_response_time = total_response_time
        self.average_response_time = average_response_time
        self.prompt_template_usage = prompt_template_usage
        self.weekly_responses = weekly_responses

# 전역 metrics 객체 생성
metrics = ChatbotMetrics()