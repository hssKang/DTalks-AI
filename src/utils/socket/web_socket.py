import websocket
import ssl
import time
import threading
import random
import requests
import os
from dotenv import load_dotenv
import logging


import src.layers.guardrail.guardrail as guardrail
import src.utils.tools.translate as translate
import src.layers.filter.total_model as filter
import src.layers.prompt.prompt_smalltalk as prompt_smalltalk
import src.layers.prompt.prompt_internal as prompt_internal
import src.layers.prompt.member_prompt as prompt_member
import src.layers.prompt.faq_prompt as prompt_faq
import src.layers.prompt.template_prompt as prompt_template
import src.layers.LLM.bedrock_model as bedrock_model
import src.utils.database.redis_caching as redis_caching
import src.layers.monitoring.monitoring as monitoring
import src.utils.tools.context_manager as context_manager
import src.utils.socket.json_template as json_template
from src.layers.filter.total_model import update_feedback

load_dotenv()
bedrock_client = bedrock_model.setup_bedrock()
redis_caching.configure_redis()

FEEDBACK_PERCENT = 0.1


class WebSocketClient:
    def __init__(self, url, bot_token, webhook_url=None):
        self.url = url
        self.bot_token = bot_token  # WebSocket 연결용 토큰
        self.webhook_url = webhook_url  # Webhook URL (이미 토큰이 포함됨)
        self.ws = None
        self.ping_thread = None
        self.input_thread = None
        self.running = False
        self.retry_count = 0
        self.max_retries = 5
        self.connection_failed = False  # 연결 실패 플래그 추가
        self.pre_chat = {}
        self.pre_label = {}

    def pipeline(self, input_text, user_id="default_user"):
        start_time = time.time()

        # 변수 초기화
        filtered_label = "unknown"
        filtered_confidence = 0.0
        INPUT_LANG = "KO"

        try:
            # 번역 레이어
            translated_text, INPUT_LANG = translate.translater(input_text)
            if INPUT_LANG == "EN":
                INPUT_LANG = "EN-US"

            temp_text = "대화의 주제를 확인하는 중이에요"
            if INPUT_LANG != "KO":
                temp_text, _ = translate.translater(temp_text, INPUT_LANG)
            self.send_webhook_message("[SYSTEM] " + temp_text + "...")

            # 대화 수 기록
            monitoring.record_conversation(language=INPUT_LANG)

            # 가드레일 설정
            csv_file_path = "./dataset/chat_scenario_dataset.csv"
            groq_client, blacklist_keywords, blacklist_responses = (
                guardrail.setup_guardrail(csv_file_path)
            )

            final_response = guardrail.comprehensive_profanity_filter(
                input_text,
                blacklist_keywords,
                blacklist_responses,
                groq_client,
            )

            # 가드레일 필터링
            if "정상적인 대화입니다." != final_response:
                monitoring.record_success("guardrail_blocked", 1.0)
                monitoring.record_weekly_response("guardrail", success=True)

                # 전체 응답 시간 기록 (실패)
                total_duration = time.time() - start_time
                monitoring.record_total_response_time(
                    "guardrail", total_duration, success=True
                )

                if INPUT_LANG != "KO":
                    final_response, _ = translate.translater(final_response, INPUT_LANG)

                return final_response, None

            # 관련 컨텍스트 찾기 (프롬프트 생성 전에 수행)
            related_context = context_manager.find_related_context(
                translated_text,  # 번역된 텍스트 사용
                user_id,
                bedrock_client,
            )

            # 필터 레이어
            filtered_text = filter.hybrid_predict(translated_text, k=1)
            print(filtered_text)

            if filtered_text:
                filtered_label = filtered_text[0][0]  # 필터링된 라벨
                filtered_confidence = filtered_text[1][0]  # 필터링된 신뢰도

                if filtered_confidence <= 0.6 and not related_context:
                    # 전체 응답 시간 기록 (실패)
                    total_duration = time.time() - start_time
                    monitoring.record_total_response_time(
                        filtered_label, total_duration, success=False
                    )
                    low_confidence_response = "좀 더 구체적으로 말씀해 주시겠어요?"
                    # 기억 추가
                    context_manager.add_to_history(
                        user_id, input_text, low_confidence_response
                    )
                    if INPUT_LANG != "KO":
                        low_confidence_response, _ = translate.translater(
                            low_confidence_response, INPUT_LANG
                        )
                    return low_confidence_response, None

            # 캐쉬 확인
            url_data = None
            temp_text = "캐시를 확인하는 중이에요"
            if INPUT_LANG != "KO":
                temp_text, _ = translate.translater(temp_text, INPUT_LANG)
            self.send_webhook_message("[SYSTEM] " + temp_text + "...")

            if filtered_label != "__label__smalltalk":
                answer, _, url_data = redis_caching.search_cache(translated_text)
                if answer:
                    result, _ = translate.translater(answer, INPUT_LANG)

                    # 캐시 히트 시 성공 기록
                    monitoring.record_success(filtered_label, filtered_confidence)
                    monitoring.record_weekly_response(filtered_label, success=True)

                    # 전체 응답 시간 기록 (성공)
                    total_duration = time.time() - start_time
                    monitoring.record_total_response_time(
                        filtered_label, total_duration, success=True
                    )

                    return result, url_data

            # 컨텍스트를 포함한 프롬프트 생성
            if related_context:
                prompt_text = context_manager.build_context_prompt(
                    input_text, related_context
                )

            # 프롬프트 레이어
            elif "__label__smalltalk" == filtered_label:
                prompt_text = prompt_smalltalk.build_smalltalk_prompt(input_text)
                monitoring.record_prompt_usage("smalltalk", filtered_label)
            elif "__label__org_chart" == filtered_label:
                prompt_text = prompt_member.make_prompt(input_text)
                monitoring.record_prompt_usage("org_chart", filtered_label)
            elif "__label__form_request" == filtered_label:
                prompt_text, url_data = prompt_template.make_prompt(input_text)
                monitoring.record_prompt_usage("form_request", filtered_label)
            elif "__label__internal_info" == filtered_label:
                tmp = prompt_faq.find_faq_answer(input_text)
                if tmp["status"] == "fallback_to_rag":
                    prompt_text = prompt_internal.build_prompt(
                        input_text, user_id, auth=True
                    )
                    monitoring.record_prompt_usage("internal_rag", filtered_label)
                elif tmp["status"] == "success":
                    prompt_text = tmp["answer"]
                    monitoring.record_prompt_usage("faq", filtered_label)
                else:
                    temp_text = "관련된 정보를 찾을 수 없어요."
                    if INPUT_LANG != "KO":
                        temp_text, _ = translate.translater(temp_text, INPUT_LANG)
                    return temp_text, None
            else:
                prompt_text = input_text

            # LLM 레이어
            temp_text = "답변을 생성하는 중이에요"
            if INPUT_LANG != "KO":
                temp_text, _ = translate.translater(temp_text, INPUT_LANG)
            self.send_webhook_message("[SYSTEM] " + temp_text + "...")
            response = bedrock_model.call_model(bedrock_client, prompt_text)

            # 캐싱 저장
            if filtered_label != "__label__smalltalk":
                redis_caching.add_cache(translated_text, response, url_data)

            # 기억 추가
            context_manager.add_to_history(user_id, input_text, response)

            # 아웃풋에 대한 번역
            response, _ = translate.translater(response, INPUT_LANG)

            # 전체 응답 시간 기록(성공)
            total_duration = time.time() - start_time
            monitoring.record_total_response_time(
                filtered_label, total_duration, success=True
            )

            # 답변 성공률 기록
            monitoring.record_success(filtered_label, filtered_confidence)

            # 주간 응답 횟수 통계 기록
            monitoring.record_weekly_response(filtered_label, success=True)

            # 대화 기록
            self.pre_chat[user_id] = input_text
            self.pre_label[user_id] = filtered_label

            return response, url_data

        except Exception as e:
            # 에러 기록
            monitoring.record_failure(
                "system_error", getattr(locals(), "filtered_label", "unknown")
            )
            monitoring.record_weekly_response(
                getattr(locals(), "filtered_label", "unknown"), success=False
            )

            # 전체 응답 시간 기록 (실패)
            total_duration = time.time() - start_time
            monitoring.record_total_response_time(
                filtered_label, total_duration, success=False
            )

            logging.error(f"챗봇 파이프라인 오류: {e}")
            raise

    def on_message(self, ws, message):
        try:
            import json

            # JSON 파싱 시도
            data = json.loads(message)
            print(f"\n[DEBUG] 받은 전체 데이터: {data}")  # 디버그용

            if isinstance(data, dict):
                # 이벤트 메시지 처리
                if "event" in data:
                    event_type = data.get("event")

                    if event_type == "message":
                        # 메시지 이벤트 상세 처리
                        msg_data = data.get("data", {})
                        user_name = msg_data.get("user", {}).get(
                            "display_name", "Unknown"
                        )
                        text = msg_data.get("text", "")
                        user_id = msg_data.get("user_id", None)
                        print(f"\n[{user_name} : {user_id}] {text}")

                        # 봇 메시지는 무시(루프 방지)
                        if msg_data.get("user", {}).get("is_bot"):
                            print("[INFO] Bot message ignored")
                        else:
                            """"""
                            if (
                                not text
                                or not isinstance(text, str)
                                or not text.strip()
                            ):
                                return {"text": "메시지를 찾을 수 없습니다."}

                            # FAQ 처리
                            if self.pre_label.get(user_id) == "faq-category":
                                if text.isdigit():
                                    category_id = int(text)
                                    self.send_blockkit_message(
                                        json_template.faq_question_template(category_id)
                                    )
                                    self.pre_label[user_id] = "faq-question"
                                else:
                                    self.send_webhook_message(
                                        '숫자만 입력해 주세요! 다른 대화가 하고 싶으시면 "@나가기"를 입력해주세요!'
                                    )
                            elif self.pre_label.get(user_id) == "faq-question":
                                if text.isdigit():
                                    question_id = int(text)
                                    self.send_blockkit_message(
                                        json_template.faq_answer_template(question_id)
                                    )
                                    self.pre_label[user_id] = None
                                else:
                                    self.send_webhook_message(
                                        '숫자만 입력해 주세요! 다른 대화가 하고 싶으시면 "@나가기"를 입력해주세요!'
                                    )

                            # @ 처리
                            elif isinstance(text, str) and text.startswith("@"):
                                if text == "@좋아요" or text == "@싫어요":
                                    if self.pre_label.get(user_id) is not None:
                                        return_message = "피드백 감사합니다! 더 좋은 서비스를 제공하기 위해 노력하겠습니다!"
                                        self.send_webhook_message(return_message)

                                        # 피드백 적용 후 재예측
                                        update_feedback(
                                            self.pre_chat[user_id],
                                            self.pre_label[user_id],
                                            is_correct=(
                                                True if text == "@좋아요" else False
                                            ),
                                            learning_rate=0.1,
                                        )

                                        monitoring.record_user_feedback(
                                            label_type=self.pre_label.get(user_id),
                                            feedback_type=(
                                                "like"
                                                if text == "@좋아요"
                                                else "dislike"
                                            ),
                                        )

                                        print(
                                            f"[{text} {self.pre_label.get(user_id)}] {self.pre_chat.get(user_id)} : 피드백 적용 완료"
                                        )
                                        self.pre_chat[user_id] = None

                                    else:
                                        return_message = (
                                            "평가를 진행하기 전에 대화를 먼저 해주세요!"
                                        )
                                        self.send_webhook_message(return_message)
                                elif text.upper() == "@FAQ":
                                    payload = json_template.faq_category_template()
                                    self.send_blockkit_message(payload)
                                    self.pre_label[user_id] = "faq-category"
                                elif text == "@나가기" and (
                                    self.pre_label.get(user_id) == "faq-category"
                                    or self.pre_label.get(user_id) == "faq-question"
                                ):
                                    self.send_webhook_message(
                                        "FAQ 대화가 종료되었습니다. 궁금한 것을 물어보세요!"
                                    )
                                    self.pre_label[user_id] = None

                                else:
                                    self.send_webhook_message(
                                        "오타가 있거나 언급된 내용을 지원하지 않습니다. 다시 입력해주세요!"
                                    )
                            else:

                                def worker():
                                    # pipeline 실행 후 send_webhook_message로 응답 전송
                                    response_text, url_data = self.pipeline(
                                        text, user_id
                                    )
                                    self.send_webhook_message(response_text)
                                    # URL 데이터가 있는 경우 메시지 전송
                                    if url_data != None and url_data["url"] != None:
                                        payload = json_template.url_template(url_data)
                                        self.send_blockkit_message(payload)
                                    # pipeline 작업이 끝난 뒤 10% 확률로 피드백 메시지 전송
                                    if random.random() < FEEDBACK_PERCENT:
                                        payload = json_template.feedback_template()
                                        self.send_blockkit_message(payload)
                                    else:
                                        self.pre_label[user_id] = None

                                threading.Thread(target=worker, daemon=True).start()

                    else:
                        print(f"\n[이벤트] {event_type}: {data}")
                else:
                    # 일반 데이터
                    print(f"\n[받은 데이터] {data}")
            else:
                print(f"\n[받은 데이터] {data}")
        except json.JSONDecodeError:
            # JSON이 아닌 경우 문자열로 처리
            print(f"\n[받은 메시지] {message}")

    def on_error(self, ws, error):
        print(f"\n[에러] {error}")
        print(f"[에러 타입] {type(error)}")
        if hasattr(error, "status_code"):
            print(f"[HTTP 상태 코드] {error.status_code}")
        if hasattr(error, "headers"):
            print(f"[응답 헤더] {error.headers}")

        # 연결 실패 플래그 설정
        self.connection_failed = True

    def on_pong(self, ws, data):
        """Pong 응답 처리"""
        print(
            f"[시스템] Pong received at {time.strftime('%H:%M:%S')}"
        )  # 간단한 pong 로그

    def on_close(self, ws, close_status_code, close_msg):
        print(f"\n[연결 종료] {close_status_code} - {close_msg}")
        self.running = False
        if self.ping_thread:
            self.ping_thread = None
        if self.input_thread:
            self.input_thread = None

        # 연결 실패 플래그 설정 (인증 실패 등의 경우)
        if (
            close_status_code is None or close_status_code != 1000
        ):  # 정상 종료가 아닌 경우
            self.connection_failed = True

    def on_open(self, ws):
        print("[연결 성공] WebSocket 연결이 열렸습니다!")
        print("메시지를 입력하세요 (종료: /quit)")
        print("=" * 50)
        self.running = True
        self.retry_count = 0

        # ping/pong 스레드 시작
        self.start_ping_thread()

        # CLI 입력 스레드 시작
        self.start_input_thread()

    def start_ping_thread(self):
        """30초마다 WebSocket Frame ping을 보내는 스레드 시작"""

        def ping_worker():
            while self.running and self.ws:
                try:
                    time.sleep(30)  # 30초 대기
                    if self.running and self.ws:
                        self.ws.send("", websocket.ABNF.OPCODE_PING)
                        print(f"\n[시스템] Ping sent at {time.strftime('%H:%M:%S')}")
                except Exception as e:
                    print(f"[에러] Ping 전송 실패: {e}")
                    # ping 실패해도 치명적이지 않으므로 계속 진행

        self.ping_thread = threading.Thread(target=ping_worker, daemon=True)
        self.ping_thread.start()

    def send_webhook_message(self, text):
        """Webhook을 통해 메시지 전송"""
        if not self.webhook_url:
            return False, "Webhook URL이 설정되지 않았습니다."

        try:
            payload = {"text": text}

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if response.status_code == 200:
                return True, "메시지 전송 성공"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"

        except requests.exceptions.RequestException as e:
            return False, f"요청 오류: {str(e)}"

    def send_blockkit_message(self, payload):
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if response.status_code == 200:
                return True, "메시지 전송 성공"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
        except requests.exceptions.RequestException as e:
            return False, f"요청 오류: {str(e)}"

    def start_input_thread(self):
        """사용자 입력을 받는 스레드 시작"""

        def input_worker():
            print("메시지 입력 (종료: /quit): ", end="", flush=True)
            while self.running and self.ws:
                try:
                    user_input = input().strip()

                    if user_input.lower() == "/quit":
                        print("연결을 종료합니다...")
                        self.close()
                        break
                    elif user_input:
                        # Webhook을 통해 메시지 전송
                        if self.webhook_url:
                            success, message = self.send_webhook_message(user_input)
                            if success:
                                print(f"[전송 성공] {user_input}")
                            else:
                                print(f"[전송 실패] {message}")
                        else:
                            print("[알림] Webhook URL이 설정되지 않았습니다.")
                            print(f"[입력한 메시지] {user_input}")

                        print("메시지 입력 (종료: /quit): ", end="", flush=True)
                    else:
                        print("메시지 입력 (종료: /quit): ", end="", flush=True)

                except EOFError:
                    # Ctrl+D나 입력 스트림이 닫힌 경우
                    break
                except Exception as e:
                    print(f"입력 오류: {e}")
                    break

        self.input_thread = threading.Thread(target=input_worker, daemon=True)
        self.input_thread.start()

    def connect(self):
        """WebSocket 연결 시작 (단순 버전 - connect_with_retry에서 사용)"""
        # connect_with_retry에서 직접 처리하므로 이 메서드는 단순화
        pass

    def connect_with_retry(self):
        """재연결 로직이 포함된 연결 메서드"""
        while self.retry_count < self.max_retries:
            try:
                print(
                    f"Connecting... (attempt {self.retry_count + 1}/{self.max_retries})"
                )

                # 연결 실패 플래그 초기화
                self.connection_failed = False

                # 토큰과 프로토콜 버전을 쿼리 파라미터로 추가
                if "?" in self.url:
                    connection_url = f"{self.url}&bot_token={self.bot_token}&vsn=2.0.0"
                else:
                    connection_url = f"{self.url}?bot_token={self.bot_token}&vsn=2.0.0"

                # Authorization 헤더도 추가 (이중 인증)
                headers = {"Authorization": f"Bearer {self.bot_token}"}

                # 디버그 출력 비활성화 (연결 확인 완료)
                websocket.enableTrace(False)
                self.ws = websocket.WebSocketApp(
                    connection_url,
                    header=headers,
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close,
                    on_pong=self.on_pong,
                )

                # SSL context 설정 (외부 HTTPS 연결용)
                self.ws.run_forever(
                    sslopt={
                        "cert_reqs": ssl.CERT_NONE
                    }  # WARNING: only for development!
                )

                # run_forever가 끝났는데 connection_failed가 True이면 재시도
                if self.connection_failed:
                    raise Exception("Connection failed")
                else:
                    break  # 성공하면 루프 종료

            except Exception as e:
                self.retry_count += 1
                print(f"Connection failed: {e}")

                if self.retry_count < self.max_retries:
                    # 3~10초 사이의 랜덤 대기 시간
                    retry_delay = random.uniform(3, 10)
                    print(f"Retrying in {retry_delay:.1f} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("Maximum retry attempts reached. Giving up.")

    def close(self):
        """연결 종료"""
        print("\n[시스템] 연결을 종료합니다...")
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                print(f"[에러] 소켓 종료 중 오류: {e}")
        # os._exit(0) 대신 메인 스레드에서만 종료


