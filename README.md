# 🧾 영수증 자동 분석 앱

Streamlit과 OpenAI API를 사용하여 영수증 텍스트를 자동으로 분석하고 정보를 추출해 보여주는 웹 앱입니다.


##  목표와 필요성
자연어로 입력한 영수증에서 데이터를 추출하여 여러 가지 정보를 보여 주는 것을 목표로 합니다.
영수증 사용 내역을 각종 통계(전체 지출, 이번 달 지출, 최다 카테고리, 카테고리별 지출 등)와 함께 한눈에 볼 수 있게 합니다.


## ✨ 주요 기능

- 📝 영수증 텍스트 입력
- 🤖 AI 기반 자동 정보 추출 (날짜, 상호명, 금액, 카테고리)
- 📊 영수증 목록 관리 및 통계 제공
- 🔄 세션 기반 데이터 누적 저장
- 🥧 카테고리별 비율 파이차트
- 📈 일자별 지출 추이 라인차트

## 🧠 핵심 로직

1. 사용자 입력을 수집하고 AI 분석을 요청
2. 결과를 JSON으로 파싱하고 필드 검증
3. 실패 시 로컬 fallback 추출로 전환
4. session_state에 누적 저장 후 통계/차트 갱신

### 데이터 스키마(요약)

Receipt
- id: string (UUID)
- date: YYYY-MM-DD
- store: string
- amount: int
- category: 식비|교통비|쇼핑|엔터테인먼트|의료|교육|기타
- items: [{name, qty, price}] (옵션)
- raw_text: string (옵션)
- source: manual|ocr|api
- created_at: ISO8601

### Pandas 분석 함수

- to_df: receipts -> DataFrame 변환
- calc_total: 총 지출 계산
- calc_daily: 일자별 합계 시계열
- calc_category: 카테고리별 합계
- calc_top_category: 최다 카테고리/금액
- summary_stats: 총액/건수/평균/최대

### FastAPI 엔드포인트

- POST /api/receipts
	- 영수증 저장
- GET /api/receipts
	- 목록 조회(기간/카테고리 필터)
- GET /api/receipts/stats
	- 기간별 통계 반환

## 🚀 설치 및 실행 방법

### 1. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env.example` 파일을 `.env`로 복사하고 OpenAI API 키를 입력하세요:

```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

`.env` 파일을 열고 API 키를 입력:
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

> OpenAI API 키는 https://platform.openai.com/api-keys 에서 발급받을 수 있습니다.

### 3. 앱 실행

```bash
streamlit run app.py
```
### 4. API 서버 실행(선택)

```bash
uvicorn api_app:app --reload
```

브라우저에서 자동으로 `http://localhost:8501`이 열립니다.

## 📖 사용 방법

1. **영수증 입력**: 왼쪽 입력창에 영수증 내용을 입력하거나 붙여넣기
2. **분석하기**: '분석하기' 버튼을 클릭하여 AI가 정보 추출
3. **리스트 추가**: 추출된 정보를 확인하고 '리스트에 추가' 버튼 클릭
4. **결과 확인**: 오른쪽에서 저장된 영수증 목록 확인
5. **다운로드**: CSV 파일로 다운로드하여 엑셀 등에서 활용

## 📋 입력 예시

```
스타벅스 강남점
2026-02-24
아메리카노 4,500원
카페라떼 5,000원
합계: 9,500원
```

## 🗂️ 추출되는 정보

- **날짜 (date)**: YYYY-MM-DD 형식
- **상호명 (store)**: 가게 이름
- **금액 (amount)**: 숫자만 추출
- **카테고리 (category)**: 식비, 교통비, 쇼핑, 엔터테인먼트, 의료, 교육, 기타

## 🛠️ 기술 스택

- **Streamlit**: 웹 앱 프레임워크
- **OpenAI API**: GPT-4o-mini 모델 사용
- **Pandas**: 데이터 처리 및 CSV 변환
- **FastAPI**: REST API 서버
- **Plotly**: 시각화 차트
- **Python**: 3.8 이상

## 📁 프로젝트 구조

```
Project_J/
├── app.py              # Streamlit 앱 메인 파일
├── api_app.py           # FastAPI 서버
├── analytics.py         # Pandas 분석 유틸
├── schemas.py           # 데이터 스키마
├── requirements.txt    # 필요한 패키지 목록
├── .env.example        # 환경 변수 예시 파일
├── .env               # 환경 변수 파일 (직접 생성)
├── tests/              # pytest 테스트
└── README.md          # 프로젝트 설명서
```

## ⚠️ 주의사항

- OpenAI API 사용 시 비용이 발생할 수 있습니다
- API 키는 절대 공개하지 마세요
- `.env` 파일은 `.gitignore`에 추가하여 버전 관리에서 제외하세요

## 📝 라이선스

MIT License
