import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import time
import os
import yaml

# core 폴더의 함수들 불러오기
from core.collector import fetch_real_naver_products 
from core.processor import refine_products_batch, register_to_market

# 1. 페이지 설정
st.set_page_config(page_title="AutoSeller AI Pro", page_icon="☁️", layout="wide")

# 2. 세션 데이터 초기화
if 'products' not in st.session_state:
    st.session_state['products'] = []
if 'ai_chat_count' not in st.session_state:
    st.session_state['ai_chat_count'] = 0

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
    st.caption("초자동화 쇼핑몰 솔루션")
    selected = option_menu(
        None, 
        ["대시보드", "AI 자동 크롤링", "자동 가격 설정", "마켓 자동 등록", "AI 고객 응대", "API 연동 설정"],
        icons=['grid-fill', 'search', 'currency-dollar', 'cloud-arrow-up', 'chat-dots', 'gear'],
        default_index=0,
        styles={
            "container": {"background-color": "#1e293b", "padding": "5px"},
            "nav-link": {"color": "#cbd5e1", "font-size": "14px", "text-align": "left"},
            "nav-link-selected": {"background-color": "#2563eb", "color": "white"},
        }
    )
    st.divider()
    st.caption(f"👤 셀러: 장종윤 (KNUT)")

# --- 공통 함수: 상세 정보 섹션 ---
def display_selected_product(df, selection):
    if selection and "rows" in selection and selection["rows"]:
        selected_row_index = selection["rows"][0]
        p = df.iloc[selected_row_index]
        
        st.markdown("---")
        st.write("### 🔍 선택 상품 상세 정보")
        col_img, col_info = st.columns([1, 2])
        
        with col_img:
            st.image(p["이미지URL"], use_container_width=True)
            
        with col_info:
            st.write(f"#### {p['원본상품명']}")
            if p.get('AI최적화명'):
                st.info(f"✨ AI 최적화명: {p['AI최적화명']}")
            
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**💰 원가:** ₩{p['원가']:,}")
                st.write(f"**📂 카테고리:** {p['카테고리']}")
            with c2:
                st.write(f"**🏷️ 상태:** {p['상태']}")
                st.link_button("🔗 원본 상품 페이지", p["링크"])

# --- 화면별 로직 ---

if selected == "대시보드":
    st.subheader("📊 실시간 비즈니스 현황")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 수집 상품", f"{total_count:,}개")
    m2.metric("마켓 등록 완료", f"{reg_count:,}개", delta=f"{reg_count}건")
    m3.metric("AI 자동 응대", f"{st.session_state['ai_chat_count']}건")
    m4.metric("오늘의 예상 마진", f"₩{total_margin:,}")
    
    st.divider()
    
    if total_count > 0:
        df = pd.DataFrame(st.session_state['products'])
        # 표 출력 및 선택 감지
        event = st.dataframe(
            df[["이미지URL", "상태", "원본상품명", "AI최적화명", "원가"]],
            column_config={
                "이미지URL": st.column_config.ImageColumn("미리보기"),
                "원가": st.column_config.NumberColumn("원가", format="₩%d"),
            },
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        # 상세 정보 표시
        display_selected_product(df, event.get("selection"))
    else:
        st.info("데이터가 없습니다. 'AI 자동 크롤링' 메뉴에서 상품을 수집하세요.")

elif selected == "AI 자동 크롤링":
    st.subheader("🔍 실시간 네이버 상품 수집")
    
    col_in, col_bt = st.columns([3, 1])
    with col_in:
        keyword = st.text_input("수집 키워드 입력", "캠핑용품")
    with col_bt:
        st.write(" ") 
        if st.button("실시간 수집", use_container_width=True):
            with st.spinner("네이버 API에서 실시간 데이터 불러오는 중..."):
                new_data = fetch_real_naver_products(keyword, 10)
                if new_data:
                    st.session_state['products'] = new_data
                    st.rerun()

    if st.session_state['products']:
        st.divider()
        if st.button("✨ GPT-4o-mini 일괄 최적화", type="primary"):
            with st.spinner("AI가 상품명을 최적화하고 있습니다..."):
                refine_products_batch(st.session_state['products'])
            st.rerun()
        
        df = pd.DataFrame(st.session_state['products'])
        event = st.dataframe(
            df,
            column_config={
                "이미지URL": st.column_config.ImageColumn("상품이미지"),
                "링크": st.column_config.LinkColumn("네이버링크"),
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
    st.info("💡 현재 시뮬레이션 모드입니다. 상품을 클릭하여 전송 상세 내용을 확인하세요.")
    
    if st.session_state['products']:
        ready_to_reg = [p for p in st.session_state['products'] if p.get('상태') == "가공완료"]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"✅ 등록 대기: **{len(ready_to_reg)}**개")
        with col2:
            if st.button("🚀 마켓 일괄 등록 시뮬레이션", type="primary"):
                if not ready_to_reg:
                    st.warning("먼저 AI 가공을 완료해 주세요.")
                else:
                    progress_bar = st.progress(0)
                    for i, p in enumerate(st.session_state['products']):
                        if p.get('상태') == "가공완료":
                            time.sleep(0.3) 
                            p['상태'] = "등록완료"
                            p['판매가'] = int(p['원가'] * 1.2)
                        progress_bar.progress((i + 1) / len(st.session_state['products']))
                    st.balloons()
                    st.rerun()
        
        df = pd.DataFrame(st.session_state['products'])
        event = st.dataframe(
            df,
            column_config={"이미지URL": st.column_config.ImageColumn("이미지")},
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        display_selected_product(df, event.get("selection"))
    else:
        st.warning("수집된 상품이 없습니다.")

# 나머지 메뉴 생략 (이전과 동일)
elif selected == "API 연동 설정":
    st.subheader("⚙️ API 인증 관리")
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r', encoding='utf-8') as f:
            conf = yaml.safe_load(f)
            st.success(f"✅ 네이버 API: 연동됨")
            st.success(f"✅ OpenAI API: 연동됨")
    else: st.error("config.yaml 미설정")
else:
    st.info(f"{selected} 기능은 준비 중입니다.")