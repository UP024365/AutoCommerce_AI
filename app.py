import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import time
import os
import yaml

# core 폴더의 함수들 불러오기
from core.collector import fetch_real_naver_products, fetch_coupang_products 
from core.processor import refine_products_batch, register_to_market
from core.register import bulk_register_to_coupang

# 1. 페이지 설정
st.set_page_config(page_title="AutoSeller AI Pro", page_icon="☁️", layout="wide")

# 2. 세션 데이터 초기화
if 'products' not in st.session_state:
    st.session_state['products'] = []
if 'ai_chat_count' not in st.session_state:
    st.session_state['ai_chat_count'] = 0
if 'search_start' not in st.session_state:
    st.session_state['search_start'] = 1 

# 3. 실시간 통계 계산 함수
def get_stats():
    data = st.session_state['products']
    total = len(data)
    registered = sum(1 for p in data if p.get('상태') == "등록완료")
    margin = sum((p.get('판매가', 0) - p.get('원가', 0)) for p in data if p.get('상태') == "등록완료")
    return total, registered, margin

total_count, reg_count, total_margin = get_stats()

# 4. 사이드바 메뉴
with st.sidebar:
    st.title("☁️ AutoSeller AI")
    selected = option_menu(None, ["대시보드", "AI 자동 크롤링", "자동 가격 설정", "마켓 자동 등록", "API 연동 설정"], 
                           icons=['grid-fill', 'search', 'currency-dollar', 'cloud-arrow-up', 'gear'], default_index=1)
    st.caption(f"👤 셀러: 장종윤 (KNUT)")

# --- 공통 함수: 상세 정보 섹션 ---
def display_selected_product(df, selection):
    if selection and "rows" in selection and selection["rows"]:
        selected_row_index = selection["rows"][0]
        p = df.iloc[selected_row_index]
        st.markdown("---")
        st.write(f"### 🔍 상세 정보: {p['원본상품명']}")
        col_img, col_info = st.columns([1, 2])
        with col_img:
            if p["이미지URL"]:
                st.image(p["이미지URL"], width="stretch")
            else:
                st.info("이미지 없음")
        with col_info:
            st.write(f"**💰 원가:** ₩{p['원가']:,} | **🏷️ 상태:** {p['상태']}")
            if p.get('AI최적화명'):
                st.info(f"✨ AI 최적화명: {p['AI최적화명']}")
            st.link_button("🔗 상품 페이지 이동", p["링크"])

# --- 화면별 로직 ---

if selected == "대시보드":
    st.subheader("📊 비즈니스 현황")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 수집", f"{total_count:,}개")
    m2.metric("등록 완료", f"{reg_count:,}개")
    m3.metric("AI 자동 응대", f"{st.session_state['ai_chat_count']}건")
    m4.metric("오늘의 예상 마진", f"₩{total_margin:,}")
    
    if total_count > 0:
        st.divider()
        st.write("### 📦 수집된 상품 목록")
        df = pd.DataFrame(st.session_state['products'])
        st.dataframe(df[["상태", "원본상품명", "원가", "카테고리"]], use_container_width=True, hide_index=True)

elif selected == "AI 자동 크롤링":
    st.subheader("🔍 실시간 타사 상품 수집")
    
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        keyword = st.text_input("수집 키워드", "캠핑용품")
    with c2:
        sort_type = st.selectbox("정렬", ["최신순", "가격 낮은순", "가격 높은순"])
    with c3:
        st.write(" ")
        if st.button("🔄 초기화", use_container_width=True):
            st.session_state['products'] = []
            st.session_state['search_start'] = 1
            st.rerun()

    # 상품 수집 버튼
    if st.button("🚀 상품 10개 더 가져오기 (중복 제거)", type="primary", use_container_width=True):
        with st.spinner("새로운 상품 불러오는 중..."):
            new_data = fetch_real_naver_products(keyword, 10, start=st.session_state['search_start'])
            
            if new_data:
                existing_links = [p['링크'] for p in st.session_state['products']]
                unique_new_data = [p for p in new_data if p['링크'] not in existing_links]
                
                st.session_state['products'].extend(unique_new_data)
                st.session_state['search_start'] += 10
                
                if not unique_new_data:
                    st.warning("이미 모든 상품이 수집되었습니다. 다음 페이지를 시도하려면 다시 누르세요.")
                else:
                    st.success(f"신규 상품 {len(unique_new_data)}개를 추가했습니다. (총 {len(st.session_state['products'])}개)")
                st.rerun()

    # 수집 데이터 출력
    if st.session_state['products']:
        st.divider()
        df = pd.DataFrame(st.session_state['products'])
        
        # 정렬 로직 적용
        if sort_type == "가격 낮은순":
            df = df.sort_values(by="원가")
        elif sort_type == "가격 높은순":
            df = df.sort_values(by="원가", ascending=False)
        
        # 최적화 버튼
        if st.button("✨ GPT-4o-mini 일괄 최적화 (현재 목록)", type="secondary"):
            with st.spinner("AI가 상품명을 최적화하고 있습니다..."):
                refine_products_batch(st.session_state['products'])
            st.rerun()

        # 데이터프레임 (하나로 통합)
        event = st.dataframe(
            df,
            column_config={
                "이미지URL": st.column_config.ImageColumn("상품이미지"),
                "링크": st.column_config.LinkColumn("링크"),
                "원가": st.column_config.NumberColumn("원가", format="₩%d"),
            },
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        display_selected_product(df, event.get("selection"))

elif selected == "마켓 자동 등록":
    st.subheader("📦 마켓 자동 등록 (Coupang API 연동)")
    
    if st.session_state['products']:
        ready_to_reg = [p for p in st.session_state['products'] if p.get('상태') in ["가공완료", "수집완료", "쿠팡수집", "승인완료"]]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"✅ 등록 대기: **{len(ready_to_reg)}**개")
        with col2:
            if st.button("🚀 마켓 일괄 등록 시뮬레이션", type="primary", use_container_width=True):
                if not ready_to_reg:
                    st.warning("등록 가능한 대기 상품이 없습니다. 먼저 상품 가공을 완료하세요.")
                else:
                    progress_bar = st.progress(0)
                    for i, p in enumerate(st.session_state['products']):
                        time.sleep(0.1) 
                        p['상태'] = "등록완료"
                        p['판매가'] = int(p.get('원가', 10000) * 1.2)
                        progress_bar.progress((i + 1) / len(st.session_state['products']))
                    st.balloons()
                    st.rerun()
        
        df = pd.DataFrame(st.session_state['products'])
        event = st.dataframe(
            df,
            column_config={
                "이미지URL": st.column_config.ImageColumn("이미지"),
                "원가": st.column_config.NumberColumn("원가", format="₩%d"),
            },
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        display_selected_product(df, event.get("selection"))
    else:
        st.warning("수집된 상품이 없습니다. 'AI 자동 크롤링' 메뉴에서 상품을 수집하세요.")

elif selected == "API 연동 설정":
    st.subheader("⚙️ API 인증 관리")
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r', encoding='utf-8') as f:
            conf = yaml.safe_load(f)
            st.success(f"✅ 네이버 API: 연동됨 (ID: {conf.get('naver_client_id')})")
            st.success(f"✅ OpenAI API: 연동됨")
            if conf.get('coupang_access_key'):
                st.success(f"✅ 쿠팡 API: 연동됨 (업체코드: {conf.get('coupang_vendor_id')})")
            else:
                st.warning("⚠️ 쿠팡 API 키 정보가 부족합니다.")
    else: 
        st.error("config.yaml 파일이 존재하지 않습니다.")