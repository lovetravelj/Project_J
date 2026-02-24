# -*- coding: utf-8 -*-
import streamlit as st
import openai
import json
import pandas as pd
from datetime import datetime
import os
import sys
import locale
import logging
import warnings
import traceback
import re
import time
import plotly.express as px
from dotenv import load_dotenv
from analytics import to_df, calc_daily, calc_category, calc_monthly, calc_top_category

# 모든 경고 무시
warnings.filterwarnings('ignore')

# UTF-8 인코딩 강제 설정
if sys.platform.startswith('win'):
    # Windows 환경에서 UTF-8 설정
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except:
            pass

# 환경 변수로 UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# 전체 로깅 레벨을 CRITICAL로 설정 (ASCII 인코딩 오류 완전 방지)
logging.basicConfig(level=logging.CRITICAL)
for logger_name in ['openai', 'httpx', 'httpcore', 'urllib3', 'asyncio']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)
    logging.getLogger(logger_name).propagate = False

# .env 파일 로드
load_dotenv()

# OpenAI 환경 변수 검증 (ASCII-only)
startup_warnings = []

def _validate_ascii_env(name):
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip().replace("\ufeff", "")
    try:
        value.encode("ascii")
        return value
    except UnicodeEncodeError:
        startup_warnings.append(
            f"환경 변수 {name}에 ASCII가 아닌 문자가 포함되어 OpenAI 호출을 중단합니다."
        )
        return None

api_key = _validate_ascii_env("OPENAI_API_KEY")
openai_org = _validate_ascii_env("OPENAI_ORGANIZATION")
openai_project = _validate_ascii_env("OPENAI_PROJECT")

# OpenAI 클라이언트 초기화 (httpcore 로깅 완전 비활성화)
client = None
if api_key:
    try:
        import httpx
        # httpx 클라이언트를 커스터마이징하여 로깅 비활성화
        http_client = httpx.Client()
        client = openai.OpenAI(
            api_key=api_key,
            organization=openai_org,
            project=openai_project,
            http_client=http_client
        )
    except Exception:
        # 기본 클라이언트 사용
        client = openai.OpenAI(
            api_key=api_key,
            organization=openai_org,
            project=openai_project
        )

def extract_receipt_info(receipt_text):
    """
    OpenAI API를 사용하여 영수증 텍스트에서 정보 추출
    
    Args:
        receipt_text: 영수증 텍스트
        
    Returns:
        dict: 날짜, 상호명, 금액, 카테고리를 포함한 딕셔너리
    """
    def log_error(trace_text):
        try:
            with open("error.log", "a", encoding="utf-8") as f:
                f.write("\n" + "=" * 80 + "\n")
                f.write(trace_text)
        except Exception:
            pass

    def fallback_extract(text):
        # Basic fallback parsing without external calls.
        text = str(text)
        date_match = re.search(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", text)
        if date_match:
            yyyy, mm, dd = date_match.groups()
            date = f"{yyyy}-{int(mm):02d}-{int(dd):02d}"
        else:
            date = datetime.now().strftime('%Y-%m-%d')

        numbers = re.findall(r"\d{1,3}(?:,\d{3})+|\d+", text)
        amounts = [int(n.replace(",", "")) for n in numbers] if numbers else [0]
        amount = max(amounts) if amounts else 0

        first_line = text.strip().splitlines()[0] if text.strip() else "Unknown"
        store = first_line.strip() if first_line else "Unknown"

        category = "other"
        lower = text.lower()
        if any(k in lower for k in ["coffee", "cafe", "meal", "food", "restaurant", "dining"]):
            category = "food"
        elif any(k in lower for k in ["bus", "subway", "taxi", "transport", "train"]):
            category = "transport"
        elif any(k in lower for k in ["mall", "shop", "store", "clothing", "market"]):
            category = "shopping"
        elif any(k in lower for k in ["movie", "cinema", "game", "entertain"]):
            category = "entertainment"
        elif any(k in lower for k in ["pharmacy", "hospital", "clinic", "medical"]):
            category = "medical"
        elif any(k in lower for k in ["school", "academy", "education", "course"]):
            category = "education"

        return {
            "date": date,
            "store": store or "Unknown",
            "amount": amount,
            "category": category
        }

    try:
        if client is None:
            st.error("OpenAI API 키 또는 관련 환경 변수에 문제가 있어 로컬 추출로 전환합니다.")
            return fallback_extract(receipt_text)
        # 문자열로 변환
        receipt_text = str(receipt_text)
        
        prompt = f"""
    Extract the following fields from the receipt text.
    Respond ONLY in JSON with the exact keys and no extra text.

    Receipt text:
    {receipt_text}

    Fields to extract:
    - date: YYYY-MM-DD (use today's date if missing)
    - store: store name
    - amount: number only (use 0 if missing)
    - category: one of food, transport, shopping, entertainment, medical, education, other

    JSON format:
    {{
        "date": "YYYY-MM-DD",
        "store": "store name",
        "amount": 0,
        "category": "food"
    }}
    """
        
        system_content = "You extract receipt fields and always return JSON only."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # JSON 파싱 시도
        try:
            # 코드 블록으로 감싸져 있을 수 있으므로 처리
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            result = json.loads(result_text.strip())
            
        except json.JSONDecodeError as je:
            st.error(f"❌ AI 응답을 JSON으로 파싱할 수 없습니다: {str(je)}")
            st.warning("AI가 올바른 JSON 형식으로 응답하지 않았습니다. 다시 시도해주세요.")
            st.text(f"AI 응답: {result_text[:200]}...")
            return None
        
        # 필수 필드 검증 및 기본값 설정
        # 1. 날짜가 없으면 오늘 날짜로 설정
        if not result.get('date') or result.get('date') == "":
            result['date'] = datetime.now().strftime('%Y-%m-%d')
            st.info("ℹ️ 날짜 정보가 없어 오늘 날짜로 설정되었습니다.")
        
        # 2. 금액이 없거나 0이면 경고
        if not result.get('amount') or result.get('amount') == 0:
            result['amount'] = 0
            st.warning("⚠️ 금액 정보를 찾을 수 없습니다. 수동으로 입력해주세요.")
            # 사용자에게 수동 입력 받기
            manual_amount = st.number_input(
                "💰 금액을 입력하세요:",
                min_value=0,
                value=0,
                step=100,
                key="manual_amount_input"
            )
            if manual_amount > 0:
                result['amount'] = int(manual_amount)
        
        # 3. 상호명이 없으면 기본값
        if not result.get('store') or result.get('store') == "":
            result['store'] = "미상"
            st.info("ℹ️ 상호명 정보가 없어 '미상'으로 설정되었습니다.")
        
        # 4. 카테고리가 없으면 기본값 및 영문 카테고리 매핑
        if not result.get('category') or result.get('category') == "":
            result['category'] = "기타"
            st.info("ℹ️ 카테고리 정보가 없어 '기타'로 설정되었습니다.")
        else:
            category_map = {
                "food": "식비",
                "transport": "교통비",
                "shopping": "쇼핑",
                "entertainment": "엔터테인먼트",
                "medical": "의료",
                "education": "교육",
                "other": "기타"
            }
            category_key = str(result['category']).strip().lower()
            result['category'] = category_map.get(category_key, result['category'])
        
        # 5. amount가 숫자인지 확인
        try:
            result['amount'] = int(result['amount'])
        except (ValueError, TypeError):
            st.error("❌ 금액 형식이 올바르지 않습니다.")
            result['amount'] = 0
            st.warning("⚠️ 금액을 0으로 설정했습니다. 수동으로 수정해주세요.")
        
        return result
        
    except openai.APIError as api_err:
        log_error(traceback.format_exc())
        st.error("OpenAI API error. Using local fallback extraction.")
        return fallback_extract(receipt_text)
    except Exception:
        log_error(traceback.format_exc())
        st.error("Unexpected error. Using local fallback extraction.")
        return fallback_extract(receipt_text)

def main():
    st.set_page_config(
        page_title="영수증 분석 앱",
        page_icon="🧾",
        layout="wide"
    )
    
    st.title("🧾 영수증 자동 분석 앱")
    st.markdown("영수증 내역을 입력하면 AI가 자동으로 정보를 추출합니다.")

    if startup_warnings:
        for warn in startup_warnings:
            st.warning(warn)
    
    # session_state 초기화
    if 'receipts' not in st.session_state:
        st.session_state.receipts = []
    
    # 사이드바 - 영수증 입력
    with st.sidebar:
        st.header("📝 영수증 입력")

        # 초기화 요청 처리 (위젯 생성 전에 수행)
        if st.session_state.get('clear_form', False):
            st.session_state.pop('receipt_input', None)
            st.session_state.analysis_result = None
            st.session_state.clear_form = False

        # 영수증 예시
        with st.expander("💡 예시 보기"):
            st.code("""스타벅스 강남점
2026-02-24
아메리카노 4,500원
카페라떼 5,000원
합계: 9,500원""")

        with st.form("receipt_form", clear_on_submit=False):
            receipt_text = st.text_area(
                "🧾 영수증 내역을 입력하세요:",
                height=250,
                placeholder="영수증 내용을 입력하거나 붙여넣으세요...",
                key="receipt_input"
            )

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                analyze_button = st.form_submit_button("🔍 분석", use_container_width=True)

            with col_btn2:
                clear_button = st.form_submit_button("🔄 초기화", use_container_width=True)

        if clear_button:
            st.session_state.clear_form = True
            st.rerun()

        # 분석 결과 표시 영역
        if 'analysis_result' not in st.session_state:
            st.session_state.analysis_result = None

        if analyze_button:
            if not receipt_text.strip():
                st.warning("⚠️ 영수증 내역을 입력해주세요.")
            else:
                with st.spinner("🤖 AI가 분석 중입니다..."):
                    result = extract_receipt_info(receipt_text)

                    if result:
                        st.session_state.analysis_result = result
                        success_placeholder = st.empty()
                        success_placeholder.success("✅ 분석 완료!")
                        time.sleep(3)
                        success_placeholder.empty()
        
        # 분석 결과가 있으면 표시
        if st.session_state.analysis_result:
            st.divider()
            st.subheader("📊 추출된 정보")
            result = st.session_state.analysis_result
            
            st.markdown(f"**📅 날짜:** {result['date']}")
            st.markdown(f"**🏪 상호명:** {result['store']}")
            st.markdown(f"**💰 금액:** {result['amount']:,}원")
            st.markdown(f"**📂 카테고리:** {result['category']}")
            
            # 추가 버튼
            if st.button("➕ 리스트에 추가", use_container_width=True, type="primary", key="add_btn"):
                st.session_state.receipts.append(result)
                st.session_state.clear_form = True
                st.session_state.analysis_result = None
                st.success("✅ 리스트에 추가되었습니다!")
                st.rerun()
        
        st.divider()
        
        # 전체 삭제 버튼
        if st.session_state.receipts:
            if st.button("🗑️ 전체 삭제", use_container_width=True, type="secondary"):
                st.session_state.receipts = []
                st.rerun()
    
    # 메인 화면
    if st.session_state.receipts:
        # DataFrame 생성
        df = to_df(st.session_state.receipts)
        
        # 전체 통계 계산
        total_amount = int(df['amount'].sum()) if not df.empty else 0
        total_count = len(df)
        
        # 이번 달 계산
        current_month = datetime.now().strftime('%Y-%m')
        df['month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
        month_receipts = df[df['month'] == current_month]
        
        # 오늘 등록한 영수증
        today = datetime.now().strftime('%Y-%m-%d')
        today_receipts = df[df['date'] == today]
        
        # 상단 4개 메트릭
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💵 전체 총 지출",
                value=f"{total_amount:,}원",
                delta=f"{total_count}건"
            )
        
        with col2:
            month_total = month_receipts['amount'].sum() if not month_receipts.empty else 0
            st.metric(
                label="💳 이번 달 지출",
                value=f"{month_total:,}원",
                delta=f"{len(month_receipts)}건"
            )
        
        with col3:
            if not df.empty:
                top_category, top_amount = calc_top_category(df)
                st.metric(
                    label="🏆 최다 카테고리",
                    value=top_category,
                    delta=f"{top_amount:,}원"
                )
            else:
                st.metric(label="🏆 최다 카테고리", value="-")
        
        with col4:
            today_count = len(today_receipts)
            today_amount = today_receipts['amount'].sum() if not today_receipts.empty else 0
            st.metric(
                label="📅 오늘 등록",
                value=f"{today_count}건",
                delta=f"{today_amount:,}원" if today_count > 0 else None
            )
        
        st.divider()
        
        # 차트와 테이블
        tab1, tab2, tab3 = st.tabs(["📊 차트", "📋 데이터 테이블", "📈 월별 통계"])
        
        with tab1:
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("🍰 카테고리별 지출 비율")
                category_sum = calc_category(df)
                pastel_colors = [
                    "#A7C7E7", "#FFD1DC", "#B5EAD7", "#FFDAC1", "#C7CEEA",
                    "#E2F0CB", "#FFB7B2", "#B5B9FF"
                ]
                pie_df = category_sum.reset_index()
                pie_df.columns = ['category', 'amount']
                fig_pie = px.pie(
                    pie_df,
                    names='category',
                    values='amount',
                    color='category',
                    color_discrete_sequence=pastel_colors,
                    hole=0.4
                )
                fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_pie, use_container_width=True)
                
                # 카테고리 상세
                st.markdown("#### 📂 카테고리 상세")
                for cat, amt in category_sum.items():
                    count = len(df[df['category'] == cat])
                    st.markdown(f"**{cat}**: {amt:,}원 ({count}건)")
            
            with col_chart2:
                st.subheader("📈 일자별 지출 추이")
                daily_sum = calc_daily(df)
                line_df = daily_sum.reset_index()
                line_df.columns = ['date', 'amount']
                fig_line = px.line(
                    line_df,
                    x='date',
                    y='amount',
                    markers=True,
                    color_discrete_sequence=["#A7C7E7"]
                )
                fig_line.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    xaxis_title="Date",
                    yaxis_title="Amount"
                )
                st.plotly_chart(fig_line, use_container_width=True)
                
                # 최근 7일 통계
                st.markdown("#### 📊 최근 7일 통계")
                recent_7days = daily_sum.tail(7)
                if not recent_7days.empty:
                    avg_amount = recent_7days.mean()
                    st.metric("평균 일일 지출", f"{avg_amount:,.0f}원")
                    st.metric("최고 지출일", f"{recent_7days.max():,.0f}원")
        
        with tab2:
            st.subheader("📋 전체 영수증 목록")
            
            # 정렬 옵션
            col_sort1, col_sort2, col_sort3 = st.columns([2, 2, 6])
            with col_sort1:
                sort_by = st.selectbox("정렬 기준", ["날짜", "금액", "카테고리", "상호명"])
            with col_sort2:
                sort_order = st.selectbox("정렬 순서", ["내림차순", "오름차순"])
            
            # 데이터 정렬
            display_df = df.copy()
            sort_column_map = {"날짜": "date", "금액": "amount", "카테고리": "category", "상호명": "store"}
            display_df = display_df.sort_values(
                by=sort_column_map[sort_by],
                ascending=(sort_order == "오름차순")
            )
            
            # 금액 포맷팅
            display_df['amount_formatted'] = display_df['amount'].apply(lambda x: f"{x:,}원")
            
            # 열 순서 재정렬
            display_df = display_df[['date', 'store', 'amount_formatted', 'category']]
            display_df.columns = ['📅 날짜', '🏪 상호명', '💰 금액', '📂 카테고리']
            
            # 인덱스 재설정
            display_df = display_df.reset_index(drop=True)
            display_df.index = display_df.index + 1
            
            # 테이블 표시
            st.dataframe(display_df, use_container_width=True, height=400)
            
            # 통계 정보
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            with col_stat1:
                st.metric("📊 총 건수", f"{len(df)}건")
            with col_stat2:
                st.metric("💵 총 지출", f"{df['amount'].sum():,}원")
            with col_stat3:
                st.metric("📊 평균 지출", f"{df['amount'].mean():,.0f}원")
            with col_stat4:
                st.metric("🔝 최고 지출", f"{df['amount'].max():,}원")
            
            # CSV 다운로드 버튼
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 CSV 다운로드",
                data=csv,
                file_name=f"receipts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with tab3:
            st.subheader("📈 월별 지출 분석")
            
            # 월별 통계
            monthly_sum = df.groupby('month')['amount'].agg(['sum', 'count', 'mean']).sort_index(ascending=False)
            monthly_sum.columns = ['총 지출', '건수', '평균 지출']
            monthly_sum['총 지출'] = monthly_sum['총 지출'].apply(lambda x: f"{x:,}원")
            monthly_sum['평균 지출'] = monthly_sum['평균 지출'].apply(lambda x: f"{x:,.0f}원")
            
            st.dataframe(monthly_sum, use_container_width=True)
            
            # 월별 차트
            st.subheader("📊 월별 지출 추이")
            monthly_chart = calc_monthly(df)
            st.bar_chart(monthly_chart)
            
            # 카테고리별 월별 분석
            st.subheader("📂 월별 카테고리 분석")
            pivot_table = df.pivot_table(
                values='amount',
                index='month',
                columns='category',
                aggfunc='sum',
                fill_value=0
            ).sort_index(ascending=False)
            
            # 포맷팅
            pivot_display = pivot_table.copy()
            for col in pivot_display.columns:
                pivot_display[col] = pivot_display[col].apply(lambda x: f"{x:,}원" if x > 0 else "-")
            
            st.dataframe(pivot_display, use_container_width=True)
    
    else:
        # 데이터가 없을 때
        st.info("📝 왼쪽 사이드바에서 영수증을 입력하고 분석해보세요!")
        
        st.markdown("""
        ### 💡 사용 방법
        1. **📝 왼쪽 사이드바**에서 영수증 내용을 입력하세요
        2. **🔍 분석 버튼**을 클릭하여 AI가 정보를 추출하게 하세요
        3. **➕ 리스트에 추가** 버튼으로 저장하세요
        4. **📊 메인 화면**에서 차트와 통계를 확인하세요
        
        ### 🎯 주요 기능
        - 🤖 **AI 자동 분석**: 날짜, 상호명, 금액, 카테고리 자동 추출
        - 📊 **실시간 통계**: 이번 달 지출, 카테고리별 분석, 일별 추이
        - 📈 **시각화**: 다양한 차트와 그래프로 지출 패턴 파악
        - 💾 **데이터 관리**: CSV 다운로드 및 전체 삭제 기능
        """)

if __name__ == "__main__":
    main()
