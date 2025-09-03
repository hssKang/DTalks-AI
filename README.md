## Commit Type

- `feat` : 새로운 기능 구현
- `fix` : 버그 및 오류 해결
- `refactor` : 코드 리팩토링
- `rename` : 파일이나 폴더명 수정
- `chore` : 버전 코드, 패키지 구조, 함수 및 변수명 변경 등의 작은 작업
- `mod` : 코드 및 내부 파일 수정
- `add` : feat 이외의 부수적인 코드, 파일, 라이브러리 추가
- `del` : 불필요한 코드나 파일 삭제
- `ui` :  UI 관련 작업
- `hotfix` : 배포된 버전에 이슈 발생 시, 긴급하게 수정 작업
- `docs` : README나 Wiki 등의 문서 작업
- `merge` : 서로 다른 브랜치 간의 병합
- `comment` : 필요한 주석 추가 및 변경
  
[type] #Issue Number 제목(작업 내용)  
	
ex) [feat] #Issue Number ~~~한 기능 구현 

-----------------------------------------------------------------------------

## 파일 위치

- `dataset` : 모델 학습용 데이터
- `src` : 모든 소스 코드
- `src\utils` : 본 기능을 서포팅 할 코드 (DB, Monitoring 등)
- `src\layer\guardrail` : 프롬프트 가드레일 부분
- `src\layer\filter` : 프롬프트 템플릿 필터 부분
- `src\prompt` : 프롬프트 템플릿 부분
- `src\LLM` : LLM와 실제로 통신할 부분
