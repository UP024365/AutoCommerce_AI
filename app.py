import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import time
import os
import yaml

# core 폴더의 함수들 불러오기
from core.collector import fetch_real_naver_products
from core.processor import refine_products_batch, calculate_selling_price
from core.register import bulk_register_to_coupang, get_registered_products, stop_selling_product

# 1. 페이지 설정
st.set_page_config(page_title="AutoSeller AI Pro", page_icon="☁️", layout="wide")

# 2. 세션 데이터 초기화
if 'products' not in st.session_state:
    st.session_state['products'] = []
if 'ai_chat_count' not in st.session_state:
    st.session_state['ai_chat_count'] = 0
if 'search_start' not in st.session_state:
    st.session_state['search_start'] = 1 
if 'remote_prods' not in st.session_state:
    st.session_state['remote_prods'] = []

# 3. 실시간 통계 계산 함수
def get_stats():
    data = st.session_state['products']
    total = len(data)
    registered = sum(1 for p in data if isinstance(p, dict) and p.get('상태') == "등록완료")
    margin = sum((p.get('판매가', 0) - p.get('원가', 0)) for p in data if isinstance(p, dict) and p.get('상태') == "등록완료")
    return total, registered, margin

total_count, reg_count, total_margin = get_stats()

# 4. 사이드바 메뉴 (모든 기능 통합)
with st.sidebar:
    st.title("☁️ AutoSeller AI")
    selected = option_menu(None, 
        ["대시보드", "상품 수동 등록", "등록 상품 관리", "AI 자동 크롤링", "자동 가격 설정", "마켓 자동 등록", "API 연동 설정"], 
        icons=['grid-fill', 'pencil-square', 'list-check', 'search', 'currency-dollar', 'cloud-arrow-up', 'gear'], 
        default_index=1)

# --- 공통 함수: 상세 정보 섹션 ---
def display_selected_product(df, selection):
    if selection and "rows" in selection and selection["rows"]:
        selected_row_index = selection["rows"][0]
        p = df.iloc[selected_row_index]
        st.markdown("---")
        st.write(f"### 🔍 상세 정보: {p.get('원본상품명', '이름 없음')}")
        col_img, col_info = st.columns([1, 2])
        with col_img:
            if p.get("이미지URL"):
                st.image(p["이미지URL"], width=300)
            else:
                st.info("이미지 없음")
        with col_info:
            st.write(f"**💰 원가:** ₩{p.get('원가', 0):,} | **🏷️ 상태:** {p.get('상태', '대기')}")
            if p.get('AI최적화명'):
                st.info(f"✨ AI 최적화명: {p['AI최적화명']}")
            if p.get('링크'):
                st.link_button("🔗 상품 페이지 이동", p["링크"])

# --- 화면별 로직 ---

if selected == "대시보드":
    st.subheader("📊 비즈니스 현황")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 관리 상품", f"{total_count:,}개")
    m2.metric("등록 완료", f"{reg_count:,}개")
    m3.metric("AI 자동 응대", f"{st.session_state['ai_chat_count']}건")
    m4.metric("오늘의 예상 마진", f"₩{total_margin:,}")
    
    if total_count > 0:
        st.divider()
        st.write("### 📦 전체 상품 리스트")
        df = pd.DataFrame(st.session_state['products'])
        st.dataframe(df[["상태", "원본상품명", "원가", "판매가"]], use_container_width=True, hide_index=True)

elif selected == "상품 수동 등록":
    st.subheader("📝 사촌(원재)님 전용 상품 입력창")
    with st.form("manual_input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            p_name = st.text_input("상품명 (도매처 이름)")
            p_cost = st.number_input("소싱 원가 (원)", min_value=0, value=10000)
        with col2:
            p_img = st.text_input("이미지 URL")
            p_cat = st.text_input("쿠팡 카테고리 코드", value="1001")
            
        if st.form_submit_button("➕ 상품 리스트에 추가"):
            new_item = {
                "원본상품명": p_name, "원가": p_cost, "이미지URL": p_img, "카테고리": p_cat,
                "상태": "수집완료", "선택": False, "판매가": calculate_selling_price(p_cost)
            }
            st.session_state['products'].append(new_item)
            st.success("대기열에 추가되었습니다.")
            st.rerun()

    if st.session_state['products']:
        st.divider()
        st.write("### 📋 현재 입력된 상품 대기열")
        df = pd.DataFrame(st.session_state['products'])
        st.dataframe(df[["상태", "원본상품명", "원가", "카테고리"]], use_container_width=True)

elif selected == "등록 상품 관리":
    st.subheader("📋 쿠팡 마켓 등록 현황 및 삭제")
    if st.button("🔄 쿠팡 실시간 목록 새로고침"):
        with st.spinner("조회 중..."):
            st.session_state['remote_prods'] = get_registered_products()
    
    if st.session_state.get('remote_prods'):
        df_remote = pd.DataFrame(st.session_state['remote_prods'])
        df_remote['선택'] = False
        edited = st.data_editor(df_remote, use_container_width=True, hide_index=True)
        
        target = edited[edited['선택'] == True]
        if not target.empty and st.button("🗑️ 선택 상품 판매 중지", type="primary"):
            for pid in target['sellerProductId']:
                stop_selling_product(pid)
            st.success("중지 처리가 완료되었습니다.")
            st.rerun()
        else:
            st.info("등록된 상품이 없습니다.")

elif selected == "AI 자동 크롤링":
    st.subheader("🔍 네이버 상품 참고 수집")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        keyword = st.text_input("수집 키워드", "캠핑용품")
    with c2:
        sort_type = st.selectbox("정렬", ["최신순", "가격 낮은순", "가격 높은순"])
    with c3:
        st.write(" ")
        if st.button("🔄 초기화", use_container_width=True):
            st.session_state['products'] = []
            st.rerun()

    if st.button("🚀 상품 10개 더 가져오기", type="primary", use_container_width=True):
        with st.spinner("불러오는 중..."):
            new_data = fetch_real_naver_products(keyword, 10, start=st.session_state['search_start'])
            if new_data:
                for item in new_data: item['선택'] = False
                st.session_state['products'].extend(new_data)
                st.session_state['search_start'] += 10
                st.rerun()

    if st.session_state['products']:
        df = pd.DataFrame(st.session_state['products'])
        if st.button("✨ 일괄 이름 최적화 (GPT-4o-mini)", type="secondary"):
            with st.spinner("AI 가공 중..."):
                refine_products_batch(st.session_state['products'])
            st.rerun()
        st.dataframe(df, use_container_width=True)

elif selected == "자동 가격 설정":
    st.subheader("💰 마진 및 판매가 일괄 설정")
    if not st.session_state['products']:
        st.warning("먼저 상품을 추가하세요.")
    else:
        with st.expander("📈 마진 계산 설정", expanded=True):
            col1, col2, col3 = st.columns(3)
            m_rate = st.slider("목표 마진율 (%)", 5, 50, 20) / 100
            f_rate = st.slider("쿠팡 수수료 (%)", 5, 15, 10) / 100
            t_rate = st.slider("기타비용 (%)", 0, 20, 10) / 100
        
        if st.button("🔢 판매가 일괄 재계산", type="primary", use_container_width=True):
            for p in st.session_state['products']:
                p['판매가'] = calculate_selling_price(p['원가'], m_rate, f_rate, t_rate)
            st.success("계산 완료!")
            st.rerun()
        
        st.dataframe(pd.DataFrame(st.session_state['products'])[["원본상품명", "원가", "판매가"]], use_container_width=True)

elif selected == "마켓 자동 등록":
    st.subheader("📦 쿠팡 마켓 실제 등록")
    if st.session_state['products']:
        input_df = pd.DataFrame(st.session_state['products'])
        if '선택' not in input_df.columns:
            input_df['선택'] = False

        edited_df = st.data_editor(
            input_df,
            column_config={
                "선택": st.column_config.CheckboxColumn("선택", default=False),
                "이미지URL": st.column_config.ImageColumn("이미지"),
                "판매가": st.column_config.NumberColumn("판매가", format="₩%d"),
                "상태": st.column_config.TextColumn("상태", disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            key="market_reg_editor"
        )
        
        st.session_state['products'] = edited_df.to_dict('records')
        ready = [p for p in st.session_state['products'] if p.get('선택') == True]
        
        st.divider()
        if st.button("🚀 선택 상품 쿠팡 전송", type="primary", use_container_width=True):
            if not ready:
                st.warning("등록할 상품을 먼저 선택해 주세요.")
            else:
                with st.spinner("쿠팡 서버에 전송 중..."):
                    results = bulk_register_to_coupang(ready)
                    st.success(f"{len(ready)}개 상품 처리 완료")
                    st.balloons()
                    st.rerun()
    else:
        st.warning("등록할 상품이 없습니다.")

elif selected == "API 연동 설정":
    st.subheader("⚙️ API 인증 관리")
    if os.path.exists('config.yaml'):
        st.success("✅ 설정 파일 로드 완료")
    else:
        st.error("config.yaml 파일이 없습니다.")