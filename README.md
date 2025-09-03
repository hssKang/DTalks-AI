<div align="center">

<img width="75" alt="DTalks Logo" src="https://github.com/user-attachments/assets/8901ef46-86b0-44d8-b9f5-d32f831a5651" />

<h1>DTalks AI</h1>

<p><em>DTalks 웹 서비스를 위한 Python 기반 AI 리포지토리입니다</em></p>

<p>
  <img src="https://img.shields.io/badge/Qdrant-FF4B4B?style=for-the-badge&logo=qdrant&logoColor=white" alt="Qdrant"/>
  <img src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL"/>
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis"/>
  <img src="https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white" alt="Prometheus"/>
<br>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/AWS_Bedrock-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white" alt="AWS Bedrock"/>
<br>
  <img src="https://img.shields.io/badge/개발기간-2025.07~2025.08-7D57C1?style=for-the-badge&logo=github&logoColor=white" alt="개발기간"/>
</p>

</div>

<div align="left" display="flex">

<br>

### 📁 프로젝트 구조

```
├── dataset/                   # 모델 학습 및 테스트에 사용되는 다양한 데이터셋 파일들 (CSV, TXT, XLSX)
├── prometheus/                # Prometheus 설정 파일
├── layers/                    # 비즈니스 로직의 각 계층
│   ├── filter/                # 입력 데이터 필터링 및 전처리
│   ├── guardrail/             # LLM 응답 제어 및 안전 장치
│   ├── llm/                   # Bedrock 등 외부 LLM 연동
│   ├── monitoring/            # 애플리케이션 메트릭 수집
│   └── prompt/                # LLM 프롬프트 생성 및 관리
├── utils/                     # 공통 유틸리티
│   ├── database/              # MySQL, Qdrant, Redis 등 데이터베이스 처리
│   ├── socket/                # 웹소켓 통신
│   └── tools/                 # 임베딩, STT, 번역 등 보조 도구
└── YourAppApplication.java    # 메인 애플리케이션 클래스
```

<br>

### 🔧 주요 기능

- **사용자 관리**
  - 회원가입, 로그인, 권한 관리
  - 사용자 질문 유형 자동 감지 (type_detection.py)

- **이메일 서비스**
  - 이메일 인증 및 알림 발송 기능

- **보안**
  - JWT 기반 인증
  - 권한 기반 접근 제어
  - 콘텐츠 필터링(FastText 모델) 및 LLM 답변 제어(guardrail.py)

- **파일 관리**
  - 파일 업로드, 다운로드, 버전 관리
  - 음성(STT) 및 텍스트 벡터화
  - 멀티 모달 데이터 관리

- **FAQ 관리**
  - 카테고리별 FAQ CRUD
  - RAG 기반 검색 증강 생성
  - FAQ 벡터화(faq_vector.py) 및 다중 소스 활용

- **AI 통합**
  - LLM 기반 챗봇(AWS Bedrock 연동)
  - 동적 프롬프트 생성 및 대화 맥락 유지(context_manager.py)
  - 실시간 웹소켓 통신(json_template.py)
  - 사용자 피드백 수집(feedback_modal.py)
  - 벡터 DB(Qdrant) 활용 유사도 검색
  - 캐싱(Redis) 기반 성능 최적화
  - 음성 입력 처리(stt.py, voice_vector.py)
<img width="1176" height="656" alt="image" src="https://github.com/user-attachments/assets/1895825c-61d6-483e-9171-22e8a2387a89" />


<br>

### 👩🏻‍💻 Contributors

| <img width="160px" src="https://avatars.githubusercontent.com/hssKang" /> | <img width="160px" src="https://avatars.githubusercontent.com/ChoSunHyun" /> | <img width="160px" src="https://avatars.githubusercontent.com/juwonleee" /> | <img width="160px" src="https://avatars.githubusercontent.com/dogsub" /> |
|:---:|:---:|:---:|:---:|
| [강현승](https://github.com/hssKang) | [조선현](https://github.com/ChoSunHyun) | [이주원](https://github.com/juwonleee) | [김동섭](https://github.com/dogsub) |


</div> 
